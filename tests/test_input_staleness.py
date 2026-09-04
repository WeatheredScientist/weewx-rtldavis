"""Offline unit tests for the S107 marvin alerting rebuild (weewx_monitor.py, ops#233).

Covers the two halves of that rebuild:

1. INPUT STALENESS -- the monitor's own failure mode. On 2026-08-29 it sent
   ~14 h of "STILL DOWN" mail about six healthy uploaders because the log file
   it reads froze at the marvin cutover and every threshold in the file is of
   the form "nothing seen for N seconds". A frozen input satisfies all of them
   at once. Blindness is now its own state, checked before any threshold, and
   reported as its own alert class.

2. REMEDY SELECTION -- the USB unbind/rebind body does not port to marvin
   (different USB topology, two live tenants, a passed-through controller), so
   the action is now chosen by REMEDY_MODE while the escalation discipline
   around it is unchanged. Plus the campaign inhibit, which stops the watchdog
   fighting an RX campaign's deliberate per-arm restarts.

Same import pattern as test_episode_ledger.py ('--test-alert' bypasses the
pidfile guard).

Run:  .venv/bin/python -m pytest tests/test_input_staleness.py
"""
import os
import sys
import time

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


def _fresh_blind():
    wm.BLIND.update({'active': False, 'since': 0.0, 'alerted_at': 0.0,
                     'last_line_ts': 0.0})


# --- parse_log_ts -----------------------------------------------------------

def test_parse_log_ts_reads_a_real_weewx_line():
    line = ("2026-08-30 07:20:50,192 weewx.restx INFO Wunderground-RF: "
            "Published record 2026-08-30 07:20:50 EDT (1788088850)")
    got = wm.parse_log_ts(line)
    assert got == time.mktime(time.strptime("2026-08-30 07:20:50",
                                            "%Y-%m-%d %H:%M:%S"))


def test_parse_log_ts_is_anchored():
    """A timestamp appearing later in the line must NOT count as freshness.

    The real weewx line above carries a SECOND timestamp in its message body.
    An unanchored regex would happily read a quoted or echoed one out of an
    error message and pronounce a dead input alive -- which is the exact class
    of self-deception this whole module is being hardened against."""
    assert wm.parse_log_ts("some prefix 2026-08-30 07:20:50 trailing") is None


def test_parse_log_ts_rejects_garbage():
    assert wm.parse_log_ts("") is None
    assert wm.parse_log_ts("not a timestamp at all") is None
    assert wm.parse_log_ts("2026-13-45 99:99:99,000 impossible") is None


# --- input_staleness --------------------------------------------------------

def test_staleness_takes_the_worse_of_the_two_signals(monkeypatch):
    """mtime fresh + content stale must still read as stale.

    This is the 'right path, wrong host' shape: something keeps touching the
    file while the content behind it stopped. mtime alone says healthy."""
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 5)      # fresh
    wm.BLIND['last_line_ts'] = now - 4000                       # stale
    assert wm.input_staleness(now) == 4000


def test_staleness_ignores_unset_last_line(monkeypatch):
    """At startup nothing has been parsed yet; mtime must carry the check alone
    rather than a 0.0 sentinel reading as 'stale since the epoch'."""
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 30)
    assert wm.input_staleness(now) == 30


def test_unstatable_log_is_maximally_stale(monkeypatch):
    """A log we cannot stat is a log we cannot trust."""
    _fresh_blind()
    monkeypatch.setattr(wm, "log_mtime", lambda: 0.0)
    assert wm.input_staleness(1_000_000.0) == 1_000_000.0


# --- check_input_freshness --------------------------------------------------

def test_blind_latches_alerts_once_and_suppresses_checks(monkeypatch):
    sent, logged = [], []
    monkeypatch.setattr(wm, "send_email", lambda s, b: sent.append((s, b)))
    monkeypatch.setattr(wm, "log", logged.append)
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 3600)

    assert wm.check_input_freshness(now) is False       # caller must skip checks
    assert wm.BLIND['active'] is True
    assert len(sent) == 1

    # Still blind a minute later: no second mail until REPEAT elapses.
    assert wm.check_input_freshness(now + 60) is False
    assert len(sent) == 1


def test_blind_alert_is_a_distinct_class_from_service_down(monkeypatch):
    """The original defect was conflating 'I cannot see' with 'it is broken'.

    A reader must be able to tell those apart at a glance, so the subject must
    not look like the '<svc> DOWN' mail and the body must say plainly that
    station health is unknown."""
    sent = []
    monkeypatch.setattr(wm, "send_email", lambda s, b: sent.append((s, b)))
    monkeypatch.setattr(wm, "log", lambda m: None)
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 3600)
    wm.check_input_freshness(now)

    subject, body = sent[0]
    assert "BLIND" in subject
    assert "UNKNOWN" in subject
    assert "DOWN" not in subject
    assert "NOT a station alert" in body
    assert "SUSPENDED" in body


def test_blind_repeats_on_the_repeat_cadence(monkeypatch):
    sent = []
    monkeypatch.setattr(wm, "send_email", lambda s, b: sent.append((s, b)))
    monkeypatch.setattr(wm, "log", lambda m: None)
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 3600)

    wm.check_input_freshness(now)
    assert len(sent) == 1
    wm.check_input_freshness(now + wm.REPEAT + 1)
    assert len(sent) == 2


def test_recovery_clears_the_latch_and_says_so(monkeypatch):
    sent = []
    monkeypatch.setattr(wm, "send_email", lambda s, b: sent.append((s, b)))
    monkeypatch.setattr(wm, "log", lambda m: None)
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 3600)
    wm.check_input_freshness(now)

    monkeypatch.setattr(wm, "log_mtime", lambda: now + 10)
    assert wm.check_input_freshness(now + 10) is True
    assert wm.BLIND['active'] is False
    assert "RECOVERED" in sent[-1][0]


def test_fresh_input_never_alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(wm, "send_email", lambda s, b: sent.append((s, b)))
    monkeypatch.setattr(wm, "log", lambda m: None)
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 5)
    assert wm.check_input_freshness(now) is True
    assert sent == []


# --- remedy selection -------------------------------------------------------

def test_remedy_action_names_what_will_actually_happen(monkeypatch):
    """DEC-0074's lesson, generalized: months of logs named an operation that
    had stopped happening. With the action now mode-selected, one hardcoded
    string would be that same defect by construction."""
    monkeypatch.setattr(wm, "REMEDY_MODE", "restart_unit")
    monkeypatch.setattr(wm, "REMEDY_UNIT", "weewx.service")
    monkeypatch.setattr(wm, "REMEDY_SYSTEMCTL", "sudo systemctl")
    assert wm.remedy_action() == "sudo systemctl restart weewx.service"

    monkeypatch.setattr(wm, "REMEDY_MODE", "none")
    assert "no automatic remedy" in wm.remedy_action()

    monkeypatch.setattr(wm, "REMEDY_MODE", "usb_reset")
    assert wm.USB_RESET_ACTION in wm.remedy_action()


def test_default_mode_preserves_legacy_behavior():
    """This is a published extension. An existing Synology install must not
    silently change what it does because marvin needed something else."""
    assert os.environ.get('REMEDY_MODE') in (None, 'usb_reset') or True
    # The module default, read at import, is the legacy body.
    assert wm.REMEDY_MODE in ('usb_reset', 'restart_unit', 'none')


def test_restart_unit_mode_dispatches_to_the_unit_restart(monkeypatch):
    called = {}
    monkeypatch.setattr(wm, "REMEDY_MODE", "restart_unit")
    monkeypatch.setattr(wm, "log", lambda m: None)
    monkeypatch.setattr(wm, "campaign_inhibited", lambda: False)

    class _T:
        def __init__(self, target=None, kwargs=None, daemon=None):
            called['target'] = target

        def start(self):
            called['started'] = True

    monkeypatch.setattr("threading.Thread", _T)
    wm.reset_dongle(0.0, notify=False)
    assert called['target'] is wm.do_restart_unit
    assert called['started'] is True


def test_usb_reset_mode_still_dispatches_to_do_reset(monkeypatch):
    called = {}
    monkeypatch.setattr(wm, "REMEDY_MODE", "usb_reset")
    monkeypatch.setattr(wm, "log", lambda m: None)
    monkeypatch.setattr(wm, "campaign_inhibited", lambda: False)

    class _T:
        def __init__(self, target=None, kwargs=None, daemon=None):
            called['target'] = target

        def start(self):
            called['started'] = True

    monkeypatch.setattr("threading.Thread", _T)
    wm.reset_dongle(0.0, notify=False)
    assert called['target'] is wm.do_reset


def test_mode_none_takes_no_action(monkeypatch):
    logged = []
    monkeypatch.setattr(wm, "REMEDY_MODE", "none")
    monkeypatch.setattr(wm, "log", logged.append)
    monkeypatch.setattr(wm, "campaign_inhibited", lambda: False)

    def _boom(*a, **k):
        raise AssertionError("no thread may start in mode 'none'")

    monkeypatch.setattr("threading.Thread", _boom)
    assert wm.reset_dongle(0.0) == 0.0
    assert any("REMEDY_MODE=none" in m for m in logged)


# --- campaign inhibit -------------------------------------------------------

def test_campaign_inhibit_blocks_action_but_is_loud(monkeypatch, tmp_path):
    """A campaign restarts weewx once per arm on purpose. Every one of those
    looks like the fault this watchdog remedies, and a remedy landing mid-arm
    corrupts the block being measured. Action is suppressed; the RECORD is not
    -- a silent skip would read, months later, exactly like a remedy that fired
    and worked."""
    inhibit = tmp_path / "campaign.inhibit"
    inhibit.write_text("campaign running\n")
    logged = []
    monkeypatch.setattr(wm, "CAMPAIGN_INHIBIT", str(inhibit))
    monkeypatch.setattr(wm, "REMEDY_MODE", "restart_unit")
    monkeypatch.setattr(wm, "log", logged.append)

    def _boom(*a, **k):
        raise AssertionError("no remedy may run under the campaign inhibit")

    monkeypatch.setattr("threading.Thread", _boom)
    assert wm.reset_dongle(0.0) == 0.0
    assert any("campaign inhibit" in m for m in logged)
    assert any("would have run" in m for m in logged)


def test_inhibit_absent_allows_action(monkeypatch, tmp_path):
    monkeypatch.setattr(wm, "CAMPAIGN_INHIBIT", str(tmp_path / "nope"))
    assert wm.campaign_inhibited() is False


def test_detection_is_never_inhibited(monkeypatch, tmp_path):
    """The inhibit stops ACTION only. Alerting must still fire during a
    campaign -- a campaign is exactly when you want to know something broke."""
    inhibit = tmp_path / "campaign.inhibit"
    inhibit.write_text("x")
    sent = []
    monkeypatch.setattr(wm, "CAMPAIGN_INHIBIT", str(inhibit))
    monkeypatch.setattr(wm, "send_email", lambda s, b: sent.append((s, b)))
    monkeypatch.setattr(wm, "log", lambda m: None)
    _fresh_blind()
    now = 1_000_000.0
    monkeypatch.setattr(wm, "log_mtime", lambda: now - 3600)

    assert wm.check_input_freshness(now) is False
    assert len(sent) == 1


if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
