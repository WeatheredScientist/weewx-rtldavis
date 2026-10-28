"""#459 / DEC-0223: the burst-gate patch drops only second decodes of one burst.

The owner's requirement for decoder changes (DEC-0216): rigorous testing, and no
false positives that kill good packets. This patch DOES drop frames, so unlike the
crcstats patch it cannot be proved harmless by construction. These tests make its
reach a checked property instead:

  1. STATIC: the patch touches only main.go and the new burstgate/ package; it
     removes exactly two lines (the loop header, which gains an index, and the
     duplicate log line, which gains the gap in samples) and every line it adds to
     main.go is on an allow-list. The only new drops are the two burst checks, each
     a log line and a `continue`, placed after the duplicate filter and before the
     accept. A positive control proves the audit rejects a patch that adds control
     flow.
  2. DYNAMIC (needs `go` and network once): the patch applies after dupgate and
     crcstats to the pinned source; the gate's Go tests pass, including a replay of
     synthetic bursts through the real Demodulate and Parse; where librtlsdr headers
     exist the whole program builds.
"""
import os
import re
import shutil
import subprocess
import tempfile

import pytest

from test_crcstats_patch import _pinned_tree, DUPGATE, PATCH as CRCSTATS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH = os.path.join(ROOT, "patch", "rtldavis-burstgate.patch")
GO_TESTS = [os.path.join(ROOT, "tests", "go", f)
            for f in ("burstgate_test.go", "burst_replay_test.go")]

REMOVED_OK = [
    "            for _, msg := range parsed {",
    '                    log.Printf("duplicate packet: %02X (%.3f s)", msg.Data, '
    'float64(curTime - lastRecTime) / float64(time.Second))',
]
ADDED_OK = [
    r'\s*"lheijst/rtldavis/burstgate"$',
    r'\s*burstG\s+\*burstgate\.Gate\s*(//.*)?$',
    r'\s*blockNum\s+int64\s*(//.*)?$',
    r'\s*burstG = burstgate\.New\(int64\(p\.Cfg\.PreambleLength \+ p\.Cfg\.PacketLength\)\)$',
    r'\s*log\.Printf\("burstWindow=%d samples", burstG\.Window\(\)\)$',
    r'\s*blockNum\+\+$',
    r'\s*burstPos := make\(\[\]int64, len\(parsed\)\)$',
    r'\s*for i, msg := range parsed \{$',
    r'\s*burstPos\[i\] = burstgate\.Pos\(blockNum, p\.Cfg\.BlockSize, msg\.Idx\)$',
    r'\s*\}$',
    r'\s*burstConflict := burstG\.Conflicts\(burstPos\)$',
    r'\s*log\.Printf\("duplicate packet: %02X \(%\.3f s\) \(\+%d smp\)", msg\.Data, '
    r'float64\(curTime - lastRecTime\) / float64\(time\.Second\), burstG\.Gap\(burstPos\[i\]\)\)$',
    r'\s*if burstConflict\[i\] >= 0 \{$',
    r'\s*log\.Printf\("burst conflict: %02X \(\+%d smp\)", msg\.Data, burstConflict\[i\]\)$',
    r'\s*if burstG\.Copy\(burstPos\[i\]\) \{$',
    r'\s*log\.Printf\("burst copy: %02X \(\+%d smp\)", msg\.Data, burstG\.Gap\(burstPos\[i\]\)\)$',
    r'\s*continue  // read next message$',
    r'\s*burstG\.Accept\(burstPos\[i\]\)$',
]


def audit(patch_text):
    """Return a list of violations in a unified diff."""
    problems, current = [], None
    for line in patch_text.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            if current not in ("b/main.go", "b/burstgate/burstgate.go"):
                problems.append("touches %s" % current)
            continue
        if line.startswith("--- ") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            if line[1:] not in REMOVED_OK:
                problems.append("removes: %r" % line[1:])
        elif line.startswith("+") and current == "b/main.go":
            body = line[1:]
            if not body.strip() or body.strip().startswith("//"):
                continue
            if not any(re.fullmatch(p, body) for p in ADDED_OK):
                problems.append("adds to main.go: %r" % body)
    return problems


def test_patch_touches_only_main_and_the_gate_and_adds_only_listed_lines():
    assert audit(open(PATCH).read()) == []


def test_exactly_two_new_drops_both_logged():
    added = [ln[1:] for ln in open(PATCH).read().split("+++ b/main.go", 1)[1].splitlines()
             if ln.startswith("+")]
    assert sum("continue" in ln for ln in added) == 2
    assert sum("nextHop" in ln or "loopTimer" in ln for ln in added) == 0


def test_audit_rejects_control_flow_and_other_files():
    """POSITIVE CONTROL: the checker must fail on what it guards."""
    bad = ("--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n"
           "+                if msg.ID == 3 { continue }\n")
    assert any("adds to main.go" in p for p in audit(bad))
    bad2 = ("--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n"
            "-                    continue  // read next message\n")
    assert any("removes" in p for p in audit(bad2))
    bad3 = ("--- a/vendor/x/protocol.go\n+++ b/vendor/x/protocol.go\n@@ -1 +1 @@\n+x\n")
    assert any("touches" in p for p in audit(bad3))


# --- dynamic -------------------------------------------------------------------

def _patched(tmp):
    d = _pinned_tree(tmp)
    for p in (DUPGATE, CRCSTATS, PATCH):
        r = subprocess.run(["patch", "-p1", "--batch", "--forward", "-i", p], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, p + "\n" + r.stdout + r.stderr
    return d


def test_checks_run_in_the_order_the_replay_mirrors():
    """burst_replay_test.go's gateRun mirrors main.go: duplicate filter, then burst
    conflict, then burst copy, then accept. Pin that order in the patched main.go."""
    with tempfile.TemporaryDirectory() as tmp:
        main = open(os.path.join(_patched(tmp), "main.go")).read()
        order = [main.index(s) for s in (
            "burstConflict := burstG.Conflicts(burstPos)",
            "if seen == lastRecMsg && curTime - lastRecTime <",
            "if burstConflict[i] >= 0 {",
            "if burstG.Copy(burstPos[i]) {",
            "lastRecTime = curTime",
            "burstG.Accept(burstPos[i])",
        )]
        assert order == sorted(order)
        assert main.count("burstG") == 8  # the Dockerfile guard asserts the same
        assert main.count("crcT") == 4    # crcstats' lines are untouched


def test_patch_applies_after_crcstats_and_gate_tests_pass():
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        for f in GO_TESTS:
            shutil.copy(f, os.path.join(d, "burstgate", os.path.basename(f)))
        r = subprocess.run(["go", "test", "-mod=vendor", "-count=1", "-v", "./burstgate"], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "decoded from two blocks" in r.stdout  # the replay ran and straddled


def test_whole_program_builds_where_librtlsdr_is_available():
    if shutil.which("pkg-config") is None or subprocess.run(
            ["pkg-config", "--exists", "librtlsdr"]).returncode != 0:
        pytest.skip("librtlsdr development files not installed (the Docker build covers this)")
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        r = subprocess.run(["go", "build", "-mod=vendor", "-o", os.devnull, "."], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
