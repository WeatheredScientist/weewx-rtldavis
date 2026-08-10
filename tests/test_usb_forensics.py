"""Offline tests for the S68 reset-forensics capture (BOOT blocker 4, DEC-0074).

The USB resets fire and do not work -- 3/3 on 2026-08-06, 9/9 on 2026-08-02 --
and the hypothesis (the reset treats the DEVICE while the fault is the CONSUMER's
grip on it) is explicitly not established. ops/usb_forensics.sh exists to settle
it at the next stall. These tests pin the three properties that decide whether
that capture is trustworthy when it finally fires, since the event is ~1/day and
unpredictable and there is no second chance to get it right:

  1. It never captures /proc/<pid>/environ. A capture file that a later session
     reads with `nasctl cat` lands in a Claude transcript in plaintext -- the
     transcript is an egress path (DEC-0047), and container env is where the
     credentials are.
  2. It can never prevent a reset. The reset is the remedy; the capture is only
     evidence about it. usb_reset.sh must still unbind/rebind if the capture is
     missing, unreadable, or broken.
  3. It runs to completion and writes a file even when every path it wants is
     absent. This one is executed for real against a machine with no /proc and
     no /sys, which is the strongest available stand-in for "the capture fired
     during an outage and half the reads failed."

Run:  .venv/bin/python -m pytest tests/test_usb_forensics.py
"""
import os
import subprocess
import sys
import tempfile

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORENSICS = os.path.join(REPO, "ops", "usb_forensics.sh")
RESET = os.path.join(REPO, "usb_reset.sh")


def _read(path):
    with open(path) as f:
        return f.read()


def _code(path):
    """Executable lines only -- comments stripped.

    These scripts DOCUMENT the things they must never do, in prose, at length.
    A naive substring scan over the whole file therefore matches the warning
    against the practice and reports the practice itself, which is how the first
    draft of these tests failed: the ban on /proc/<pid>/environ is spelled out in
    the header, and the scanner found that sentence.
    """
    return [ln for ln in _read(path).splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


# --- 1. the egress guard ---

def test_forensics_never_reads_environ():
    """/proc/<pid>/environ is where a container's credentials live, and these
    capture files are read back through a Claude session (DEC-0047)."""
    assert not any("environ" in ln for ln in _code(FORENSICS))


def test_forensics_dumps_no_environment():
    """The same hole by another spelling: `printenv`, or `docker inspect` (whose
    output carries Config.Env) would each land credentials in a file we intend to
    read back."""
    code = _code(FORENSICS)
    for banned in ("printenv", "docker inspect"):
        assert not any(banned in ln for ln in code)


def test_forensics_does_not_use_proc_dir_mtime_as_start_time():
    """Measured on the NAS 2026-08-09: `stat -c %y /proc/<pid>` reported 17
    seconds for an rtldavis that had been up 2.88 days by /proc/<pid>/stat field
    22, on a container up 3 days with unbroken output. That directory's mtime
    tracks ACCESS, and this script reads several files under it moments before.

    In a stall capture the wrong version would have reported "rtldavis just
    restarted" about a process that never did -- a fabricated event in the one
    artifact meant to settle the question. So the age must come from field 22,
    and any use of the proc-dir mtime must be labelled as access time.
    """
    code = _code(FORENSICS)
    stat_mtime = [ln for ln in code if 'stat -c %y "/proc/' in ln]
    for line in stat_mtime:
        assert "proc-dir-mtime" in line and "NOT start" in line, \
            "proc-dir mtime may only appear labelled as access time"
    assert any("/stat" in ln and "$22" in ln for ln in code), \
        "start time must be derived from /proc/<pid>/stat field 22"
    assert any("/proc/uptime" in ln for ln in code)


def test_forensics_bounds_every_log_read():
    """An unbounded log read wedged this NAS for 7h18m once (DEC-0036)."""
    invocations = [ln for ln in _code(FORENSICS)
                   if "dmesg" in ln and not ln.strip().startswith("sec ")]
    assert invocations, "expected a dmesg capture"
    for line in invocations:
        assert "tail -n" in line


# --- 2. the capture can never prevent the reset ---

def test_reset_still_unbinds_and_rebinds():
    """S68 added capture calls to usb_reset.sh. What it DOES to the device must
    be byte-for-byte the same operation -- USB_RESET_ACTION in the monitor names
    an unbind/rebind, and a message drifting from its action is the exact defect
    DEC-0074 was written about."""
    src = _read(RESET)
    assert "echo '1-3' > /sys/bus/usb/drivers/usb/unbind" in src
    assert "echo '1-3' > /sys/bus/usb/drivers/usb/bind" in src
    assert "sleep 3" in src


def test_reset_captures_before_unbind_and_after_bind():
    """Order is the whole point: a 'pre' taken after the unbind photographs the
    aftermath, not the fault."""
    src = _read(RESET)
    pre = src.index("capture pre")
    unbind = src.index("drivers/usb/unbind")
    bind = src.index("drivers/usb/bind")
    post = src.index("capture post")
    assert pre < unbind < bind < post


def test_reset_tolerates_a_broken_capture():
    """Run the real script with a forensics helper that exits non-zero, against
    fake sysfs targets, and prove the unbind/rebind still happened."""
    with tempfile.TemporaryDirectory() as d:
        broken = os.path.join(d, "broken.sh")
        with open(broken, "w") as f:
            f.write("#!/bin/sh\nexit 9\n")
        os.chmod(broken, 0o755)

        # Rewrite the two sysfs writes to land in the temp dir instead.
        script = os.path.join(d, "reset.sh")
        with open(script, "w") as f:
            f.write(_read(RESET)
                    .replace("/sys/bus/usb/drivers/usb/", d + "/")
                    .replace("sleep 3", "true"))
        os.chmod(script, 0o755)

        r = subprocess.run(["/bin/sh", script],
                           env={**os.environ, "USB_FORENSICS_SCRIPT": broken},
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr
        assert _read(os.path.join(d, "unbind")).strip() == "1-3"
        assert _read(os.path.join(d, "bind")).strip() == "1-3"


def _reset_harness(d, helper_body="#!/bin/sh\ntouch \"$MARKER\"\n", mode=0o755):
    """A runnable copy of usb_reset.sh with the sysfs writes redirected into d,
    plus a forensics helper that drops a marker file when it actually runs."""
    helper = os.path.join(d, "forensics.sh")
    with open(helper, "w") as f:
        f.write(helper_body)
    os.chmod(helper, mode)
    script = os.path.join(d, "reset.sh")
    with open(script, "w") as f:
        f.write(_read(RESET)
                .replace("/sys/bus/usb/drivers/usb/", d + "/")
                .replace("sleep 3", "true"))
    os.chmod(script, 0o755)
    marker = os.path.join(d, "ran")
    r = subprocess.run(["/bin/sh", script],
                       env={**os.environ, "USB_FORENSICS_SCRIPT": helper,
                            "MARKER": marker},
                       capture_output=True, text=True, timeout=30)
    return r, marker


def test_reset_refuses_a_helper_it_does_not_own():
    """usb_reset.sh runs as root under a sudoers grant scoped to its own path, so
    anything it executes runs as root too. A helper writable by weewx-monitor
    would turn that narrow grant into arbitrary root execution -- exactly what the
    dedicated-user setup exists to prevent (README "Security Note").

    Only the REFUSING direction is testable here: this test cannot create a
    root-owned file. The permissive direction is exercised on the NAS, where
    usb_forensics.sh is deployed root-owned beside usb_reset.sh.
    """
    with tempfile.TemporaryDirectory() as d:
        r, marker = _reset_harness(d)
        assert not os.path.exists(marker), \
            "a non-root-owned helper was executed under the sudo grant"
        assert "FORENSICS REFUSED" in r.stderr
        # and the reset itself still happened -- evidence is never load-bearing
        assert _read(os.path.join(d, "bind")).strip() == "1-3"


def test_reset_refusal_is_loud_not_silent():
    """A security check that silently skips the capture would read, months later,
    as 'the forensics found nothing' rather than 'the forensics never ran'. That
    confusion is what DEC-0074 cost this repo 2.5 months on."""
    with tempfile.TemporaryDirectory() as d:
        r, _ = _reset_harness(d)
        assert r.stderr.strip(), "refusal must be reported, not swallowed"
        assert "escalate" in r.stderr


def test_monitor_logs_the_reset_scripts_output_on_success():
    """The refusal above travels to the log only if do_reset stops discarding
    output on a zero exit."""
    import types
    logged = []
    orig_run, orig_log, orig_email = subprocess.run, wm.log, wm.send_email
    subprocess.run = lambda *a, **k: types.SimpleNamespace(
        returncode=0, stdout="", stderr="FORENSICS REFUSED: bad owner\n")
    wm.log = logged.append
    wm.send_email = lambda s, b: None
    try:
        wm.do_reset(notify=False)
    finally:
        subprocess.run, wm.log, wm.send_email = orig_run, orig_log, orig_email
    assert any("FORENSICS REFUSED" in m for m in logged)


def test_reset_tolerates_a_missing_capture():
    """The normal state of any box where the S68 deploy has not landed."""
    with tempfile.TemporaryDirectory() as d:
        script = os.path.join(d, "reset.sh")
        with open(script, "w") as f:
            f.write(_read(RESET)
                    .replace("/sys/bus/usb/drivers/usb/", d + "/")
                    .replace("sleep 3", "true"))
        os.chmod(script, 0o755)
        r = subprocess.run(["/bin/sh", script],
                           env={**os.environ,
                                "USB_FORENSICS_SCRIPT": os.path.join(d, "nope.sh")},
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr
        assert _read(os.path.join(d, "bind")).strip() == "1-3"


# --- 3. it completes and self-describes when the reads fail ---

def test_forensics_writes_a_capture_even_with_nothing_readable():
    """Executed for real. This host has no /proc/<pid>/fd for a container and no
    /sys/bus/usb at all, so nearly every read fails -- which is precisely the
    shape of a capture taken mid-outage. A partial capture must still be a file."""
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["/bin/sh", FORENSICS, "unit-test"],
                           env={**os.environ, "USB_FORENSICS_DIR": d},
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        out = r.stdout.strip()
        assert out and os.path.exists(out)
        body = _read(out)
        assert "phase=unit-test" in body
        assert "=== end phase=unit-test ===" in body
        assert "euid=" in body           # every capture states its own privilege


def test_forensics_filename_carries_the_phase():
    """Captures are read as a before/after pair; the pairing lives in the name."""
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["/bin/sh", FORENSICS, "pre"],
                           env={**os.environ, "USB_FORENSICS_DIR": d},
                           capture_output=True, text=True, timeout=60)
        assert os.path.basename(r.stdout.strip()).endswith("-pre.txt")


# --- monitor wiring ---

def test_monitor_forensics_is_a_noop_when_the_script_is_absent():
    orig = wm.USB_FORENSICS_SCRIPT
    wm.USB_FORENSICS_SCRIPT = "/nonexistent/usb_forensics.sh"
    try:
        assert wm.usb_forensics('pre') is None
    finally:
        wm.USB_FORENSICS_SCRIPT = orig


def test_monitor_forensics_swallows_a_raising_subprocess():
    """Evidence must never be load-bearing over the watchdog it observes."""
    orig_run, orig_access = subprocess.run, os.access
    subprocess.run = lambda *a, **k: (_ for _ in ()).throw(OSError("boom"))
    os.access = lambda *a, **k: True
    logged = []
    orig_log, wm.log = wm.log, logged.append
    try:
        assert wm.usb_forensics('post') is None
    finally:
        subprocess.run, os.access, wm.log = orig_run, orig_access, orig_log
    assert any('reset path unaffected' in m for m in logged)


def test_watchdog_poll_captures_on_both_verdicts():
    """The effective case matters as much as the ineffective one: it is the only
    control this investigation has to diff a failed reset against."""
    calls = []
    orig = wm.usb_forensics
    wm.usb_forensics = calls.append
    wm.WD.update({'last_reset': 0.0, 'tries': 0, 'check_at': 0.0,
                  'escalated': False})
    orig_log, wm.log = wm.log, lambda m: None
    try:
        wm.WD['check_at'] = 100.0
        wm.watchdog_poll(0, 200.0)
        wm.WD['check_at'] = 300.0
        wm.watchdog_poll(5, 400.0)
    finally:
        wm.usb_forensics, wm.log = orig, orig_log
    assert calls == ['verify-effective', 'verify-ineffective']


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
