"""Offline regression tests for 4 unguarded crash paths (issue #221).

All four share the same fix pattern already established elsewhere in this
file: guard the input, log-and-degrade instead of letting the driver crash.

  1. calculate_thermistor_temp(0) -- uncaught ZeroDivisionError
  2. rain-rate decode, time_between_tips_raw=0 -- uncaught ZeroDivisionError
     (both the heavy-rain and light-rain branches)
  3. ch_to_xmit's iss_channel=0 -- uncaught ValueError (negative shift)
  4. DATAPacket.parse_text's CRC mismatch -- uncaught ValueError, propagates
     all the way out of genLoopPackets and exits the daemon

weewx is not installed in the test/CI environment, so we stub it (same
pattern as test_parse_raw_channel.py / test_battery_status_dispatch.py).

Run:  python3 -m pytest tests/   OR   python3 tests/test_crash_guards.py
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
_weewx.WeeWxIOError = type("WeeWxIOError", (IOError,), {})
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
from rtldavis import (  # noqa: E402
    DATAPacket, DEFAULT_SOIL_TEMP, RtldavisDriver, calculate_thermistor_temp,
)


class _FakeDriver:
    """Same minimal stand-in as test_parse_raw_channel.py's .channels, plus
    .rain_per_tip (read by the pre-existing heavy/light rain branches) and
    .stats (written by ch_to_xmit's activeTrIds/activeTrIdPtrs bookkeeping,
    unrelated to what issue #221 fixes there but needed for the function to
    run at all -- plain dicts so arbitrary-index assignment never raises,
    unlike the real list-shaped stats)."""
    channels = {'iss': 1, 'anemometer': 0, 'leaf_soil': 0,
                'temp_hum_1': 0, 'temp_hum_2': 0, 'wind_channel': 1}
    rain_per_tip = 0.2
    stats: dict = {'activeTrIds': {}, 'activeTrIdPtrs': {}}


# --- 1. calculate_thermistor_temp(0) -----------------------------------

def test_thermistor_temp_raw_zero_degrades_instead_of_crashing():
    """Pre-fix: ZeroDivisionError from `1.0 / temp_raw`, raised outside the
    function's own try/except (which only wrapped math.log()). Post-fix:
    same degrade path as an out-of-domain math.log(), same sentinel."""
    assert calculate_thermistor_temp(0) == DEFAULT_SOIL_TEMP


def test_thermistor_temp_normal_value_still_works():
    """Guard against over-correcting: a plausible raw value still decodes
    to something other than the degraded default."""
    assert calculate_thermistor_temp(300) != DEFAULT_SOIL_TEMP


# --- 2. rain-rate decode, time_between_tips_raw=0 -----------------------
# message_type 5 (rain rate), channel 1 (iss): pkt[0] = 0x50. Byte 3 and the
# low nibble of byte 4 together form time_between_tips_raw; byte 4 bit 6
# additionally selects heavy (0) vs light (1) rain when that raw value is
# 0 -- both branches divide by it (issue #221), so both need a payload.

def test_rain_rate_zero_tip_interval_heavy_branch_does_not_crash():
    pkt = bytearray([0x50, 0, 0, 0x00, 0x00, 0, 0, 0])  # bit6=0 -> heavy
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data.get('rain_rate') is None


def test_rain_rate_zero_tip_interval_light_branch_does_not_crash():
    pkt = bytearray([0x50, 0, 0, 0x00, 0x40, 0, 0, 0])  # bit6=1 -> light
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data.get('rain_rate') is None


def test_rain_rate_no_rain_sentinel_still_works():
    """Guard against over-correcting: the pre-existing 0x3FF sentinel (a
    completely different value from the new 0-guard) still reports 0."""
    pkt = bytearray([0x50, 0, 0, 0xFF, 0x30, 0, 0, 0])  # 0x3FF, no rain
    data = RtldavisDriver.parse_raw(_FakeDriver(), pkt)
    assert data.get('rain_rate') == 0


# --- 3. ch_to_xmit's iss_channel=0 --------------------------------------

def test_ch_to_xmit_iss_channel_zero_does_not_crash():
    """Pre-fix: 1 << (0 - 1) raises ValueError: negative shift count,
    crashing __init__ entirely -- even though 0="not present" is documented
    as valid for iss_channel, same as the other 4 channel settings."""
    transmitters, tr_count = RtldavisDriver.ch_to_xmit(
        _FakeDriver(), 0, 0, 0, 0, 0)
    assert transmitters == 0
    assert tr_count == 0


def test_ch_to_xmit_iss_channel_nonzero_still_sets_its_bit():
    """Guard against over-correcting: a real iss_channel still contributes
    its bit, same as it always did."""
    transmitters, tr_count = RtldavisDriver.ch_to_xmit(
        _FakeDriver(), 1, 0, 0, 0, 0)
    assert transmitters == 1
    assert tr_count == 1
    transmitters, _ = RtldavisDriver.ch_to_xmit(_FakeDriver(), 3, 0, 0, 0, 0)
    assert transmitters == 1 << 2


# --- 4. DATAPacket.parse_text's CRC mismatch ----------------------------

_CRC_TEST_LINE = "20:31:04.102918 E000000505009F3D 9 0 0 0"


def test_crc_mismatch_returns_none_instead_of_raising(monkeypatch):
    """Pre-fix: PacketFactory._check_crc's bare ValueError propagated out of
    parse_text uncaught. Simulated here by making the stubbed crc16 report
    a mismatch (real crc16 is stubbed to always return 0 in this test
    environment, so a genuine bad checksum can't occur naturally)."""
    monkeypatch.setattr(rtldavis, "crc16", lambda msg: 1)  # != 0 -> mismatch
    lines = [_CRC_TEST_LINE]
    pkt = DATAPacket.parse_text(_FakeDriver(), _CRC_TEST_LINE, lines)
    assert pkt is None
    assert lines == []  # still consumed, like every other malformed case


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
