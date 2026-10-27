"""Config parsing and refusals for the writer's opt-in extra fields (DEC-0220 steps 2, #473).

Offline: `weewx` is stubbed (the real naming rule has its own file,
test_loop_json_extra_names.py), so each test pins the unit lookup with a table and
asserts what the writer does with the names it gets. Every refusal test also asserts the
accepted field is present, so a parser that drops everything cannot pass.
"""
import logging
import os
import sys
import types
from typing import Any

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Reuse whatever stub another file installed first; build one only if weewx is absent.
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

# The writer keeps the first stub it was imported under, so whichever test file loads
# first decides what it sees. Give that stub what the other file's tests rely on.
if not hasattr(ljw.weewx.units, 'to_US'):
    ljw.weewx.units.to_US = lambda pkt: pkt
if not hasattr(ljw.weewx, 'NEW_LOOP_PACKET'):
    ljw.weewx.NEW_LOOP_PACKET = 'NEW_LOOP_PACKET'
if not hasattr(ljw.StdService, 'bind'):
    ljw.StdService.bind = lambda self, event_type, handler: None

# observation -> (US unit type, group) for the names used below
UNITS = {
    'luminosity': ('lux', 'group_illuminance'),
    'pm2_5': ('microgram_per_meter_cubed', 'group_concentration'),
    'inTemp': ('degree_F', 'group_temperature'),
    'outTemp': ('degree_F', 'group_temperature'),
    'dateTime': ('unix_epoch', 'group_time'),
    'barometer_fetch_epoch': ('unix_epoch', 'group_time'),
}


@pytest.fixture(autouse=True)
def _pin_units(monkeypatch):
    monkeypatch.setattr(ljw.weewx.units, 'getStandardUnitType',
                        lambda system, obs: UNITS.get(obs, (None, None)), raising=False)
    monkeypatch.setattr(ljw.weewx, 'US', 1, raising=False)


def _writer(tmp_path, **section):
    section.setdefault('path', str(tmp_path / 'loop-data.txt'))
    section.setdefault('current_path', str(tmp_path / 'current.json'))
    return ljw.LoopJsonWriter(engine=None, config_dict={'LoopJsonWriter': section})


def test_default_has_no_extras(tmp_path):
    assert _writer(tmp_path).extras == []


def test_list_is_named_in_order(tmp_path):
    w = _writer(tmp_path, extra_fields=['luminosity', 'pm2_5', 'inTemp'])
    assert w.extras == [('luminosity', 'luminosity_lux'),
                        ('pm2_5', 'pm2_5_microgram_per_meter_cubed'),
                        ('inTemp', 'inTemp_F')]


def test_single_value_arrives_as_a_string(tmp_path):
    """configobj hands back a str, not a list, for `extra_fields = luminosity`."""
    assert _writer(tmp_path, extra_fields='luminosity').extras == [
        ('luminosity', 'luminosity_lux')]


def test_blank_entries_are_dropped(tmp_path):
    w = _writer(tmp_path, extra_fields=['', ' luminosity ', ''])
    assert w.extras == [('luminosity', 'luminosity_lux')]


def test_key_already_written_is_ignored_at_info(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    w = _writer(tmp_path, extra_fields=['outTemp', 'luminosity'])
    assert w.extras == [('luminosity', 'luminosity_lux')]
    assert any(r.levelno == logging.INFO and 'outTemp_F' in r.message
               for r in caplog.records)
    assert not any(r.levelno >= logging.WARNING and 'outTemp' in r.message
                   for r in caplog.records)


@pytest.mark.parametrize('reserved', ['dateTime', 'barometer_fetch_epoch'])
def test_reserved_key_is_refused_with_a_warning(tmp_path, caplog, reserved):
    caplog.set_level(logging.INFO)
    w = _writer(tmp_path, extra_fields=[reserved, 'luminosity'])
    assert w.extras == [('luminosity', 'luminosity_lux')]
    assert any(r.levelno == logging.WARNING and reserved in r.message
               for r in caplog.records)


def test_same_key_from_two_observations_keeps_the_first(tmp_path, caplog, monkeypatch):
    monkeypatch.setitem(UNITS, 'inTemp2', ('degree_F', 'group_temperature'))
    monkeypatch.setattr(ljw, '_extra_key', lambda obs: 'shared_key')
    caplog.set_level(logging.INFO)
    w = _writer(tmp_path, extra_fields=['luminosity', 'inTemp2'])
    assert w.extras == [('luminosity', 'shared_key')]
    assert any(r.levelno == logging.WARNING and 'inTemp2' in r.message
               for r in caplog.records)


def test_repeated_observation_is_kept_once(tmp_path):
    w = _writer(tmp_path, extra_fields=['luminosity', 'luminosity'])
    assert w.extras == [('luminosity', 'luminosity_lux')]


def test_naming_failure_skips_one_field_not_the_writer(tmp_path, caplog, monkeypatch):
    def boom(system, obs):
        if obs == 'pm2_5':
            raise RuntimeError('registry broke')
        return UNITS.get(obs, (None, None))
    monkeypatch.setattr(ljw.weewx.units, 'getStandardUnitType', boom, raising=False)
    w = _writer(tmp_path, extra_fields=['pm2_5', 'luminosity'])
    assert w.extras == [('luminosity', 'luminosity_lux')]
    assert any(r.levelno == logging.WARNING and 'pm2_5' in r.message
               for r in caplog.records)


def test_ttl_lands_under_the_output_key(tmp_path):
    w = _writer(tmp_path, extra_fields=['luminosity', 'pm2_5'],
                ttl={'luminosity': '45'})
    assert w._ttl('luminosity_lux') == 45
    assert w._ttl('pm2_5_microgram_per_meter_cubed') == w.ttl_default


def test_bad_ttl_value_falls_back_with_a_warning(tmp_path, caplog):
    w = _writer(tmp_path, extra_fields=['luminosity'], ttl={'luminosity': 'soon'})
    assert w.extras == [('luminosity', 'luminosity_lux')]
    assert w._ttl('luminosity_lux') == w.ttl_default
    assert any(r.levelno == logging.WARNING and 'soon' in r.message
               for r in caplog.records)


def test_ttl_for_an_unlisted_observation_is_ignored_with_a_warning(tmp_path, caplog):
    w = _writer(tmp_path, extra_fields=['luminosity'], ttl={'pm2_5': '45'})
    assert w._ttl('pm2_5_microgram_per_meter_cubed') == w.ttl_default
    assert any(r.levelno == logging.WARNING and 'pm2_5' in r.message
               for r in caplog.records)
