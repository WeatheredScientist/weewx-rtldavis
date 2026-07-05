"""Offline regression test for the unknown-channel error path (S24, finding H1).

The bug (H1): rtldavis.py's parse_raw() ended with
    logerr("unknown station with channel: %s, raw message: %s"
           % (data['channel'], raw))
but `raw` is never defined in parse_raw (the parameter is `pkt`). So a packet
arriving on a channel that matches none of the configured sensors raised
NameError *inside* genLoopPackets instead of logging the intended diagnostic --
turning a benign "unknown station" into a driver crash. This test drives that
exact path and asserts parse_raw returns cleanly (no NameError).

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing the driver (same pattern as test_rain_filter).

Run:  python3 -m pytest tests/   OR   python3 tests/test_parse_raw_channel.py
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


class _FakeDriver:
    """Minimal stand-in carrying only what parse_raw reads: the channel map.
    All sensor channels but the ISS are 0 (not present), so a packet on any
    other channel falls through to the unknown-station else branch (H1)."""
    channels = {'iss': 1, 'anemometer': 0, 'leaf_soil': 0,
                'temp_hum_1': 0, 'temp_hum_2': 0}


def _pkt_on_channel(chan):
    # channel = (pkt[0] & 0x7) + 1  ->  pkt[0] low 3 bits = chan - 1
    b0 = (chan - 1) & 0x7
    return bytearray([b0, 0, 0, 0, 0, 0, 0, 0])


def test_unknown_channel_does_not_raise():
    """The H1 repro: channel 3 matches no configured sensor -> else branch.
    Before the fix this raised NameError('raw'); after, it logs and returns."""
    pkt = _pkt_on_channel(3)
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)   # must not raise
    assert data['channel'] == 3


def test_known_iss_channel_still_parses():
    """Guard against over-correcting: a normal ISS packet still parses.
    message_type 0xE (rain), rain_count in low 7 bits of pkt[3]."""
    pkt = bytearray([0xE0, 0, 0, 0x05, 0x05, 0, 0x9F, 0x3D])  # channel 1 = iss
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data['channel'] == 1
    assert data.get('rain_count') == 5


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
