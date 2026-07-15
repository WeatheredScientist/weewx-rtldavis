"""Offline unit tests for DEC-0024 Layer B (S43): the driver publishes
freqError channel-hop packets as their own dataless loop packets, which every
uploader (WU RapidFire etc.) then treats as a full weather update -- the
~1.6x reception/publish overcount measured at S21. freqError{n} also maps
onto real archive schema columns via DEFAULT_SENSOR_MAP (consBatteryVoltage/
hail/hailRate/heatingTemp/heatingVoltage), so it can't simply be dropped
(Option A) without silently breaking that and ops/reception_service.py's
freqError logging.

The fix (Option B, agreed design): cache a channel-hop packet's freqError
fields and ride them in on the *next* real DATA packet instead of yielding a
standalone loop packet for the channel-hop packet at all.

These tests drive the two extracted helpers directly --
_cache_pending_freq_fields / _merge_pending_freq_fields -- the same logic
genLoopPackets calls inline, so this is what's actually deployed.

weewx is not installed in the test/CI environment, so we stub it (same
pattern as test_reception_stats.py / test_parse_raw_channel.py).

Run:  python3 -m pytest tests/   OR   python3 tests/test_reception_layer_b.py
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
from rtldavis import RtldavisDriver  # noqa: E402


def _make_driver():
    """Bare object with just the state Layer B touches. __init__ is skipped
    (it spawns a subprocess)."""
    d = RtldavisDriver.__new__(RtldavisDriver)
    d._pending_freq_fields = {}
    return d


def test_channel_hop_packet_is_cached_not_yielded():
    """A channel-hop packet (no curr_cnt0) carrying freqError0 is cached, and
    the caller is expected to `continue` (never yield it) -- this test
    exercises the caching half of that contract."""
    d = _make_driver()
    hop_data = {'dateTime': 1700000000, 'usUnits': 16, 'freqError0': 431}
    d._cache_pending_freq_fields(hop_data)
    assert d._pending_freq_fields == {'freqError0': 431}


def test_hop_without_freq_fields_caches_nothing():
    """A channel-hop packet for a transmitter that isn't being tracked this
    period carries only dateTime/usUnits -- nothing to cache."""
    d = _make_driver()
    hop_data = {'dateTime': 1700000000, 'usUnits': 16}
    d._cache_pending_freq_fields(hop_data)
    assert d._pending_freq_fields == {}


def test_pending_freq_fields_ride_the_next_data_packet():
    d = _make_driver()
    d._cache_pending_freq_fields({'dateTime': 1, 'freqError0': 431})

    data_pkt = {'channel': 1, 'curr_cnt0': 5, 'curr_cnt1': 0,
                'curr_cnt2': 0, 'curr_cnt3': 0, 'outTemp': 72.0}
    d._merge_pending_freq_fields(data_pkt)

    assert data_pkt['freqError0'] == 431, \
        "freqError should have merged onto the real DATA packet"
    assert data_pkt['outTemp'] == 72.0, "real fields must survive the merge"


def test_pending_freq_fields_ride_exactly_once():
    """Each cached value should be consumed by the next DATA packet only --
    it must not keep riding along on every subsequent packet forever."""
    d = _make_driver()
    d._cache_pending_freq_fields({'dateTime': 1, 'freqError0': 431})

    first = {'curr_cnt0': 5}
    d._merge_pending_freq_fields(first)
    assert first.get('freqError0') == 431

    second = {'curr_cnt0': 6}
    d._merge_pending_freq_fields(second)
    assert 'freqError0' not in second, \
        "a stale freqError value rode a second packet -- should ride exactly once"


def test_no_pending_fields_leaves_data_packet_untouched():
    d = _make_driver()
    data_pkt = {'curr_cnt0': 5, 'outTemp': 72.0}
    d._merge_pending_freq_fields(data_pkt)
    assert data_pkt == {'curr_cnt0': 5, 'outTemp': 72.0}


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
