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
