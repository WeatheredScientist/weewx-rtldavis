"""Offline regression test for the windy.py rain unit and window (S145, #405).

The bug: windy.py converted the record with to_METRIC, whose rain unit is
centimeters, and sent 'rain' (the accumulation over one archive interval) as
precip. Windy documents precip as precipitation over the last hour in millimeters,
so the value had the wrong unit (10x low) and the wrong window. windy.py had no
tests, so nothing saw it. The same unit error sat in owm.py behind an identity
unit stub (see test_owm_post_body.py); the stub here models weewx's real unit
systems instead.

This test asserts:
  * precip is the last hour (hourRain) in millimeters, whatever unit system the
    archive record is in;
  * precip is left out when there is no hourly total, not filled from the
    per-interval 'rain', while a dry hour (0.0) is sent as zero;
  * every other field keeps the unit and number format it was already sent in;
  * None fields are omitted.

weewx is not installed in the test/CI environment, so we stub the weewx modules
in sys.modules before importing windy (same pattern as the other tests here).

Run:  python3 -m pytest tests/ (pytest only)
"""
import sys
import types
import urllib.parse
import urllib.request


# --- stub the weewx deps so windy.py imports without weewx installed ---
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
    # Minimal stand-in: WindyThread only needs a base class to call.
    def __init__(self, queue, **kwargs):
        self.queue = queue
        self.rest_kwargs = kwargs

    # process_record, get_request and get_post_body follow weewx 5.5.2's RESTThread,
    # less the database read and the record checks, so the payload test below sees
    # exactly what would go on the wire. post_with_retries is the HTTP call; the
    # test replaces it.
    def process_record(self, record, dbmanager):
        _url = self.format_url(record)
        _request = self.get_request(_url)
        _payload = self.get_post_body(record)
        if _payload:
            _request.add_header('Content-Type', _payload[1])
            data = _payload[0]
        else:
            data = None
        self.post_with_retries(_request, data)

    def get_request(self, url):
        _request = urllib.request.Request(url)
        _request.add_header("User-Agent", "weewx/5.5.2")
        return _request

    def get_post_body(self, record):
        return None

    def post_with_retries(self, request, data=None):
        raise AssertionError("the test must capture the HTTP call")


def _get_site_dict(config_dict, *args, **kwargs):
    return {}


weewx_restx.StdRESTbase = _StdRESTbase
weewx_restx.RESTThread = _RESTThread
weewx_restx.get_site_dict = _get_site_dict
weewx.restx = weewx_restx

weewx_units = _mod("weewx.units")

# A small model of weewx.units, so the tests run a real unit conversion. An identity
# stub hid a 10x rain error in owm.py (#405): METRIC rain is centimeters and the
# vendor APIs want millimeters. System numbers and factors are weewx 5.3.1's (checked
# against the real module in S145). Only the types windy.py converts are listed; the
# rest pass through, as in weewx, because humidity, direction, UV, radiation and time
# are the same in every system.
US, METRIC, METRICWX = 1, 16, 17
_GROUP = {"outTemp": "temp", "dewpoint": "temp", "barometer": "pressure",
          "windSpeed": "speed", "windGust": "speed",
          "hourRain": "rain", "rain": "rain"}
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

import windy  # noqa: E402


def _make_thread():
    return windy.WindyThread(queue=None, station_id="STN", password="PW",
                             manager_dict={})


def _params(record):
    """format_url() as a dict of query parameters."""
    base, _, query = _make_thread().format_url(record).partition("?")
    assert base == windy.STATION_URL
    return {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}


def test_precip_is_last_hour_in_millimeters():
    # #405: the same 2.54 mm fell in the last hour whichever unit system the
    # archive record arrives in: 0.1 in for US (the default target_unit), 0.254 cm
    # for METRIC, 2.54 mm for METRICWX. 'rain' (one archive interval) is set to a
    # different amount each time, so a fix of only the unit or only the window fails.
    for us_units, hour_rain, interval_rain in ((US, 0.1, 0.02),
                                               (METRIC, 0.254, 0.0508),
                                               (METRICWX, 2.54, 0.508)):
        record = {"dateTime": 1783256300, "usUnits": us_units,
                  "hourRain": hour_rain, "rain": interval_rain}
        precip = _params(record).get("precip")
        assert precip == "2.54", \
            "usUnits=%s: precip=%s, want 2.54 mm" % (us_units, precip)
    print("  [PASS] test_precip_is_last_hour_in_millimeters")


def test_precip_omitted_without_an_hourly_total():
    # hourRain is None when the archive holds no rain rows for the last hour. The
    # per-interval 'rain' is not the same quantity, so it must not stand in for it.
    for hour_rain in ({"hourRain": None}, {}):
        record = {"dateTime": 1783256300, "usUnits": US, "rain": 0.02}
        record.update(hour_rain)
        assert "precip" not in _params(record), hour_rain
    print("  [PASS] test_precip_omitted_without_an_hourly_total")


def test_dry_hour_is_sent_as_zero():
    # 0.0 is a real reading, not a missing one, so the rain guard must not treat
    # it as falsy and drop it.
    record = {"dateTime": 1783256300, "usUnits": US, "hourRain": 0.0}
    assert _params(record)["precip"] == "0.00"
    print("  [PASS] test_dry_hour_is_sent_as_zero")


def test_other_fields_keep_their_units():
    # A US archive record, the production path. Every non-rain field must reach
    # Windy as it did before #405: degC, degC, %, m/s, m/s, degrees, Pa, UV index,
    # W/m^2. The record carries no rain, so precip is absent here.
    record = {"dateTime": 1783256300, "usUnits": US, "outTemp": 70.7,
              "dewpoint": 59.0, "outHumidity": 63.0, "windSpeed": 10.0,
              "windGust": 20.0, "windDir": 270.0, "barometer": 29.92,
              "UV": 5.5, "radiation": 512.3}
    assert _params(record) == {
        "id": "STN", "PASSWORD": "PW", "time": "now", "temp": "21.5",
        "dewpoint": "15.0", "humidity": "63", "wind": "4.5", "gust": "8.9",
        "winddir": "270", "pressure": "101321", "uv": "5.5",
        "solarradiation": "512.3"}
    print("  [PASS] test_other_fields_keep_their_units")


def test_none_fields_are_omitted():
    record = {"dateTime": 1783256300, "usUnits": METRIC, "outTemp": None,
              "windSpeed": None, "hourRain": None, "rain": None}
    # only the always-present keys survive
    assert set(_params(record)) == {"id", "PASSWORD", "time"}
    print("  [PASS] test_none_fields_are_omitted")


# Payload identity (S180a, audit 23). The bytes each record produced before owm.py and
# windy.py moved onto the shared rest_site base, captured from the old code and pinned
# here. A refactor must send the same thing; a deliberate payload change must update
# these with a reason. The records cover a US archive record (the production path, with
# an int humidity that must stay an int), values sitting on a rounding boundary in both
# US and METRIC, a METRICWX record, and missing fields.
PAYLOAD_RECORDS = [
    {"dateTime": 1783256300, "usUnits": US, "outTemp": 70.73, "outHumidity": 63,
     "barometer": 29.921, "windSpeed": 7.333333333333333, "windGust": 15,
     "windDir": 247.5, "dewpoint": 58.12, "heatindex": 71.6,
     "hourRain": 0.01 + 0.01 + 0.01, "rain": 0.01, "UV": 5.5, "radiation": 512.25},
    {"dateTime": 1783256600, "usUnits": US, "windSpeed": 0.5592340730136006,
     "windGust": 0.0, "hourRain": 0.0, "outTemp": -40.0},
    {"dateTime": 1783256900, "usUnits": METRIC, "windSpeed": 0.18,
     "windGust": 36.0, "barometer": 1013.25, "hourRain": 0.254, "outHumidity": 99.5},
    {"dateTime": 1783257200, "usUnits": METRICWX, "outTemp": 21.45, "windSpeed": 4.25,
     "windGust": 8.95, "hourRain": 2.54, "dewpoint": None, "UV": None},
    {"dateTime": 1783257500, "usUnits": US, "outTemp": None, "windSpeed": None,
     "hourRain": None, "rain": 0.02},
]


def _sent(record):
    """What process_record hands to the HTTP call: (url, Content-Type, body)."""
    t = _make_thread()
    calls = []
    t.post_with_retries = lambda request, data=None: calls.append(
        (request.full_url, request.get_header("Content-type"), data))
    t.process_record(record, None)
    assert len(calls) == 1
    return calls[0]


_WINDY_URL = "https://stations.windy.com/api/v2/observation/update?id=STN&PASSWORD=PW&time=now"


def test_payload_bytes_unchanged():
    expected = [
        "&temp=21.5&dewpoint=14.5&humidity=63&wind=3.3&gust=6.7&winddir=248"
        "&pressure=101324&precip=0.76&uv=5.5&solarradiation=512.2",
        "&temp=-40.0&wind=0.2&gust=0.0&precip=0.00",
        "&humidity=100&wind=0.0&gust=10.0&pressure=101325&precip=2.54",
        "&temp=21.4&wind=4.2&gust=8.9&precip=2.54",
        "",
    ]
    for record, query in zip(PAYLOAD_RECORDS, expected):
        # a GET: no body and no Content-Type
        assert _sent(record) == (_WINDY_URL + query, None, None), record
