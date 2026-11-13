"""loop_json_writer 1.2.0 against the contract (DEC-0234, docs/LOOPJSON-1.2-DESIGN.md §3).

The real new_loop() is driven with adversarial packets: NaN, infinity, bools, numpy-like
objects, strings in number keys, broken dateTimes. Every file it writes must pass
contract/check_contract.py and, where installed, jsonschema (REQUIRE_JSONSCHEMA=1 in CI
makes its absence fail). Then the cleaning table, the allow_nan guard, the dateTime rule
and the reserved names, one by one.
"""
import decimal
import importlib.util
import json
import logging
import os
import sys
import types
from typing import Any

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Reuse whatever stub another file installed first; build one only if weewx is absent
# (the pattern of test_loop_json_extra_config.py).
if 'weewx' not in sys.modules:
    _w: Any = types.ModuleType('weewx')
    _eng: Any = types.ModuleType('weewx.engine')
    _units: Any = types.ModuleType('weewx.units')
    _w.__path__ = []
    _eng.StdService = type('StdService', (), {
        '__init__': lambda self, *args, **kw: None,
        'bind': lambda self, event_type, handler: None})
    _w.engine, _w.units = _eng, _units
    _w.NEW_LOOP_PACKET = 'NEW_LOOP_PACKET'
    sys.modules.update({'weewx': _w, 'weewx.engine': _eng, 'weewx.units': _units})
import loop_json_writer as ljw  # noqa: E402

if not hasattr(ljw.weewx.units, 'to_US'):
    ljw.weewx.units.to_US = lambda pkt: pkt
if not hasattr(ljw.weewx, 'NEW_LOOP_PACKET'):
    ljw.weewx.NEW_LOOP_PACKET = 'NEW_LOOP_PACKET'
if not hasattr(ljw.StdService, 'bind'):
    ljw.StdService.bind = lambda self, event_type, handler: None

_spec = importlib.util.spec_from_file_location(
    'check_contract', os.path.join(ROOT, 'contract', 'check_contract.py'))
assert _spec is not None and _spec.loader is not None
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

UNITS = {
    'luminosity': ('lux', 'group_illuminance'),
    'windGust10': ('mile_per_hour', 'group_speed'),
}


@pytest.fixture(autouse=True)
def _pin_units(monkeypatch):
    monkeypatch.setattr(ljw.weewx.units, 'getStandardUnitType',
                        lambda system, obs: UNITS.get(obs, (None, None)), raising=False)
    monkeypatch.setattr(ljw.weewx, 'US', 1, raising=False)
    monkeypatch.setattr(ljw.weewx.units, 'to_US', lambda pkt: pkt, raising=False)


def _writer(tmp_path, **section):
    section.setdefault('path', str(tmp_path / 'loop-data.txt'))
    section.setdefault('current_path', str(tmp_path / 'current.json'))
    section.setdefault('current_interval', '0')  # both files on every packet
    return ljw.LoopJsonWriter(engine=None, config_dict={'LoopJsonWriter': section})


def _send(w, **packet):
    w.new_loop(types.SimpleNamespace(packet=packet))


def _raw(path):
    with open(path, 'rb') as f:
        return f.read()


class NpInt:
    """Stands in for numpy.int64: an integer through __index__ only."""
    def __index__(self):
        return 7


class NpFloat:
    def __init__(self, v):
        self.v = v

    def __float__(self):
        return self.v


class Unconvertible:
    def __float__(self):
        raise ArithmeticError('no')


NAN, INF = float('nan'), float('inf')

ADVERSARIAL = [
    {'dateTime': 1000, 'outTemp': NAN, 'outHumidity': INF, 'windSpeed': -INF},
    {'dateTime': 1003, 'outTemp': 61.0, 'UV': True, 'rainRate': False, 'windDir': NpInt()},
    {'dateTime': 1006, 'barometer': NpFloat(30.01), 'radiation': NpFloat(NAN),
     'dewpoint': decimal.Decimal('40.5'), 'heatindex': decimal.Decimal('NaN')},
    {'dateTime': 1009, 'outTemp': '59', 'windchill': [1, 2], 'cloudbase': {'a': 1},
     'windGust': b'3', 'luminosity': 'bright', 'windGust10': NAN},
    {'dateTime': 1012, 'outTemp': None, 'windGust10': NpFloat(4.0),
     'barometer_fetch_epoch': 999.9, 'luminosity': Unconvertible()},
    {'dateTime': 1015.7, 'barometer_fetch_epoch': NAN, 'outTemp': 60.0},
    {'dateTime': None, 'outTemp': 60.5},
    {'dateTime': NAN, 'outTemp': 60.6},
    {'dateTime': '1020', 'outTemp': 60.7},
    {'dateTime': True, 'outTemp': 60.8},
    {'dateTime': -5, 'outTemp': 60.9},
    {'outTemp': 61.0},
    {'dateTime': 1030, 'outTemp': 61.1, 'barometer_fetch_epoch': -1},
]


def test_every_file_the_writer_writes_meets_the_contract(tmp_path):
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(cc.SCHEMA_V1)
    except ImportError:
        if os.environ.get('REQUIRE_JSONSCHEMA') == '1':
            pytest.fail('REQUIRE_JSONSCHEMA=1 but jsonschema is not installed')
        validator = None
    w = _writer(tmp_path, extra_fields=['luminosity', 'windGust10'])
    seen = set()
    for packet in ADVERSARIAL:
        _send(w, **packet)
        for path in (w.path, w.current_path):
            if not os.path.exists(path):
                continue
            raw = _raw(path)
            seen.add(raw)
            result = cc.check_loop(raw, now=1100)
            assert result.status == 0, (packet, raw, result.findings)
            assert b'NaN' not in raw and b'Infinity' not in raw and b'null' not in raw
            assert json.loads(raw)['contract'] == ljw.CONTRACT
            if validator is not None:
                validator.validate(json.loads(raw))
    assert len(seen) >= 5, 'the sequence must actually write varied files'


def test_adversarial_values_land_as_the_cleaning_table_says(tmp_path):
    w = _writer(tmp_path, extra_fields=['luminosity', 'windGust10'])
    for packet in ADVERSARIAL[:5]:
        _send(w, **packet)
    feed = json.loads(_raw(w.path))
    assert feed['outTemp_F'] == 61.0, 'a None leaves the cached value alone'
    assert feed['UV'] == 1 and feed['rainRate_inch_per_hour'] == 0
    assert type(feed['UV']) is int, 'a bool is written as 0 or 1, never true/false'
    assert feed['windDir'] == 7
    assert feed['barometer_inHg'] == 30.01 and feed['dewpoint_F'] == 40.5
    assert feed['windGust10_mph'] == 4.0
    assert feed['barometer_fetch_epoch'] == 999
    assert feed['luminosity_lux'] == 'bright', 'a string passes for an extra'
    for absent in ('outHumidity', 'windSpeed_mph', 'radiation_Wpm2', 'heatindex_F',
                   'windchill_F', 'cloudbase_foot', 'windGust_mph'):
        assert absent not in feed, absent


@pytest.mark.parametrize('value,allow_str,want', [
    (3, False, 3), (2.5, False, 2.5), (True, False, 1), (False, False, 0),
    (NpInt(), False, 7), (NpFloat(1.5), False, 1.5), (decimal.Decimal('2.25'), False, 2.25),
    ('x', True, 'x'),
])
def test_clean_passes(value, allow_str, want):
    got, why = ljw._clean(value, allow_str=allow_str)
    assert got == want and type(got) is type(want) and why is None


@pytest.mark.parametrize('value,why', [
    (None, None), (NAN, 'is not finite'), (INF, 'is not finite'), (-INF, 'is not finite'),
    (NpFloat(NAN), 'is not finite'), (decimal.Decimal('Infinity'), 'is not finite'),
    ('59', 'is a string, not a number'), ([1], 'is a list, not a number'),
    ({}, 'is a dict, not a number'), (b'1', 'is a bytes, not a number'),
    (Unconvertible(), 'cannot be converted (no)'),
])
def test_clean_refuses(value, why):
    got, reason = ljw._clean(value)
    assert got is ljw._MISSING and reason == why


def test_a_refused_value_warns_once_per_key_until_it_recovers(tmp_path, caplog):
    w = _writer(tmp_path)
    caplog.set_level(logging.WARNING)
    for t in (1000, 1003, 1006):
        _send(w, dateTime=t, outTemp=NAN)
    _send(w, dateTime=1009, outTemp=60.0)
    _send(w, dateTime=1012, outTemp=NAN)
    lines = [r.message for r in caplog.records if 'treated as missing' in r.message]
    assert lines == ['LoopJsonWriter: outTemp_F value nan is not finite, treated as '
                     'missing'] * 2


def test_the_allow_nan_guard_fires_when_cleaning_is_bypassed(tmp_path, caplog,
                                                            monkeypatch):
    """Positive control: with _clean disabled, NaN reaches the payload and the
    strict serialization must refuse it, logging and writing nothing."""
    monkeypatch.setattr(ljw, '_clean', lambda value, allow_str=False: (
        (ljw._MISSING, None) if value is None else (value, None)))
    w = _writer(tmp_path)
    caplog.set_level(logging.ERROR)
    _send(w, dateTime=1000, outTemp=NAN)
    assert not os.path.exists(w.path) and not os.path.exists(w.current_path)
    assert any('payload is not strict JSON' in r.message and 'outTemp_F' in r.message
               for r in caplog.records)
    assert not list(tmp_path.glob('*.tmp'))


def test_both_files_carry_the_same_bytes(tmp_path):
    w = _writer(tmp_path)
    _send(w, dateTime=1000, outTemp=60.0)
    assert _raw(w.path) == _raw(w.current_path)


@pytest.mark.parametrize('stamp', [None, NAN, INF, '1000', True, -5, [1000]])
def test_a_bad_datetime_writes_nothing_and_errors_once(tmp_path, caplog, stamp):
    w = _writer(tmp_path)
    caplog.set_level(logging.INFO)
    packet = {'outTemp': 60.0}
    if stamp is not None:
        packet['dateTime'] = stamp
    _send(w, **packet)
    _send(w, **packet)
    assert not os.path.exists(w.path)
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1 and 'writing nothing' in errors[0].message
    _send(w, dateTime=1003, outTemp=60.1)
    assert json.loads(_raw(w.path))['outTemp_F'] == 60.1
    assert any('writing resumes' in r.message for r in caplog.records)


def test_a_bad_datetime_keeps_the_previous_file(tmp_path):
    w = _writer(tmp_path)
    _send(w, dateTime=1000, outTemp=60.0)
    before = _raw(w.path)
    _send(w, dateTime=NAN, outTemp=61.0)
    assert _raw(w.path) == before


def test_a_fractional_datetime_is_truncated(tmp_path):
    w = _writer(tmp_path)
    _send(w, dateTime=1000.7, outTemp=60.0)
    feed = json.loads(_raw(w.path))
    assert feed['dateTime'] == 1000 and type(feed['dateTime']) is int


@pytest.mark.parametrize('name', ['contract', 'writer', 'dateTime', 'loop_interval_s',
                                  'barometer_fetch_epoch', 'skyState', 'ongoingEvents',
                                  'loop_cadence_s', 'stale_after_s'])
def test_reserved_names_are_refused_as_extras(tmp_path, caplog, name):
    caplog.set_level(logging.WARNING)
    w = _writer(tmp_path, extra_fields=[name])
    assert w.extras == []
    assert any('reserved key name' in r.message for r in caplog.records)


def test_reserved_set_is_the_nine_names():
    assert ljw._RESERVED_KEYS == {
        'contract', 'writer', 'dateTime', 'loop_interval_s', 'barometer_fetch_epoch',
        'skyState', 'ongoingEvents', 'loop_cadence_s', 'stale_after_s'}


@pytest.mark.parametrize('name', ['bad-name', '9lives', 'x' * 65])
def test_an_extra_key_the_schema_would_refuse_is_skipped(tmp_path, caplog, name):
    caplog.set_level(logging.WARNING)
    w = _writer(tmp_path, extra_fields=[name])
    assert w.extras == []
    assert any('not a valid key name' in r.message for r in caplog.records)


def test_the_writer_key_regex_is_the_schema_pattern():
    (pattern,) = cc.SCHEMA_V1['patternProperties']
    assert pattern.endswith(ljw._KEY_RE.pattern.lstrip('^'))


def test_every_key_the_writer_stamps_is_a_schema_property():
    props = cc.SCHEMA_V1['properties']
    for _pkt_key, out_key in ljw._FIELDS:
        assert props[out_key] == {'type': 'number'}, out_key
    for key in ('dateTime', 'writer', 'contract', 'loop_interval_s',
                'barometer_fetch_epoch'):
        assert key in props, key
    assert set(props) == {k for _p, k in ljw._FIELDS} | {
        'dateTime', 'writer', 'contract', 'loop_interval_s', 'barometer_fetch_epoch'}


def test_startup_line_names_version_and_contract(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    _writer(tmp_path)
    assert any(r.message.startswith('LoopJsonWriter 1.2.0 (contract 1.2): writing to')
               for r in caplog.records)
