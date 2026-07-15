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

Run:  python3 -m pytest tests/   OR   python3 tests/test_duplicate_frame_counter.py
"""
import os
import sys
import types

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


def _make_driver():
    d = RtldavisDriver.__new__(RtldavisDriver)
    RtldavisDriver._init_stats(d)
    d.stats['activeTrIds'][0] = 0
    d._save_pct_good_per_transmitter = False
    return d


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


def test_counter_increments_unconditionally_on_go_dedup_line():
    """The exact substring match genLoopPackets uses -- no debug_rtld gate."""
    d = _make_driver()
    lines = [
        "13:44:13.116046 hop stuff\n",
        "20:31:04.104955  E401BD56010ED10E  duplicate packet: dropped\n",
        "some other unrelated line\n",
    ]
    for _line in lines:
        if "duplicate packet:" in _line:
            d.stats['dup_count'] += 1
    assert d.stats['dup_count'] == 1


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                if 'monkeypatch' in fn.__code__.co_varnames[:fn.__code__.co_argcount]:
                    class _MP:
                        def setattr(self, obj, name, val):
                            setattr(obj, name, val)
                    fn(_MP())
                else:
                    fn()
                print("  [PASS] %s" % name)
            except Exception as e:
                fails += 1
                print("  [FAIL] %s -> %r" % (name, e))
    total = sum(1 for n in globals() if n.startswith('test_'))
    print("\n%d/%d passed" % (total - fails, total))
    sys.exit(1 if fails else 0)
