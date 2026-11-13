"""DEC-0235 (ops#440): which dongle, everywhere it is decided.

The Go decoder (patch/rtldavis-devsel.patch), doctor.select_dongle, the driver's RTLSDR_DEVICE
splice and entrypoint.sh's bias-tee call must agree on which stick is "the" dongle:

  1. doctor.select_dongle passes the case table the Go tests use (tests/go/devsel_cases.json),
     so the decoder and doctor cannot pick differently.
  2. rtldavis.apply_device: RTLSDR_DEVICE becomes -d; a -d that disagrees stops the start.
  3. doctor with two dongles: lists both, fails 15 when the choice is ambiguous, checks and probes
     the chosen one, and warns on shared or all-digit serials and on a V4 with rewritten strings.
  4. entrypoint.sh hands rtl_biast the index doctor resolves, and leaves the tee alone when the
     setting matches no single dongle.

Serials here are made up.
"""
import json
import os
import shutil
import subprocess

import pytest

import doctor
from rtldavis import apply_device, cmd_device
from test_doctor import R820T_OUTPUT, _add_node, _add_usb, _runner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = json.load(open(os.path.join(ROOT, 'tests', 'go', 'devsel_cases.json')))['cases']

V4_OUTPUT = """\
Found 2 device(s):
  0:  Realtek, RTL2838UHIDIR, SN: SER1
  1:  RTLSDRBlog, Blog V4, SN: WXV4

Using device 1: Generic RTL2832U OEM
Found Rafael Micro R828D tuner
RTL-SDR Blog V4 Detected
Supported gain values (29): 0.0 0.9 1.4
"""


# --- 1. one rule, two implementations -------------------------------------------

def test_the_case_table_is_loaded():
    assert len(CASES) >= 20
    assert any(c['outcome'] == 'error' for c in CASES) and any(c['warn'] for c in CASES)


@pytest.mark.parametrize('case', CASES, ids=[c['name'] for c in CASES])
def test_select_dongle_matches_the_go_case_table(case):
    index, warning, error = doctor.select_dongle(case['arg'], case['given'], case['serials'])
    if case['outcome'] == 'error':
        assert error and index is None
    else:
        assert error is None and index == case['outcome']
        assert bool(warning) == case['warn']


def test_the_case_table_catches_a_first_match_lookup():
    """POSITIVE CONTROL: librtlsdr's own lookup (first match wins) must fail the table."""
    def first_match(arg, given, serials):
        for i, s in enumerate(serials):
            if s == arg:
                return i, '', None
        return doctor.select_dongle(arg, given, serials)
    failures = [c['name'] for c in CASES if c['outcome'] == 'error'
                and first_match(c['arg'], c['given'], c['serials'])[2] is None]
    assert 'shared serial is refused' in failures


# --- 2. the driver's splice -----------------------------------------------------

CMD = '/usr/local/bin/rtldavis -gain 372'


@pytest.mark.parametrize('value', [None, '', '   '])
def test_unset_leaves_cmd_alone(value):
    assert apply_device(CMD, value) == CMD


def test_set_appends_d():
    assert apply_device(CMD, 'WXV4') == CMD + ' -d WXV4'
    assert cmd_device(apply_device(CMD, 'WXV4')) == ['WXV4']


@pytest.mark.parametrize('cmd', [CMD + ' -d WXV4', CMD + ' -d=WXV4', CMD + ' --d WXV4'])
def test_agreeing_d_is_left_alone(cmd):
    assert apply_device(cmd, 'WXV4') == cmd


def test_disagreeing_d_stops_the_start_naming_both():
    with pytest.raises(ValueError) as e:
        apply_device(CMD + ' -d SER1', 'WXV4')
    assert 'RTLSDR_DEVICE=WXV4' in str(e.value) and '-d SER1' in str(e.value)


def test_two_d_flags_or_a_spaced_value_are_refused():
    with pytest.raises(ValueError):
        apply_device(CMD + ' -d SER1 -d SER1', 'SER1')
    with pytest.raises(ValueError):
        apply_device(CMD, 'WX V4')


def test_cmd_without_device_still_has_none():
    assert cmd_device(CMD) == [] and cmd_device(CMD + ' -dupwindow 2000') == []


def test_the_driver_applies_it_before_the_band_flags_and_logs_go_dongle_lines():
    src = open(os.path.join(ROOT, 'rtldavis.py')).read()
    init = src.index("self.cmd = apply_device(self.cmd, os.environ.get('RTLSDR_DEVICE'))")
    assert src.index("self.cmd = stn_dict.get('cmd', DEFAULT_CMD)") < init
    assert init < src.index('self.cmd = self.cmd + " -tf "')
    assert 'if "dongle: " in _line:' in src


# --- 3. doctor with more than one dongle -----------------------------------------

@pytest.fixture
def two(tmp_path):
    sys_root, dev_root = tmp_path / 'sys', tmp_path / 'dev'
    (sys_root / 'bus' / 'usb' / 'devices').mkdir(parents=True)
    dev_root.mkdir()
    return sys_root, dev_root, tmp_path / 'weewx.conf'


def _stick(tree, port, strings, bus, dev, node=True):
    d = _add_usb(tree[0], port, '0bda', '2838', bus=bus, dev=dev)
    for name, value in zip(('manufacturer', 'product', 'serial'), strings):
        (d / name).write_text(value + '\n')
    if node:
        _add_node(tree[1], bus=bus, dev=dev)
    return d


V3 = ('Realtek', 'RTL2838UHIDIR', 'SER1')
BLOG = ('RTLSDRBlog', 'Blog V4', 'WXV4')


def _run(tree, device, listed, run=None):
    lines = []
    run = run or _runner(R820T_OUTPUT)
    code = doctor.run_doctor(str(tree[0]), str(tree[1]), str(tree[2]), run=run,
                             access=lambda p, m: True, uid=1000, out=lines.append,
                             device=device, lister=lambda: listed)
    return code, '\n'.join(lines), run


def test_two_dongles_and_no_setting_is_15_and_lists_both(two):
    _stick(two, '5-1', V3, 5, 2)
    _stick(two, '7-1.3', BLOG, 7, 4)
    code, text, run = _run(two, '', [BLOG, V3])
    assert code == 15 and doctor.ROWS[15] in text
    assert '5-1: Realtek RTL2838UHIDIR, SN SER1 (RTL-SDR Blog V3 or another RTL2832U)' in text
    assert '7-1.3: RTLSDRBlog Blog V4, SN WXV4 (RTL-SDR Blog V4)' in text
    assert 'RTLSDR_DEVICE' in text and run.calls == []


def test_a_serial_picks_its_dongle_and_probes_it_by_librtlsdr_index(two):
    _stick(two, '5-1', V3, 5, 2)
    _stick(two, '7-1.3', BLOG, 7, 4)
    code, text, run = _run(two, 'SER1', [BLOG, V3])  # librtlsdr lists the V4 first
    assert code == 0, text
    assert 'the station uses 5-1 (RTLSDR_DEVICE=SER1)' in text
    assert run.calls == [['timeout', '3', 'rtl_test', '-d', '1', '-t']]


def test_only_the_chosen_dongle_needs_a_node(two):
    """Inside a container passed one node, the other stick shows in sysfs but has no node."""
    _stick(two, '5-1', V3, 5, 2)
    _stick(two, '7-1.3', BLOG, 7, 4, node=False)
    code, text, _ = _run(two, 'SER1', [V3, BLOG])
    assert code == 0, text


def test_a_shared_serial_is_15_with_the_burn_fix(two):
    _stick(two, '5-1', ('Realtek', 'RTL2838UHIDIR', '00000001'), 5, 2)
    _stick(two, '7-1.3', ('RTLSDRBlog', 'Blog V4', '00000001'), 7, 4)
    code, text, _ = _run(two, '00000001', None)
    assert code == 15
    assert 'share the serial 00000001' in text and 'all digits' in text
    assert 'rtl_eeprom -d 0 -s' in text and 'never pass -m, -p or -g' in text


def test_an_index_is_resolved_through_librtlsdr_with_a_warning(two):
    _stick(two, '5-1', V3, 5, 2)
    _stick(two, '7-1.3', BLOG, 7, 4)
    code, text, run = _run(two, '0', [BLOG, V3], run=_runner(V4_OUTPUT))
    assert code == 0, text
    assert 'the station uses 7-1.3' in text and 'is an index' in text
    assert run.calls == [['timeout', '3', 'rtl_test', '-d', '0', '-t']]
    assert 'R828D tuner' in text and 'EEPROM strings were changed' not in text


def test_an_index_without_librtlsdr_is_15(two):
    _stick(two, '5-1', V3, 5, 2)
    _stick(two, '7-1.3', BLOG, 7, 4)
    code, text, _ = _run(two, '1', None)
    assert code == 15 and 'set it to a serial' in text


def test_an_unknown_serial_is_15(two):
    _stick(two, '5-1', V3, 5, 2)
    code, text, _ = _run(two, 'NOPE', [V3])
    assert code == 15 and 'neither the serial nor the index' in text


def test_an_r828d_without_v4_strings_warns_with_the_restore_line(two):
    _stick(two, '7-1.3', ('Realtek', 'RTL2838UHIDIR', 'WXV4'), 7, 4)
    code, text, _ = _run(two, '', None, run=_runner(V4_OUTPUT))
    assert code == 0
    assert 'EEPROM strings were changed' in text and 'rtl_eeprom -m RTLSDRBlog -p "Blog V4"' in text


def test_one_dongle_and_no_setting_is_unchanged(two):
    _stick(two, '5-1', V3, 5, 2)
    code, text, run = _run(two, '', None)
    assert code == 0 and run.calls == [['timeout', '3', 'rtl_test', '-t']]
    assert 'the station uses' not in text and 'WARNING' not in text


def test_resolve_prints_the_librtlsdr_index_or_fails_15(capsys):
    errs = []
    assert doctor.resolve('SER1', lambda: [BLOG, V3], errs.append) == 0
    assert capsys.readouterr().out.strip() == '1'
    assert doctor.resolve('DUP', lambda: [('a', 'b', 'DUP'), ('c', 'd', 'DUP')], errs.append) == 15
    assert doctor.resolve('SER1', lambda: None, errs.append) == 15
    assert capsys.readouterr().out == ''
    assert any('matches the serial of 2' in e for e in errs)


# --- 4. entrypoint.sh's bias-tee call ---------------------------------------------

def _entrypoint(tmp_path, env, resolve_out='1', resolve_rc=0):
    """Run entrypoint.sh with its absolute paths pointed at stubs; return rtl_biast's argv."""
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    log = tmp_path / 'biast.log'
    (bindir / 'rtl_biast').write_text('#!/bin/bash\necho "$@" >> %s\n' % log)
    (bindir / 'resolve').write_text('#!/bin/bash\necho %s\nexit %d\n' % (resolve_out, resolve_rc))
    for f in ('rtl_biast', 'resolve'):
        os.chmod(bindir / f, 0o755)
    script = open(os.path.join(ROOT, 'entrypoint.sh')).read()
    script = (script.replace('/opt/weewx-venv/bin/python3 /opt/doctor.py --resolve', str(bindir / 'resolve'))
              .replace('/opt/weewx-venv/bin/python3 /opt/seed_config.py', 'true')
              .replace('mkdir -p /var/log/weewx', 'true')
              .replace('exec /opt/weewx-venv/bin/weewxd /opt/weewx-data/weewx.conf', 'exit 0'))
    assert 'doctor.py --resolve' not in script and 'seed_config' not in script and 'weewxd /opt' not in script
    path = tmp_path / 'entrypoint.sh'
    path.write_text(script)
    full_env = dict(PATH='%s:%s' % (bindir, os.environ['PATH']), TZ='UTC', **env)
    r = subprocess.run(['bash', str(path)], env=full_env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return (log.read_text().splitlines() if log.exists() else []), r.stdout


@pytest.mark.skipif(shutil.which('bash') is None, reason='needs bash')
def test_entrypoint_unset_drives_index_0_as_before(tmp_path):
    calls, _ = _entrypoint(tmp_path, {})
    assert calls == ['-b 0']


@pytest.mark.skipif(shutil.which('bash') is None, reason='needs bash')
def test_entrypoint_hands_rtl_biast_the_resolved_index(tmp_path):
    calls, out = _entrypoint(tmp_path, {'RTLSDR_DEVICE': 'WXV4', 'BIAS_TEE': '1'})
    assert calls == ['-d 1 -b 1'] and 'RTLSDR_DEVICE=WXV4 is librtlsdr dongle 1' in out


@pytest.mark.skipif(shutil.which('bash') is None, reason='needs bash')
def test_entrypoint_leaves_the_tee_alone_when_unresolved(tmp_path):
    calls, out = _entrypoint(tmp_path, {'RTLSDR_DEVICE': 'NOPE', 'BIAS_TEE': '1'},
                             resolve_out='', resolve_rc=15)
    assert calls == [] and 'leaving the bias tee alone' in out
