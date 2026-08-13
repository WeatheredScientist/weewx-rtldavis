"""Offline tests for ops/freeze_baseline.py — the DEC-0083 freeze-rate readout.

This tool's whole value rests on getting the three-way split right: a >150s
archive gap is RF-dead, a scheduled arm swap, or a freeze, and getting any of
those wrong either hides a real RF episode inside "freeze" or inflates the
freeze rate with expected downtime.

POSITIVE CONTROLS (DEC-0045 — a passing test proves nothing if the assertion
is wrong):

  * test_control_unfiltered_interval_would_be_wrong asserts that skipping the
    interval=1 filter gives a materially different (and wrong) answer — the
    exact S37 backfill trap BACKLOG.md documents.
  * test_rf_dead_takes_precedence_over_swap_slot asserts the classification
    ORDER matters, not just that each check works in isolation.

Run:  .venv/bin/python -m pytest tests/test_freeze_baseline.py
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ops"))
import freeze_baseline as fb  # noqa: E402


def ts(*args: str) -> list[datetime]:
    return [datetime.strptime(a, "%Y-%m-%d %H:%M:%S") for a in args]


def test_find_gaps_only_returns_gaps_over_threshold() -> None:
    t = ts("2026-08-01 00:00:00", "2026-08-01 00:01:00",  # 60s, not a gap
           "2026-08-01 00:10:00")                          # 540s, a gap
    gaps = fb.find_gaps(t, fb.GAP_SEC)
    assert len(gaps) == 1
    assert gaps[0][2] == 540.0


def test_per_minute_drops_non_unit_interval_rows() -> None:
    rows = [(datetime(2026, 7, 13, 0, 0), "1"),
            (datetime(2026, 7, 13, 0, 15), "15"),   # S37 backfill row
            (datetime(2026, 7, 13, 0, 30), "15"),
            (datetime(2026, 7, 13, 0, 31), "1")]
    clean, dropped = fb.per_minute(rows)
    assert dropped == 2
    assert clean == [datetime(2026, 7, 13, 0, 0), datetime(2026, 7, 13, 0, 31)]


def test_control_unfiltered_interval_would_be_wrong() -> None:
    """Positive control: without the interval=1 filter, a run of interval=15
    backfill rows reads as phantom ~900s freezes that never happened.
    """
    rows = [(datetime(2026, 7, 13, 0, 0), "1"),
            (datetime(2026, 7, 13, 0, 15), "15"),
            (datetime(2026, 7, 13, 0, 30), "15"),
            (datetime(2026, 7, 13, 0, 45), "15")]
    unfiltered_gaps = fb.find_gaps([dt for dt, _ in rows], fb.GAP_SEC)
    clean, _ = fb.per_minute(rows)
    filtered_gaps = fb.find_gaps(clean, fb.GAP_SEC)
    assert len(unfiltered_gaps) == 3          # three phantom 900s "freezes"
    assert len(filtered_gaps) == 0            # correctly nothing, once dropped


def test_is_rf_dead_within_pad() -> None:
    stalls = ts("2026-08-10 23:58:00")
    a, b = ts("2026-08-10 23:52:00", "2026-08-11 00:01:00")
    assert fb.is_rf_dead(a, b, stalls, pad_min=5) is True


def test_is_rf_dead_false_when_stall_too_far_outside_pad() -> None:
    stalls = ts("2026-08-10 20:00:00")
    a, b = ts("2026-08-10 23:52:00", "2026-08-11 00:01:00")
    assert fb.is_rf_dead(a, b, stalls, pad_min=5) is False


def test_is_swap_slot_matches_the_real_schedule() -> None:
    # ops/rx_experiment.sh SCHEDULE rows are always "<hour>:05" at 00/06/12/18.
    for hh in ("00", "06", "12", "18"):
        assert fb.is_swap_slot(
            datetime.strptime(f"2026-08-13 {hh}:07:00", "%Y-%m-%d %H:%M:%S"),
            restarts=[])


def test_is_swap_slot_false_off_schedule_with_no_restart_evidence() -> None:
    assert fb.is_swap_slot(datetime(2026, 8, 13, 3, 5), restarts=[]) is False
    assert fb.is_swap_slot(datetime(2026, 8, 13, 0, 45), restarts=[]) is False


def test_is_logged_restart_catches_the_s79_ad_hoc_case() -> None:
    """The actual event that found this gap: the S79 abort-recovery self-heal
    logged `tick: swapping A -> H` at 10:25:01, off the fixed 0/6/12/18
    schedule entirely. The archive gap it caused started at 10:24 — a minute
    *before* the log line, which is why the padding is asymmetric.
    """
    restarts = ts("2026-08-13 10:25:01")
    gap_start = datetime(2026, 8, 13, 10, 24, 0)
    assert fb.is_logged_restart(gap_start, restarts) is True
    assert fb.is_swap_slot(gap_start, restarts) is True


def test_control_without_restart_evidence_the_s79_case_reads_as_freeze() -> None:
    """Positive control: the exact same gap, with no restart log data (the
    tool's behavior before this fix), is NOT recognized as a swap — proving
    the assertion above is checking something real, not a tautology. This is
    the actual 2026-08-13 10:24 misclassification that motivated the fix.
    """
    gap_start = datetime(2026, 8, 13, 10, 24, 0)
    assert fb.is_swap_slot(gap_start, restarts=[]) is False


def test_is_logged_restart_respects_the_pad_boundaries() -> None:
    r = ts("2026-08-13 10:25:00")
    just_inside_before = datetime(2026, 8, 13, 10, 22, 0)   # -3min
    just_outside_before = datetime(2026, 8, 13, 10, 21, 59)  # -3min01s
    just_inside_after = datetime(2026, 8, 13, 10, 37, 0)    # +12min
    just_outside_after = datetime(2026, 8, 13, 10, 37, 1)   # +12min01s
    assert fb.is_logged_restart(just_inside_before, r) is True
    assert fb.is_logged_restart(just_outside_before, r) is False
    assert fb.is_logged_restart(just_inside_after, r) is True
    assert fb.is_logged_restart(just_outside_after, r) is False


def test_is_logged_restart_false_when_nowhere_near_any_restart() -> None:
    restarts = ts("2026-08-13 10:25:01")
    assert fb.is_logged_restart(datetime(2026, 8, 13, 15, 0, 0), restarts) is False


def test_rf_dead_takes_precedence_over_swap_slot() -> None:
    """A real RF outage landing on a swap slot must classify as RF-dead, not
    be absorbed into "just the swap" — BACKLOG.md's stated classification
    order.
    """
    a, b = ts("2026-08-13 00:04:00", "2026-08-13 00:09:00")
    stalls = ts("2026-08-13 00:06:00")   # inside the swap window
    gaps = [(a, b, (b - a).total_seconds())]
    rf, swap, freeze = fb.classify(gaps, stalls, restarts=[], pad_min=5)
    assert len(rf) == 1 and not swap and not freeze


def test_rf_dead_takes_precedence_over_a_logged_restart_too() -> None:
    """Same precedence rule, but via the new ad hoc path: a genuine outage
    that happens to overlap a logged restart's health-check window must still
    read as RF-dead, not swap.
    """
    a, b = ts("2026-08-13 10:24:00", "2026-08-13 10:30:00")
    stalls = ts("2026-08-13 10:26:00")        # inside the restart's window
    restarts = ts("2026-08-13 10:25:01")
    gaps = [(a, b, (b - a).total_seconds())]
    rf, swap, freeze = fb.classify(gaps, stalls, restarts, pad_min=5)
    assert len(rf) == 1 and not swap and not freeze


def test_control_ignoring_precedence_would_be_wrong() -> None:
    """Positive control: the same gap, checked swap-slot-first, would be
    misfiled — proving the precedence assertion above is checking something
    real, not a tautology.
    """
    a, b = ts("2026-08-13 00:04:00", "2026-08-13 00:09:00")
    assert fb.is_swap_slot(a, restarts=[]) is True
    stalls = ts("2026-08-13 00:06:00")
    assert fb.is_rf_dead(a, b, stalls, pad_min=5) is True


def test_silent_off_slot_gap_is_a_freeze() -> None:
    a, b = ts("2026-08-13 09:14:00", "2026-08-13 09:19:00")
    gaps = [(a, b, (b - a).total_seconds())]
    rf, swap, freeze = fb.classify(gaps, stalls=[], restarts=[], pad_min=5)
    assert not rf and not swap
    assert len(freeze) == 1


def test_classify_handles_empty_gaps() -> None:
    assert fb.classify([], [], [], pad_min=5) == ([], [], [])


def test_gap_duration_is_seconds_not_minutes() -> None:
    t = [datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 1, 0, 5)]
    gaps = fb.find_gaps(t, fb.GAP_SEC)
    assert gaps[0][2] == 300.0
