"""Offline regression test for the owm.py RESTThread rebase (S24, findings U1/U2).

The bug (U1/U2): owm.py overrode RESTThread.run_loop with a hand-rolled
queue.get/urlopen loop, so it silently discarded every RESTThread resilience
feature it was constructed with -- post_interval, max_backlog, stale, max_tries,
retry_wait, skip_upload -- and a single transient network failure dropped the
record with no retry. The fix drives the OWM JSON POST through the standard
RESTThread hooks (format_url + get_post_body) so retry/backoff come for free.

The bug (#405, S145): owm.py converted the record with to_METRIC, whose rain unit
is centimeters, and sent hourRain as rain_1h. OpenWeatherMap documents rain_1h in
millimeters, so the value went out 10x low. The unit stub here used to be an
identity function, so no test could see it. It now models weewx's real unit systems.

This test asserts:
  * OWMThread no longer overrides run_loop / post_request (they belong to
    RESTThread now);
  * get_post_body() returns the correct (json_body, content_type) pair, with
    None fields omitted and the km/h -> m/s wind conversion applied;
  * rain_1h is in millimeters whatever unit system the archive record is in, and a
    dry hour (0.0) is sent as zero (#405).

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing owm (same pattern as the other tests here).

Run:  python3 -m pytest tests/   OR   python3 tests/test_owm_post_body.py
"""
import json
import os
import sys
import types

# --- stub the weewx deps so owm.py imports without weewx installed ---
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
weewx.NEW_ARCHIVE_RECORD = "NEW_ARCHIVE_RECORD"

weewx_restx = _mod("weewx.restx")


class _StdRESTbase:
    def __init__(self, *a, **k):
        pass

    def bind(self, *a, **k):
        pass


class _RESTThread:
    # Minimal stand-in: records the kwargs it was constructed with so the test
    # can prove they are actually passed through (not discarded like before).
    def __init__(self, queue, **kwargs):
        self.queue = queue
        self.rest_kwargs = kwargs


def _get_site_dict(config_dict, *args, **kwargs):
    return {}


weewx_restx.StdRESTbase = _StdRESTbase
weewx_restx.RESTThread = _RESTThread
weewx_restx.get_site_dict = _get_site_dict
weewx.restx = weewx_restx

weewx_units = _mod("weewx.units")

# A small model of weewx.units, so the tests run a real unit conversion. The old stub
# was an identity to_METRIC, which hid a 10x rain error (#405): METRIC rain is
# centimeters and the OWM API wants millimeters. System numbers and factors are
# weewx 5.3.1's (checked against the real module in S145). Only the types owm.py
# converts are listed; the rest pass through, as in weewx, because humidity,
# direction and time are the same in every system.
US, METRIC, METRICWX = 1, 16, 17
_GROUP = {"outTemp": "temp", "dewpoint": "temp", "heatindex": "temp",
          "barometer": "pressure", "windSpeed": "speed", "windGust": "speed",
          "hourRain": "rain"}
_UNIT = {US:       {"temp": "degree_F", "pressure": "inHg",
                    "speed": "mile_per_hour", "rain": "inch"},
         METRIC:   {"temp": "degree_C", "pressure": "mbar",
                    "speed": "km_per_hour", "rain": "cm"},
         METRICWX: {"temp": "degree_C", "pressure": "mbar",
                    "speed": "meter_per_second", "rain": "mm"}}
# unit -> (scale, offset): value * scale + offset is the group's base unit
# (degree_C, mbar, meter_per_second, mm)
_BASE = {"degree_F": (5.0 / 9.0, -160.0 / 9.0), "degree_C": (1.0, 0.0),
         "inHg": (33.8638815, 0.0), "mbar": (1.0, 0.0),
         "mile_per_hour": (0.44704, 0.0), "km_per_hour": (1.0 / 3.6, 0.0),
         "meter_per_second": (1.0, 0.0),
         "inch": (25.4, 0.0), "cm": (10.0, 0.0), "mm": (1.0, 0.0)}


def _to_system(record, target):
    if record["usUnits"] == target:
        return record  # weewx.units.to_std_system leaves it untouched
    out = {"usUnits": target}
    for key, val in record.items():
        group = _GROUP.get(key)
        if key == "usUnits":
            continue
        if group is None or val is None:
            out[key] = val
            continue
        s_scale, s_off = _BASE[_UNIT[record["usUnits"]][group]]
        t_scale, t_off = _BASE[_UNIT[target][group]]
        out[key] = (val * s_scale + s_off - t_off) / t_scale
    return out


# Both converters exist so the assertions below hold for either one; they check
# what the API receives, not which weewx function produced it.
weewx_units.to_METRIC = lambda record: _to_system(record, METRIC)
weewx_units.to_METRICWX = lambda record: _to_system(record, METRICWX)
weewx.units = weewx_units

weewx_manager = _mod("weewx.manager")
weewx_manager.get_manager_dict_from_config = lambda *a, **k: {}
weewx.manager = weewx_manager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import owm  # noqa: E402


def _make_thread():
    return owm.OWMThread(queue=None, api_key="KEY", station_id="STN",
                         manager_dict={})


def test_resthread_kwargs_are_passed_through():
    # U1/U2: the constructor must hand its resilience knobs to RESTThread,
    # not swallow them.
    t = _make_thread()
    for k in ("post_interval", "max_backlog", "stale", "max_tries",
              "retry_wait", "skip_upload"):
        assert k in t.rest_kwargs, "%s not forwarded to RESTThread" % k
    assert t.rest_kwargs["protocol_name"] == "OWM"
    print("  [PASS] test_resthread_kwargs_are_passed_through")


def test_run_loop_and_post_request_not_overridden():
    # The whole point of the fix: RESTThread owns the loop again.
    assert "run_loop" not in vars(owm.OWMThread)
    assert "post_request" not in vars(owm.OWMThread)
    print("  [PASS] test_run_loop_and_post_request_not_overridden")


def test_get_post_body_shape_and_content_type():
    t = _make_thread()
    record = {"dateTime": 1783256300, "usUnits": METRIC, "outTemp": 21.5,
              "outHumidity": 63.0, "barometer": 1013.2, "windSpeed": 18.0,
              "windGust": 36.0, "windDir": 270.0, "dewpoint": 14.1,
              "heatindex": 22.0, "hourRain": 0.25}
    body, content_type = t.get_post_body(record)
    assert content_type == "application/json"
    payload = json.loads(body)
    assert isinstance(payload, list) and len(payload) == 1
    d = payload[0]
    assert d["station_id"] == "STN"
    assert d["dt"] == 1783256300
    assert d["temperature"] == 21.5
    # km/h -> m/s conversion (18.0 / 3.6 = 5.0, 36.0 / 3.6 = 10.0)
    assert d["wind_speed"] == 5.0
    assert d["wind_gust"] == 10.0
    # hourRain is 0.25 cm in a METRIC record, which is 2.5 mm (#405)
    assert d["rain_1h"] == 2.5
    print("  [PASS] test_get_post_body_shape_and_content_type")


def test_rain_1h_is_millimeters_in_every_unit_system():
    # #405: the OWM API takes rain_1h in millimeters. The same 2.54 mm of rain must
    # come out whichever unit system the archive record arrives in: 0.1 in for
    # US (the default target_unit), 0.254 cm for METRIC, 2.54 mm for METRICWX.
    t = _make_thread()
    for us_units, hour_rain in ((US, 0.1), (METRIC, 0.254), (METRICWX, 2.54)):
        record = {"dateTime": 1783256300, "usUnits": us_units,
                  "hourRain": hour_rain}
        d = json.loads(t.get_post_body(record)[0])[0]
        assert d["rain_1h"] == 2.54, \
            "usUnits=%s: rain_1h=%s, want 2.54 mm" % (us_units, d["rain_1h"])
    print("  [PASS] test_rain_1h_is_millimeters_in_every_unit_system")


def test_dry_hour_is_sent_as_zero():
    # 0.0 is a real reading, not a missing one, so the rain guard must not treat
    # it as falsy and drop it.
    t = _make_thread()
    record = {"dateTime": 1783256300, "usUnits": US, "hourRain": 0.0}
    d = json.loads(t.get_post_body(record)[0])[0]
    assert d["rain_1h"] == 0.0
    print("  [PASS] test_dry_hour_is_sent_as_zero")


def test_us_record_uses_api_units_for_every_field():
    # The production path: a US archive record (inches, mph, degF, inHg). Every
    # field must reach the API in its documented unit: degC, %, hPa, m/s, degrees,
    # mm. Only rain_1h changed with #405; the rest pin the numbers already sent.
    t = _make_thread()
    record = {"dateTime": 1783256300, "usUnits": US, "outTemp": 70.7,
              "outHumidity": 63.0, "barometer": 29.92, "windSpeed": 10.0,
              "windGust": 20.0, "windDir": 270.0, "dewpoint": 59.0,
              "heatindex": 71.6, "hourRain": 0.1}
    d = json.loads(t.get_post_body(record)[0])[0]
    assert d == {"station_id": "STN", "dt": 1783256300, "temperature": 21.5,
                 "humidity": 63.0, "pressure": 1013.2, "wind_speed": 4.5,
                 "wind_gust": 8.9, "wind_deg": 270.0, "dew_point": 15.0,
                 "heat_index": 22.0, "rain_1h": 2.54}, d
    print("  [PASS] test_us_record_uses_api_units_for_every_field")


def test_none_fields_are_omitted():
    t = _make_thread()
    # hourRain is None when the archive holds no rain rows for the last hour
    record = {"dateTime": 1783256300, "usUnits": METRIC, "outTemp": None,
              "windSpeed": None, "hourRain": None}
    body, _ = t.get_post_body(record)
    d = json.loads(body)[0]
    # only the always-present keys survive
    assert set(d.keys()) == {"station_id", "dt"}
    print("  [PASS] test_none_fields_are_omitted")


def test_format_url_carries_appid():
    t = _make_thread()
    assert t.format_url({}) == owm.STATION_URL + "?appid=KEY"
    print("  [PASS] test_format_url_carries_appid")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
    print("\n%d/%d passed" % (len(tests), len(tests)))
