"""Offline tests for wcloud.py, the vendored WeatherCloud uploader (S180c, audit 39).

wcloud.py had no test reference at all. This covers what the module itself does:
  * the service reads [StdRESTful][[WeatherCloud]] (id and key required), starts one
    thread, binds the archive event once, and does nothing when unconfigured;
  * the thread constructor forwards its resilience knobs to RESTThread and keeps its
    documented defaults;
  * get_record converts a record to METRICWX, adds the 10-minute wind figures, folds
    wind direction into [0, 359], and inverts the battery flags (weewx 1 = low,
    WeatherCloud 1 = ok);
  * format_url scales and rounds each field the way WeatherCloud expects, leaves out
    None and missing fields, keeps a zero, and redacts the key in the debug log;
  * the module refuses to import under weewx older than 3.

CHANGES-FROM-UPSTREAM.md lists two edits for this file, an SPDX line and three
`# type: ignore` comments on the import shims. Neither changes behavior, so neither has
a test of its own; the mypy gate covers the second.

NOT covered here, because wcloud.py has no code of its own for it: the HTTP request, the
retry loop and the non-2xx response path live in weewx.restx.RESTThread, which is not
installed in the test environment and is not part of this repo. What can be pinned is
that max_tries, retry_wait, timeout and log_failure reach RESTThread (below).

weewx is not installed in the test/CI environment, so the fakes below stand in for it.
They are installed per test through monkeypatch, so they never leak into another file's
stubs. The unit model (US, METRIC, METRICWX; factors from weewx 5.3.1) is the same idea
as in test_owm_post_body.py.

Run:  python3 -m pytest tests/ (pytest only)
"""
import importlib
import logging
import sys
import time
import types
import urllib.parse

import pytest

US, METRIC, METRICWX = 1, 16, 17
TS = 1700000000  # 2023-11-14 22:13:20 UTC

# (group of a record key) -> unit per system, and unit -> (scale, offset) to the METRICWX
# unit of that group.
_GROUP = {"outTemp": "temp", "inTemp": "temp", "dewpoint": "temp", "heatindex": "temp",
          "windchill": "temp", "barometer": "pressure", "windSpeed": "speed",
          "windGust": "speed", "dayRain": "rain", "rainRate": "rain"}
_UNIT = {US:       {"temp": "degree_F", "pressure": "inHg", "speed": "mile_per_hour",
                    "rain": "inch"},
         METRIC:   {"temp": "degree_C", "pressure": "mbar", "speed": "km_per_hour",
                    "rain": "cm"},
         METRICWX: {"temp": "degree_C", "pressure": "mbar", "speed": "meter_per_second",
                    "rain": "mm"}}
_BASE = {"degree_F": (5.0 / 9.0, -160.0 / 9.0), "degree_C": (1.0, 0.0),
         "inHg": (33.8638815, 0.0), "mbar": (1.0, 0.0),
         "mile_per_hour": (0.44704, 0.0), "km_per_hour": (1.0 / 3.6, 0.0),
         "meter_per_second": (1.0, 0.0),
         "inch": (25.4, 0.0), "cm": (10.0, 0.0), "mm": (1.0, 0.0)}


def _to_metricwx(record):
    if record["usUnits"] == METRICWX:
        return record
    out = {"usUnits": METRICWX}
    for key, val in record.items():
        group = _GROUP.get(key)
        if key == "usUnits":
            continue
        if group is None or val is None:
            out[key] = val
            continue
        s_scale, s_off = _BASE[_UNIT[record["usUnits"]][group]]
        t_scale, t_off = _BASE[_UNIT[METRICWX][group]]
        out[key] = (val * s_scale + s_off - t_off) / t_scale
    return out


def _convert(val_t, target_unit):
    # weewx.units.convert returns a None value untouched
    value, unit, group = val_t
    if value is None or unit == target_unit:
        return (value, target_unit, group)
    s_scale, s_off = _BASE[unit]
    t_scale, t_off = _BASE[target_unit]
    return ((value * s_scale + s_off - t_off) / t_scale, target_unit, group)


def _get_site_dict(config_dict, service, *required):
    # the part of weewx.restx.get_site_dict that wcloud.py relies on
    _get_site_dict.calls.append((service, required))
    try:
        site = dict(config_dict["StdRESTful"][service])
    except KeyError:
        return None
    if str(site.pop("enable", "true")).lower() not in ("1", "true", "yes", "on"):
        return None
    if any(k not in site for k in required):
        return None
    return site


class _FakeRESTThread:
    def __init__(self, queue, protocol_name, manager_dict, **kwargs):
        self.queue = queue
        self.protocol_name = protocol_name
        self.manager_dict = manager_dict
        self.rest_kwargs = kwargs
        self.started = 0

    def get_record(self, record, dbm):
        return dict(record)

    def start(self):
        self.started += 1


class _FakeRESTbase:
    def __init__(self, engine, config_dict):
        self.bound = []

    def bind(self, event_type, handler):
        self.bound.append((event_type, handler))


def _install_fakes(monkeypatch, version="5.3.1"):
    def mod(name, **attrs):
        m = types.ModuleType(name)
        vars(m).update(attrs)
        monkeypatch.setitem(sys.modules, name, m)
        return m

    _get_site_dict.calls = []
    wx = mod("weewx", __version__=version, debug=0, METRICWX=METRICWX,
             NEW_ARCHIVE_RECORD="NEW_ARCHIVE_RECORD",
             UnsupportedFeature=type("UnsupportedFeature", (Exception,), {}))
    wx.__path__ = []
    wx.restx = mod("weewx.restx", StdRESTbase=_FakeRESTbase, RESTThread=_FakeRESTThread,
                   get_site_dict=_get_site_dict)
    wx.manager = mod("weewx.manager",
                     get_manager_dict=lambda binds, dbs, name: {"binding": name,
                                                                "dbs": dbs})
    wx.units = mod("weewx.units", to_METRICWX=_to_metricwx, convert=_convert,
                   getStandardUnitType=lambda system, obs: (_UNIT[system]["speed"],
                                                            "group_speed"))
    wx.wxformulas = mod("weewx.wxformulas",
                        heatindexC=lambda t, h: ("heatindexC", t, h),
                        dewpointC=lambda t, h: ("dewpointC", t, h))
    mod("weeutil", __path__=[])
    mod("weeutil.weeutil",
        to_bool=lambda v: str(v).lower() in ("1", "true", "yes", "on"))
    mod("weeutil.logger")
    return wx


def _load(monkeypatch, version="5.3.1"):
    wx = _install_fakes(monkeypatch, version)
    monkeypatch.delitem(sys.modules, "wcloud", raising=False)
    return importlib.import_module("wcloud"), wx


@pytest.fixture
def wc(monkeypatch):
    module, _ = _load(monkeypatch)
    yield module
    sys.modules.pop("wcloud", None)


@pytest.fixture
def wx():
    return sys.modules["weewx"]


def _config(**site):
    return {"StdRESTful": {"WeatherCloud": site},
            "DataBindings": {"wx_binding": {}}, "Databases": {"archive_sqlite": {}}}


def _thread(wc, **kw):
    return wc.WeatherCloudThread(None, "ID123", "SECRETKEY", {}, **kw)


class _Dbm:
    """A manager whose getSql answers by the aggregate the SQL asks for."""
    table_name = "archive"

    def __init__(self, avg=(10.0,), hi=(20.0,), avgdir=(90.0,)):
        self.rows = {"AVG(windSpeed)": avg, "MAX(": hi, "AVG(windDir)": avgdir}
        self.calls = []

    def getSql(self, sql, args):
        self.calls.append((sql, args))
        for needle, row in self.rows.items():
            if needle in sql:
                return row
        raise AssertionError("unexpected SQL: %s" % sql)


# ---------------------------------------------------------------- service

def test_service_starts_one_thread_and_binds_once(wc):
    cfg = _config(id="ID123", key="KEY456", post_interval="300")
    svc = wc.WeatherCloud(engine=None, config_dict=cfg)
    t = svc.archive_thread
    assert isinstance(t, wc.WeatherCloudThread)
    assert t.started == 1
    assert svc.bound == [("NEW_ARCHIVE_RECORD", svc.new_archive_record)]
    assert (t.id, t.key) == ("ID123", "KEY456")
    assert t.queue is svc.archive_queue
    # the manager dict comes from the wx_binding of the configured databases
    assert t.manager_dict == {"binding": "wx_binding", "dbs": cfg["Databases"]}
    # id and key are the required options, nothing else
    assert sys.modules["weewx.restx"].get_site_dict.calls == [
        ("WeatherCloud", ("id", "key"))]
    # a configured option is forwarded to the thread
    assert t.rest_kwargs["post_interval"] == "300"


@pytest.mark.parametrize("site", [
    {"id": "ID123"},                            # key missing
    {"key": "KEY456"},                          # id missing
    {"id": "ID123", "key": "K", "enable": "false"},
])
def test_unconfigured_service_does_nothing(wc, site):
    svc = wc.WeatherCloud(engine=None, config_dict=_config(**site))
    assert not hasattr(svc, "archive_thread")
    assert svc.bound == []


def test_no_weathercloud_section_does_nothing(wc):
    svc = wc.WeatherCloud(engine=None, config_dict={"StdRESTful": {}})
    assert not hasattr(svc, "archive_thread")
    assert svc.bound == []


def test_new_archive_record_queues_the_record(wc):
    svc = wc.WeatherCloud(engine=None, config_dict=_config(id="I", key="K"))
    event = types.SimpleNamespace(record={"dateTime": TS})
    svc.new_archive_record(event)
    assert svc.archive_queue.get_nowait() == {"dateTime": TS}


# ---------------------------------------------------------------- thread config

def test_thread_forwards_resilience_knobs_with_defaults(wc):
    t = _thread(wc)
    assert t.protocol_name == "WeatherCloud"
    kw = t.rest_kwargs
    assert (kw["post_interval"], kw["max_tries"], kw["timeout"], kw["retry_wait"]) == \
        (600, 3, 60, 5)
    assert kw["stale"] is None
    assert kw["log_success"] is True and kw["log_failure"] is True
    assert kw["max_backlog"] == sys.maxsize
    assert t.server_url == "http://api.weathercloud.net/v01/set"
    assert t.skip_upload is False


def test_thread_forwards_overrides(wc):
    t = _thread(wc, post_interval=300, max_tries=7, timeout=9, retry_wait=2,
                stale=120, max_backlog=4, log_failure=False, skip_upload="true",
                server_url="http://example.invalid/set")
    kw = t.rest_kwargs
    assert (kw["post_interval"], kw["max_tries"], kw["timeout"], kw["retry_wait"],
            kw["stale"], kw["max_backlog"], kw["log_failure"]) == \
        (300, 7, 9, 2, 120, 4, False)
    assert t.skip_upload is True            # to_bool of the config string
    assert t.server_url == "http://example.invalid/set"


# ---------------------------------------------------------------- helpers

def test_invert_flips_weewx_battery_status(wc):
    # weewx: 0 ok, 1 low. weathercloud: 1 ok, 0 low. None stays None.
    assert wc._invert(0) == 1
    assert wc._invert(1) == 0
    assert wc._invert(None) is None


def test_convert_windspeed_units(wc):
    assert wc._convert_windspeed(None, US) is None
    assert wc._convert_windspeed(5.0, None) is None
    assert wc._convert_windspeed(5.0, METRICWX) == 5.0
    assert wc._convert_windspeed(10.0, US) == pytest.approx(4.4704)
    assert wc._convert_windspeed(36.0, METRIC) == pytest.approx(10.0)


def test_calc_thw(wc):
    assert wc._calc_thw(None, 2.0) is None
    assert wc._calc_thw(30.0, None) is None
    # 30 C = 86 F; 2 m/s = 4.5 mph; 86 - 1.072 * 4.5 = 81.176 F = 27.32 C
    assert wc._calc_thw(30.0, 2.0) == pytest.approx(27.32, abs=1e-3)


def test_wind_queries_use_a_ten_minute_window(wc):
    dbm = _Dbm()
    assert wc._get_windavg(dbm, TS) == 10.0
    assert wc._get_windhi(dbm, TS) == 20.0
    assert wc._get_winddiravg(dbm, TS) == 90.0
    for _, args in dbm.calls:
        assert args == (TS - 600, TS)
    assert all("FROM archive" in sql for sql, _ in dbm.calls)


def test_wind_queries_pass_through_no_data(wc):
    class NoRows(_Dbm):
        def getSql(self, sql, args):
            return None
    for fn in (wc._get_windavg, wc._get_windhi, wc._get_winddiravg):
        assert fn(NoRows(), TS) is None
    assert wc._get_windavg(_Dbm(avg=(None,)), TS) is None


# ---------------------------------------------------------------- get_record

def _us_record(**over):
    rec = {"dateTime": TS, "usUnits": US, "outTemp": 50.0, "outHumidity": 63.0,
           "barometer": 29.92, "windSpeed": 5.0, "windDir": 200.0, "dayRain": 0.5}
    rec.update(over)
    return rec


def test_get_record_converts_a_us_record_to_metricwx(wc):
    rec = _thread(wc).get_record(_us_record(), _Dbm(avg=(10.0,), hi=(20.0,)))
    assert rec["usUnits"] == METRICWX
    assert rec["outTemp"] == pytest.approx(10.0)
    assert rec["barometer"] == pytest.approx(1013.2, abs=0.1)
    assert rec["windSpeed"] == pytest.approx(2.2352)
    assert rec["dayRain"] == pytest.approx(12.7)
    assert rec["outHumidity"] == 63.0
    # the 10-minute wind figures come out of the archive in the record's own units
    assert rec["windavg"] == pytest.approx(4.4704)
    assert rec["windhi"] == pytest.approx(8.9408)
    assert rec["winddiravg"] == 90.0


def test_get_record_converts_wind_figures_from_a_metric_archive(wc):
    rec = _thread(wc).get_record(
        {"dateTime": TS, "usUnits": METRIC, "windSpeed": 18.0},
        _Dbm(avg=(36.0,), hi=(72.0,)))
    assert rec["windSpeed"] == pytest.approx(5.0)
    assert rec["windavg"] == pytest.approx(10.0)
    assert rec["windhi"] == pytest.approx(20.0)


def test_get_record_missing_wind_data_stays_none(wc):
    rec = _thread(wc).get_record(
        _us_record(windSpeed=None, windDir=None),
        _Dbm(avg=(None,), hi=(None,), avgdir=(None,)))
    assert rec["windSpeed"] is None and rec["windDir"] is None
    assert rec["windavg"] is None and rec["windhi"] is None
    assert rec["winddiravg"] is None


@pytest.mark.parametrize("direction, expected", [(0.0, 0.0), (359.0, 359.0),
                                                 (360.0, 0.0), (365.0, 5.0)])
def test_get_record_folds_wind_direction_into_0_359(wc, direction, expected):
    rec = _thread(wc).get_record(_us_record(windDir=direction),
                                 _Dbm(avgdir=(direction,)))
    assert rec["windDir"] == expected
    assert rec["winddiravg"] == expected


def test_get_record_derives_indoor_figures_from_converted_values(wc):
    rec = _thread(wc).get_record(_us_record(inTemp=68.0, inHumidity=40.0), _Dbm())
    # the formulas run on the METRICWX temperature, not the archive's Fahrenheit
    assert rec["inheatindex"] == ("heatindexC", pytest.approx(20.0), 40.0)
    assert rec["indewpoint"] == ("dewpointC", pytest.approx(20.0), 40.0)


def test_get_record_without_indoor_sensors_has_no_indoor_figures(wc):
    rec = _thread(wc).get_record(_us_record(inTemp=68.0), _Dbm())
    assert "inheatindex" not in rec and "indewpoint" not in rec


def test_get_record_inverts_each_battery_flag(wc):
    rec = _thread(wc).get_record(
        _us_record(txBatteryStatus=0, windBatteryStatus=1, rainBatteryStatus=None,
                   outTempBatteryStatus=1, inTempBatteryStatus=0), _Dbm())
    assert (rec["bat01"], rec["bat02"], rec["bat03"], rec["bat04"], rec["bat05"]) == \
        (1, 0, None, 0, 1)


def test_get_record_without_battery_fields_has_no_battery_keys(wc):
    rec = _thread(wc).get_record(_us_record(), _Dbm())
    assert not any(k in rec for k in ("bat01", "bat02", "bat03", "bat04", "bat05"))


# ---------------------------------------------------------------- format_url

def _query(url):
    base, _, qs = url.partition("?")
    return base, {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}


def test_format_url_scales_and_rounds_each_field(wc):
    record = {"dateTime": TS, "outTemp": 21.5, "outHumidity": 63.4, "windDir": 270.0,
              "windSpeed": 5.0, "barometer": 1013.2, "dayRain": 2.5, "rainRate": 0.0,
              "inTemp": 22.0, "UV": 3.0, "radiation": 450.0,
              "consBatteryVoltage": 4.1, "bat01": 1, "windhi": 8.9}
    base, q = _query(_thread(wc).format_url(record))
    assert base == "http://api.weathercloud.net/v01/set"
    assert q["ver"] == "5.3.1" and q["type"] == "251"
    assert (q["wid"], q["key"]) == ("ID123", "SECRETKEY")
    assert (q["time"], q["date"]) == ("2213", "20231114")   # UTC
    assert q["temp"] == "215" and q["hum"] == "63" and q["wdir"] == "270"
    assert q["wspd"] == "50" and q["bar"] == "10132" and q["rain"] == "25"
    assert q["tempin"] == "220" and q["uvi"] == "30" and q["solarrad"] == "4500"
    assert q["battery"] == "410" and q["battery01"] == "1" and q["wspdhi"] == "89"
    # a zero reading is a reading, not a gap
    assert q["rainrate"] == "0"


def test_format_url_leaves_out_none_and_missing_fields(wc):
    record = {"dateTime": TS, "outTemp": None, "outHumidity": 50.0}
    _, q = _query(_thread(wc).format_url(record))
    assert set(q) == {"ver", "type", "wid", "key", "time", "date", "hum"}


def test_format_url_uses_the_configured_server(wc):
    url = _thread(wc, server_url="http://example.invalid/set").format_url(
        {"dateTime": TS})
    assert url.startswith("http://example.invalid/set?")


def test_format_url_zero_pads_time_and_date(wc):
    # 2024-01-02 03:04:00 UTC
    ts = 1704164640
    assert time.gmtime(ts)[:5] == (2024, 1, 2, 3, 4)
    _, q = _query(_thread(wc).format_url({"dateTime": ts}))
    assert (q["time"], q["date"]) == ("0304", "20240102")


def test_format_url_debug_log_redacts_the_key(wc, wx, caplog):
    wx.debug = 2
    caplog.set_level(logging.DEBUG, logger="wcloud")
    url = _thread(wc).format_url({"dateTime": TS, "outHumidity": 50.0})
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "key=XXX" in text and "SECRETKEY" not in text
    assert "SECRETKEY" in url   # the real key still goes on the wire


def test_format_url_logs_nothing_below_debug_level_2(wc, wx, caplog):
    wx.debug = 1
    caplog.set_level(logging.DEBUG, logger="wcloud")
    _thread(wc).format_url({"dateTime": TS})
    assert not [r for r in caplog.records if "url:" in r.getMessage()]


# ---------------------------------------------------------------- import guard

def test_import_refuses_weewx_older_than_3(monkeypatch):
    wx = _install_fakes(monkeypatch, version="2.7.0")
    monkeypatch.delitem(sys.modules, "wcloud", raising=False)
    with pytest.raises(wx.UnsupportedFeature):
        importlib.import_module("wcloud")
    assert "wcloud" not in sys.modules
