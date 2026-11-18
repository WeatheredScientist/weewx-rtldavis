"""influx.py accepts and ignores the retired `lease_dir` key (DEC-0242, #558).

The NAS-LEASE courtesy yield (DEC-0111) is gone: it had nothing to yield to
since DEC-0141. Influx builds its upload thread with `InfluxThread(queue,
**site_dict)`, so an unknown key in `[[Influx]]` would be a TypeError that
stops weewxd at startup. Prod's live config and its rx-baseline copy still set
`lease_dir`, and so may an adopter's, so the service must drop the key, log one
INFO line, and start. These tests pin that.

weewx is not installed in the test/CI environment, so the weewx modules are
stubbed in sys.modules before importing influx (the pattern the retired
test_influx_lease_yield.py used).

Run:  python3 -m pytest tests/ (pytest only)
"""
import sys
import types

import pytest


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
weewx.NEW_LOOP_PACKET = "NEW_LOOP_PACKET"
weewx.debug = 0
weewx.__version__ = "5.5.0"


class ViolatedPrecondition(Exception):
    pass


class UnknownBinding(Exception):
    pass


class UnsupportedFeature(Exception):
    pass


weewx.ViolatedPrecondition = ViolatedPrecondition
weewx.UnknownBinding = UnknownBinding
weewx.UnsupportedFeature = UnsupportedFeature

weewx_restx = _mod("weewx.restx")


class _StdRESTbase:
    def __init__(self, *a, **k):
        pass

    def bind(self, *a, **k):
        pass


class _RESTThread:
    """Takes exactly the keyword set weewx 5.5's RESTThread.__init__ takes, so
    an unexpected key fails here the way it fails in weewxd."""

    def __init__(self, queue, protocol_name=None, manager_dict=None,
                 post_interval=None, max_backlog=None, stale=None,
                 log_success=True, log_failure=True, max_tries=3,
                 timeout=60, retry_wait=5):
        self.queue = queue
        self.post_interval = post_interval

    def start(self):
        pass


def _get_site_dict(config_dict, service, *args):
    return dict(config_dict['StdRESTful'][service])


weewx_restx.StdRESTbase = _StdRESTbase
weewx_restx.RESTThread = _RESTThread
weewx_restx.get_site_dict = _get_site_dict
weewx.restx = weewx_restx

weewx_units = _mod("weewx.units")
weewx_units.unit_constants = {}
weewx_units.to_std_system = lambda record, usn: record
weewx.units = weewx_units

weewx_manager = _mod("weewx.manager")
weewx_manager.get_manager_dict_from_config = lambda *a, **k: {}
weewx.manager = weewx_manager

weeutil_weeutil = _mod("weeutil.weeutil")
weeutil_weeutil.to_bool = lambda v: bool(v)
weeutil_weeutil.accumulateLeaves = lambda d: d
weeutil_pkg = _pkg("weeutil")
weeutil_pkg.weeutil = weeutil_weeutil

import influx  # noqa: E402


def _config(**extra):
    site = {"server_url": "http://x", "org": "o", "bucket": "b",
            "token": "t", "augment_record": False}
    site.update(extra)
    return {"StdRESTful": {"Influx": site}}


@pytest.fixture
def infos(monkeypatch):
    seen = []
    monkeypatch.setattr(influx, "loginf", seen.append)
    return seen


def test_a_config_that_still_sets_lease_dir_starts(infos):
    # Building the thread is the check: the stub RESTThread, like weewx's,
    # raises TypeError on a key it does not take.
    svc = influx.Influx(engine=None, cfg_dict=_config(lease_dir="/nas-lease"))
    assert isinstance(svc.archive_thread, influx.InfluxThread)
    assert any("Data will be uploaded" in m for m in infos)


def test_lease_dir_logs_one_ignored_line(infos):
    influx.Influx(engine=None, cfg_dict=_config(lease_dir="/nas-lease"))
    hits = [m for m in infos if "lease_dir" in m]
    assert len(hits) == 1
    assert "ignored" in hits[0]


def test_no_lease_dir_no_message(infos):
    influx.Influx(engine=None, cfg_dict=_config())
    assert not [m for m in infos if "lease_dir" in m]
    assert any("Data will be uploaded" in m for m in infos)


def test_the_thread_itself_rejects_lease_dir():
    """Positive control: without the service's pop, the key would crash the
    start, which is why the pop must stay."""
    with pytest.raises(TypeError):
        influx.InfluxThread(None, server_url="http://x", org="o", bucket="b",
                            token="t", lease_dir="/nas-lease")


def test_the_yield_is_gone():
    assert "skip_this_post" not in influx.InfluxThread.__dict__
    assert not hasattr(influx, "LEASE_YIELD_POST_INTERVAL_S")
    assert not hasattr(influx, "TENANT")
    assert influx.VERSION == "0.20+ws.3"
