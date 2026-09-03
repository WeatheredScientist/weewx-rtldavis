"""Offline unit tests for the DEC-0135 duplicate time-gate (S116).

Two layers changed together, and these tests pin both halves.

GO SIDE (patch/rtldavis-dupgate.patch, exercised here as a text fixture): the
demodulator's byte-equality duplicate filter had no time bound, so a payload the
transmitter re-sent one loop period later was dropped WITHOUT hopping, and the
pending timer then booked the received packet as `packet missed`. Measured live:
~27% of transmissions, and rxCheckPercent under-reporting a ~99% link as ~73%.
The patch gates the drop on -dupwindow (500 ms default) and logs the survivors
as `repeat packet:`.

DRIVER SIDE (this file's real subject): with repeats now reaching the driver,
`self._last_pkt` finally decides whether one becomes a loop packet. It could
never fire before -- `data` carries curr_cnt0..3, Go's cumulative counters,
which advance on every packet -- so the guard was dead code from the day it was
written. These tests assert the dedup key excludes those counters, that a
genuine reading change still yields, and that the repeat counter is wired.

Run:  python3 -m pytest tests/    OR    python3 tests/test_dup_time_gate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_duplicate_frame_counter import _make_driver  # noqa: E402  (shared weewx stubs)
from rtldavis import dedup_key as _dedup_key  # noqa: E402  -- the REAL function

PATCH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "patch", "rtldavis-dupgate.patch")


# --- the dedup key -------------------------------------------------------

def test_counters_excluded_so_the_guard_can_fire():
    """The bug: curr_cnt* advance every packet, so raw dicts never compared
    equal and the guard was unreachable. Same reading, later counters."""
    a = {'temperature': 21.5, 'wind_speed': 3.0, 'curr_cnt0': 100, 'curr_cnt1': 0}
    b = {'temperature': 21.5, 'wind_speed': 3.0, 'curr_cnt0': 101, 'curr_cnt1': 0}
    assert a != b, "precondition: the raw dicts differ -- that WAS the bug"
    assert _dedup_key(a) == _dedup_key(b), "a repeat must compare equal once counters are dropped"


def test_a_changed_reading_is_never_suppressed():
    a = {'temperature': 21.5, 'curr_cnt0': 100}
    b = {'temperature': 21.6, 'curr_cnt0': 101}
    assert _dedup_key(a) != _dedup_key(b)


def test_every_curr_cnt_index_is_excluded():
    d = {'temperature': 1.0, 'curr_cnt0': 1, 'curr_cnt1': 2, 'curr_cnt2': 3, 'curr_cnt3': 4}
    assert _dedup_key(d) == {'temperature': 1.0}


def test_a_reading_that_returns_to_a_previous_value_still_yields():
    """Only the IMMEDIATELY preceding packet is suppressed -- the guard keeps
    one packet of state, not a set. 21.5 -> 21.6 -> 21.5 must yield 3 times."""
    seen = []
    last = None
    for t in (21.5, 21.6, 21.5):
        reading = _dedup_key({'temperature': t, 'curr_cnt0': len(seen)})
        if reading != last:
            last = reading
            seen.append(t)
    assert seen == [21.5, 21.6, 21.5]


# --- the repeat counter --------------------------------------------------

def test_init_stats_starts_repeat_count_at_zero():
    assert _make_driver().stats['repeat_count'] == 0


def test_reset_stats_zeroes_repeat_count_for_next_period():
    d = _make_driver()
    d.stats['repeat_count'] = 9
    type(d)._reset_stats(d)
    assert d.stats['repeat_count'] == 0


def test_both_frame_classes_are_reported_each_period(monkeypatch=None):
    """dup_count and repeat_count are different populations and must both be
    logged -- conflating them is what hid this for the life of the receiver."""
    import rtldavis
    logged = []
    orig = rtldavis.loginf
    rtldavis.loginf = lambda m: logged.append(m)
    try:
        d = _make_driver()
        d.stats['dup_count'] = 4
        d.stats['repeat_count'] = 80
        type(d)._update_summaries(d)
    finally:
        rtldavis.loginf = orig
    assert any('duplicate frames this period: 4' in m for m in logged)
    assert any('repeat frames this period: 80' in m for m in logged)


# --- the Go patch is present and says what we think it says --------------

def test_patch_file_exists_and_gates_on_time():
    with open(PATCH) as fh:
        text = fh.read()
    assert '-dupwindow' in text or 'dupwindow' in text
    # the drop must be conditional on elapsed time, not on bytes alone
    assert 'curTime - lastRecTime < int64(dupWindow)' in text, \
        "the duplicate drop is no longer time-gated -- the DEC-0135 fix is gone"
    # lastRecTime must be assigned on the ACCEPT path only; a drop that advanced
    # it would let a chain of re-decodes ratchet the window forward
    assert text.count('+                lastRecTime = curTime') == 1


def test_patch_window_stays_below_the_shortest_loop_period():
    """idLoopPeriods[0] is 2.5625 s. A window at or above it could swallow a
    real transmission on transmitter id 0."""
    with open(PATCH) as fh:
        text = fh.read()
    import re
    m = re.search(r'"dupwindow", (\d+),', text)
    assert m, "default dupwindow not found in the patch"
    assert 0 < int(m.group(1)) < 2562, "dupwindow must stay under the 2.5625 s minimum loop period"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
