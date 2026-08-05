"""Offline tests for ops/campaign_analyze.py — the DEC-0069 freeze-aware metric.

This tool decides which reception records count toward a campaign arm's mean, and
that mean is what a ≥2.0-point adoption decision is read off (DEC-0059). A wrong
exclusion rule does not crash; it quietly moves a number that a hardware decision
rests on. So the fixtures below are the REAL measured records from the two
DEC-0068 freezes on 2026-08-04, not invented ones.

POSITIVE CONTROLS (DEC-0045 — a passing test proves nothing if the assertion is
wrong, and this repo's secret gate was green-and-wrong for nine sessions):

  * test_control_uncleaned_mean_is_measurably_wrong asserts the UNCLEANED mean is
    displaced by a freeze. If that ever stops being true, the fixture has lost its
    teeth and every other test here is proving nothing.
  * test_control_magnitude_rule_would_discard_a_real_fade asserts that the
    rejected design (drop anything below a threshold) destroys a genuine deep
    fade that the structural rule correctly keeps.

Run:  python3 -m pytest tests/test_campaign_analyze.py
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ops"))
import campaign_analyze as ca  # noqa: E402

MIN = 60


def _rec(minute, rx, interval=1):
    """Record at `minute` minutes past an arbitrary fixed epoch."""
    return ca.Rec(1785879600 + minute * MIN, interval, rx)


# The measured 2026-08-04 17:48 freeze, exactly as read from the archive DB:
# 17:47 fine, 17:48 truncated, 17:49-17:51 absent entirely, 17:52 fine.
FREEZE_1 = [
    _rec(0, 77.27), _rec(1, 66.67), _rec(2, 60.0), _rec(3, 80.0),
    _rec(4, 77.27), _rec(5, 80.0), _rec(6, 60.0), _rec(7, 72.73),
    _rec(8, 10.31),                        # <- the truncated freeze-start record
    #  minutes 9, 10, 11 are ABSENT (the freeze itself)
    _rec(12, 87.5), _rec(13, 77.27), _rec(14, 90.0), _rec(15, 80.0),
]


def test_gap_adjacent_flags_both_sides_of_a_gap():
    idx = ca.gap_adjacent(FREEZE_1)
    # index 8 is the 10.31 record (before the gap); index 9 is 87.5 (after it)
    assert 8 in idx
    assert 9 in idx
    assert 7 not in idx          # 72.73, a full minute before the gap, is clean
    assert 10 not in idx         # 77.27, a full minute after, is clean


def test_measured_freeze_record_is_excluded_and_neighbours_survive():
    keep, drop = ca.partition(FREEZE_1)
    kept_rx = [r.rx for r in keep]
    assert 10.31 not in kept_rx
    assert 72.73 in kept_rx      # the good minute BEFORE the freeze is preserved
    assert 77.27 in kept_rx      # and the good minute two after it
    reasons = {e.reason for e in drop}
    assert reasons == {"gap-adjacent"}


def test_absent_minutes_need_no_handling():
    """The freeze minutes are missing rows, not zero rows — nothing to exclude.

    This is the finding that shrank the whole design: BOOT.md assumed the freeze
    minutes scored as zeros and cost ~0.8 points. They are simply not in the DB.
    """
    keep, drop = ca.partition(FREEZE_1)
    assert len(keep) + len(drop) == len(FREEZE_1) == 13
    assert all(r.rx is not None and r.rx > 50 for r in keep)


def test_nonphysical_record_is_excluded():
    """The measured 2026-07-29 03:10 record: rxCheckPercent = 200.0.

    A record that absorbed a 2-minute span while still stamped interval=1.
    summarize_reception_rows() applies no cap, so it would contribute twice its
    expected packets.
    """
    recs = [_rec(0, 75.0), _rec(1, 200.0), _rec(2, 75.0)]
    keep, drop = ca.partition(recs)
    assert [r.rx for r in keep] == [75.0, 75.0]
    assert [e.reason for e in drop] == ["nonphysical"]


def test_null_rx_is_excluded_as_restart_artifact():
    recs = [_rec(0, 75.0), _rec(1, None), _rec(2, 75.0)]
    keep, drop = ca.partition(recs)
    assert len(keep) == 2
    assert [e.reason for e in drop] == ["null"]


def test_nonphysical_takes_priority_over_gap_adjacent():
    """Reason labels must not depend on rule order silently.

    The 200% record is BOTH non-physical and gap-adjacent (it follows the gap it
    absorbed). It should be reported under the more specific cause.
    """
    recs = [_rec(0, 75.0), _rec(5, 200.0), _rec(6, 75.0)]
    _, drop = ca.partition(recs)
    by_ts = {e.ts: e.reason for e in drop}
    assert by_ts[_rec(5, 0).ts] == "nonphysical"


# ── Positive controls ────────────────────────────────────────────────────────

def test_control_uncleaned_mean_is_measurably_wrong():
    """THE CONTROL. If a freeze does NOT displace the uncleaned mean, the fixture
    is toothless and every assertion above is vacuous.

    A 6 h arm block at 1 record/min with one freeze in it, built from the real
    measured values.
    """
    block = [_rec(i, 75.0) for i in range(360)]
    block[100] = _rec(100, 10.31)                    # the truncated record
    del block[101:104]                               # the absent freeze minutes
    keep, _ = ca.partition(block)

    raw_mean = sum(r.rx for r in block) / len(block)
    clean_mean = sum(r.rx for r in keep) / len(keep)

    assert clean_mean == 75.0                        # cleaned is undisplaced
    assert raw_mean < clean_mean                     # uncleaned is dragged down
    # ~0.18 pts on a 6 h block — real, and an order below the 2.0-pt bar
    assert 0.1 < (clean_mean - raw_mean) < 0.3


def test_control_magnitude_rule_would_discard_a_real_fade():
    """THE SECOND CONTROL — why the rejected design is wrong.

    A genuine deep fade (30%) that is NOT adjacent to any gap must survive. A
    'drop anything under 40%' rule would delete it and bias the arm upward; the
    structural rule keeps it, which is the whole argument for structure over
    magnitude.
    """
    recs = [_rec(0, 75.0), _rec(1, 30.0), _rec(2, 75.0)]
    keep, drop = ca.partition(recs)
    assert 30.0 in [r.rx for r in keep]
    assert drop == []
    # the positive half of the control: a magnitude rule DOES destroy it
    assert [r.rx for r in recs if r.rx >= 40.0] == [75.0, 75.0]


# ── Block parsing ────────────────────────────────────────────────────────────

SWAP_LOG = [
    "2026-07-30 00:05:03 tick: swapping NONE -> A",
    "2026-07-30 06:05:02 tick: swapping A -> B",
    "2026-07-30 12:05:02 tick: swapping B -> C",
    "2026-08-02 00:08:21 ABORT: container did not produce records",
]


def test_parse_blocks_applies_settle_and_closes_on_next_event():
    blocks = ca.parse_blocks(SWAP_LOG, settle_s=600)
    assert [b.arm for b in blocks] == ["A", "B", "C"]
    a = blocks[0]
    assert a.start - a.raw_start == 600           # settle window applied
    assert a.end == blocks[1].raw_start           # closes at the next swap
    assert blocks[-1].end == ca._epoch("2026-08-02 00:08:21")   # ABORT ends it


def test_parse_blocks_tolerates_nasctl_line_number_prefix():
    """`nasctl grep` prefixes 'NNN:'; a direct ssh grep does not. A parser that
    only handled one of the two ways we read this log would be a trap."""
    prefixed = [f"{i}:{line}" for i, line in enumerate(SWAP_LOG, 1)]
    assert ca.parse_blocks(prefixed, 600) == ca.parse_blocks(SWAP_LOG, 600)


def test_parse_blocks_ignores_baseline_terminator():
    log = SWAP_LOG[:1] + ["2026-07-30 02:00:00 tick: swapping A -> BASELINE"]
    blocks = ca.parse_blocks(log, settle_s=0)
    assert [b.arm for b in blocks] == ["A"]


def test_attempt_starts_detects_the_real_campaign_a_false_start():
    """Campaign A aborted on 07-29 and restarted clean on 07-30.

    Pooling the two silently unbalanced the square -- arm B carried ~60 extra
    records while the table still looked tidy. This is the mechanical detector
    for that condition.
    """
    log = [
        "2026-07-29 10:50:04 tick: swapping NONE -> B",
        "2026-07-29 12:05:14 tick: swapping B -> C",
        "2026-07-29 12:13:27 ABORT: container did not produce records",
        "2026-07-30 00:05:03 tick: swapping NONE -> A",
        "2026-07-30 06:05:02 tick: swapping A -> B",
    ]
    assert ca.attempt_starts(log) == [ca._epoch("2026-07-29 10:50:04"),
                                      ca._epoch("2026-07-30 00:05:03")]


def test_attempt_starts_is_singular_for_an_uninterrupted_campaign():
    """The control: no abort, no warning. If this ever returns >1 the detector
    would cry wolf on every clean run and get ignored."""
    assert len(ca.attempt_starts(SWAP_LOG[:3])) == 1


def test_summarize_reports_clean_and_raw_side_by_side():
    blocks = [ca.Block("A", _rec(0, 0).ts, _rec(16, 0).ts, _rec(0, 0).ts)]
    stats = ca.summarize(FREEZE_1, blocks)
    assert len(stats) == 1
    s = stats[0]
    assert s.arm == "A"
    assert s.n < s.raw_n                 # exclusions actually removed records
    assert s.mean > s.raw_mean           # and the raw figure was dragged down


if __name__ == "__main__":
    sys.exit(os.system(f"python3 -m pytest -q {__file__}"))
