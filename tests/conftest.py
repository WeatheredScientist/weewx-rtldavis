"""Shared setup for the whole suite (#411).

The suite used to pass only in alphabetical collection order: `pytest
tests/test_sensor_qc.py tests/test_hotswap_control.py` failed three tests, and so did a
reverse-sorted run. Two causes, both fixed here.

1. weewx is not installed in CI, so 27 test files each fake a `weewx` package in
   sys.modules. A module under test keeps whichever fake existed at its first import.
   Every file swaps in its own fake right before importing, so `rtldavis.weewx`
   belonged to whichever file was collected first. Twelve of the 18 rtldavis fakes lack
   WeeWxIOError. Installing one fake up front would not help, because each file
   replaces it. Instead this file imports the two modules that several files share
   (rtldavis, dewpoint_service) against one superset fake, so a file's own `import`
   finds the cached module. A new test for either module needs no stub of its own.
   The per-file stubs stay. They are inert for those two modules but still serve
   standalone `python tests/test_x.py` runs. The local workarounds in
   test_temp_twos_complement, test_dewpoint_units_224 and test_issue_226_cli_fixes are
   redundant now and can go with them. The stubs stay live for influx, owm,
   loop_json_writer and pressure_service, which are each imported by a single file and
   never had the problem.
   A new `import weewx.x` in rtldavis.py or dewpoint_service.py needs its name added
   to the superset below; a missing one fails when this file loads.

2. weewx_monitor keeps state in module-level dicts (WD, EP, BLIND), and tests leave them
   dirty. test_watchdog_escalation left WD['escalated'] set for the two
   test_reception_full_outage tests that read it without resetting. The autouse fixture
   at the bottom restores the dicts around every test.
"""
import copy
import importlib
import os
import sys
import types

import pytest

# Repo root and ops/, once. The per-file sys.path.insert shims are redundant now.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (os.path.join(ROOT, "ops"), ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)


class WeeWxIOError(OSError):
    pass


class UnsupportedFeature(Exception):
    pass


class AbstractDevice:
    def __init__(self, *a, **k):
        pass


class AbstractConfEditor:
    pass


class StdService:
    def __init__(self, *a, **k):
        pass

    def bind(self, event_type, handler):
        self._bound = (event_type, handler)


def _module(name, package=False, **attrs):
    m = types.ModuleType(name)
    if package:
        m.__path__ = []  # a submodule missing from sys.modules then raises ImportError
    vars(m).update(attrs)
    sys.modules[name] = m
    return m


def _install_weewx_superset():
    """The union of what the 23 rtldavis and dewpoint_service test stubs define."""
    weewx = _module(
        "weewx", package=True, __version__="5.3.1",
        # Real weewx values (US 0x01, METRIC 0x10, METRICWX 0x11). dewpoint_service
        # keys lookup tables on all three at import, so they must be distinct.
        US=1, METRIC=16, METRICWX=17,
        NEW_LOOP_PACKET="NEW_LOOP_PACKET", NEW_ARCHIVE_RECORD="NEW_ARCHIVE_RECORD",
        WeeWxIOError=WeeWxIOError, UnsupportedFeature=UnsupportedFeature)
    weewx.drivers = _module("weewx.drivers", AbstractDevice=AbstractDevice,
                            AbstractConfEditor=AbstractConfEditor)
    weewx.engine = _module("weewx.engine", StdService=StdService)
    # rtldavis registers its group_frequency unit by writing into these at import.
    weewx.units = _module("weewx.units", **{n: {} for n in (
        "obs_group_dict", "USUnits", "MetricUnits", "MetricWXUnits",
        "default_unit_format_dict", "default_unit_label_dict")})
    weewx.crc16 = _module("weewx.crc16", crc16=lambda *a, **k: 0)
    weewx.wxformulas = _module(
        "weewx.wxformulas",
        dewpointF=lambda t, h: 0.0, heatindexF=lambda t, h: 0.0,
        dewpointC=lambda t, h: 0.0, heatindexC=lambda t, h: 0.0,
        FtoC=lambda f: (f - 32.0) * 5.0 / 9.0)
    weeutil = _module("weeutil", package=True)
    weeutil.weeutil = _module(
        "weeutil.weeutil", tobool=lambda v: str(v).lower() in ("1", "true", "yes", "on"))
    weeutil.logger = _module("weeutil.logger")


_install_weewx_superset()
for _name in ("rtldavis", "dewpoint_service"):
    importlib.import_module(_name)


@pytest.fixture(autouse=True)
def _restore_monitor_state():
    """Give every test the weewx_monitor state dicts it found, whatever ran before.

    Every upper-case module-level dict is covered, so a new state dict written in the
    module-global style of WD and EP is protected without touching this file. The lookup
    goes through sys.modules because importing the monitor runs its pidfile guard, which
    only the files that put --test-alert in argv first may trigger. The restore is in
    place, since the module and the tests hold these dicts by reference.
    """
    wm = sys.modules.get("weewx_monitor")
    saved = {} if wm is None else {
        k: copy.deepcopy(v) for k, v in vars(wm).items() if k.isupper() and isinstance(v, dict)}
    yield
    for k, v in saved.items():
        state = getattr(wm, k)
        state.clear()
        state.update(v)
