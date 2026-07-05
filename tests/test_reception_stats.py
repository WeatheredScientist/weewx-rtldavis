"""Offline regression test for the pct_good_all deadlock (S24, finding H2).

The bug (H2): _update_summaries computed the overall reception metric under
    if total_max_count > 0 and self.stats['pct_good_all'] is not None:
        self.stats['pct_good_all'] = 100.0 * total_count / total_max_count
but _init_stats and _reset_stats set pct_good_all to None every archive period,
so the guard could never pass. pct_good_all stayed None forever, and
new_archive_record therefore never wrote event.record['rxCheckPercent'] -- the
driver's native reception metric was silently dead.

These tests drive the REAL _update_summaries / _reset_stats / new_archive_record
across two archive periods and assert the metric is actually produced. They fail
on the pre-fix code (pct_good_all stays None) and pass after.

weewx is not installed in the test/CI environment, so we stub it (same pattern
as test_rain_filter / test_parse_raw_channel).

Run:  python3 -m pytest tests/   OR   python3 tests/test_reception_stats.py
"""
import os
import sys
import time
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
from rtldavis import RtldavisDriver  # noqa: E402


def _make_driver():
    """Bare object carrying just the state the stats methods touch. __init__ is
    skipped (it spawns a subprocess); we call _init_stats to populate stats and
    mark one active transmitter (ID 0 -> loop_times[0])."""
    d = RtldavisDriver.__new__(RtldavisDriver)
    RtldavisDriver._init_stats(d)
    d.stats['activeTrIds'][0] = 0          # one active transmitter, ID 0
    d._save_pct_good_per_transmitter = False
    return d


def _run_period(d, curr_cnt0, period_s=60):
    """Simulate one archive period that received curr_cnt0 messages since
    startup, spanning period_s seconds, and close it via _update_summaries."""
    d.stats['curr_cnt'][0] = curr_cnt0
    # backdate last_ts so _update_summaries sees a real elapsed period
    if d.stats['last_ts'] > 0:
        d.stats['last_ts'] = int(time.time()) - period_s
    RtldavisDriver._update_summaries(d)


def test_pct_good_all_is_computed_after_a_valid_period():
    d = _make_driver()
    # Period 1: first data since startup -> establishes the baseline count.
    _run_period(d, curr_cnt0=20)
    RtldavisDriver._reset_stats(d)          # normal end-of-period reset
    # Period 2: 20 more messages received over ~60s.
    _run_period(d, curr_cnt0=40)
    assert d.stats['pct_good_all'] is not None, \
        "pct_good_all stayed None -> the H2 deadlock is still present"
    assert 0 < d.stats['pct_good_all'] <= 200


def test_new_archive_record_stores_rxCheckPercent():
    d = _make_driver()
    _run_period(d, curr_cnt0=20)
    RtldavisDriver._reset_stats(d)
    # Second period arrives as a NEW_ARCHIVE_RECORD event.
    d.stats['curr_cnt'][0] = 40
    d.stats['last_ts'] = int(time.time()) - 60
    event = types.SimpleNamespace(record={'dateTime': int(time.time()),
                                           'usUnits': 16})
    RtldavisDriver.new_archive_record(d, event)
    assert 'rxCheckPercent' in event.record, \
        "rxCheckPercent was not written -> driver reception metric still dead"
    assert event.record['rxCheckPercent'] is not None


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
