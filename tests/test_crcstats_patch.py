"""#458 safety net: the CRC-statistics patch must be measurement only.

The owner's requirement: no false positives that kill good data packets. This patch
cannot drop a packet by construction (no accept/drop/hop decision reads the tracker);
these tests make that a checked property instead of a promise:

  1. STATIC: the patch removes exactly one line (the loop header that is rewritten to
     take Parse's result first), and every line it adds to main.go / protocol.go is on
     an allow-list of counter and log statements. A checker positive control proves
     the checker rejects a patch that adds control flow.
  2. DYNAMIC (needs `go` and network once): the patch applies after dupgate to the
     pinned source, the tracker's Go tests pass (including a brute-force oracle), and
     where librtlsdr headers exist the whole program still builds.
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH = os.path.join(ROOT, "patch", "rtldavis-crcstats.patch")
DUPGATE = os.path.join(ROOT, "patch", "rtldavis-dupgate.patch")
GO_TEST = os.path.join(ROOT, "tests", "go", "crcstat_test.go")
SRC_URL = ("https://github.com/weewx-contrib/weewx-rtldavis/raw/"
           "bfa9e3d9e1a9fc198fcf81124b709d63d8c30a1f/src.tgz")
SRC_SHA = "7c1a7de1923d2c96844adfba51ec0497f5e8f0a629cc3a6ba64a86d62f26e368"

REMOVED_OK = ["            for _, msg := range p.Parse(p.Demodulate(block)) {"]
# Lines the patch may ADD to existing files (comments and blanks are always fine).
ADDED_OK = [
    r'\s*"time"$',
    r'\s*"lheijst/rtldavis/crcstat"$',
    r'\s*CRCFailTimes \[\]int64$',
    r'\s*if len\(p\.CRCFailTimes\) < 1024 \{$',
    r'\s*p\.CRCFailTimes = append\(p\.CRCFailTimes, time\.Now\(\)\.UnixNano\(\)\)$',
    r'\s*\}$',
    r'\s*parsed := p\.Parse\(p\.Demodulate\(block\)\)$',
    r'\s*for _, ft := range p\.CRCFailTimes \{$',
    r'\s*crcT\.Fail\(ft, nextHopChan\)$',
    r'\s*p\.CRCFailTimes = p\.CRCFailTimes\[:0\]$',
    r'\s*if line, ok := crcT\.Report\(time\.Now\(\)\.UnixNano\(\)\); ok \{$',
    r'\s*log\.Print\(line\)$',
    r'\s*for _, msg := range parsed \{$',
    r'\s*crcT\.Accept\(curTime\)$',
    r'\s*crcT\s+= crcstat\.New\(.*\)\s*(//.*)?$',
]


def audit(patch_text):
    """Return a list of violations in a unified diff."""
    problems, current = [], None
    for line in patch_text.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            continue
        if line.startswith("--- ") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            if line[1:] not in REMOVED_OK:
                problems.append("removes: %r" % line[1:])
        elif line.startswith("+") and current and not current.endswith("crcstat/crcstat.go"):
            body = line[1:]
            if not body.strip() or body.strip().startswith("//"):
                continue
            if not any(re.fullmatch(p, body) for p in ADDED_OK):
                problems.append("adds to %s: %r" % (current, body))
    return problems


def test_patch_removes_one_line_and_adds_only_counters():
    assert audit(open(PATCH).read()) == []


def test_audit_rejects_a_patch_that_adds_control_flow():
    """POSITIVE CONTROL: the checker must actually fail on the thing it guards."""
    bad = ("--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n"
           "-            for _, msg := range p.Parse(p.Demodulate(block)) {\n"
           "+            for _, msg := range parsed {\n"
           "+                if crcT.Near() { continue }\n")
    assert any("continue" in p for p in audit(bad))
    bad2 = ("--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n"
            "-                    continue  // read next message\n")
    assert any("removes" in p for p in audit(bad2))


def test_accept_and_drop_lines_of_the_data_path_are_untouched():
    text = open(PATCH).read()
    for must_survive in ("lastRecMsg", "dupWindow", "nextHop <-", "chLastVisits", "msgIdToChan"):
        for line in text.splitlines():
            assert not (line.startswith("-") and must_survive in line), line


# --- dynamic: apply to the pinned source, run the Go tests -------------------

def _pinned_tree(tmp):
    if shutil.which("go") is None or shutil.which("patch") is None:
        pytest.skip("go/patch not installed")
    cache = os.path.join(tempfile.gettempdir(), "rtldavis-src-%s.tgz" % SRC_SHA[:12])
    if not os.path.exists(cache):
        try:
            data = urllib.request.urlopen(SRC_URL, timeout=60).read()
        except Exception as exc:  # offline
            pytest.skip("cannot fetch pinned source: %s" % exc)
        assert hashlib.sha256(data).hexdigest() == SRC_SHA, "pinned source changed"
        open(cache, "wb").write(data)
    subprocess.run(["tar", "zxf", cache, "-C", tmp], check=True)
    return os.path.join(tmp, "src", "rtldavis", "src", "lheijst", "rtldavis")


def _patched(tmp):
    d = _pinned_tree(tmp)
    for p in (DUPGATE, PATCH):
        r = subprocess.run(["patch", "-p1", "--batch", "--forward", "-i", p], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
    return d


def test_patch_applies_after_dupgate_and_tracker_tests_pass():
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        shutil.copy(GO_TEST, os.path.join(d, "crcstat", "crcstat_test.go"))
        r = subprocess.run(["go", "test", "-mod=vendor", "-count=1", "./crcstat"], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        main = open(os.path.join(d, "main.go")).read()
        assert main.count("crcT") == 4  # the Dockerfile guard asserts the same


def test_whole_program_still_builds_where_librtlsdr_is_available():
    if shutil.which("pkg-config") is None or subprocess.run(
            ["pkg-config", "--exists", "librtlsdr"]).returncode != 0:
        pytest.skip("librtlsdr development files not installed (the Docker build covers this)")
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        r = subprocess.run(["go", "build", "-mod=vendor", "-o", os.devnull, "."], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# --- dynamic: real Parse, patched vs unpatched ---------------------------------

PROBE = os.path.join(ROOT, "tests", "go", "parse_diff_test.go")
PROTO = os.path.join("vendor", "github.com", "lheijst", "rtldavis", "protocol")


def _probe(tree, tmp):
    shutil.copy(PROBE, os.path.join(tree, PROTO, "parse_diff_test.go"))
    out = os.path.join(tmp, "parse_%s.txt" % os.path.basename(tree))
    env = dict(os.environ, PARSE_OUT=out)
    r = subprocess.run(["go", "test", "-mod=vendor", "-count=1", "./" + PROTO.replace(os.sep, "/")],
                       cwd=tree, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return open(out).read().splitlines()


def _messages(lines):
    return [ln for ln in lines if not ln.startswith("FAILS")]


def test_parse_accepts_exactly_what_it_accepted_before():
    """The owner's requirement, tested on the real Parse: for valid, bit-flipped and
    duplicate frames the patched Parse returns byte-identical messages to the
    unpatched one, and counts only the CRC failures."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "a"))
        os.makedirs(os.path.join(tmp, "b"))
        base = _pinned_tree(os.path.join(tmp, "a"))
        patched = _patched(os.path.join(tmp, "b"))
        before, after = _probe(base, tmp), _probe(patched, tmp)
        assert _messages(before) == _messages(after)
        assert any(m.startswith("case0 msg") for m in _messages(after)), "probe accepted nothing"
        fails = [ln for ln in after if ln.startswith("FAILS")]
        assert fails == ["FAILS case0 1", "FAILS case1 1", "FAILS case2 2", "FAILS case3 0"]


def test_probe_detects_a_parse_that_lets_bad_frames_through():
    """POSITIVE CONTROL: a patched tree whose CRC failure no longer `continue`s must
    produce different messages -- otherwise the comparison above proves nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "a"))
        os.makedirs(os.path.join(tmp, "b"))
        base = _pinned_tree(os.path.join(tmp, "a"))
        mutant = _patched(os.path.join(tmp, "b"))
        proto = os.path.join(mutant, PROTO, "protocol.go")
        src = open(proto).read()
        needle = "\t\t\t}\n\t\t\tcontinue\n\t\t}\n"
        assert src.count(needle) == 1
        open(proto, "w").write(src.replace(needle, "\t\t\t}\n\t\t}\n"))
        assert _messages(_probe(base, tmp)) != _messages(_probe(mutant, tmp))
