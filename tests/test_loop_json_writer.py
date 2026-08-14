"""Offline unit tests for Cold-load Fix B (current.json) and issue #44
(windchill in the loop feed).

Cold-load Fix B: the dashboard's first-time visitor sees em-dashes because
nothing is available until the first LOOP packet writes loop-data.txt. The
fix (per the dashboard's S69 handoff + issue #44) is for loop_json_writer.py
to ALSO atomically write an identical snapshot to a second path (current.json)
on every packet -- same content, same tmp+rename pattern, different filename.

These tests drive the REAL LoopJsonWriter.new_loop() against temp file paths
and assert both files are written with identical, correct content, and that
windchill rides along the same cached-forward mechanism as the other fields.

weewx is not installed in the test/CI environment, so we stub the weewx
modules in sys.modules before importing the writer (same pattern as the
other tests here).

Run:  python3 -m pytest tests/   OR   python3 tests/test_loop_json_writer.py
"""
import json
import os
import sys
import tempfile
import types

# --- stub the weewx deps so loop_json_writer.py imports without weewx installed ---
def _pkg(name):
    m = types.ModuleType(name)
    m.__path__ = []
    sys.modules[name] = m
    return m

def _mod(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

class _StdService:
    def __init__(self, *a, **k):
        pass

    def bind(self, event_type, handler):
        self._bound = (event_type, handler)


weewx = _pkg("weewx")
weewx.NEW_LOOP_PACKET = "NEW_LOOP_PACKET"
weewx_engine = _mod("weewx.engine")
weewx_engine.StdService = _StdService
weewx_units = _mod("weewx.units")
weewx_units.to_US = lambda pkt: pkt  # no-op: tests already pass US-unit packets
weewx.engine, weewx.units = weewx_engine, weewx_units

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loop_json_writer import LoopJsonWriter  # noqa: E402


def _make_writer(tmpdir):
    cfg = {'LoopJsonWriter': {
        'path': os.path.join(tmpdir, 'loop-data.txt'),
        'current_path': os.path.join(tmpdir, 'current.json'),
    }}
    return LoopJsonWriter(engine=None, config_dict=cfg)


def test_fetch_epoch_is_passed_through_even_when_ancient():
    """#172 (S82b): barometer_fetch_epoch bypasses the cache/TTL machinery —
    its whole purpose is to reveal staleness, so an old value must be
    published verbatim, never omitted the way TTL'd fields are."""
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer(tmpdir)
        ancient = 1234567890 - 100_000          # far past every TTL in the file
        event = types.SimpleNamespace(packet={
            'dateTime': 1234567890, 'outTemp': 72.5,
            'barometer_fetch_epoch': ancient,
        })
        w.new_loop(event)
        with open(w.path) as f:
            data = json.load(f)
        assert data['barometer_fetch_epoch'] == ancient


def test_fetch_epoch_absent_when_never_stamped():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer(tmpdir)
        event = types.SimpleNamespace(packet={'dateTime': 1234567890, 'outTemp': 72.5})
        w.new_loop(event)
        with open(w.path) as f:
            data = json.load(f)
        assert 'barometer_fetch_epoch' not in data


def test_writes_both_paths_with_identical_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer(tmpdir)
        event = types.SimpleNamespace(packet={
            'dateTime': 1234567890, 'outTemp': 72.5, 'outHumidity': 41.0,
        })
        w.new_loop(event)

        with open(w.path) as f:
            loop_data = json.load(f)
        with open(w.current_path) as f:
            current_data = json.load(f)

        assert loop_data == current_data
        assert loop_data['outTemp_F'] == 72.5
        assert loop_data['dateTime'] == 1234567890


def test_current_path_defaults_alongside_loop_path():
    w = LoopJsonWriter(engine=None, config_dict={})
    assert w.path == '/opt/weewx-data/loop-data.txt'
    assert w.current_path == '/opt/weewx-data/current.json'


def test_windchill_cached_forward_like_heatindex():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer(tmpdir)
        # First packet carries windchill; a later sparse packet omits it.
        w.new_loop(types.SimpleNamespace(packet={
            'dateTime': 1, 'windchill': 28.4, 'heatindex': 75.0,
        }))
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 2}))

        with open(w.current_path) as f:
            data = json.load(f)

        assert data['windchill_F'] == 28.4, "windchill should be cached forward"
        assert data['heatindex_F'] == 75.0
        assert data['dateTime'] == 2


# --- Cache TTL (DEC-0006 / issue #45 provenance audit, S48) ------------------
# The regression these guard: the cache used to be unbounded, so a dead or
# SensorQC-rejected sensor kept emitting its last value forever -- stamped with
# the CURRENT packet's dateTime, making it indistinguishable from a live
# reading on the surface the dashboard actually reads.

def _make_writer_cfg(tmpdir, loop_extra=None, davis=None):
    cfg = {'LoopJsonWriter': dict({
        'path': os.path.join(tmpdir, 'loop-data.txt'),
        'current_path': os.path.join(tmpdir, 'current.json'),
    }, **(loop_extra or {}))}
    if davis is not None:
        cfg['DavisPressure'] = davis
    return LoopJsonWriter(engine=None, config_dict=cfg)


def _read(w):
    with open(w.current_path) as f:
        return json.load(f)


def test_stale_field_is_omitted_not_served_under_a_live_timestamp():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir)
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000, 'outTemp': 72.5}))
        # 301 s later outTemp still hasn't reappeared -- sensor dead or rejected.
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1301, 'outHumidity': 40.0}))

        data = _read(w)
        assert 'outTemp_F' not in data, "stale value must be omitted, not frozen"
        assert data['outHumidity'] == 40.0, "live fields still served"
        assert data['dateTime'] == 1301


def test_field_inside_its_ttl_is_still_cached_forward():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir)
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000, 'outTemp': 72.5}))
        # 299 s later -- inside the 300 s ISS-rotation bridge, so still valid.
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1299}))

        assert _read(w)['outTemp_F'] == 72.5


def test_barometer_survives_past_the_default_ttl():
    # barometer comes from the hourly WeatherLink fetch, not the ISS rotation;
    # the default 300 s TTL would blank it for most of every hour.
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir, davis={'fetch_interval': 3600})
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000, 'barometer': 30.02}))
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000 + 3000}))

        assert _read(w)['barometer_inHg'] == 30.02


def test_barometer_ttl_tracks_a_changed_fetch_interval():
    # Drift-proofing: the TTL is derived from DavisPressure's own config.
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir, davis={'fetch_interval': 60})
        assert w._ttl('barometer_inHg') == 120
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000, 'barometer': 30.02}))
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1121}))

        assert 'barometer_inHg' not in _read(w)


def test_expired_field_recovers_when_the_sensor_returns():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir)
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000, 'outTemp': 72.5}))
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1400}))
        assert 'outTemp_F' not in _read(w)

        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1450, 'outTemp': 68.1}))
        assert _read(w)['outTemp_F'] == 68.1


def test_ttl_default_is_configurable():
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir, loop_extra={'ttl_default': 60})
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000, 'outTemp': 72.5}))
        w.new_loop(types.SimpleNamespace(packet={'dateTime': 1061}))

        assert 'outTemp_F' not in _read(w)


# --- Calm-windDir expiry is DEBUG, not WARNING (issue #74, S52) ---------------
# The driver deliberately reports wind_dir = None while calm, so any >= TTL
# calm stretch expires windDir by design -- ~7 spurious WARNINGs/day was
# desensitizing the watch for real sensor failures.

def test_calm_winddir_expiry_logs_debug_not_warning(caplog):
    import logging
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir)
        # calm: windSpeed 0.0 keeps refreshing, windDir last seen at t=1000
        w.new_loop(types.SimpleNamespace(packet={
            'dateTime': 1000, 'windSpeed': 0.0, 'windDir': 200.0}))
        with caplog.at_level(logging.DEBUG, logger='loop_json_writer'):
            w.new_loop(types.SimpleNamespace(packet={
                'dateTime': 1301, 'windSpeed': 0.0}))
        assert 'windDir' not in _read(w), "expiry itself is unchanged (DEC-0053)"
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert not warnings, "calm windDir expiry must not WARN (#74)"
        debugs = [r for r in caplog.records if r.levelno == logging.DEBUG
                  and 'windDir' in r.getMessage()]
        assert debugs, "the expiry is still logged, at DEBUG"


def test_winddir_expiry_with_wind_still_warns(caplog):
    import logging
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir)
        w.new_loop(types.SimpleNamespace(packet={
            'dateTime': 1000, 'windSpeed': 5.0, 'windDir': 200.0}))
        # wind is blowing but direction vanished for a full TTL: anomalous
        with caplog.at_level(logging.DEBUG, logger='loop_json_writer'):
            w.new_loop(types.SimpleNamespace(packet={
                'dateTime': 1301, 'windSpeed': 5.0}))
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING
                    and 'windDir' in r.getMessage()]
        assert warnings, "windDir expiry with nonzero wind stays a WARNING"


def test_winddir_expiry_with_windspeed_also_expired_warns(caplog):
    import logging
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir)
        w.new_loop(types.SimpleNamespace(packet={
            'dateTime': 1000, 'windSpeed': 0.0, 'windDir': 200.0}))
        # BOTH wind fields go silent -- a real dropout, not calm; the last
        # cached windSpeed 0.0 is itself expired and must not count as calm
        with caplog.at_level(logging.DEBUG, logger='loop_json_writer'):
            w.new_loop(types.SimpleNamespace(packet={
                'dateTime': 1301, 'outTemp': 70.0}))
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING
                    and 'windDir' in r.getMessage()]
        assert warnings, "expired windSpeed is a dropout, not calm (#74)"


def test_calm_winddir_recovery_logs_debug_not_info(caplog):
    import logging
    with tempfile.TemporaryDirectory() as tmpdir:
        w = _make_writer_cfg(tmpdir)
        w.new_loop(types.SimpleNamespace(packet={
            'dateTime': 1000, 'windSpeed': 0.0, 'windDir': 200.0}))
        w.new_loop(types.SimpleNamespace(packet={
            'dateTime': 1301, 'windSpeed': 0.0}))          # calm expiry (DEBUG)
        with caplog.at_level(logging.DEBUG, logger='loop_json_writer'):
            w.new_loop(types.SimpleNamespace(packet={
                'dateTime': 1350, 'windSpeed': 3.0, 'windDir': 210.0}))
        assert _read(w)['windDir'] == 210.0
        infos = [r for r in caplog.records if r.levelno == logging.INFO
                 and 'recovered' in r.getMessage()]
        assert not infos, "recovery from a calm expiry must be DEBUG too (#74)"


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print("  [PASS] %s" % name)
            except Exception as e:
                fails += 1
                print("  [FAIL] %s -> %r" % (name, e))
    total = sum(1 for n in globals() if n.startswith('test_'))
    print("\n%d/%d passed" % (total - fails, total))
    sys.exit(1 if fails else 0)
