"""Offline regression test for the DewpointCacher wind honest-null (S30, v2.0.3).

The change: `_filter_wind` no longer substitutes the last cached windSpeed into a
packet whose windSpeed is None. Davis transmits wind in *every* ISS/anemometer
packet (rtldavis.py:1122 — unlike temp/humidity/rain/UV, which rotate across
message types), so windSpeed is only None when the reading is genuinely absent
(a "no sensor" raw 0,0 packet) or was just delta-rejected as a corrupt spike.
In both cases an honest null is correct; a stale substituted value is misleading
and harder to diagnose (e.g. a failed vane potentiometer looks like live wind).

This does NOT touch the temp/humidity/radiation/UV substitution — those rotating
sensors legitimately miss most packets, so they keep the carry-forward for now
(DEC-0022 sensor-QC hardening, a later session).

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing dewpoint_service (same pattern as the other tests).

Run:  python3 -m pytest tests/   OR   python3 tests/test_dewpoint_wind_honest_null.py
"""
import os
import sys
import types


# --- stub the weewx deps so dewpoint_service.py imports without weewx installed ---
def _pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m


def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m


weewx = _pkg("weewx")
weewx.NEW_LOOP_PACKET = "NEW_LOOP_PACKET"

weewx_engine = _mod("weewx.engine")


class _StdService:
    def __init__(self, engine, config_dict):
        pass

    def bind(self, *a, **k):
        pass


weewx_engine.StdService = _StdService
weewx.engine = weewx_engine

weewx_wxformulas = _mod("weewx.wxformulas")
weewx_wxformulas.dewpointF = lambda t, h: 0.0
weewx_wxformulas.heatindexF = lambda t, h: 0.0
weewx.wxformulas = weewx_wxformulas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dewpoint_service  # noqa: E402


def _make_cacher():
    return dewpoint_service.DewpointCacher(engine=None, config_dict={})


def test_none_windspeed_is_not_substituted():
    # THE regression: a packet with no windSpeed must stay null, never inherit
    # the last cached value (the old `elif ... = self.last_wind_speed` behavior).
    c = _make_cacher()
    c.last_wind_speed = 5.0  # seeded / post-warmup
    packet = {"windSpeed": None, "windGust": None, "windDir": None}
    c._filter_wind(packet)
    assert packet["windSpeed"] is None, "stale windSpeed was substituted"
    print("  [PASS] test_none_windspeed_is_not_substituted")


def test_valid_windspeed_passes_after_warmup():
    c = _make_cacher()
    c.last_wind_speed = 5.0
    packet = {"windSpeed": 6.0, "windGust": 8.0, "windDir": 90.0}
    c._filter_wind(packet)
    assert packet["windSpeed"] == 6.0
    assert c.last_wind_speed == 6.0  # cache advances on a good reading
    print("  [PASS] test_valid_windspeed_passes_after_warmup")


def test_delta_spike_is_nulled():
    # A corrupt spike beyond MAX_WIND_DELTA nulls both fields (pre-existing).
    c = _make_cacher()
    c.last_wind_speed = 5.0
    packet = {"windSpeed": 200.0, "windGust": 210.0, "windDir": 90.0}
    c._filter_wind(packet)
    assert packet["windSpeed"] is None
    assert packet["windGust"] is None
    print("  [PASS] test_delta_spike_is_nulled")


def test_gust_less_than_speed_nulls_both():
    c = _make_cacher()
    c.last_wind_speed = 5.0
    packet = {"windSpeed": 10.0, "windGust": 5.0, "windDir": 90.0}
    c._filter_wind(packet)
    assert packet["windSpeed"] is None
    assert packet["windGust"] is None
    print("  [PASS] test_gust_less_than_speed_nulls_both")


def test_cold_start_nulls_during_warmup():
    # Cold start (no cached speed yet): null wind for a clean gap rather than
    # trusting the first, unvetted reading.
    c = _make_cacher()
    packet = {"windSpeed": 4.0, "windGust": 6.0, "windDir": 90.0}
    c._filter_wind(packet)
    assert packet["windSpeed"] is None
    assert packet["windDir"] is None
    print("  [PASS] test_cold_start_nulls_during_warmup")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    print("\n%d/%d passed" % (len(tests), len(tests)))
