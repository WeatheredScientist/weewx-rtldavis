"""Offline unit tests for the decode-layer sensor plausibility filter (DEC-0029, S33).

The bad-packet bug: the same RF corruption class that caused phantom rain
(multi-bit errors passing CRC) also hits the other sensor bit-fields --
confirmed in the archive as one-minute humidity spikes with bit-flip
magnitudes (+12.8/+25.6 %RH per reading), an impossible UV 16.29 under
overcast, and a 201 mph loop-only wind spike. These tests exercise the REAL
`SensorQC` from rtldavis.py against those recorded signatures, plus the
`_data_to_packet` wiring on a bare driver object.

weewx is not installed in the test/CI environment, so we stub the weewx
modules in sys.modules before importing the driver (same pattern as
test_rain_filter.py).

Run:  python -m pytest tests/    OR    python tests/test_sensor_qc.py
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
from rtldavis import (  # noqa: E402
    SensorQC, QC_RESEED_SECONDS, RtldavisDriver, FRAME_WEATHER_KEYS)

T0 = 1_000_000.0  # arbitrary epoch for the fake clock


def _qc():
    return SensorQC()


# --- Layer 1: Davis sensor-spec bounds (recorded impossible values) ---

def test_uv_1629_rejected():
    # 2026-05-30 15:50 archive record: UV 16.29 under 320 W/m2 overcast
    v, why = _qc().check('uv', 16.29, T0)
    assert v is None and "range" in why

def test_wind_201mph_rejected():
    # 2026-07-05 dashboard gauge spike: 201 mph = 89.85 m/s > 6410 spec max
    v, why = _qc().check('wind_speed', 201 * 0.44704, T0)
    assert v is None and "range" in why

def test_radiation_1900_rejected_but_enhancement_passes():
    qc = _qc()
    v, why = qc.check('solar_radiation', 1900.0, T0)
    assert v is None
    # genuine cloud-edge enhancement observed in the archive: 1578.6 W/m2
    v, why = qc.check('solar_radiation', 1578.6, T0)
    assert v == 1578.6 and why is None

def test_bounds_reject_does_not_move_baseline():
    # an impossible value carries no information; the delta baseline must
    # survive it so the next real reading is judged against real history
    qc = _qc()
    assert qc.check('humidity', 45.0, T0)[0] == 45.0
    assert qc.check('humidity', 150.0, T0 + 30)[0] is None   # bounds reject
    v, why = qc.check('humidity', 46.0, T0 + 60)              # delta vs 45.0
    assert v == 46.0 and why is None


# --- Layer 2: delta filter (recorded glitch signatures) ---

def test_humidity_bitflip_rejected():
    # the archive signature: +12.8 %RH (bit-7 flip of the raw %x10 field)
    qc = _qc()
    assert qc.check('humidity', 45.0, T0)[0] == 45.0
    v, why = qc.check('humidity', 57.8, T0 + 30)
    assert v is None and "delta" in why

def test_isolated_spike_costs_at_most_two_readings():
    # spike then return-to-baseline: both transitions exceed the delta, so
    # two readings are nulled; the third is accepted (documented cost)
    qc = _qc()
    assert qc.check('humidity', 45.0, T0)[0] == 45.0
    assert qc.check('humidity', 70.6, T0 + 30)[0] is None   # +25.6 glitch
    assert qc.check('humidity', 46.0, T0 + 60)[0] is None   # back down: -24.6
    assert qc.check('humidity', 45.5, T0 + 90)[0] == 45.5   # resynced, accepted

def test_genuine_step_accepted_on_next_reading():
    # baseline-resync on reject: a sustained new level (real weather front)
    # loses exactly one reading, then flows -- the no-deadlock guarantee
    qc = _qc()
    assert qc.check('temperature', 20.0, T0)[0] == 20.0
    assert qc.check('temperature', 27.1, T0 + 30)[0] is None  # +12.8F glitch-size jump
    v, why = qc.check('temperature', 27.2, T0 + 60)           # jump persists = real
    assert v == 27.2 and why is None

def test_small_real_changes_pass():
    qc = _qc()
    for i, v in enumerate([20.0, 20.8, 21.5, 21.1, 22.0]):
        got, why = qc.check('temperature', v, T0 + 30 * i)
        assert got == v and why is None

def test_radiation_has_no_delta_filter():
    # genuine cloud edges swing +/-900 W/m2 within a minute; must pass
    qc = _qc()
    assert qc.check('solar_radiation', 1100.0, T0)[0] == 1100.0
    assert qc.check('solar_radiation', 200.0, T0 + 60)[0] == 200.0
    assert qc.check('solar_radiation', 1100.0, T0 + 120)[0] == 1100.0

def test_baseline_expires_after_reseed_window():
    # after a long reception gap the old baseline is stale; the next
    # in-bounds reading reseeds instead of being delta-judged
    qc = _qc()
    assert qc.check('temperature', 20.0, T0)[0] == 20.0
    v, why = qc.check('temperature', 35.0, T0 + QC_RESEED_SECONDS + 1)
    assert v == 35.0 and why is None

def test_cold_start_accepts_first_in_bounds_value():
    v, why = _qc().check('humidity', 97.0, T0)
    assert v == 97.0 and why is None

def test_delta_override():
    qc = SensorQC(limits={'humidity': (0.0, 100.0, 30.0)})
    assert qc.check('humidity', 45.0, T0)[0] == 45.0
    assert qc.check('humidity', 70.6, T0 + 30)[0] == 70.6  # 25.6 < 30 passes

def test_unknown_key_and_none_pass_through():
    qc = _qc()
    assert qc.check('soil_temp_1', 999.0, T0) == (999.0, None)
    assert qc.check('humidity', None, T0) == (None, None)


# --- _data_to_packet wiring on a bare driver object ---

def _bare_driver(enabled=True):
    drv = RtldavisDriver.__new__(RtldavisDriver)  # skip __init__ (ProcManager)
    drv.sensor_map = dict(RtldavisDriver.DEFAULT_SENSOR_MAP)
    drv.last_rain_count = None
    drv.rain_per_tip = 0.2
    drv._sensor_qc_enabled = enabled
    drv._sensor_qc = SensorQC()
    return drv

def test_packet_gets_explicit_null_and_wind_dir_nulled():
    # AMENDED for DEC-0054: this test used to assert the same-frame humidity
    # SURVIVES a wind bounds failure (pkt['outHumidity'] == 55.0). That
    # assertion encoded exactly the gap ERR-0004 exposed from the other
    # direction -- a bounds failure proves the whole frame corrupt, so the
    # sibling must now be nulled too (the S40 lesson: a passing test is not
    # evidence if the assertion is wrong).
    drv = _bare_driver()
    pkt = drv._data_to_packet({'wind_speed': 201 * 0.44704, 'wind_dir': 180.0,
                               'humidity': 55.0})
    assert pkt['windSpeed'] is None, "rejected windSpeed must be an explicit null"
    assert pkt['windDir'] is None, "same-packet direction byte is suspect too"
    assert pkt['outHumidity'] is None, \
        "bounds proof on wind co-rejects same-frame humidity (DEC-0054)"

def test_filter_can_be_disabled():
    drv = _bare_driver(enabled=False)
    pkt = drv._data_to_packet({'uv': 16.29})
    assert pkt['UV'] == 16.29

def test_good_packet_unchanged():
    drv = _bare_driver()
    pkt = drv._data_to_packet({'temperature': 21.5, 'humidity': 48.0,
                               'wind_speed': 3.2, 'wind_dir': 270.0,
                               'solar_radiation': 850.0, 'uv': 6.1})
    assert (pkt['outTemp'], pkt['outHumidity'], pkt['windSpeed'],
            pkt['windDir'], pkt['radiation'], pkt['UV']) == (
        21.5, 48.0, 3.2, 270.0, 850.0, 6.1)


# --- Frame-level co-rejection (DEC-0054, the ERR-0004 phantom-gust class) ---

MPH_TO_MPS = 0.44704


def test_err0004_replay_corrupt_humidity_co_rejects_wind():
    # The 2026-07-27 14:55:50 EDT frame verbatim: humidity_raw 59a9 decoded
    # to 144.9 %RH (bounds reject) while the same frame's wind byte decoded
    # to 39 mph from a calm baseline -- under the old per-field filter the
    # wind passed (17.4 m/s is in spec, +16.5 m/s is under the 20 m/s delta
    # cap) and became the interval's gust max on every external network.
    drv = _bare_driver()
    # establish a calm baseline, as prod had (~1-3 mph readings)
    drv._data_to_packet({'wind_speed': 0.9 * MPH_TO_MPS, 'wind_dir': 210.0})
    pkt = drv._data_to_packet({'humidity': 144.9,
                               'wind_speed': 39 * MPH_TO_MPS,
                               'wind_dir': 209.0})
    assert pkt['outHumidity'] is None
    assert pkt['windSpeed'] is None, "the phantom gust must not survive"
    assert pkt['windDir'] is None

def test_delta_trip_does_not_co_reject():
    # a delta trip is not corruption proof -- a genuine squall front from
    # calm can exceed the cap; only the tripped field (and its direction
    # pair) is nulled, the same-frame payload flows
    drv = _bare_driver()
    drv._data_to_packet({'wind_speed': 0.5, 'wind_dir': 180.0,
                         'humidity': 55.0})
    pkt = drv._data_to_packet({'wind_speed': 25.0, 'wind_dir': 190.0,
                               'humidity': 55.5})
    assert pkt['windSpeed'] is None, "delta trip still nulls the field itself"
    assert pkt['outHumidity'] == 55.5, \
        "a delta trip must NOT co-reject the frame (DEC-0054 asymmetry)"

def test_corrupt_frame_does_not_poison_baselines():
    # the corrupt frame's in-spec wind (17.4 m/s) must not become the delta
    # baseline: the next genuine calm reading is judged against pre-glitch
    # history and accepted immediately, with zero extra nulled readings
    drv = _bare_driver()
    drv._data_to_packet({'wind_speed': 1.0, 'wind_dir': 200.0})
    drv._data_to_packet({'humidity': 144.9, 'wind_speed': 17.4,
                         'wind_dir': 209.0})                 # corrupt frame
    pkt = drv._data_to_packet({'wind_speed': 1.2, 'wind_dir': 205.0})
    assert pkt['windSpeed'] == 1.2, \
        "post-glitch calm must be accepted against the pre-glitch baseline"

def test_corrupt_frame_skips_rain_counter_without_resync():
    # the counter is cumulative: skipping the corrupt frame entirely means
    # genuine tips still land in the next clean frame's delta
    drv = _bare_driver()
    p0 = drv._data_to_packet({'rain_count': 10})     # cold start: 0 tips
    assert p0['rain'] == 0.0 and drv.last_rain_count == 10
    p1 = drv._data_to_packet({'humidity': 144.9, 'rain_count': 77})
    assert p1['rain'] is None, "corrupt frame's counter must not count"
    assert drv.last_rain_count == 10, \
        "baseline must NOT resync to the corrupt frame's counter byte"
    p2 = drv._data_to_packet({'rain_count': 12})     # 2 genuine tips survive
    assert p2['rain'] == 2 * drv.rain_per_tip

def test_co_rejection_nulls_only_weather_fields():
    # diagnostics describe the link/station, not the weather: battery flag
    # and reception stats must survive a co-rejected frame
    drv = _bare_driver()
    pkt = drv._data_to_packet({'uv': 16.29, 'wind_speed': 2.0,
                               'wind_dir': 90.0, 'bat_iss': 0,
                               'pct_good_all': 67.0})
    assert pkt['UV'] is None and pkt['windSpeed'] is None
    assert pkt['txBatteryStatus'] == 0
    assert pkt['rxCheckPercent'] == 67.0

def test_frame_weather_keys_cover_all_qc_keys():
    # every QC-bounded field must be in the co-rejection set, or a corrupt
    # frame could null its siblings while a later-added field escapes
    assert set(SensorQC().limits) <= set(FRAME_WEATHER_KEYS)


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    for n, f in fns:
        f()
        print("  [PASS] %s" % n)
    print("%d tests passed" % len(fns))
