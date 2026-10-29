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


# --- delta refusal (DEC-0220 step 3) -----------------------------------------------

SUM_DEFAULTS = {'rain': {'extractor': 'sum'}, 'lightning_strike_count': {'extractor': 'sum'}}
PACKET = types.SimpleNamespace(packet={'dateTime': 1000, 'outTemp': 70.0})


@pytest.fixture
def sum_defaults(monkeypatch):
    monkeypatch.setattr(ljw, '_accumulator_defaults', lambda: SUM_DEFAULTS)


def test_default_sum_observation_is_refused_at_the_first_packet(tmp_path, caplog,
                                                                  sum_defaults, monkeypatch):
    monkeypatch.setitem(UNITS, 'rain', ('inch', 'group_rain'))
    w = _writer(tmp_path, extra_fields=['rain', 'luminosity'])
    assert [o for o, _k in w.extras] == ['rain', 'luminosity'], 'checked only at packet one'
    w.new_loop(PACKET)
    assert w.extras == [('luminosity', 'luminosity_lux')]
    refusals = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(refusals) == 1 and 'rain' in refusals[0].message
    assert 'dayRain' in refusals[0].message, 'the warning names the cumulative counterpart'


def test_site_accumulator_section_is_read_from_the_config(tmp_path, caplog, sum_defaults,
                                                           monkeypatch):
    """t_rain is a driver delta: only the site's [Accumulator] says so."""
    monkeypatch.setitem(UNITS, 't_rain', ('inch', 'group_rain'))
    w = ljw.LoopJsonWriter(engine=None, config_dict={
        'LoopJsonWriter': {'extra_fields': ['t_rain', 'luminosity'],
                           'path': str(tmp_path / 'a'),
                           'current_path': str(tmp_path / 'b')},
        'Accumulator': {'t_rain': {'extractor': 'sum'}}})
    w.new_loop(PACKET)
    assert w.extras == [('luminosity', 'luminosity_lux')]
    assert any(r.levelno == logging.WARNING and 't_rain' in r.message
               for r in caplog.records)


def test_site_accumulator_overrides_the_default(tmp_path, caplog, sum_defaults, monkeypatch):
    monkeypatch.setitem(UNITS, 'rain', ('inch', 'group_rain'))
    w = ljw.LoopJsonWriter(engine=None, config_dict={
        'LoopJsonWriter': {'extra_fields': ['rain'], 'path': str(tmp_path / 'a'),
                           'current_path': str(tmp_path / 'b')},
        'Accumulator': {'rain': {'extractor': 'max'}}})
    w.new_loop(PACKET)
    assert w.extras == [('rain', 'rain_in')]
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_refusal_is_logged_once_and_holds_on_later_packets(tmp_path, caplog, sum_defaults,
                                                            monkeypatch):
    monkeypatch.setitem(UNITS, 'rain', ('inch', 'group_rain'))
    w = _writer(tmp_path, extra_fields=['rain', 'luminosity'])
    for t in (1000, 1003, 1006):
        w.new_loop(types.SimpleNamespace(packet={'dateTime': t, 'outTemp': 70.0}))
    assert w.extras == [('luminosity', 'luminosity_lux')]
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


# --- extras ride the cache (DEC-0220 step 4) ---------------------------------------

def _feed(w):
    import json
    with open(w.path) as f:
        return json.load(f)


def _step(w, t, **fields):
    w.new_loop(types.SimpleNamespace(packet=dict(fields, dateTime=t)))
    return _feed(w)


def test_extra_value_is_written_cached_forward_and_expires(tmp_path, caplog):
    w = _writer(tmp_path, extra_fields=['luminosity'], ttl={'luminosity': '60'})
    assert _step(w, 1000, outTemp=70.0, luminosity=500.0)['luminosity_lux'] == 500.0
    assert _step(w, 1030, outTemp=70.1)['luminosity_lux'] == 500.0, 'cached forward'
    caplog.set_level(logging.INFO)
    feed = _step(w, 1100, outTemp=70.2)
    assert 'luminosity_lux' not in feed, 'past its 60 s TTL: omitted, not served stale'
    assert feed['outTemp_F'] == 70.2, 'the standard fields are untouched'
    assert any(r.levelno == logging.WARNING and 'luminosity_lux expired' in r.message
               for r in caplog.records)
    assert _step(w, 1103, outTemp=70.3, luminosity=480.0)['luminosity_lux'] == 480.0


def test_extra_uses_the_default_ttl_without_an_entry(tmp_path):
    w = _writer(tmp_path, extra_fields=['luminosity'])
    _step(w, 1000, luminosity=500.0)
    assert _step(w, 1000 + w.ttl_default, outTemp=70.0)['luminosity_lux'] == 500.0
    assert 'luminosity_lux' not in _step(w, 1000 + w.ttl_default + 1, outTemp=70.0)


def test_group_less_string_value_passes_untouched(tmp_path, monkeypatch):
    w = _writer(tmp_path, extra_fields=['txBatteryStatus'])
    assert _step(w, 1000, txBatteryStatus='OK')['txBatteryStatus'] == 'OK'


def test_unlisted_observation_in_the_packet_is_not_written(tmp_path):
    w = _writer(tmp_path, extra_fields=['luminosity'])
    feed = _step(w, 1000, outTemp=70.0, luminosity=500.0, pm2_5=12.0)
    assert feed['luminosity_lux'] == 500.0 and 'pm2_5_microgram_per_meter_cubed' not in feed


# Golden output of the 1.0.0 writer (git: origin/dev at S170) for this packet sequence,
# `writer` key removed. With no extras configured the output must not change (DEC-0220 item 6).
_GOLDEN_SEQUENCE = [
    {'dateTime': 1000, 'windSpeed': 4.0, 'windDir': 90.0, 'outTemp': 61.5,
     'outHumidity': 70, 'barometer': 29.9},
    {'dateTime': 1003, 'windSpeed': 5.0, 'radiation': 120.0, 'UV': 2.0, 'rainRate': 0.0},
    {'dateTime': 1100, 'outTemp': 61.8, 'windSpeed': 0.0},
    {'dateTime': 1400, 'outTemp': 62.0},
    {'dateTime': 1404, 'windSpeed': 3.0, 'windDir': 100.0},
]
_GOLDEN_OUTPUT = [
    {'windSpeed_mph': 4.0, 'windDir': 90.0, 'outTemp_F': 61.5, 'outHumidity': 70,
     'barometer_inHg': 29.9, 'dateTime': 1000},
    {'windSpeed_mph': 5.0, 'windDir': 90.0, 'outTemp_F': 61.5, 'outHumidity': 70,
     'barometer_inHg': 29.9, 'rainRate_inch_per_hour': 0.0, 'radiation_Wpm2': 120.0,
     'UV': 2.0, 'dateTime': 1003},
    {'windSpeed_mph': 0.0, 'windDir': 90.0, 'outTemp_F': 61.8, 'outHumidity': 70,
     'barometer_inHg': 29.9, 'rainRate_inch_per_hour': 0.0, 'radiation_Wpm2': 120.0,
     'UV': 2.0, 'dateTime': 1100},
    {'windSpeed_mph': 0.0, 'outTemp_F': 62.0, 'dateTime': 1400},
    {'windSpeed_mph': 3.0, 'windDir': 100.0, 'outTemp_F': 62.0, 'dateTime': 1404},
]


def test_no_extras_output_equals_the_1_0_0_golden(tmp_path):
    w = _writer(tmp_path)
    got = []
    for pkt in _GOLDEN_SEQUENCE:
        fields = {k: v for k, v in pkt.items() if k != 'dateTime'}
        feed = _step(w, pkt['dateTime'], **fields)
        feed.pop('writer')
        feed.pop('loop_interval_s', None)  # the one new key in 1.1.0 (DEC-0221)
        got.append(feed)
    assert len(got) == len(_GOLDEN_OUTPUT) == 5, 'the golden is not empty'
    assert got == _GOLDEN_OUTPUT


# --- loop_interval_s (DEC-0221 step 5) ---------------------------------------------

def _interval_feeds(tmp_path, clock_times, monkeypatch=None, fail_on=()):
    """Feed one packet per clock reading; return each file's loop_interval_s (or None)."""
    w = _writer(tmp_path)
    ticks = iter(clock_times)
    w._clock = lambda: next(ticks)
    out = []
    for i in range(len(clock_times) + len(fail_on)):
        if i in fail_on:
            real = ljw.os.replace
            ljw.os.replace = lambda *a: (_ for _ in ()).throw(OSError('disk full'))
            try:
                w.new_loop(types.SimpleNamespace(packet={'dateTime': 1000 + i}))
            finally:
                ljw.os.replace = real
            out.append('failed')
            continue
        out.append(_step(w, 1000 + i, outTemp=70.0).get('loop_interval_s'))
    return out


def test_interval_absent_until_a_gap_exists_then_median_from_the_first_gap(tmp_path):
    # writes at 0, 1, 301, 601 give gaps 1, 300, 300: the key shows from the third file
    got = _interval_feeds(tmp_path, [0.0, 1.0, 301.0, 601.0])
    assert got == [None, None, 1.0, 150.5]


def test_interval_median_settles(tmp_path):
    got = _interval_feeds(tmp_path, [0.0, 1.0, 301.0, 601.0, 901.0])
    assert got[-1] == 300.0


def test_interval_is_omitted_outside_one_to_3600_never_clamped(tmp_path):
    assert _interval_feeds(tmp_path, [0.0, 0.4, 0.8])[2] is None        # 0.4 s
    assert _interval_feeds(tmp_path, [0.0, 4000.0, 8000.0])[2] is None  # 4000 s


def test_interval_range_is_checked_on_the_rounded_value(tmp_path):
    assert _interval_feeds(tmp_path, [0.0, 0.96, 1.92])[2] == 1.0       # 0.96 rounds to 1.0
    assert _interval_feeds(tmp_path, [0.0, 3600.0, 7200.0])[2] == 3600.0
    assert _interval_feeds(tmp_path, [0.0, 0.94, 1.88])[2] is None      # 0.94 rounds to 0.9


def test_a_failed_write_adds_no_gap(tmp_path):
    # write 0 at t=0 ok; write 1 fails (no clock read); write 2 ok at t=10; write 3 at t=20
    got = _interval_feeds(tmp_path, [0.0, 10.0, 20.0], fail_on=(1,))
    assert got == [None, 'failed', None, 10.0]


def test_only_the_last_32_gaps_count(tmp_path):
    # 16 gaps of 100 s, then 32 gaps of 5 s: the 100 s gaps have all aged out
    times = [0.0]
    for gap in [100.0] * 16 + [5.0] * 32:
        times.append(times[-1] + gap)
    assert _interval_feeds(tmp_path, times)[-1] == 5.0


def test_interval_also_rides_current_json(tmp_path):
    import json
    w = _writer(tmp_path)
    ticks = iter([0.0, 2.0, 4.0])
    w._clock = lambda: next(ticks)
    for t in (1000, 1002, 1004):
        w.new_loop(types.SimpleNamespace(packet={'dateTime': t, 'outTemp': 70.0}))
    w.current_interval = 0
    ticks = iter([6.0])
    w._clock = lambda: next(ticks)
    w.new_loop(types.SimpleNamespace(packet={'dateTime': 1006, 'outTemp': 70.0}))
    with open(w.current_path) as f:
        assert json.load(f)['loop_interval_s'] == 2.0
