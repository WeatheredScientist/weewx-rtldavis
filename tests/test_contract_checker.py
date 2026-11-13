"""contract/: the v1 schema, the checker and the fixtures, tied to each other and to
docs/INTERFACES.md (DEC-0234, design docs/LOOPJSON-1.2-DESIGN.md §4.4).

The checker is a standalone file, not a package, so it is loaded by path. jsonschema is
a CI-only test dependency: the agreement tests skip without it, unless
REQUIRE_JSONSCHEMA=1 (set in ci.yml), which makes a missing jsonschema fail. The influx
catalog is checked against REAL WeeWX in a subprocess, as test_loop_json_extra_names.py
does; REQUIRE_REAL_WEEWX=1 makes a missing weewx fail.
"""
import ast
import copy
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT_DIR = os.path.join(ROOT, 'contract')
SCHEMA_PATH = os.path.join(CONTRACT_DIR, 'loop-json.v1.schema.json')
CHECKER_PATH = os.path.join(CONTRACT_DIR, 'check_contract.py')
LOOP_FIXTURES = os.path.join(CONTRACT_DIR, 'fixtures', 'loop')
INFLUX_FIXTURES = os.path.join(CONTRACT_DIR, 'fixtures', 'influx')
INTERFACES = os.path.join(ROOT, 'docs', 'INTERFACES.md')
WRITER = os.path.join(ROOT, 'loop_json_writer.py')
INFLUX = os.path.join(ROOT, 'influx.py')

_spec = importlib.util.spec_from_file_location('check_contract', CHECKER_PATH)
assert _spec is not None and _spec.loader is not None
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

NOW = 1794409280  # nine seconds after the fixtures' dateTime


def _schema_file():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def _expected():
    with open(os.path.join(LOOP_FIXTURES, 'expected.json')) as f:
        return json.load(f)


def _interfaces():
    with open(INTERFACES, encoding='utf-8') as f:
        return f.read()


def _section(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i + len(start))]


def _writer_constant(name):
    """A module-level string constant of the writer, read with ast (no weewx import)."""
    with open(WRITER) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError('%s not found in loop_json_writer.py' % name)


def _jsonschema():
    try:
        import jsonschema
    except ImportError:
        if os.environ.get('REQUIRE_JSONSCHEMA') == '1':
            pytest.fail('REQUIRE_JSONSCHEMA=1 but jsonschema is not installed')
        pytest.skip('jsonschema not installed (a CI-only test dependency)')
    return jsonschema


# --- one schema, one version --------------------------------------------------------------

def test_embedded_schema_equals_the_file():
    assert cc.SCHEMA_V1 == _schema_file()


def test_contract_version_agrees_everywhere():
    header = re.search(r'\*\*Contract version:\*\* (\d+\.\d+)', _interfaces())
    assert header, 'INTERFACES.md header has no "Contract version: X.Y"'
    version = header.group(1)
    assert _writer_constant('CONTRACT') == version
    assert cc.CONTRACT == version
    assert ('contract %s,' % version) in _schema_file()['$comment']
    assert int(version.split('.')[0]) == cc.SUPPORTED_MAJOR


def test_schema_properties_equal_interfaces_section_1_keys():
    text = _interfaces()
    keys_table = _section(text, '**Keys.**', '**Extra observations')
    relayed = _section(text, '**Optional extension: a relayed barometer.**', '**Example**')
    documented = set()
    for block in (keys_table, relayed):
        for line in block.splitlines():
            m = re.match(r'\| `([^`]+)` \|', line)
            if m:
                documented.add(m.group(1))
    assert len(documented) >= 18, documented
    assert documented == set(_schema_file()['properties'])


def test_schema_reserves_the_proxy_names_and_interfaces_lists_them():
    text = _interfaces()
    reserved = _section(text, '**Reserved names.**', '\n\n')
    proxy = ['skyState', 'ongoingEvents', 'loop_cadence_s', 'stale_after_s']
    for name in proxy + ['contract', 'writer', 'dateTime', 'loop_interval_s',
                         'barometer_fetch_epoch']:
        assert '`%s`' % name in reserved, name
    for name in proxy:
        codes = [f.code for f in cc.validate(cc.SCHEMA_V1, {'dateTime': 1, name: 1})]
        assert codes == ['E-KEY-NAME'], name


# --- the validator stays honest -------------------------------------------------------------

def test_validator_refuses_an_unknown_keyword():
    schema = copy.deepcopy(cc.SCHEMA_V1)
    schema['properties']['outTemp_F']['oneOf'] = [{'type': 'number'}]
    with pytest.raises(cc.SchemaError, match='oneOf'):
        cc.validate(schema, {'dateTime': 1, 'outTemp_F': 1.0})


def test_validator_refuses_an_unknown_keyword_at_the_top():
    schema = dict(cc.SCHEMA_V1, propertyNames={'maxLength': 3})
    with pytest.raises(cc.SchemaError):
        cc.check_loop(b'{"dateTime": 1}', schema=schema)


@pytest.mark.parametrize('body,code', [
    (b'{"dateTime": 1, "x": NaN}', 'E-PARSE-NAN'),
    (b'{"dateTime": 1, "x": 1e999}', 'E-PARSE-OVERFLOW'),
    (b'{"dateTime": 1, "x": 1' + b'0' * 400 + b'}', 'E-PARSE-OVERFLOW'),
    (b'{"dateTime": 1, "dateTime": 2}', 'E-DUPLICATE-KEY'),
    (b'{"dateTime": 1, "x": {"y": 1, "y": 2}}', 'E-DUPLICATE-KEY'),
    (b'\xff\xfe', 'E-PARSE'),
    (b'   \n', 'E-PARSE'),
    (b'7', 'E-NOT-OBJECT'),
])
def test_strict_parse_positive_controls(body, code):
    obj, findings = cc.parse_strict(body)
    assert obj is None and [f.code for f in findings] == [code]


def test_python_json_alone_would_accept_what_the_checker_refuses():
    """Why the strict parse exists: the lax parse lets each of these through."""
    for body in ('{"dateTime": 1, "a": NaN}', '{"dateTime": 1, "a": 1e400}',
                 '{"dateTime": 1, "a": 1, "a": 2}'):
        json.loads(body)
        assert cc.check_loop(body).status == 1, body


# --- fixtures are a conformance suite ------------------------------------------------------

def _fixture_names():
    names = []
    for kind in ('valid', 'invalid'):
        for name in sorted(os.listdir(os.path.join(LOOP_FIXTURES, kind))):
            names.append('%s/%s' % (kind, name))
    return names


def test_every_fixture_is_listed_and_every_listing_exists():
    assert sorted(_expected()) == sorted(_fixture_names())
    assert len([n for n in _fixture_names() if n.startswith('invalid/')]) >= 20


@pytest.mark.parametrize('name', _fixture_names())
def test_fixture_verdict(name):
    want = _expected()[name]
    result = cc.check_loop(_read(os.path.join(LOOP_FIXTURES, name)), now=NOW)
    errors = [f for f in result.findings if f.code.startswith('E-')]
    if want['valid']:
        assert result.status == 0 and not errors, result
        assert [f.code for f in result.findings if f.code.startswith('W-')] == \
            want['warnings']
    else:
        assert result.status == 1
        assert [f.code for f in errors] == [want['code']], result.findings
        assert errors[0].level == want['level']


def test_reference_fixture_is_the_interfaces_example():
    example = _section(_interfaces(), '```json', '```')[len('```json'):]
    assert '"contract": "1.2"' in example
    with open(os.path.join(LOOP_FIXTURES, 'valid', 'reference-1.2.json')) as f:
        assert json.loads(example) == json.load(f)


def test_fixtures_agree_with_jsonschema():
    jsonschema = _jsonschema()
    validator = jsonschema.Draft202012Validator(_schema_file())
    checked = 0
    for name, want in _expected().items():
        if want.get('level') == 'parse':
            continue  # jsonschema sees an already-parsed value; the parse is the checker's
        obj = json.loads(_read(os.path.join(LOOP_FIXTURES, name)))
        ours = cc.check_loop(_read(os.path.join(LOOP_FIXTURES, name)), now=NOW).status == 0
        assert validator.is_valid(obj) == ours, name
        checked += 1
    assert checked >= 15


# --- command line ---------------------------------------------------------------------------

def _run(*args, stdin=None):
    return subprocess.run([sys.executable, '-I', CHECKER_PATH] + list(args), input=stdin,
                          capture_output=True)


def test_cli_exit_codes():
    valid = os.path.join(LOOP_FIXTURES, 'valid', 'reference-1.2.json')
    r = _run('loop', '--now', str(NOW), valid)
    assert r.returncode == 0
    assert b'OK: contract 1.2, 17 keys, writer loop_json_writer/1.2.0, age 9 s' in r.stdout
    assert _run('loop', os.path.join(LOOP_FIXTURES, 'invalid', 'nan.json')).returncode == 1
    assert _run('loop', '--now', str(NOW), '--max-age', '5', valid).returncode == 1
    assert _run('loop', os.path.join(CONTRACT_DIR, 'no-such-file')).returncode == 2
    assert _run().returncode == 2


def test_cli_reads_stdin():
    r = _run('loop', '-', stdin=b'{"dateTime": 1, "contract": "1.2"}')
    assert r.returncode == 0 and b'OK: contract 1.2' in r.stdout


# --- influx-fields ----------------------------------------------------------------------------

def test_influx_fixtures():
    with open(os.path.join(INFLUX_FIXTURES, 'expected.json')) as f:
        expected = json.load(f)
    assert sorted(expected) == sorted(n for n in os.listdir(INFLUX_FIXTURES)
                                      if n.endswith('.txt'))
    for name, want in expected.items():
        with open(os.path.join(INFLUX_FIXTURES, name)) as f:
            result = cc.check_influx_fields(f.read())
        if want['valid']:
            assert result.status == 0 and result.summary == want['summary'], name
        else:
            assert result.status == 1
            assert sorted(f.code for f in result.findings
                          if f.code.startswith('E-')) == want['codes']


def test_influx_reads_annotated_csv():
    csv = ('#group,false,false,false\n#datatype,string,long,string\n'
           ',result,table,_value\n,_result,0,outTemp_F\n,_result,0,windSpeed_mph\n')
    assert cc.read_field_names(csv) == ['outTemp_F', 'windSpeed_mph']


def test_influx_empty_list_is_an_error():
    assert cc.check_influx_fields('\n\n').status == 1


def _us_names(catalog_items):
    return {cc._spelling(obs, labels[0]) for obs, labels in catalog_items}


def _backticked(block):
    return set(re.findall(r'`([^`]+)`', block))


def test_influx_catalog_equals_interfaces_section_2():
    text = _section(_interfaces(), '## 2. InfluxDB', '## 3. SQLite')
    contract = _section(text, '*Contract fields*', '*Written, optional*')
    table = '\n'.join(line.split('|')[1] for line in contract.splitlines()
                      if line.startswith('| `'))
    assert _backticked(table) == _us_names(
        (o, labels) for o, (_c, labels) in cc.INFLUX_CONTRACT.items())
    optional = _section(text, '*Written, optional*', '*Outside the contract*')
    optional = optional.split('\n\n', 1)[1]
    assert _backticked(optional) == _us_names(cc.INFLUX_OPTIONAL.items())
    outside = _section(text, '*Outside the contract*', '## 3.') if '## 3.' in text else \
        text[text.index('*Outside the contract*'):]
    table = '\n'.join(line.split('|')[1] for line in outside.splitlines()
                      if line.startswith('| `'))
    assert _backticked(table) == set(cc.INFLUX_DIAGNOSTICS)


# Runs in a subprocess with real WeeWX: prints {obs: [label per system]} by influx.py's rule.
_LABELS = '''
import json, sys
import weewx, weewx.units
weewx.units.obs_group_dict['windGust10'] = 'group_speed'  # as rtldavis.py registers it
reductions = json.loads(sys.argv[1])
out = {}
for obs in json.loads(sys.argv[2]):
    labels = []
    for system in (weewx.US, weewx.METRIC, weewx.METRICWX):
        unit_type, _group = weewx.units.getStandardUnitType(system, obs)
        labels.append(reductions.get(unit_type, unit_type))
    out[obs] = labels
print(json.dumps(out))
'''


def _python_with_weewx():
    for exe in (sys.executable, os.environ.get('WEEWX_TEST_PYTHON')):
        if exe and subprocess.run([exe, '-I', '-c', 'import weewx.units'],
                                  capture_output=True).returncode == 0:
            return exe
    if os.environ.get('REQUIRE_REAL_WEEWX') == '1':
        pytest.fail('REQUIRE_REAL_WEEWX=1 but no Python with weewx was found')
    pytest.skip('no Python with weewx (set WEEWX_TEST_PYTHON)')


def _influx_reductions():
    with open(INFLUX) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'UNIT_REDUCTIONS' for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError('UNIT_REDUCTIONS not found in influx.py')


def test_influx_catalog_labels_match_real_weewx():
    exe = _python_with_weewx()
    catalog = dict((o, labels) for o, (_c, labels) in cc.INFLUX_CONTRACT.items())
    catalog.update(cc.INFLUX_OPTIONAL)
    r = subprocess.run([exe, '-I', '-c', _LABELS, json.dumps(_influx_reductions()),
                        json.dumps(sorted(catalog))], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    real = json.loads(r.stdout)
    assert real == {obs: list(labels) for obs, labels in catalog.items()}
