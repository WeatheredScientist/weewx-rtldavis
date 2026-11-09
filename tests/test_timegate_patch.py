"""#536 / DEC-0229: the time-gate patch drops only frames off their schedule.

The owner's requirement for decoder changes (DEC-0216): rigorous testing, and no
false positives that kill good packets. Like the burst gate, this patch drops frames,
so its reach has to be a checked property:

  1. STATIC: the patch touches only main.go, crcstat/crcstat.go and the new timegate/
     package; main.go loses no line and every line it gains is on an allow-list; the
     only new drop is a log line and a `continue`, placed after the burst gate and
     before the accept, inside a check that init and undefined IDs skip. A positive
     control proves the audit rejects a patch that adds control flow.
  2. DYNAMIC (needs `go` and network once): the patch applies after the other three
     to the pinned source; the gate's Go tests pass, including a replay of synthetic
     frames through the real Demodulate and Parse; where librtlsdr headers exist the
     whole program builds.
"""
import os
import re
import shutil
import subprocess
import tempfile

from rtldavis import parse_crc_stats
from test_burstgate_patch import PATCH as BURSTGATE
from test_crcstats_patch import _pinned_tree, skip_or_fail, DUPGATE, PATCH as CRCSTATS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATCH = os.path.join(ROOT, "patch", "rtldavis-timegate.patch")
GO = os.path.join(ROOT, "tests", "go")

REMOVED_OK = [
    '\tline := fmt.Sprintf("crc_stats: crc_fail=%d near=%d slots=%s", t.fails, t.near, '
    'strings.Join(slots, ","))',
    '\t\tline = fmt.Sprintf("crc_stats: crc_fail=%d near=%d slots=-", t.fails, t.near)',
    '\tt.fails, t.near, t.perSlot = 0, 0, [crcSlots]int{}',
]
ADDED_OK = [
    r'\s*"lheijst/rtldavis/timegate"$',
    r'\s*tolerance\s+int\s*(//.*)?$',
    r'\s*flag\.IntVar\(&tolerance, "tolerance", 100, ".*"\)$',
    r'\s*log\.Printf\("tolerance=%d ms", tolerance\)$',
    r'\s*nextHopChan = 0\s*(//.*)?$',
    r'\s*if ch := msgIdToChan\[int\(msg\.ID\)\]; !initTransmitrs && ch != 9 \{$',
    r'\s*offset := timegate\.Offset\(curTime, chLastVisits\[ch\], '
    r'int64\(idLoopPeriods\[actChan\[ch\]\]\)\)$',
    r'\s*if timegate\.Off\(offset, int64\(tolerance\) \* int64\(time\.Millisecond\)\) \{$',
    r'\s*crcT\.OffSched\(\)$',
    r'\s*log\.Printf\("offschedule packet: %02X \(%\+\.1f ms\)", msg\.Data, '
    r'float64\(offset\) / float64\(time\.Millisecond\)\)$',
    r'\s*continue  // read next message$',
    r'\s*\}$',
]


def audit(patch_text):
    """Return a list of violations in a unified diff."""
    problems, current = [], None
    for line in patch_text.splitlines():
        if line.startswith("+++ "):
            current = line[4:].strip()
            if current not in ("b/main.go", "b/crcstat/crcstat.go", "b/timegate/timegate.go"):
                problems.append("touches %s" % current)
            continue
        if line.startswith("--- ") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            if line[1:] not in REMOVED_OK:
                problems.append("removes: %r" % line[1:])
            elif current != "b/crcstat/crcstat.go":
                problems.append("removes from %s: %r" % (current, line[1:]))
        elif line.startswith("+") and current == "b/main.go":
            body = line[1:]
            if not body.strip() or body.strip().startswith("//"):
                continue
            if not any(re.fullmatch(p, body) for p in ADDED_OK):
                problems.append("adds to main.go: %r" % body)
    return problems


def test_patch_touches_only_the_listed_files_and_adds_only_listed_lines():
    assert audit(open(PATCH).read()) == []


def test_exactly_one_new_drop_and_no_new_hop():
    added = [ln[1:] for ln in open(PATCH).read().split("+++ b/main.go", 1)[1].splitlines()
             if ln.startswith("+")]
    assert sum("continue" in ln for ln in added) == 1
    assert sum("nextHop <-" in ln or "loopTimer" in ln or "HandleNextHopChannel" in ln
               for ln in added) == 0


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
    bad4 = ("--- a/main.go\n+++ b/main.go\n@@ -1 +1 @@\n"
            "-\tt.fails, t.near, t.perSlot = 0, 0, [crcSlots]int{}\n")
    assert any("removes from" in p for p in audit(bad4))


def test_the_driver_parses_the_line_go_prints():
    """Go's format string and the driver's regex are two sides of one contract."""
    text = open(PATCH).read()
    formats = re.findall(r'^\+\s*line :?= fmt\.Sprintf\("(crc_stats: [^"]+)"', text, re.M)
    assert len(formats) == 2
    for fmt in formats:
        line = fmt.replace("%d", "3").replace("%s", "17:3")
        assert parse_crc_stats(line) == (3, 3, 3, {17: 3} if "17:3" in line else {})


# --- dynamic -------------------------------------------------------------------

def _patched(tmp):
    d = _pinned_tree(tmp)
    for p in (DUPGATE, CRCSTATS, BURSTGATE, PATCH):
        r = subprocess.run(["patch", "-p1", "--batch", "--forward", "-i", p], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, p + "\n" + r.stdout + r.stderr
    return d


def test_the_gate_sits_after_the_burst_gate_and_before_anything_is_booked():
    """timegate_replay_test.go's timeRun mirrors main.go: duplicate filter, burst
    conflict, burst copy, time gate, accept. Pin that order in the patched main.go,
    and that the re-init branch resets the slot label."""
    with tempfile.TemporaryDirectory() as tmp:
        main = open(os.path.join(_patched(tmp), "main.go")).read()
        order = [main.index(s) for s in (
            "if seen == lastRecMsg && curTime - lastRecTime <",
            "if burstConflict[i] >= 0 {",
            "if burstG.Copy(burstPos[i]) {",
            "; !initTransmitrs && ch != 9 {",
            "crcT.OffSched()",
            "lastRecMsg = seen",
            "lastRecTime = curTime",
            "crcT.Accept(curTime)",
            "burstG.Accept(burstPos[i])",
            "chAlarmCnts[msgIdToChan[int(msg.ID)]] = 0",
            "chLastVisits[msgIdToChan[int(msg.ID)]] = curTime",
        )]
        assert order == sorted(order)
        assert main.count("timegate.O") == 2  # the Dockerfile guard asserts the same
        assert main.count("burstG") == 8     # the burst gate's lines are untouched
        assert main.count("crcT") == 5       # crcstats' four, plus OffSched
        reinit = main.index("totInit++")
        assert reinit < main.index("nextHopChan = 0") < main.index("nextHop <- p.SetHop(0, 0)", reinit)


def test_patch_applies_after_the_others_and_gate_tests_pass():
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        shutil.copy(os.path.join(GO, "timegate_test.go"), os.path.join(d, "timegate"))
        shutil.copy(os.path.join(GO, "timegate_crcstat_test.go"), os.path.join(d, "crcstat"))
        for f in ("burst_replay_test.go", "burstgate_test.go", "timegate_replay_test.go"):
            shutil.copy(os.path.join(GO, f), os.path.join(d, "burstgate"))
        r = subprocess.run(["go", "test", "-mod=vendor", "-count=1", "-v",
                            "./timegate", "./crcstat", "./burstgate"], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "TestANoiseDecodeIsDroppedAndTheStationStaysOnSchedule" in r.stdout
        assert "TestOffSchedIsReportedAndResets" in r.stdout


def test_whole_program_builds_where_librtlsdr_is_available():
    if shutil.which("pkg-config") is None or subprocess.run(
            ["pkg-config", "--exists", "librtlsdr"]).returncode != 0:
        skip_or_fail("librtlsdr development files not installed (the Docker build covers this)")
    with tempfile.TemporaryDirectory() as tmp:
        d = _patched(tmp)
        r = subprocess.run(["go", "build", "-mod=vendor", "-o", os.devnull, "."], cwd=d,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
