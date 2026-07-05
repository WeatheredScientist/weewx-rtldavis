"""Offline regression test for the owm.py RESTThread rebase (S24, findings U1/U2).

The bug (U1/U2): owm.py overrode RESTThread.run_loop with a hand-rolled
queue.get/urlopen loop, so it silently discarded every RESTThread resilience
feature it was constructed with -- post_interval, max_backlog, stale, max_tries,
retry_wait, skip_upload -- and a single transient network failure dropped the
record with no retry. The fix drives the OWM JSON POST through the standard
RESTThread hooks (format_url + get_post_body) so retry/backoff come for free.

This test asserts:
  * OWMThread no longer overrides run_loop / post_request (they belong to
    RESTThread now);
  * get_post_body() returns the correct (json_body, content_type) pair, with
    None fields omitted and the km/h -> m/s wind conversion applied.

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
# Identity to_METRIC: feed the test records values already in METRIC units.
weewx_units.to_METRIC = lambda record: dict(record)
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
    record = {"dateTime": 1783256300, "usUnits": 16, "outTemp": 21.5,
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
    assert d["rain_1h"] == 0.25
    print("  [PASS] test_get_post_body_shape_and_content_type")


def test_none_fields_are_omitted():
    t = _make_thread()
    record = {"dateTime": 1783256300, "usUnits": 16, "outTemp": None,
              "windSpeed": None}
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
