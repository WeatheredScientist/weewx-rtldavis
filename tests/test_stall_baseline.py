"""Offline tests for ops/stall_baseline.py — the DEC-0083 stall-rate readout.

This tool answers "is the stall rate actually unusual?", and S75 showed the cost
of getting that wrong by eye. Its whole value rests on ONE transformation: raw
`rtldavis process stalled` lines are collapsed into episodes, because the 150 s
watchdog re-raises every ~3 m 40 s for as long as an episode lasts. Get that
wrong and 2026-08-02 scores as 21 events instead of 1, which would swamp every
comparison the tool exists to make.

POSITIVE CONTROLS (DEC-0045 — a passing test proves nothing if the assertion is
wrong):

  * test_control_raw_line_count_would_be_wrong asserts that NOT clustering gives
    a materially different (and wrong) answer. If clustering ever silently
    becomes a no-op, this is what goes red.
  * test_control_ground_truth_from_dec0081 replays the real 2026-08-10/11 night
    and asserts the clusterer recovers the episode boundaries DEC-0081 derived
    independently, from forensic capture sets rather than from this method.

Fixtures are the REAL measured stamps pulled from the NAS rotations at S76, not
invented ones.

Run:  .venv/bin/python -m pytest tests/test_stall_baseline.py
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ops"))
import stall_baseline as sb  # noqa: E402


def ts(*args: str) -> list[datetime]:
    return [datetime.strptime(a, "%Y-%m-%d %H:%M:%S") for a in args]


# The real 08-02 serial-respawn burst (ERR-0005): 21 lines, ~3m40s apart, one event.
BURST_0802 = ts(
    "2026-08-02 00:11:13", "2026-08-02 00:14:53", "2026-08-02 00:18:33",
    "2026-08-02 00:22:13", "2026-08-02 00:25:54", "2026-08-02 00:29:35",
    "2026-08-02 00:33:15", "2026-08-02 00:36:56", "2026-08-02 00:40:36",
    "2026-08-02 00:44:16", "2026-08-02 00:47:57", "2026-08-02 00:51:38",
    "2026-08-02 00:55:19", "2026-08-02 00:58:59", "2026-08-02 01:02:38",
    "2026-08-02 01:06:18", "2026-08-02 01:09:57", "2026-08-02 01:13:37",
    "2026-08-02 01:17:17", "2026-08-02 01:20:56", "2026-08-02 01:27:03",
)

# The 08-10/11 night. DEC-0081 derived TWO episodes here from forensic capture
# sets (23:52->00:01 and 01:49->02:14) — independently of this clustering method.
NIGHT_0810 = ts(
    "2026-08-10 23:56:40", "2026-08-11 01:51:46", "2026-08-11 01:58:31",
)


def test_serial_respawn_burst_is_one_episode() -> None:
    """21 stall lines from one RF-dead episode must collapse to one event."""
    eps = sb.cluster(BURST_0802, 30)
    assert len(eps) == 1
    assert len(eps[0]) == 21


def test_control_raw_line_count_would_be_wrong() -> None:
    """Positive control: unclustered, the same burst reads as 21 events.

    If this stops holding, clustering has become a no-op and every other
    assertion in this file is proving nothing.
    """
    assert len(BURST_0802) == 21
    assert len(sb.cluster(BURST_0802, 30)) != len(BURST_0802)


def test_control_ground_truth_from_dec0081() -> None:
    """Recover DEC-0081's independently-derived boundaries for 08-10/11.

    DEC-0081 read these two episodes off forensic capture sets and the monitor
    log, not off this clusterer. Agreement is therefore evidence about the
    method, not a restatement of it.
    """
    eps = sb.cluster(NIGHT_0810, 30)
    assert len(eps) == 2
    assert eps[0][0] == datetime(2026, 8, 10, 23, 56, 40)
    assert len(eps[0]) == 1
    assert eps[1][0] == datetime(2026, 8, 11, 1, 51, 46)
    assert len(eps[1]) == 2


def test_episode_count_is_stable_across_thresholds() -> None:
    """The verdict must not rest on one arbitrary cut (30/45/60 min agree)."""
    combined = sorted(BURST_0802 + NIGHT_0810)
    counts = {th: len(sb.cluster(combined, th)) for th in (30, 45, 60)}
    assert len(set(counts.values())) == 1, counts


def test_the_two_failure_classes_have_distinct_signatures() -> None:
    """`not running` must never be folded into the RF-dead stall class.

    DEC-0081/S62 separate them: `stalled` is a mute-or-emitting child under a
    live driver; `is not running` is the driver process gone, the no-reset path,
    and the strictly-worse mode ERR-0005 hit after reset #10. A future widening
    of the grep that made one match the other would merge two failure modes the
    whole diagnosis depends on keeping apart.
    """
    assert sb.STALL_SIG not in sb.NOTRUN_SIG
    assert sb.NOTRUN_SIG not in sb.STALL_SIG
    line = "2026-08-02 00:11:13,992 weewxd CRITICAL Caught WeeWxIOError: " + sb.NOTRUN_SIG
    assert sb.STALL_SIG not in line


def test_stamps_ignores_unparseable_lines() -> None:
    """A malformed line is dropped, never silently dated to now."""
    good = "2026-08-02 00:11:13,992 weewxd CRITICAL Caught WeeWxIOError: stalled"
    assert sb.stamps([good, "", "garbage", "not a timestamp"]) == \
        [datetime(2026, 8, 2, 0, 11, 13)]


def test_cluster_handles_empty_input() -> None:
    assert sb.cluster([], 30) == []


def test_window_start_uses_oldest_rotation() -> None:
    """Left-censored at the oldest surviving rotation, not the newest.

    Shared with ops/freeze_baseline.py (extracted S77) -- both tools must
    agree on where history starts.
    """
    files = ["weewx.log", "weewx.log.2026-08-05", "weewx.log.2026-07-20"]
    assert sb.window_start(files, [datetime(2026, 8, 1)]) == \
        datetime(2026, 7, 20)


def test_window_start_falls_back_to_first_stall_with_no_rotations() -> None:
    first_stall = datetime(2026, 8, 1, 12, 0)
    assert sb.window_start(["weewx.log"], [first_stall]) == first_stall
