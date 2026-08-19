"""Offline regression tests for channel-gating inconsistencies (issue #222).

Every sibling field (temp, humidity, rain_rate) gates its decode on the
channel it actually owns; wind and rain_count did not, and the 5 configured
channel numbers were never checked for collisions:

  1. Wind bytes (pkt[1]/pkt[2]) decoded unconditionally for a frame from ANY
     of the 4 configured channel roles (iss/anemometer/temp_hum_1/
     temp_hum_2), not just the one identified by `wind_channel`. A
     temp_hum_1 frame with plausible-looking pkt[1]/pkt[2] bytes fabricated
     a windSpeed/windDir reading alongside the real humidity value.
  2. message_type 0xE (rain_count) had no channel check, unlike its sibling
     message_type 5 (rain_rate), which already checks
     `data['channel'] == self.channels['iss']`. An RF-corrupted byte from a
     non-ISS transmitter (expected to read the 0x80 "no sensor" sentinel)
     could pass through as a real rain_count.
  3. ch_to_xmit() accumulated `1 << (channel-1)` per configured role with no
     check the 5 channel numbers are pairwise-distinct. Two roles sharing a
     channel number ADD the same bit instead of OR-ing, carrying into a
     different bit than either role was configured for -- silently telling
     the Go binary to listen on the wrong channel.

weewx is not installed in the test/CI environment, so we stub it (same
pattern as test_parse_raw_channel.py / test_battery_status_dispatch.py /
test_crash_guards.py).

Run:  python3 -m pytest tests/   OR   python3 tests/test_channel_gating.py
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
    iss=1, anemometer=0 (so wind_channel falls back to iss per __init__'s own
    precedence rule), a temp_hum_1 sensor on channel 5."""
    channels = {'iss': 1, 'anemometer': 0, 'leaf_soil': 0,
                'temp_hum_1': 5, 'temp_hum_2': 0, 'wind_channel': 1}


class _FakeDriverWithAnemometer:
    """Same, but a dedicated Anemometer Transport Kit on channel 2 -- so
    wind_channel is 2, NOT iss's channel 1 (the precedence #222 asked to
    confirm: anemometer_channel wins when configured)."""
    channels = {'iss': 1, 'anemometer': 2, 'leaf_soil': 0,
                'temp_hum_1': 5, 'temp_hum_2': 0, 'wind_channel': 2}


def _pkt(chan, b1=0, b2=0, b3=0, b4=0, b5=0):
    # channel = (pkt[0] & 0x7) + 1  ->  pkt[0] low 3 bits = chan - 1
    b0 = (chan - 1) & 0x7
    return bytearray([b0, b1, b2, b3, b4, b5, 0, 0])


# --- 1. wind bytes gated on wind_channel ---------------------------------

def test_wind_not_decoded_on_non_wind_channel():
    """The #222 repro: a channel-5 (temp_hum_1) frame with plausible wind
    bytes must NOT populate windSpeed/windDir. pkt[1]=77,pkt[2]=130 is the
    issue's own empirically-confirmed fabricating pair."""
    pkt = _pkt(5, b1=77, b2=130)
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data['channel'] == 5
    assert 'wind_speed' not in data
    assert 'wind_dir' not in data


def test_wind_still_decoded_on_iss_when_no_anemometer():
    """Guard against over-correcting: iss-only config (anemometer=0) still
    decodes wind from the iss channel, since wind_channel falls back to it."""
    pkt = _pkt(1, b1=77, b2=130)
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data['channel'] == 1
    assert 'wind_speed' in data
    assert 'wind_dir' in data


def test_wind_decoded_on_dedicated_anemometer_channel_not_iss():
    """With a real Anemometer Transport Kit, wind_channel is the anemometer's
    channel (2), not iss's (1) -- confirming the precedence #222 flagged."""
    pkt_wind = _pkt(2, b1=77, b2=130)
    data_wind = RtldavisDriver.parse_raw(_FakeDriverWithAnemometer(), pkt_wind)
    assert 'wind_speed' in data_wind

    pkt_iss = _pkt(1, b1=77, b2=130)
    data_iss = RtldavisDriver.parse_raw(_FakeDriverWithAnemometer(), pkt_iss)
    assert 'wind_speed' not in data_iss


# --- 2. rain_count gated on iss, like rain_rate already is ---------------

def test_rain_count_not_accepted_from_non_iss_channel():
    """message_type 0xE on a non-iss channel (5 = temp_hum_1) must not set
    rain_count, matching rain_rate's existing iss-only gate."""
    # pkt[0]: low 3 bits = channel-1 (4 for chan 5), high nibble 0xE = rain
    pkt = _pkt(5, b3=0x05)
    pkt[0] = (0xE << 4) | ((5 - 1) & 0x7)
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data['channel'] == 5
    assert 'rain_count' not in data


def test_rain_count_still_accepted_from_iss_channel():
    """Guard against over-correcting: a normal ISS rain frame still parses
    (same fixture test_parse_raw_channel.py already validates)."""
    pkt = bytearray([0xE0, 0, 0, 0x05, 0x05, 0, 0x9F, 0x3D])  # channel 1 = iss
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data['channel'] == 1
    assert data.get('rain_count') == 5


# --- 3. duplicate configured channel numbers rejected at ch_to_xmit ------

class _FakeChToXmit:
    stats: dict = {'activeTrIds': {}, 'activeTrIdPtrs': {}}


def test_ch_to_xmit_distinct_channels_unaffected():
    """Guard against over-correcting: 5 distinct (or 0) channel numbers
    still compose bits normally -- ch_to_xmit itself has no dup check
    (that lives in __init__, see below); this just confirms the sibling
    fix (#221's iss_channel=0 guard) still composes correctly alongside
    #222's own __init__-level validation."""
    transmitters, tr_count = RtldavisDriver.ch_to_xmit(
        _FakeChToXmit(), 1, 2, 0, 3, 4)
    assert transmitters == (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3)
    assert tr_count == 4


def _config_dict(iss=1, anemometer=0, leaf_soil=0, temp_hum_1=0, temp_hum_2=0):
    # __init__ reads stn_dict = config_dict.get(DRIVER_NAME, {}) -- DRIVER_NAME = 'Rtldavis'
    return {'Rtldavis': {
        'iss_channel': iss, 'anemometer_channel': anemometer,
        'leaf_soil_channel': leaf_soil, 'temp_hum_1_channel': temp_hum_1,
        'temp_hum_2_channel': temp_hum_2,
    }}


def test_init_rejects_duplicate_channel_numbers():
    """The #222 repro: iss_channel=3 and temp_hum_1_channel=3 must raise at
    startup instead of silently corrupting the -tr bitmask (previously
    produced transmitters=8 instead of the intended 4). Patches
    ProcManager.startup so a pre-fix run (which reaches it) fails cleanly on
    "DID NOT RAISE" rather than on an unrelated subprocess-spawn error."""
    import pytest
    from unittest.mock import patch
    with patch('rtldavis.ProcManager.startup', return_value=None):
        with pytest.raises(ValueError, match="duplicate channel"):
            RtldavisDriver(None, _config_dict(iss=3, temp_hum_1=3))


def test_init_accepts_distinct_channel_numbers():
    """Guard against over-correcting: a normal distinct-channel config still
    initializes (patches ProcManager.startup so __init__ doesn't try to
    actually spawn the Go binary)."""
    from unittest.mock import patch
    with patch('rtldavis.ProcManager.startup', return_value=None):
        driver = RtldavisDriver(None, _config_dict(iss=1, anemometer=2))
    assert driver.channels['iss'] == 1
    assert driver.channels['anemometer'] == 2


def test_init_allows_multiple_channels_unset_at_zero():
    """0 means 'not present' for every channel role (#221's own fix made
    iss_channel=0 legal too) -- multiple roles left at the default 0 must
    NOT be treated as a collision."""
    from unittest.mock import patch
    with patch('rtldavis.ProcManager.startup', return_value=None):
        driver = RtldavisDriver(None, _config_dict(iss=1))
    assert driver.channels['anemometer'] == 0
    assert driver.channels['leaf_soil'] == 0


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
