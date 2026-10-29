"""Driver side of #458: the Go `crc_stats:` summary line becomes an INFO counter.

Measurement only. Nothing here may influence which frames are accepted; these
tests pin the strict parse (a foreign or malformed line is ignored, never
half-counted) and the per-period accounting.
"""
import os

import pytest  # noqa: E402
import rtldavis  # noqa: E402
from rtldavis import RtldavisDriver, parse_crc_stats  # noqa: E402
from test_duplicate_frame_counter import _make_driver  # noqa: E402  (shared weewx stubs)


def test_parses_the_line_go_emits():
    line = "2026/10/18 19:40:00 crc_stats: crc_fail=5 near=2 slots=17:3,22:2"
    assert parse_crc_stats(line) == (5, 2, {17: 3, 22: 2})


def test_zero_period_line_parses():
    assert parse_crc_stats("crc_stats: crc_fail=0 near=0 slots=-") == (0, 0, {})


@pytest.mark.parametrize("line", [
    "",
    "duplicate packet: 0123456789ABCDEF (0.002 s)",
    "crc_stats: crc_fail=5 near=2",                        # slots missing
    "crc_stats: crc_fail=x near=2 slots=-",                # non-numeric
    "crc_stats: crc_fail=5 near=2 slots=17:3,",            # trailing comma
    "crc_stats: crc_fail=5 near=2 slots=17",               # slot without count
    "crc_stats: crc_fail=5 near=9 slots=-",                # near > fail is impossible
    "crc_stats: crc_fail=-1 near=0 slots=-",               # negative
    "crc_stats: crc_fail=5 near=2 slots=17:3 garbage",     # trailing junk
])
def test_malformed_or_foreign_lines_are_ignored(line):
    assert parse_crc_stats(line) is None


def test_init_and_reset_zero_the_counters():
    d = _make_driver()
    assert (d.stats['crc_fail'], d.stats['crc_near'], d.stats['crc_slots']) == (0, 0, {})
    d.stats['crc_fail'], d.stats['crc_near'], d.stats['crc_slots'] = 7, 3, {1: 7}
    d.stats['curr_ts'] = 1
    RtldavisDriver._reset_stats(d)
    assert (d.stats['crc_fail'], d.stats['crc_near'], d.stats['crc_slots']) == (0, 0, {})


def test_summary_logs_at_info_every_period_even_when_quiet(monkeypatch):
    d = _make_driver()
    logged = []
    monkeypatch.setattr(rtldavis, 'loginf', lambda msg: logged.append(msg))
    RtldavisDriver._update_summaries(d)
    assert any('crc failures this period: 0 (near an accepted frame: 0) slots: -' in m for m in logged)


def test_summary_reports_accumulated_counts(monkeypatch):
    d = _make_driver()
    logged = []
    monkeypatch.setattr(rtldavis, 'loginf', lambda msg: logged.append(msg))
    for line in ("crc_stats: crc_fail=3 near=1 slots=4:2,9:1", "crc_stats: crc_fail=2 near=2 slots=4:2"):
        fail, near, slots = parse_crc_stats(line)
        d.stats['crc_fail'] += fail
        d.stats['crc_near'] += near
        for s, n in slots.items():
            d.stats['crc_slots'][s] = d.stats['crc_slots'].get(s, 0) + n
    RtldavisDriver._update_summaries(d)
    assert any('crc failures this period: 5 (near an accepted frame: 3) slots: 4:4,9:1' in m for m in logged)


def test_the_driver_loop_consumes_the_line_without_touching_packet_flow():
    """The stderr loop must only add to counters. Pin that the crc branch assigns
    nothing but self.stats and never continues/breaks/skips the line."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rtldavis.py")).read()
    start = src.index("_crc = parse_crc_stats(_line)")
    end = src.index('if "repeat packet:" in _line:', start)
    block = src[start:end]
    for banned in ("continue", "break", "return", "lines.remove", "lines.pop", "del "):
        assert banned not in block, "crc stats branch must not alter packet flow: %r" % banned
