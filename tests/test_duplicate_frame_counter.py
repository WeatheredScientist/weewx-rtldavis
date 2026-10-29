"""Offline unit tests for the DEC-0035 duplicate-frame counter (S43).

DEC-0035 (S37) confirmed the Go demodulator double-decodes a single RF burst
~730 times/day on this station -- the mechanism behind phantom rain and
humidity/UV-spike corruption. Its own proposal: "a permanent, cheap counter
in the driver: tally duplicate-packet lines off the Go stderr stream and log
one summary line per archive period at INFO" -- no debug mode required.

These tests drive the real _init_stats / _reset_stats / _update_summaries
against a synthetic stats dict, and confirm the counter increments
unconditionally (no debug gate) on Go's own "duplicate packet:" stderr line,
is logged once per period at INFO, and resets for the next period.

weewx is not installed in the test/CI environment, so we stub it (same
pattern as test_reception_stats.py).

Run:  python3 -m pytest tests/ (pytest only)
"""

import rtldavis  # noqa: E402
from rtldavis import RtldavisDriver  # noqa: E402
from conftest import make_driver  # noqa: E402


_make_driver = make_driver


class _BatchMgr:
    """A ProcManager stand-in: get_stderr() hands genLoopPackets one batch of Go
    stderr lines per loop pass, then running() turns false."""

    def __init__(self, batches):
        self.batches = list(batches)

    def running(self):
        return bool(self.batches)

    def get_stderr(self):
        return iter([list(self.batches.pop(0))])

    def drain_stderr(self, max_lines=50):
        return []


def _fake_create(_driver, lines):
    """PacketFactory.create stand-in. A line `DATA <temp> <cnt0>` becomes a data
    dict carrying Go's cumulative counters, as real DATA packets do; anything
    else decodes to nothing. Drains `lines`, as the real one does."""
    for line in list(lines):
        parts = line.split()
        if parts[:1] == ['DATA']:
            yield {'temperature': float(parts[1]), 'curr_cnt0': int(parts[2]),
                   'curr_cnt1': 0, 'curr_cnt2': 0, 'curr_cnt3': 0}
    del lines[:]


def run_loop(monkeypatch, batches):
    """Run the REAL genLoopPackets over `batches` (one list of stderr lines per
    loop pass) until the fake process stops. Returns (driver, temperatures of
    the loop packets it yielded). Only the decode, the stats bookkeeping and the
    packet conversion are stubbed; the line scan and the dedup guard are the
    driver's own (#456, audit item 35)."""
    d = _make_driver()
    d._mgr = _BatchMgr(batches)
    d.tr_count = 1
    d._stderr_sample_count = 0
    d._hotswap_path = None
    d._last_pkt = None
    d._maybe_hotswap = lambda: False
    d._update_stats = lambda *a: None
    d._merge_pending_freq_fields = lambda data: None
    d._data_to_packet = lambda data: {'outTemp': data['temperature']}
    monkeypatch.setattr(rtldavis.PacketFactory, 'create', staticmethod(_fake_create))
    monkeypatch.setattr(rtldavis.time, 'time', lambda: 1_000_000.0)
    yielded = []
    try:
        for packet in d.genLoopPackets():
            yielded.append(packet['outTemp'])
    except rtldavis.weewx.WeeWxIOError as e:
        assert 'not running' in str(e), e
    return d, yielded


def test_init_stats_starts_dup_count_at_zero():
    d = _make_driver()
    assert d.stats['dup_count'] == 0


def test_counter_survives_into_the_period_summary_log(monkeypatch):
    """genLoopPackets increments self.stats['dup_count'] directly (the
    real code: `if "duplicate packet:" in _line: self.stats['dup_count'] += 1`).
    This test simulates that increment, then confirms _update_summaries logs
    it at INFO unconditionally -- not gated behind any debug flag."""
    d = _make_driver()
    logged = []
    monkeypatch.setattr(rtldavis, 'loginf', lambda msg: logged.append(msg))

    d.stats['dup_count'] = 3  # 3 "duplicate packet:" lines seen this period
    RtldavisDriver._update_summaries(d)

    assert any('duplicate frames this period: 3' in m for m in logged), \
        "the duplicate-frame count was not logged at INFO this period"


def test_zero_duplicates_still_logs_a_line():
    """DEC-0035: "log one summary line per archive period" -- a quiet period
    (0 duplicates) must still produce a line, so the instrument's silence is
    distinguishable from it not running at all."""
    d = _make_driver()
    logged = []
    import rtldavis as _r
    orig = _r.loginf
    _r.loginf = lambda msg: logged.append(msg)
    try:
        RtldavisDriver._update_summaries(d)
    finally:
        _r.loginf = orig
    assert any('duplicate frames this period: 0' in m for m in logged)


def test_reset_stats_zeroes_dup_count_for_next_period():
    d = _make_driver()
    d.stats['dup_count'] = 7
    RtldavisDriver._reset_stats(d)
    assert d.stats['dup_count'] == 0


def test_counter_increments_unconditionally_on_go_dedup_line(monkeypatch):
    """genLoopPackets' own line scan, run for real with debug off: each Go
    "duplicate packet:" line counts once, and no other line does. (This test
    used to repeat the substring match inline, so deleting the driver's counter
    left it green -- #456, audit item 35.)"""
    d, _ = run_loop(monkeypatch, [
        ["13:44:13.116046 hop stuff\n",
         "20:31:04.104955  E401BD56010ED10E  duplicate packet: dropped\n",
         "some other unrelated line\n"],
        ["20:31:07.000000  E401BD56010ED10E  duplicate packet: dropped\n",
         "DATA 21.5 100\n"],
    ])
    assert d.stats['dup_count'] == 2
    assert d.stats['repeat_count'] == 0
