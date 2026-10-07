"""Full-outage vs. degraded reception alert classification (#373, DEC-0154).

The 2026-09-07 incident (`#370`) logged `WINDOW: 0/21 (0%)` for ~71 minutes,
identical in shape to a milder sustained dip below WU_RF_MIN_PCT -- nothing in
the log or the alert email's subject line told the two apart. `#373` asked for
a distinct, louder alert class for the genuinely-dead case.

`classify_reception_alert()` cross-references two independent signals, either
sufficient on its own (same shape as `ops/freeze_baseline.py`'s RF-dead-vs-
freeze classification): every window in the current sustain streak saw
literally zero packets, or the driver's own watchdog has already escalated
(`WD['escalated']`) -- a stall past its reset budget, or an immediate
not-running exit. A plain below-threshold window with the driver still trying
is neither.

weewx_monitor.py writes a pidfile at import; `--test-alert` bypasses that
guard (same pattern as test_watchdog_escalation.py).
"""
import os
import sys

sys.argv = ["weewx_monitor.py", "--test-alert"]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weewx_monitor as wm  # noqa: E402


class _Harness:
    """Replaces send_email / log / the episode ledger with recorders, so
    close_reception_window() can be driven without touching disk or the real
    clock semantics beyond what each test controls explicitly."""

    def __init__(self):
        self.emails = []   # (subject, body)
        self.logs = []
        self._orig = {}

    def __enter__(self):
        wm.WD.update({'last_reset': 0.0, 'tries': 0,
                      'check_at': 0.0, 'escalated': False})
        self._orig = {'send_email': wm.send_email, 'log': wm.log,
                      'episode_open': wm.episode_open,
                      'episode_note_avg': wm.episode_note_avg,
                      'episode_close': wm.episode_close}
        wm.send_email = lambda s, b: self.emails.append((s, b))
        wm.log = lambda m: self.logs.append(m)
        wm.episode_open = lambda avg, now: None
        wm.episode_note_avg = lambda avg: None
        wm.episode_close = lambda now: None
        return self

    def __exit__(self, *a):
        for k, v in self._orig.items():
            setattr(wm, k, v)

    def close_windows(self, counts, start=1000.0, state=None):
        """Feed one window count at a time through close_reception_window(),
        advancing `now` by WU_RF_WINDOW each call. Returns the final state
        tuple; pass a prior return value back in as `state` to continue a
        streak (e.g. across a REPEAT boundary)."""
        if state is None:
            state = ([], 0, False, 0.0, 0.0, {})
        now = start
        for count in counts:
            wu_period_counts, wu_bad_windows, wu_in_alert, \
                wu_alert_sent_at, wu_repeat_sent_at, wu_hourly_buckets = state
            state = wm.close_reception_window(
                count, wu_period_counts, wu_bad_windows, wu_in_alert,
                wu_alert_sent_at, wu_repeat_sent_at, wu_hourly_buckets, now)
            now += wm.WU_RF_WINDOW
        return state, now


def _degraded_counts(n):
    """n windows at ~38% (below WU_RF_MIN_PCT=60, but not zero)."""
    return [8] * n


def _dead_counts(n):
    return [0] * n


# --- classify_reception_alert() unit tests ---

def test_degraded_windows_are_not_full_outage():
    full, reason = wm.classify_reception_alert(_degraded_counts(wm.WU_RF_SUSTAIN))
    assert full is False
    assert reason == ''


def test_all_zero_windows_is_full_outage():
    full, reason = wm.classify_reception_alert(_dead_counts(wm.WU_RF_SUSTAIN))
    assert full is True
    assert 'zero packets' in reason


def test_one_nonzero_window_in_the_streak_is_not_full_outage_by_itself():
    counts = _dead_counts(wm.WU_RF_SUSTAIN - 1) + [1]
    full, reason = wm.classify_reception_alert(counts)
    assert full is False


def test_escalated_watchdog_is_full_outage_even_with_nonzero_windows():
    with _Harness():
        wm.WD['escalated'] = True
        full, reason = wm.classify_reception_alert(_degraded_counts(wm.WU_RF_SUSTAIN))
        assert full is True
        assert 'driver watchdog' in reason
        assert 'zero packets' not in reason


def test_both_signals_report_both_reasons():
    with _Harness():
        wm.WD['escalated'] = True
        full, reason = wm.classify_reception_alert(_dead_counts(wm.WU_RF_SUSTAIN))
        assert full is True
        assert 'zero packets' in reason and 'driver watchdog' in reason


# --- close_reception_window() integration tests ---

def test_degraded_streak_alerts_low_not_down():
    with _Harness() as h:
        h.close_windows(_degraded_counts(wm.WU_RF_SUSTAIN))
        assert len(h.emails) == 1
        subject, body = h.emails[0]
        assert subject.endswith('RF reception LOW')
        assert 'DOWN' not in subject


def test_all_zero_streak_alerts_down():
    with _Harness() as h:
        h.close_windows(_dead_counts(wm.WU_RF_SUSTAIN))
        assert len(h.emails) == 1
        subject, body = h.emails[0]
        assert subject.endswith('RF reception DOWN')
        assert 'zero packets in every recent window' in body
        assert any('FULL OUTAGE' in line for line in h.logs)


def test_escalated_watchdog_upgrades_a_degraded_streak_to_down():
    with _Harness() as h:
        wm.WD['escalated'] = True
        h.close_windows(_degraded_counts(wm.WU_RF_SUSTAIN))
        assert len(h.emails) == 1
        subject, body = h.emails[0]
        assert subject.endswith('RF reception DOWN')
        assert 'driver watchdog already escalated' in body


def test_repeat_after_full_outage_alert_says_still_down():
    with _Harness() as h:
        state, now = h.close_windows(_dead_counts(wm.WU_RF_SUSTAIN))
        # Advance past REPEAT and close one more dead window.
        state, now = h.close_windows(_dead_counts(1), start=now + wm.REPEAT + 1,
                                      state=state)
        assert len(h.emails) == 2
        subject, body = h.emails[-1]
        assert subject.endswith('RF reception STILL DOWN')


def test_recovery_email_unaffected_by_full_outage_wording():
    with _Harness() as h:
        state, now = h.close_windows(_dead_counts(wm.WU_RF_SUSTAIN))
        # A healthy window (count == WU_RF_EXPECTED) closes the alert.
        h.close_windows([wm.WU_RF_EXPECTED], start=now, state=state)
        assert len(h.emails) == 2
        subject, _ = h.emails[-1]
        assert subject.endswith('RF reception RECOVERED')


if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__, '-v']))
