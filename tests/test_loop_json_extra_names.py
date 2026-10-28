"""Naming rule for the loop-JSON writer's opt-in extra observations (DEC-0220, #473).

Two checks, neither of which can pass vacuously:

1. The rule runs against REAL WeeWX in a subprocess, because the rest of the suite stubs
   `weewx` in sys.modules and a stub says nothing about real unit groups. The subprocess
   needs a Python with weewx installed: this interpreter if it has one, else
   WEEWX_TEST_PYTHON. With REQUIRE_REAL_WEEWX=1 (set in loopjson.yml) a missing weewx
   FAILS instead of skipping.
2. The writer's copy of influx.py's UNIT_REDUCTIONS must equal the original, read with
   `ast` (no import). A mutated copy must turn the comparison red.
"""
import ast
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRITER = os.path.join(ROOT, 'loop_json_writer.py')
INFLUX = os.path.join(ROOT, 'influx.py')

# Packet key -> output key, the 13 observations the writer has always emitted (1.0.0).
EXISTING_13 = {
    'windSpeed': 'windSpeed_mph', 'windGust': 'windGust_mph', 'windDir': 'windDir',
    'outTemp': 'outTemp_F', 'dewpoint': 'dewpoint_F', 'outHumidity': 'outHumidity',
    'heatindex': 'heatindex_F', 'windchill': 'windchill_F',
    'barometer': 'barometer_inHg', 'rainRate': 'rainRate_inch_per_hour',
    'radiation': 'radiation_Wpm2', 'UV': 'UV', 'cloudbase': 'cloudbase_foot',
}

# The class table's examples (DEC-0220 item 7), after registering the two groups the
# gw1000 driver adds at import. Battery and signal names have no group, so they stay bare.
GW1000_GROUPS = {'luminosity': 'group_illuminance', 'lightningcount': 'group_count'}
CLASS_TABLE = {
    'luminosity': 'luminosity_lux', 'illuminance': 'illuminance_lux',
    'lightning_distance': 'lightning_distance_mile',
    'lightning_last_det_time': 'lightning_last_det_time',
    'lightningcount': 'lightningcount_count',
    'pm2_5': 'pm2_5_microgram_per_meter_cubed',
    'pm10_0': 'pm10_0_microgram_per_meter_cubed', 'co2': 'co2_ppm',
    'soilMoist1': 'soilMoist1_centibar', 'soilTemp1': 'soilTemp1_F',
    'leafWet1': 'leafWet1_count', 'leafTemp1': 'leafTemp1_F',
    'extraTemp1': 'extraTemp1_F', 'extraHumid1': 'extraHumid1',
    'inTemp': 'inTemp_F', 'inHumidity': 'inHumidity',
    'p_rainRate': 'p_rainRate', 'txBatteryStatus': 'txBatteryStatus',
}

# Runs inside the subprocess. Loads the writer file by path (real weewx on sys.path),
# registers the gw1000 groups when asked, and prints {obs: key} as JSON.
_SCRIPT = '''
import importlib.util, json, sys
import weewx.units
spec = importlib.util.spec_from_file_location("ljw", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
register = json.loads(sys.argv[2])
weewx.units.obs_group_dict.extend(register)
print(json.dumps({o: mod._extra_key(o) for o in json.loads(sys.argv[3])}))
'''


def _python_with_weewx():
    """A Python that can import weewx, or None."""
    for exe in (sys.executable, os.environ.get('WEEWX_TEST_PYTHON')):
        if not exe:
            continue
        r = subprocess.run([exe, '-I', '-c', 'import weewx.units'], capture_output=True)
        if r.returncode == 0:
            return exe
    return None


@pytest.fixture(scope='module')
def real_python():
    exe = _python_with_weewx()
    if exe is None:
        if os.environ.get('REQUIRE_REAL_WEEWX') == '1':
            pytest.fail('REQUIRE_REAL_WEEWX=1 but no Python with weewx was found')
        pytest.skip('real weewx not installed (set WEEWX_TEST_PYTHON to run this locally)')
    return exe


def _real_keys(exe, observations, register=None):
    r = subprocess.run(
        [exe, '-I', '-c', _SCRIPT, WRITER, json.dumps(register or {}),
         json.dumps(list(observations))],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_rule_reproduces_the_13_existing_keys(real_python):
    got = _real_keys(real_python, EXISTING_13)
    assert got == EXISTING_13


def test_rule_gives_the_class_table_keys(real_python):
    got = _real_keys(real_python, CLASS_TABLE, register=GW1000_GROUPS)
    assert got == CLASS_TABLE


def test_unregistered_group_stays_bare(real_python):
    """Without the driver's registration luminosity has no unit group: bare name, no
    exception. This is why the name is computed at runtime, not from a static table."""
    assert _real_keys(real_python, ['luminosity'])['luminosity'] == 'luminosity'


def _reductions(path, name):
    with open(path) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError('%s defines no %s' % (path, name))


def _same(a, b):
    return a == b


def test_reduction_table_matches_influx():
    ours = _reductions(WRITER, '_UNIT_REDUCTIONS')
    theirs = _reductions(INFLUX, 'UNIT_REDUCTIONS')
    assert theirs, 'influx.py table read as empty'
    assert _same(ours, theirs)


def test_drift_check_goes_red_on_a_mutated_entry():
    """Positive control: the comparison above must notice a single changed entry."""
    theirs = _reductions(INFLUX, 'UNIT_REDUCTIONS')
    mutated = dict(theirs)
    mutated['inch'] = 'inches'
    assert not _same(mutated, theirs)
    del mutated['inch']
    assert not _same(mutated, theirs)


# Engine order (DEC-0220 fact 3): the writer is built first, then StdArchive calls
# weewx.accum.initialize with the site's [Accumulator]. Runs under real WeeWX.
_ENGINE_ORDER_SCRIPT = '''
import importlib.util, json, sys, tempfile, types
import weewx, weewx.accum, weewx.units
spec = importlib.util.spec_from_file_location("ljw", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
weewx.units.obs_group_dict.extend({"luminosity": "group_illuminance"})
tmp = tempfile.mkdtemp()
cfg = {"LoopJsonWriter": {"path": tmp + "/loop-data.txt", "current_path": tmp + "/current.json",
                          "extra_fields": ["t_rain", "lightning_strike_count", "luminosity"]},
       "Accumulator": {"t_rain": {"extractor": "sum"}}}
engine = types.SimpleNamespace(bind=lambda *a: None)
w = mod.LoopJsonWriter(engine, cfg)
weewx.accum.initialize(cfg)
seen = []
for t, extra in ((1000, {"t_rain": 0.2, "lightning_strike_count": 1}), (1003, {})):
    pkt = {"dateTime": t, "usUnits": weewx.US, "outTemp": 70.0, "luminosity": 50.0}
    pkt.update(extra)
    w.new_loop(types.SimpleNamespace(packet=pkt))
    seen.append([k for _o, k in w.extras])
print(json.dumps(seen))
'''


def test_deltas_refused_in_engine_order(real_python):
    r = subprocess.run([real_python, '-I', '-c', _ENGINE_ORDER_SCRIPT, WRITER],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    after_first, after_second = json.loads(r.stdout)
    assert after_first == ['luminosity_lux'], 'luminosity kept, both deltas refused'
    assert after_second == ['luminosity_lux'], 'the refusal holds on a packet with no delta'
