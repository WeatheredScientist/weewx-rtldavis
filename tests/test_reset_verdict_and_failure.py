"""Offline unit tests for two S82b watchdog fixes (weewx_monitor.py, #180).

1. void_pending_verdict(): the weewx.log rotation-reset branch zeroes
   wu_bad_windows as offset bookkeeping, not because reception verified good.
   Judging a pending reset by that zeroed counter logged 'verified effective'
   at midnight, mislabeled the verify-effective forensics capture, and
   silently refreshed the RESET_MAX_TRIES hedge budget mid-episode. A verdict
   that cannot be honestly judged is voided instead, loudly, with
   tries/escalated untouched.

2. do_reset()'s exception path emails: it used to log only, unlike the
   nonzero-exit branch -- and it fired live 2026-08-14 01:56:30 as a 15 s
   sudo timeout that told nobody.

Same import pattern as test_episode_ledger.py ('--test-alert' bypasses the
pidfile guard).

Run:  python3 -m pytest tests/   OR   python3 tests/test_reset_verdict_and_failure.py
"""
import os
import subprocess
import sys

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


def _fresh_wd():
    wm.WD.update({'last_reset': 0.0, 'tries': 0, 'check_at': 0.0,
                  'escalated': False})


def test_void_clears_pending_verdict_and_logs(monkeypatch):
    logged = []
    monkeypatch.setattr(wm, "log", logged.append)
    _fresh_wd()
    wm.WD['check_at'] = 12345.0
    wm.WD['tries'] = 1
    wm.void_pending_verdict("log rotated before the verification window closed")
    assert wm.WD['check_at'] == 0.0
    assert wm.WD['tries'] == 1, "voiding must not touch the try counter"
    assert any("verdict void" in m for m in logged)


def test_void_without_pending_verdict_is_silent(monkeypatch):
    logged = []
    monkeypatch.setattr(wm, "log", logged.append)
    _fresh_wd()
    wm.void_pending_verdict("anything")
    assert logged == [], "no pending verdict, nothing to say"


def test_voided_verdict_is_not_judged_by_watchdog_poll(monkeypatch):
    """End-to-end shape of the midnight bug: reset pending, rotation voids it,
    the next poll with (rotation-zeroed) bad_windows==0 must NOT log
    'verified effective' or clear counters."""
    logged = []
    monkeypatch.setattr(wm, "log", logged.append)
    monkeypatch.setattr(wm, "usb_forensics", lambda phase: None)
    _fresh_wd()
    wm.WD['check_at'] = 1000.0
    wm.WD['tries'] = 1
    wm.void_pending_verdict("log rotated")
    wm.watchdog_poll(wu_bad_windows=0, now=2000.0)
    assert wm.WD['tries'] == 1, "a voided verdict must not clear the counters"
    assert not any("verified effective" in m for m in logged)


def test_reset_exception_path_emails(monkeypatch):
    """The 2026-08-14 01:56:30 shape: sudo times out, the reset never ran --
    that must email like any other reset failure, not just log."""
    emails = []
    logged = []
    monkeypatch.setattr(wm, "send_email", lambda subj, body: emails.append((subj, body)))
    monkeypatch.setattr(wm, "log", logged.append)

    def _boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=15)
    monkeypatch.setattr(subprocess, "run", _boom)

    wm.do_reset(notify=False)
    assert any("FAILED" in subj for subj, _ in emails), \
        "a reset that never ran must reach the alert path"
    assert any("RESET error" in m for m in logged)


def test_reset_nonzero_exit_still_emails(monkeypatch):
    """Guard the sibling branch this fix was aligned with."""
    emails = []
    monkeypatch.setattr(wm, "send_email", lambda subj, body: emails.append((subj, body)))
    monkeypatch.setattr(wm, "log", lambda m: None)

    class _R:
        returncode = 1
        stdout = ""
        stderr = "sudo: a password is required"
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R())

    wm.do_reset(notify=False)
    assert any("FAILED" in subj for subj, _ in emails)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
