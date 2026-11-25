"""Confirm-on-reject for the rain counter (DEC-0249, docs/RAIN-CAP-DESIGN.md section 6).

A = last accepted count, P = the rejected reading after it, n = the reading after P. Two layers:
sequences through the real `_data_to_packet` on a fake clock, and the design table's exhaustive
model over every (A, rejected P, n) triple, against the shipped functions, per catch-up cap.

conftest.py imports rtldavis against its superset weewx fake, so no stub here.
"""
import logging
import os
import sys
import types

import pytest

import rtldavis
from rtldavis import (RtldavisDriver, SensorQC, rain_delta_tips,
                      rain_tips_with_anchor)

sys.argv = [sys.argv[0], "--test-alert"]   # bypass the monitor's PID guard on import
import weewx_monitor as wm  # noqa: E402

TIP = 0.2   # mm per tip on the bare driver below


class Clock:
    """monotonic() is the test's; time() jumps wildly, to prove the wall clock is unused."""

    def __init__(self):
        self.now = 1000.0
        self.wall = 1.7e9

    def time(self):
        self.wall += 1e6
        return self.wall

    def monotonic(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(rtldavis, 'time',
                        types.SimpleNamespace(time=c.time, monotonic=c.monotonic))
    return c


def _driver():
    drv = RtldavisDriver.__new__(RtldavisDriver)  # skip __init__ (ProcManager)
    drv.sensor_map = dict(RtldavisDriver.DEFAULT_SENSOR_MAP)
    drv.last_rain_count = drv.last_rain_time = None
    drv.last_accepted_rain_count = drv.last_accepted_rain_time = None
    drv.rain_per_tip = TIP
    drv._sensor_qc_enabled = True
    drv._sensor_qc = SensorQC()
    return drv


def _run(clock, steps, drv=None):
    """steps: (seconds since the previous step, count). Returns tips per step, None = rejected."""
    drv = drv or _driver()
    out = []
    for dt, count in steps:
        clock.now += dt
        rain = drv._data_to_packet({'rain_count': count})['rain']
        out.append(None if rain is None else round(rain / TIP))
    return out


# --- sequences through _data_to_packet ---------------------------------------

def test_confirmed_jump_books_the_whole_step(clock):
    # the design's section 1 loss: 20 real tips fell in a gap, old code booked 1 of 21
    assert _run(clock, [(0, 20), (120, 40), (10, 41)]) == [0, None, 21]


def test_confirmed_jump_with_no_further_tips(clock):
    assert _run(clock, [(0, 20), (120, 40), (10, 40)]) == [0, None, 20]


def test_confirmed_jump_across_the_wrap(clock):
    assert _run(clock, [(0, 120), (120, 10), (10, 11)]) == [0, None, 19]


def test_confirmation_consumes_the_reject(clock):
    assert _run(clock, [(0, 20), (120, 40), (10, 41), (10, 42)]) == [0, None, 21, 1]


def test_glitch_then_true_count_books_only_the_truth(clock):
    assert _run(clock, [(0, 20), (300, 84), (10, 21)]) == [0, None, 1]


def test_unconfirmed_jump_books_nothing(clock):
    # n fits neither A nor P: rejected, as before
    assert _run(clock, [(0, 20), (300, 40), (10, 90)]) == [0, None, None]


def test_reading_behind_the_rejected_one_is_not_a_confirmation(clock):
    assert _run(clock, [(0, 20), (300, 60), (10, 59)]) == [0, None, None]


# time: total <= elapsed / 4 + 1, elapsed since A, to n
@pytest.mark.parametrize('first, booked', [(70, 21), (69.9, 1)])
def test_elapsed_time_limit_is_inclusive(clock, first, booked):
    # 21 tips need 80 s from A to n; the last 10 s are P to n
    assert _run(clock, [(0, 20), (first, 40), (10, 41)]) == [0, None, booked]


def test_elapsed_runs_from_the_last_accepted_reading_not_the_first(clock):
    # 20 is heard again just before the jump: only 20 s for 21 tips
    assert _run(clock, [(0, 20), (500, 20), (10, 40), (10, 41)]) == [0, 0, None, 1]


def test_elapsed_runs_from_a_recovered_anchor_too(clock):
    # DEC-0218's path moves A (and its time) as well
    assert _run(clock, [(0, 20), (500, 19), (10, 20), (10, 40), (10, 41)]) == \
        [0, None, 0, None, 1]


def test_elapsed_runs_from_a_confirmed_anchor_too(clock):
    # and so does a catch-up: the second jump has 20 s, not 300
    assert _run(clock, [(0, 20), (300, 40), (10, 41), (10, 61), (10, 62)]) == \
        [0, None, 21, None, 1]


def test_wall_clock_is_never_used(clock):
    # Clock.time() leaps 1e6 s per call; a wall-clock elapsed would allow this
    assert _run(clock, [(0, 20), (5, 40), (5, 41)]) == [0, None, 1]


# 2 s: P and n must be independent transmissions
@pytest.mark.parametrize('gap, booked', [(2, 21), (1.99, 1), (0.002, 1)])
def test_two_second_rule(clock, gap, booked):
    assert _run(clock, [(0, 20), (300, 40), (gap, 41)]) == [0, None, booked]


@pytest.mark.parametrize('total, booked', [(45, 45), (46, 1)])
def test_catch_up_cap(clock, total, booked):
    assert rtldavis.MAX_CATCH_UP_TIPS == 45
    assert _run(clock, [(0, 5), (3600, 4 + total), (10, 5 + total)]) == [0, None, booked]


# zero rule
def test_reset_to_zero_books_no_catch_up(clock):
    # 100 -> 0 is 28 tips mod 128, inside the cap and the time
    assert _run(clock, [(0, 100), (300, 0), (10, 0), (10, 2)]) == [0, None, 0, 2]


def test_zero_rule_is_about_p_not_n(clock):
    # a real jump from 100 to 127 confirmed by the wrap to 0
    assert _run(clock, [(0, 100), (300, 127), (10, 0)]) == [0, None, 28]


def test_existing_reset_phantom_is_unchanged(clock):
    # 112 -> 0 still reads as a wrap (section 6: out of scope without option D)
    assert _run(clock, [(0, 112), (10, 0)]) == [0, 16]


# restart
def test_restart_clears_anchor_and_reject(clock):
    drv = _driver()
    assert _run(clock, [(0, 20), (300, 40)], drv) == [0, None]
    assert _run(clock, [(10, 41), (10, 42)], _driver()) == [0, 1]


def test_init_clears_all_four_fields():
    with open(os.path.join(os.path.dirname(rtldavis.__file__), 'rtldavis.py')) as f:
        init = f.read().split('class RtldavisDriver')[1].split('def __init__')[1]
    init = init.split('\n    def ')[0]
    for name in ('last_rain_count', 'last_rain_time',
                 'last_accepted_rain_count', 'last_accepted_rain_time'):
        assert 'self.%s = None' % name in init


# co-rejection (DEC-0054): a condemned frame is neither A nor P
def _corrupt(clock, drv, dt, count):
    clock.now += dt
    assert drv._data_to_packet({'humidity': 144.9, 'rain_count': count})['rain'] is None


def _state(drv):
    return (drv.last_rain_count, drv.last_rain_time,
            drv.last_accepted_rain_count, drv.last_accepted_rain_time)


def test_co_rejected_frame_is_not_p(clock):
    # 40 is heard only in a condemned frame, so 41 is a first, unconfirmed jump
    drv = _driver()
    _run(clock, [(0, 20)], drv)
    before = _state(drv)
    _corrupt(clock, drv, 300, 40)
    assert _state(drv) == before
    assert _run(clock, [(10, 41), (10, 42)], drv) == [None, 22]


def test_co_rejected_frame_between_p_and_n_changes_nothing(clock):
    drv = _driver()
    _run(clock, [(0, 20), (300, 40)], drv)
    before = _state(drv)
    _corrupt(clock, drv, 5, 41)
    assert _state(drv) == before
    assert _run(clock, [(5, 41)], drv) == [21]


def test_co_rejected_frame_does_not_refresh_the_anchor_time(clock):
    drv = _driver()
    _run(clock, [(0, 20)], drv)
    _corrupt(clock, drv, 290, 20)
    assert _run(clock, [(10, 40), (10, 41)], drv) == [None, 21]


def test_co_rejected_frame_does_not_refresh_p_time(clock):
    # 1 s before n, but P itself is 3 s old
    drv = _driver()
    _run(clock, [(0, 20), (300, 40)], drv)
    _corrupt(clock, drv, 2, 40)
    assert _run(clock, [(1, 41)], drv) == [21]


# stale P
def test_accepted_reading_clears_p(clock):
    # 40 was disproved by 20; a later 41 must be judged as a fresh jump
    assert _run(clock, [(0, 20), (300, 40), (10, 20), (300, 41)]) == [0, None, 0, None]


def test_only_the_latest_reject_can_confirm(clock):
    # 41 continues from 40, but 90 came between: no confirmation
    assert _run(clock, [(0, 20), (300, 40), (10, 90), (10, 41), (10, 42)]) == \
        [0, None, None, None, 22]


def test_second_reject_is_the_one_confirmed(clock):
    assert _run(clock, [(0, 20), (300, 90), (10, 40), (10, 41)]) == [0, None, None, 21]


def test_old_p_still_confirms(clock):
    # no age limit on P: the next reading may itself be a long gap away
    assert _run(clock, [(0, 20), (300, 40), (3600, 41)]) == [0, None, 21]


def test_cold_start_then_reject_has_no_false_anchor(clock):
    assert _run(clock, [(0, 0), (300, 100), (10, 101)]) == [0, None, 1]


# log lines
def _log(caplog):
    return [(r.levelname, r.getMessage()) for r in caplog.records
            if 'rain:' in r.getMessage()]


def test_catch_up_logs_once_at_info_and_the_reject_still_emails(clock, caplog):
    caplog.set_level(logging.INFO)
    _run(clock, [(0, 20), (120, 40), (10, 41)])
    (lvl_p, reject), (lvl_n, catch_up) = _log(caplog)
    assert lvl_p == 'ERROR' and wm.parse_rain_glitch(reject) is not None
    assert lvl_n == 'INFO' and wm.RAIN_GLITCH_MARKER not in catch_up
    assert wm.parse_rain_glitch(catch_up) is None
    for value in ('at 41', 'after 40', '21 tips', 'accepted 20', '130 s', 'DEC-0249'):
        assert value in catch_up


def test_recovered_reading_logs_only_the_dec0218_line(clock, caplog):
    caplog.set_level(logging.INFO)
    _run(clock, [(0, 20), (300, 40), (10, 21)])
    reject, recovered = _log(caplog)
    assert 'DEC-0218' in recovered[1]


def test_example_stdqc_limit_fits_a_catch_up_and_stops_a_bit_6_flip():
    path = os.path.join(os.path.dirname(rtldavis.__file__), 'weewx.conf.example')
    with open(path) as f:
        lines = [x.split('=')[1].split(',') for x in f if x.strip().startswith('rain = 0,')]
    assert len(lines) == 1 and lines[0][2].strip() == 'inch'
    limit = float(lines[0][1])
    assert (rtldavis.MAX_CATCH_UP_TIPS + 10) / 100 <= limit < 0.64


def test_refused_catch_up_logs_nothing_extra(clock, caplog):
    caplog.set_level(logging.INFO)
    _run(clock, [(0, 20), (5, 40), (5, 41)])
    assert [lvl for lvl, _ in _log(caplog)] == ['ERROR']


# --- the design table, exhaustively, against the shipped functions -------------

ELAPSED, GAP = 300.0, 10.0
REJECTED = [(a, p) for a in range(128) for p in range(128)
            if rain_delta_tips(a, p) is None]


def _book(a, p, n, cap):
    """What the driver books for n, with the shipped functions."""
    tips, recovered = rain_tips_with_anchor(a, p, n)
    if tips is not None and not recovered:
        total = rtldavis.rain_catch_up_tips(a, p, n, ELAPSED, GAP, cap)
        if total is not None:
            return total
    return tips


CAPS = [(20, 1270, 1152, 1143, 4), (30, 13335, 4992, 4953, 14), (45, 45339, 10752, 10668, 29)]


@pytest.mark.parametrize('cap, changed, jumps, exact, resets', CAPS)
def test_design_table(monkeypatch, cap, changed, jumps, exact, resets):
    triples = n_changed = verdicts = 0
    for a, p in REJECTED:
        for n in range(128):
            triples += 1
            old, _ = rain_tips_with_anchor(a, p, n)
            new = _book(a, p, n, cap)
            verdicts += (old is None) != (new is None)
            n_changed += old != new
    assert (triples, verdicts, n_changed) == (1818624, 0, changed)

    # real catch-ups: a jump of 17 or more, then 0 to 2 more tips, total inside the cap
    cases = hits = old_hits = 0
    for a in range(128):
        for jump in range(17, cap + 1):
            for k in range(3):
                if jump + k > cap:
                    continue
                p, n = (a + jump) % 128, (a + jump + k) % 128
                cases += 1
                got = _book(a, p, n, cap)
                hits += got == jump + k
                old_hits += rain_tips_with_anchor(a, p, n)[0] == jump + k
                if got != jump + k:
                    assert p == 0               # the only misses land on 0
    assert (cases, hits, old_hits) == (jumps, exact, 0)

    # one glitch, then the true count
    cases = 0
    for a, p in REJECTED:
        for k in range(17):
            assert _book(a, p, (a + k) % 128, cap) == k
            cases += 1
    assert cases == 241536

    # a reset to 0, heard twice: rule on, then off
    def phantoms(book):
        return sum(1 for a, p in REJECTED if p == 0 and (book(a) or 0) > 0)
    assert phantoms(lambda a: _book(a, 0, 0, cap)) == 0
    off = _without_zero_rule()
    monkeypatch.setattr(rtldavis, 'rain_catch_up_tips', off)
    assert phantoms(lambda a: _book(a, 0, 0, cap)) == resets


def _without_zero_rule():
    real = rtldavis.rain_catch_up_tips
    return lambda a, p, n, e, g, cap: real(a, 1 if p == 0 else p, n, e, g, cap)
