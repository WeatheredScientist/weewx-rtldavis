"""Driver side of #459 (DEC-0223): Go's burst-gate lines become INFO counters.

The gate itself is Go's (patch/rtldavis-burstgate.patch). The driver counts the
frames it dropped, logs each one's bytes (they are rare and show which copy of a
burst was corrupt), and reports the largest duplicate gap per period: the live
check that real copies sit far inside the gate's window. Nothing here influences
which frames are accepted.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest  # noqa: E402
import rtldavis  # noqa: E402
from rtldavis import RtldavisDriver, parse_burst_line  # noqa: E402
from test_duplicate_frame_counter import _make_driver, run_loop  # noqa: E402  (shared weewx stubs)


@pytest.mark.parametrize("line,want", [
    ("2026/10/28 09:00:00 burst copy: E401BD56010ED10E (+3 smp)", ("copy", 3)),
    ("burst conflict: E401BD56010ED10F (+0 smp)", ("conflict", 0)),
    ("2026/10/28 09:00:00 duplicate packet: E401BD56010ED10E (0.002 s) (+8 smp)\n", ("duplicate", 8)),
])
def test_parses_the_lines_go_emits(line, want):
    assert parse_burst_line(line) == want


@pytest.mark.parametrize("line", [
    "",
    "duplicate packet: E401BD56010ED10E (0.002 s)",        # a binary without the gate
    "duplicate packet: E401BD56010ED10E (0.002 s) (+-1 smp)",
    "burst copy: E401BD56010ED10E",                        # gap missing
    "burst copy: e401bd56 (+3 smp)",                       # Go prints upper-case hex
    "burst copy: E401BD56010ED10E (+3 smp) trailing",
    "burst copy: E401BD56010ED10E junk (+3 smp)",
    "duplicate packet: E401BD56010ED10E (soon) (+3 smp)",
    "repeat packet: E401BD56010ED10E (2.812 s)",
    "crc_stats: crc_fail=5 near=2 slots=17:3",
])
def test_any_other_line_is_ignored(line):
    assert parse_burst_line(line) is None


def test_summary_line_is_logged_every_period_and_resets(monkeypatch):
    d = _make_driver()
    logged = []
    monkeypatch.setattr(rtldavis, 'loginf', lambda msg: logged.append(msg))
    RtldavisDriver._update_summaries(d)
    assert any(m == "burst copies this period: 0 (conflicts: 0) largest duplicate gap: - smp"
               for m in logged), logged
    d.stats.update(burst_copy=2, burst_conflict=1, dup_gap_max=9)
    logged.clear()
    RtldavisDriver._update_summaries(d)
    assert any(m == "burst copies this period: 2 (conflicts: 1) largest duplicate gap: 9 smp"
               for m in logged), logged
    RtldavisDriver._reset_stats(d)
    assert (d.stats['burst_copy'], d.stats['burst_conflict'], d.stats['dup_gap_max']) == (0, 0, None)


def test_the_real_line_scan_counts_and_logs_each_drop(monkeypatch):
    """genLoopPackets' own scan: copies and conflicts are counted and each one is
    logged with its line; duplicates still count as before and feed the gap."""
    logged = []
    monkeypatch.setattr(rtldavis, 'loginf', lambda msg: logged.append(msg))
    d, _ = run_loop(monkeypatch, [
        ["2026/10/28 09:00:00 duplicate packet: E401BD56010ED10E (0.002 s) (+3 smp)\n",
         "2026/10/28 09:00:00 burst copy: E401BD56010ED10F (+5 smp)\n",
         "2026/10/28 09:00:03 duplicate packet: E401BD56010ED10E (0.004 s) (+11 smp)\n"],
        ["2026/10/28 09:00:06 burst conflict: 1122334455667788 (+2 smp)\n",
         "DATA 21.5 100\n"],
    ])
    assert d.stats['dup_count'] == 2
    assert d.stats['dup_gap_max'] == 11
    assert (d.stats['burst_copy'], d.stats['burst_conflict']) == (1, 1)
    drops = [m for m in logged if m.startswith("Go burst gate dropped a frame:")]
    assert len(drops) == 2 and "E401BD56010ED10F" in drops[0] and "1122334455667788" in drops[1]
