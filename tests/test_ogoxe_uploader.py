"""Offline tests for ogoxeUploader.py, the patched OgoXe uploader (S180c, audit 39).

ogoxeUploader.py had no test reference at all. This covers the module's own code and
each patch that CHANGES-FROM-UPSTREAM.md lists for it:
  * row 3 (#408, S146): __init__ calls weewx.engine.StdService.__init__ and never
    StdWunderground.__init__, so the service starts exactly one thread and binds
    NEW_ARCHIVE_RECORD exactly once, even with [[Wunderground]] configured;
  * row 1: the debug line reports the URL actually used (OGOXE_API_URL), not None;
  * config handling: station and password are required, rapidfire is dropped,
    archive_post can switch the upload off, other options reach the thread;
  * new_archive_record queues the record.
Rows 2, 4 and 5 (an SPDX line, two rewritten comments, trailing whitespace) change no
behavior and have no test.

NOT covered here, because ogoxeUploader.py has no code of its own for it: the HTTP
request, the query-string build, the retry loop and the non-2xx response path all live in
weewx.restx.AmbientThread, which is not installed in the test environment and is not part
of this repo.

weewx is not installed in the test/CI environment, so the fakes below stand in for it.
StdWunderground models what CHANGES-FROM-UPSTREAM.md row 3 says the real one does
(weewx 5.5.0 restx.py): with [[Wunderground]] configured its __init__ starts its own
thread and binds the archive event. That is what makes the row-3 test able to fail.
The fakes are installed per test through monkeypatch, so they never leak into another
file's stubs.

Run:  python3 -m pytest tests/ (pytest only)
"""
import importlib
import logging
import queue
import sys
import types

import pytest

API_URL = "https://application.ogoxe.com/upload-data"


class _FakeStdService:
    def __init__(self, engine, config_dict):
        self.bound = []

    def bind(self, event_type, handler):
        self.bound.append((event_type, handler))


class _FakeStdWunderground(_FakeStdService):
    """What row 3 of CHANGES-FROM-UPSTREAM.md says StdWunderground.__init__ does."""
    wu_threads_started = 0

    def __init__(self, engine, config_dict):
        _FakeStdService.__init__(self, engine, config_dict)
        if "Wunderground" in config_dict.get("StdRESTful", {}):
            type(self).wu_threads_started += 1
            self.bind("NEW_ARCHIVE_RECORD", self.new_archive_record)


class _FakeAmbientThread:
    instances: list = []

    def __init__(self, q, manager_dict, protocol_name, server_url, **kwargs):
        self.queue = q
        self.manager_dict = manager_dict
        self.protocol_name = protocol_name
        self.server_url = server_url
        self.kwargs = kwargs
        self.started = 0
        type(self).instances.append(self)

    def start(self):
        self.started += 1


def _get_site_dict(config_dict, service, *required):
    # the part of weewx.restx.get_site_dict that ogoxeUploader.py relies on
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


@pytest.fixture
def og(monkeypatch):
    def mod(name, **attrs):
        m = types.ModuleType(name)
        vars(m).update(attrs)
        monkeypatch.setitem(sys.modules, name, m)
        return m

    _get_site_dict.calls = []
    _FakeStdWunderground.wu_threads_started = 0
    _FakeAmbientThread.instances = []
    wx = mod("weewx", NEW_ARCHIVE_RECORD="NEW_ARCHIVE_RECORD")
    wx.__path__ = []
    wx.engine = mod("weewx.engine", StdService=_FakeStdService)
    wx.restx = mod("weewx.restx", StdWunderground=_FakeStdWunderground,
                   AmbientThread=_FakeAmbientThread, get_site_dict=_get_site_dict)
    wx.manager = mod("weewx.manager",
                     get_manager_dict_from_config=lambda cfg, name: {"binding": name})
    mod("weeutil", __path__=[])
    mod("weeutil.weeutil",
        to_bool=lambda v: str(v).lower() in ("1", "true", "yes", "on"))
    monkeypatch.delitem(sys.modules, "ogoxeUploader", raising=False)
    module = importlib.import_module("ogoxeUploader")
    yield module
    sys.modules.pop("ogoxeUploader", None)


def _config(**site):
    return {"StdRESTful": {"OgoxeUploader": site}}


def _site(**extra):
    return {"station": "STN1", "password": "PW", **extra}


def test_api_url_is_the_hardcoded_ogoxe_endpoint(og):
    assert og.OGOXE_API_URL == API_URL


def test_service_is_a_wunderground_subclass(og):
    assert issubclass(og.OgoxeUploader, _FakeStdWunderground)


def test_starts_one_thread_and_binds_once(og):
    svc = og.OgoxeUploader(engine=None, config_dict=_config(**_site()))
    assert len(_FakeAmbientThread.instances) == 1
    t = _FakeAmbientThread.instances[0]
    assert t is svc.archive_thread and t.started == 1
    assert svc.bound == [("NEW_ARCHIVE_RECORD", svc.new_archive_record)]
    assert _FakeStdWunderground.wu_threads_started == 0


def test_with_wunderground_configured_still_one_thread_and_one_bind(og):
    # #408 (CHANGES-FROM-UPSTREAM.md row 3): StdWunderground.__init__ must not run, or
    # a second set of threads starts and the archive event is bound twice.
    cfg = _config(**_site())
    cfg["StdRESTful"]["Wunderground"] = {"station": "WU", "password": "PW"}
    svc = og.OgoxeUploader(engine=None, config_dict=cfg)
    assert _FakeStdWunderground.wu_threads_started == 0
    assert len(_FakeAmbientThread.instances) == 1
    assert _FakeAmbientThread.instances[0].started == 1
    assert len(svc.bound) == 1


def test_thread_gets_the_fixed_url_manager_and_forwarded_options(og):
    og.OgoxeUploader(engine=None, config_dict=_config(**_site(
        post_interval="300", max_tries="5")))
    t = _FakeAmbientThread.instances[0]
    assert t.protocol_name == "OgoxeUploader"
    assert t.server_url == API_URL
    assert t.manager_dict == {"binding": "wx_binding"}
    assert t.kwargs == {"station": "STN1", "password": "PW",
                        "post_interval": "300", "max_tries": "5"}
    assert _get_site_dict.calls == [("OgoxeUploader", ("station", "password"))]


def test_rapidfire_and_archive_post_are_not_forwarded(og):
    og.OgoxeUploader(engine=None, config_dict=_config(**_site(
        rapidfire="true", archive_post="true")))
    kwargs = _FakeAmbientThread.instances[0].kwargs
    assert "rapidfire" not in kwargs and "archive_post" not in kwargs


@pytest.mark.parametrize("value", ["false", "False", "0"])
def test_archive_post_off_starts_nothing(og, value):
    svc = og.OgoxeUploader(engine=None, config_dict=_config(**_site(archive_post=value)))
    assert _FakeAmbientThread.instances == []
    assert svc.bound == []
    assert not hasattr(svc, "archive_thread")


@pytest.mark.parametrize("site", [{"station": "STN1"}, {"password": "PW"},
                                  {"station": "STN1", "password": "PW",
                                   "enable": "false"}])
def test_missing_required_option_logs_an_error_and_starts_nothing(og, site, caplog):
    caplog.set_level(logging.DEBUG, logger="ogoxeUploader")
    svc = og.OgoxeUploader(engine=None, config_dict=_config(**site))
    assert _FakeAmbientThread.instances == []
    assert svc.bound == []
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1 and "Missing required configuration" in errors[0].getMessage()


def test_missing_section_starts_nothing(og):
    svc = og.OgoxeUploader(engine=None, config_dict={"StdRESTful": {}})
    assert _FakeAmbientThread.instances == [] and svc.bound == []


def test_debug_log_reports_the_url_actually_used(og, caplog):
    # CHANGES-FROM-UPSTREAM.md row 1: the line used to log _ambient_dict.get('server_url'),
    # a key that is never set, so it always said None.
    caplog.set_level(logging.DEBUG, logger="ogoxeUploader")
    og.OgoxeUploader(engine=None, config_dict=_config(**_site()))
    lines = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
    assert lines == ["OgoxeUploader server_url: " + API_URL]


def test_info_logs_name_the_station_and_never_the_password(og, caplog):
    caplog.set_level(logging.DEBUG, logger="ogoxeUploader")
    og.OgoxeUploader(engine=None, config_dict=_config(**_site(password="hunter2")))
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "STN1" in text and "hunter2" not in text


def test_new_archive_record_queues_the_record(og):
    svc = og.OgoxeUploader(engine=None, config_dict=_config(**_site()))
    svc.new_archive_record(types.SimpleNamespace(record={"dateTime": 1700000000}))
    assert isinstance(svc.archive_queue, queue.Queue)
    assert svc.archive_queue.get_nowait() == {"dateTime": 1700000000}
    assert svc.archive_queue is _FakeAmbientThread.instances[0].queue
