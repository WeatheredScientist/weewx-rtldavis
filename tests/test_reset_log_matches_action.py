"""The reset log message must name the operation that actually runs.

WHY THIS EXISTS (S67, DEC-0074). `reset_dongle()` logged
`RESET: triggering syno_vbus_reset` while `do_reset()` shelled out to
`usb_reset.sh`, which is a driver unbind/rebind and NOT a power cycle. The retired
`usb_watchdog.sh` really did write that sysfs node; when the logic moved into the
monitor the action changed and the message did not. Every reset line in every log
for months named an operation that had not run, and a reader reasoning from those
logs reasons about the wrong mechanism -- which is exactly what happened at S67.

A log line is an assertion about behaviour. Nothing enforced it, so it rotted
silently: no test failed, no check went red, and the drift was only found by
reading the reset script by hand while chasing an unrelated question.

These tests bind the message to the executed command via shared constants, so the
two cannot diverge without a failure here.
"""

import re
import sys
from pathlib import Path

# Bypass the module's PID guard so importing it doesn't touch a running monitor
# (same trick as tests/test_monitor_incremental_read.py).
sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import weewx_monitor  # noqa: E402

SOURCE = (Path(__file__).resolve().parent.parent / "weewx_monitor.py").read_text()


def test_reset_constants_exist():
    """The action and the script live in one place, not scattered as literals."""
    assert weewx_monitor.USB_RESET_SCRIPT.endswith("usb_reset.sh")
    assert weewx_monitor.USB_RESET_ACTION


def test_no_stale_syno_vbus_reset_in_log_calls():
    """The monitor must not claim to trigger syno_vbus_reset.

    It does not, and has not since the logic left usb_watchdog.sh. The string may
    still appear in a comment explaining this history; it must not appear inside a
    log() or send_email() call.
    """
    calls = re.findall(r"(?:log|send_email)\((.*?)\)\n", SOURCE, re.S)
    offenders = [c for c in calls if "syno_vbus_reset" in c]
    assert not offenders, f"log/email call still names syno_vbus_reset: {offenders}"


def test_subprocess_uses_the_named_constant():
    """The executed command is the constant, not a duplicated literal path.

    A second hardcoded copy is how the message and the action drifted apart the
    first time.
    """
    assert "['sudo', USB_RESET_SCRIPT]" in SOURCE
    hardcoded = re.findall(r"'sudo',\s*'/volume1/[^']+'", SOURCE)
    assert not hardcoded, f"reset path hardcoded at the call site: {hardcoded}"


def test_reset_log_lines_reference_the_constants():
    """Every RESET log line that describes the mechanism derives it from the constants."""
    mechanism_lines = [
        line for line in SOURCE.splitlines()
        if "log(" in line and "RESET:" in line and "running" not in line and "done" not in line
    ]
    assert mechanism_lines, "expected at least one RESET mechanism log line"
    for line in mechanism_lines:
        assert "USB_RESET_ACTION" in line or "USB_RESET_SCRIPT" in line, (
            f"RESET log line describes the mechanism with a literal, so it can drift: {line.strip()}"
        )
