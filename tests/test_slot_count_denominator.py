"""S120/#317: rxCheckPercent denominates by ISS slots between received
packets, not floor(wall-clock period / loop period).

The old formula, `max_count[i] = period // loop_times[x]`, had two defects:
1. Floor bias -- 60s holds 21.33 slots at loop_time 2.8125; floor gives 21,
   so a fully-received minute reads 100% or 104.8% depending on exactly how
   many packets land, +1.6 points mean.
2. Jitter -- `period` is measured between two `int(time.time())` archive-
   event timestamps, which run 59-61s apart, not exactly 60. A 59s period
   floors to 20 slots and reads 105% for the same reception.

The fix (rtldavis.py _update_stats/_update_summaries) tracks the wall-clock
arrival time of the most recent accepted packet per transmitter
(`last_pkt_ts`) and the arrival time as of the previous archive boundary
(`prev_pkt_ts`), then denominates by `round((last - prev) / loop_time)`.
Because the ISS clock is exact (S115: 2.8124s mean, 1.0ms sd), this has no
floor bias and no jitter sensitivity, and count[i] <= max_count[i] holds by
construction -- rxCheckPercent > 100% becomes impossible.

These tests drive the real _update_stats / _update_summaries / _reset_stats
against the four synthetic cases from #317, the counter-reset guard, and a
randomized invariant sweep.

#402: the #317 cases seed prev_pkt_ts by hand, which hid an off-by-one at
seeding. The first packet after a start or a counter reset sat in `count`
while its slot never sat in the delta, and the skipped first archive boundary
never moved prev_pkt_ts. The cold-start section below drives the per-packet
path on a fake clock instead.

Run:  python3 -m pytest tests/   OR   python3 tests/test_slot_count_denominator.py
"""
import contextlib
import os
import random
import sys
import types

import pytest

# --- stub the weewx deps so rtldavis.py imports without weewx installed ---
def _pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m

def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

class _AbstractDevice:
    def __init__(self, *a, **k): pass
class _AbstractConfEditor:
    pass
class _StdService:
    def __init__(self, *a, **k): pass

_weewx = _pkg("weewx")
_weewx.__version__ = "5.3.1"
_weewx.METRICWX = 16
_drivers = _mod("weewx.drivers")
_drivers.AbstractDevice = _AbstractDevice
_drivers.AbstractConfEditor = _AbstractConfEditor
_engine = _mod("weewx.engine")
_engine.StdService = _StdService
_units = _mod("weewx.units")
for _d in ("obs_group_dict", "USUnits", "MetricUnits", "MetricWXUnits",
           "default_unit_format_dict", "default_unit_label_dict"):
    setattr(_units, _d, {})
_crc16 = _mod("weewx.crc16")
_crc16.crc16 = lambda *a, **k: 0
_weewx.drivers, _weewx.engine, _weewx.units, _weewx.crc16 = (
    _drivers, _engine, _units, _crc16)

_weeutil = _pkg("weeutil")
_wu = _mod("weeutil.weeutil")
_wu.tobool = lambda v: str(v).lower() in ("1", "true", "yes", "on")
_wlog = _mod("weeutil.logger")
_weeutil.weeutil, _weeutil.logger = _wu, _wlog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rtldavis  # noqa: E402
from rtldavis import RtldavisDriver  # noqa: E402

LOOP_TIME = 2.8125  # loop_times[4] -- our own receiver's transmitter (DIP ID 5, S119/#313)


def _make_driver():
    """Bare object carrying just the state the stats methods touch. __init__
    is skipped (it spawns a subprocess); one active transmitter at slot 0,
    mapped to loop_times[4] (this station's real transmitter)."""
    d = RtldavisDriver.__new__(RtldavisDriver)
    RtldavisDriver._init_stats(d)
    d.stats['activeTrIds'][0] = 4
    d._save_pct_good_per_transmitter = False
    return d


@contextlib.contextmanager
def _fake_clock():
    """Point rtldavis's time.time() at a settable clock (#402). It restores
    itself rather than using the monkeypatch fixture, so the __main__ runner
    below can still call every test with no arguments."""
    clock = [0.0]
    real = rtldavis.time
    rtldavis.time = types.SimpleNamespace(time=lambda: clock[0])
    try:
        yield clock
    finally:
        rtldavis.time = real


def _close_period(d, count, span_s, t0):
    """Seed transmitter 0's slot-count baseline directly (bypassing the
    per-packet _update_stats path -- the span between the first and last
    packet of the period is the thing under test, not packet-by-packet
    arrival) and close the period via _update_summaries."""
    d.stats['curr_cnt'][0] += count
    d.stats['prev_pkt_ts'][0] = t0
    d.stats['last_pkt_ts'][0] = t0 + span_s
    d.stats['last_ts'] = int(t0)  # only needs to be > 0; not read for the math anymore
    RtldavisDriver._update_summaries(d)


def _established_driver(t0):
    """A driver past the first-period guard, with transmitter 0's baseline
    seeded at t0 and no packets counted yet."""
    d = _make_driver()
    d.stats['curr_cnt'][0] = 1  # marks the transmitter active (curr_cnt > 0)
    d.stats['last_cnt'][0] = 1
    d.stats['last_ts'] = int(t0)
    d.stats['prev_pkt_ts'][0] = t0
    d.stats['last_pkt_ts'][0] = t0
    return d


# ── The four synthetic cases from #317 ─────────────────────────────────────

def test_60s_window_21_packets_is_exactly_100_pct():
    d = _established_driver(t0=1_000_000.0)
    _close_period(d, count=21, span_s=60.0, t0=1_000_000.0)
    assert d.stats['max_count'][0] == 21
    assert d.stats['pct_good'][0] == 100.0


def test_22_packets_in_61_875s_span_is_exactly_100_pct():
    d = _established_driver(t0=1_000_000.0)
    _close_period(d, count=22, span_s=61.875, t0=1_000_000.0)
    assert d.stats['max_count'][0] == 22
    assert d.stats['pct_good'][0] == 100.0


def test_21_packets_in_61_875s_span_is_95_45_pct_one_missed():
    d = _established_driver(t0=1_000_000.0)
    _close_period(d, count=21, span_s=61.875, t0=1_000_000.0)
    assert d.stats['max_count'][0] == 22
    assert d.stats['missed'][0] == 1
    assert d.stats['pct_good'][0] == pytest.approx(95.4545, abs=1e-3)


def test_59_06s_span_21_packets_is_exactly_100_pct():
    """The jitter case: a sub-60s archive interval that still holds exactly
    21 slots must read 100%, not the old formula's 105% (59 // 2.8125 == 20)."""
    d = _established_driver(t0=1_000_000.0)
    _close_period(d, count=21, span_s=59.06, t0=1_000_000.0)
    assert d.stats['max_count'][0] == 21
    assert d.stats['pct_good'][0] == 100.0


# ── Counter-reset guard ─────────────────────────────────────────────────────

def test_counter_reset_mid_period_is_skipped_and_clears_baseline():
    d = _established_driver(t0=1_000_000.0)
    # A normal period first, to establish real state.
    _close_period(d, count=21, span_s=60.0, t0=1_000_000.0)
    assert d.stats['pct_good_all'] is not None
    first_pct = d.stats['pct_good_all']
    RtldavisDriver._reset_stats(d)

    # Child respawns mid-period: curr_cnt drops below last_cnt.
    d.stats['curr_cnt'][0] = 3  # far below last_cnt (22), a reset, not RF-dead
    d.stats['last_pkt_ts'][0] = 1_000_100.0  # a post-reset packet did arrive
    RtldavisDriver._update_summaries(d)

    assert d.stats['prev_pkt_ts'][0] == 0.0, "reset must clear prev_pkt_ts"
    assert d.stats['last_pkt_ts'][0] == 0.0, "reset must clear last_pkt_ts"
    # pct_good_all was reset to None by _reset_stats and never recomputed
    # this period (total_max_count stays 0 -- no transmitter contributed).
    assert d.stats['pct_good_all'] is None

    # Next period re-establishes a fresh baseline and computes correctly.
    RtldavisDriver._reset_stats(d)
    _close_period(d, count=21, span_s=60.0, t0=1_000_200.0)
    assert d.stats['max_count'][0] == 21
    assert d.stats['pct_good'][0] == 100.0
    assert first_pct == 100.0  # sanity: unaffected by the later reset


# ── Property: count <= max_count always, for arbitrary jittered archive events ──

def test_count_never_exceeds_max_count_across_jittered_periods():
    """For any sequence of accepted-packet timestamps on the 2.8125s lattice,
    with archive events firing at arbitrary jitter around each 60s boundary,
    count[i] <= max_count[i] must hold every period -- the property that
    makes rxCheckPercent > 100% impossible by construction.

    #402: packets go through the real _update_stats. This loop used to copy
    the seeding inline, bug included, and passed only because seed 317 drops
    a packet in the first period; 68 of seeds 0-199 did not."""
    rng = random.Random(317)  # deterministic
    d = _make_driver()
    t = 1_000_000.0
    d.stats['curr_cnt'][0] = 0
    d.stats['last_cnt'][0] = 0
    d.stats['last_ts'] = int(t)

    slot = LOOP_TIME
    with _fake_clock() as clock:
        for _period in range(500):
            # Advance by ~60s of real slots (occasionally drop a slot, simulating
            # a missed packet), landing the archive event at a jittered instant.
            span = 60.0 + rng.uniform(-1.0, 1.0)
            n_slots = round(span / slot)
            packets_this_period = 0
            elapsed = 0.0
            while elapsed + slot <= span:
                elapsed += slot
                if rng.random() > 0.05:  # 95% reception -- occasional drop
                    clock[0] = t + elapsed
                    RtldavisDriver._update_stats(
                        d, d.stats['curr_cnt'][0] + 1, 0, 0, 0)
                    packets_this_period += 1
            t += span
            clock[0] = t
            RtldavisDriver._update_summaries(d)
            if d.stats['count'][0] > 0:
                assert d.stats['count'][0] <= d.stats['max_count'][0], (
                    "count exceeded max_count -- rxCheckPercent > 100%% became "
                    "possible again (period %d, n_slots=%d, packets=%d)"
                    % (_period, n_slots, packets_this_period))
            RtldavisDriver._reset_stats(d)


# ── Cold start and counter reset, through the real _update_stats (#402) ─────
# DATA lines arrive at exact loop-period spacing (the ISS clock is exact,
# S115), and each archive boundary runs the same two calls
# new_archive_record makes.

T0 = 1_000_000.0  # driver start


def _go_lines(first_line, n, first_count=2, missed=()):
    """(arrival time, cumulative count) of the DATA lines a Go child emits
    over n slots from first_line, skipping the slot indexes in `missed`.

    Go counts every packet it accepts but emits none during its init phase,
    and one transmitter's first packet is what ends init (main.go). So the
    first emitted line already carries count 2. first_count=1 is the simpler
    model the S145 audit simulated; both must read exactly."""
    lines = []
    count = first_count
    for k in range(n):
        if k in missed:
            continue
        lines.append((first_line + k * LOOP_TIME, count))
        count += 1
    return lines


def _run(lines, boundaries):
    """Cold-start a driver and feed it `lines` and archive `boundaries` in
    time order. Returns (pct_good, count, max_count) per boundary, or None
    where the period produced no value, so no rxCheckPercent is written."""
    d = _make_driver()
    events = sorted([(t, False, c) for t, c in lines] +
                    [(b, True, 0) for b in boundaries])
    out = []
    with _fake_clock() as clock:
        for t, is_boundary, cnt in events:
            clock[0] = t
            if not is_boundary:
                RtldavisDriver._update_stats(d, cnt, 0, 0, 0)
                continue
            RtldavisDriver._update_summaries(d)
            pct = d.stats['pct_good'][0]
            out.append(None if pct is None else
                       (pct, d.stats['count'][0], d.stats['max_count'][0]))
            RtldavisDriver._reset_stats(d)
    return out


FULL = (100.0, 21, 21)  # 21 lines over 21 slots: a fully received period


def test_cold_start_seed_after_the_skipped_first_boundary_reads_100_pct():
    """Go's US init takes about 128 s (DEC-0136), so the first line nearly
    always lands after the first archive boundary, which computes nothing.
    Before #402 a 4-line first period read 133% and a full one 104.8%, or
    167% and 109.5% with Go's count-2 first line."""
    boundaries = [T0 + 20 + 60 * k for k in range(5)]
    cases = (
        (T0 + 131.0, [None, None, (100.0, 3, 3), FULL, FULL]),
        (T0 + 140.8125, [None, None, None, FULL, FULL]),
    )
    for first_line, expected in cases:
        for first_count in (2, 1):
            out = _run(_go_lines(first_line, 60, first_count), boundaries)
            assert out == expected, (first_line - T0, first_count, out)


def test_cold_start_seed_before_the_skipped_first_boundary_reads_100_pct():
    """A child that syncs inside the first archive period (EU init is about
    16 s). The skipped boundary moved last_cnt but not prev_pkt_ts, so before
    #402 the next delta spanned both periods: 21/34 = 61.8%."""
    boundaries = [T0 + 50 + 60 * k for k in range(3)]
    for first_count in (2, 1):
        out = _run(_go_lines(T0 + 12.8125, 56, first_count), boundaries)
        assert out == [None, FULL, FULL], (first_count, out)


def test_first_period_after_a_counter_reset_reads_100_pct():
    """A hot swap respawns the child and its counter restarts. The boundary
    that sees the counter go backward is skipped and clears the baseline;
    before #402 the period after it read 22/21 = 104.8%."""
    boundaries = [T0 + 50 + 60 * k for k in range(5)]
    swap = T0 + 130.0
    for first_count in (2, 1):
        old = [ln for ln in _go_lines(T0 + 12.8125, 60, first_count)
               if ln[0] < swap]
        new = _go_lines(T0 + 150.5, 50, first_count)
        out = _run(old + new, boundaries)
        assert out == [None, FULL, None, FULL, FULL], (first_count, out)


def test_a_period_holding_only_the_seed_writes_no_rxcheckpercent():
    """One line spans no slots, so there is nothing to measure. That period
    must produce no value at all, rather than 100% or 200%, and the period
    after it must still read exactly."""
    boundaries = [T0 + 20 + 60 * k for k in range(4)]
    for first_count in (2, 1):
        out = _run(_go_lines(T0 + 138.5, 22, first_count), boundaries)
        assert out == [None, None, None, FULL], (first_count, out)


def test_a_missed_slot_in_the_first_period_is_still_counted():
    """Positive control: the fix must not force the first period to 100%.
    One slot missed after the seed reads exactly 20 of 21. Before #402 the
    over-count hid it: 22/21 = 104.8%."""
    boundaries = [T0 + 20 + 60 * k for k in range(5)]
    out = _run(_go_lines(T0 + 140.8125, 43, missed=(10,)), boundaries)
    assert out[:3] == [None, None, None]
    assert out[3][1:] == (20, 21)
    assert out[3][0] == pytest.approx(100.0 * 20 / 21)
    assert out[4] == FULL


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print("  [PASS] %s" % name)
            except Exception as e:
                fails += 1
                print("  [FAIL] %s -> %r" % (name, e))
    total = sum(1 for n in globals() if n.startswith('test_'))
    print("\n%d/%d passed" % (total - fails, total))
    sys.exit(1 if fails else 0)
