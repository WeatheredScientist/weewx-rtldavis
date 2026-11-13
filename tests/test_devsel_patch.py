"""ops#440 / DEC-0235: the device-selection patch opens the dongle -d names.

Upstream parsed -d and then opened index 0 regardless. This patch changes which
dongle the decoder opens, so its reach is checked like the other decoder patches:

  1. STATIC: the patch touches only main.go and the new devsel/ package; every line
     it removes from main.go is upstream's ignored lookup (and the `strconv` import
     only it used), and every line it adds is on an allow-list. No line touches the
     demodulator, the hop loop or the packet path. A positive control proves the
     audit rejects anything else. The Dockerfile's guard and this file assert the
     same counts.
  2. DYNAMIC (needs `go` and network once): the patch applies after the other four
     to the pinned source; devsel's Go tests pass against tests/go/devsel_cases.json;
     where librtlsdr headers exist the whole program builds.
"""
import os
import re
import shutil
import subprocess
import tempfile

from test_burstgate_patch import PATCH as BURSTGATE
from test_crcstats_patch import _pinned_tree, skip_or_fail, DUPGATE, PATCH as CRCSTATS
from test_timegate_patch import PATCH as TIMEGATE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH = os.path.join(ROOT, "patch", "rtldavis-devsel.patch")
GO = os.path.join(ROOT, "tests", "go")
DOCKERFILE = os.path.join(ROOT, "Dockerfile")

REMOVED_OK = [
    '    "strconv"',
    '    // First attempt to open the device as a Serial Number',
    '    sdrIndex , _ = rtlsdr.GetIndexBySerial(*deviceString)',
    '    if (sdrIndex <0 ) {',
    '        indexreturn,err := strconv.Atoi(*deviceString)',
    '        if (err != nil) {',
    '          log.Printf("Could not parse device\\n")',
    '          log.Fatal(err)',
    '        }',
    '        sdrIndex = indexreturn',
    '    }',
    '    dev, err := rtlsdr.Open(0)',
]
ADDED_OK = [
    r'\s*"lheijst/rtldavis/devsel"$',
    r'\s*dongles := make\(\[\]devsel\.Dongle, rtlsdr\.GetDeviceCount\(\)\)$',
    r'\s*for i := range dongles \{$',
    r'\s*dongles\[i\]\.Manufacturer, dongles\[i\]\.Product, dongles\[i\]\.Serial, _ = '
    r'rtlsdr\.GetDeviceUsbStrings\(i\)$',
    r'\s*\}$',
    r'\s*dGiven := false$',
    r'\s*flag\.Visit\(func\(f \*flag\.Flag\) \{ dGiven = dGiven \|\| f\.Name == "d" \}\)$',
    r'\s*sdrIndex, dWarn, err := devsel\.Pick\(\*deviceString, dGiven, dongles\)$',
    r'\s*if err != nil \{$',
    r'\s*log\.Fatal\(err\)$',
    r'\s*if dWarn != "" \{$',
    r'\s*log\.Print\(dWarn\)$',
    r'\s*log\.Print\(devsel\.Describe\(sdrIndex, dongles\)\)$',
    r'\s*dev, err := rtlsdr\.Open\(sdrIndex\)$',
]


def audit(patch_text):
    """Return a list of violations in a unified diff."""
    problems, current = [], None
    for line in patch_text.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            if current not in ("b/main.go", "b/devsel/devsel.go"):
                problems.append("touches %s" % current)
            continue
        if line.startswith("--- ") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            if current != "b/main.go" or line[1:] not in REMOVED_OK:
                problems.append("removes from %s: %r" % (current, line[1:]))
        elif line.startswith("+") and current == "b/main.go":
            body = line[1:]
            if not body.strip() or body.strip().startswith("//"):
                continue
            if not any(re.fullmatch(p, body) for p in ADDED_OK):
                problems.append("adds to main.go: %r" % body)
    return problems


def test_patch_touches_only_the_listed_files_and_lines():
    assert audit(open(PATCH).read()) == []


def test_upstreams_ignored_open_is_the_line_replaced():
    text = open(PATCH).read()
    assert "-    dev, err := rtlsdr.Open(0)" in text
    assert "+    dev, err := rtlsdr.Open(sdrIndex)" in text


def test_audit_rejects_other_files_and_lines():
    """POSITIVE CONTROL: the checker must fail on what it guards."""
    bad = "--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n+    nextHop <- p.SetHop(0, 0)\n"
    assert any("adds to main.go" in p for p in audit(bad))
    bad2 = "--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n-                    continue  // read next message\n"
    assert any("removes" in p for p in audit(bad2))
    bad3 = "--- a/vendor/x/protocol.go\n+++ b/vendor/x/protocol.go\n@@ -1 +1 @@\n+x\n"
    assert any("touches" in p for p in audit(bad3))


def test_the_dockerfile_guards_the_same_counts():
    text = open(DOCKERFILE).read()
    assert "COPY patch/rtldavis-devsel.patch /tmp/rtldavis-devsel.patch" in text
    assert text.index("rtldavis-timegate.patch &&") < text.index("rtldavis-devsel.patch &&")
    assert "test \"$(grep -c 'rtlsdr\\.Open(sdrIndex)' main.go)\" = \"1\"" in text
    assert "test \"$(grep -c 'rtlsdr\\.Open(0)' main.go)\" = \"0\"" in text
    assert "test \"$(grep -c 'devsel\\.' main.go)\" = \"3\"" in text


# --- dynamic -------------------------------------------------------------------

def _patched(tmp):
    d = _pinned_tree(tmp)
    for p in (DUPGATE, CRCSTATS, BURSTGATE, TIMEGATE, PATCH):
        r = subprocess.run(["patch", "-p1", "--batch", "--forward", "-i", p], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, p + "\n" + r.stdout + r.stderr
    return d


def test_patched_main_opens_the_picked_index_and_matches_the_dockerfile_guard():
    with tempfile.TemporaryDirectory() as tmp:
        main = open(os.path.join(_patched(tmp), "main.go")).read()
        assert main.count("rtlsdr.Open(sdrIndex)") == 1
        assert main.count("rtlsdr.Open(0)") == 0
        assert main.count("devsel.") == 3
        assert main.count("timegate.O") == 2 and main.count("burstG") == 8
        assert main.count("crcT") == 5 and main.count("dupwindow") == 2
        # Picked before the dongle is opened, and logged before anything is tuned.
        assert (main.index("devsel.Pick(") < main.index("devsel.Describe(")
                < main.index("rtlsdr.Open(sdrIndex)") < main.index("dev.SetCenterFreq("))


def test_patch_applies_after_the_others_and_devsel_tests_pass():
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        for f in ("devsel_test.go", "devsel_cases.json"):
            shutil.copy(os.path.join(GO, f), os.path.join(d, "devsel"))
        r = subprocess.run(["go", "test", "-mod=vendor", "-count=1", "-v", "./devsel"], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "TestTheSharedCaseTable" in r.stdout and "FAIL" not in r.stdout


def test_whole_program_builds_where_librtlsdr_is_available():
    if shutil.which("pkg-config") is None or subprocess.run(
            ["pkg-config", "--exists", "librtlsdr"]).returncode != 0:
        skip_or_fail("librtlsdr development files not installed (the Docker build covers this)")
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        r = subprocess.run(["go", "build", "-mod=vendor", "-o", os.devnull, "."], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
