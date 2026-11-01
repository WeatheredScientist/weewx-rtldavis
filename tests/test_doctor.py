"""doctor.py: the in-container dongle check and its exit-code contract (DEC-0228).

Each failure has its own exit code and names a row of docs/QUICKSTART.md's troubleshooting table;
the probes read a temporary /sys and /dev tree and a fake rtl_test.

Run:  python3 -m pytest tests/ (pytest only)
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import doctor  # noqa: E402

R820T_OUTPUT = """\
Found 1 device(s):
  0:  Realtek, RTL2838UHIDIR, SN: 00000001

Using device 0: Generic RTL2832U OEM
Found Rafael Micro R820T tuner
Supported gain values (29): 0.0 0.9 1.4 2.7 3.7 7.7 8.7 12.5 14.4 15.7 16.6 19.7 20.7 22.9
[R82XX] PLL not locked!
Sampling at 2048000 S/s.
No E4000 tuner found, aborting.
"""

BUSY_OUTPUT = """\
Found 1 device(s):
  0:  Realtek, RTL2838UHIDIR, SN: 00000001

Using device 0: Generic RTL2832U OEM
usb_claim_interface error -6
Failed to open rtlsdr device #0.
"""

CONF = """\
[Station]
    location = Test
[Rtldavis]
    cmd = /usr/local/bin/rtldavis -gain 372
    transceiver_frequency = US
    iss_channel = 5
    rain_bucket_type = 0
"""


def _add_usb(sys_root, name, vendor, product, bus=1, dev=4, driver=None):
    d = sys_root / 'bus' / 'usb' / 'devices' / name
    d.mkdir(parents=True)
    (d / 'idVendor').write_text(vendor + '\n')
    (d / 'idProduct').write_text(product + '\n')
    (d / 'busnum').write_text('%d\n' % bus)
    (d / 'devnum').write_text('%d\n' % dev)
    if driver:
        drv = sys_root / 'bus' / 'usb' / 'drivers' / driver
        drv.mkdir(parents=True, exist_ok=True)
        (d / ('%s:1.0' % name)).mkdir()
        os.symlink(drv, d / ('%s:1.0' % name) / 'driver')
    return d


def _add_node(dev_root, bus=1, dev=4):
    node = dev_root / 'bus' / 'usb' / ('%03d' % bus) / ('%03d' % dev)
    node.parent.mkdir(parents=True, exist_ok=True)
    node.write_text('')
    return node


def _runner(output, rc=0):
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, rc, stdout=output)
    run.calls = calls
    return run


@pytest.fixture
def tree(tmp_path):
    sys_root, dev_root = tmp_path / 'sys', tmp_path / 'dev'
    (sys_root / 'bus' / 'usb' / 'devices').mkdir(parents=True)
    dev_root.mkdir()
    return sys_root, dev_root, tmp_path / 'weewx.conf'


def _doctor(tree, run=None, access=lambda p, m: True):
    sys_root, dev_root, conf = tree
    lines = []
    code = doctor.run_doctor(str(sys_root), str(dev_root), str(conf),
                             run=run or _runner(R820T_OUTPUT), access=access, uid=1000,
                             out=lines.append)
    return code, '\n'.join(lines)


def _healthy(tree, driver=None):
    sys_root, dev_root, _ = tree
    _add_usb(sys_root, '1-1', '1d6b', '0002', dev=1)  # a root hub: not a dongle
    _add_usb(sys_root, '1-1.2', '0bda', '2838', driver=driver)
    _add_node(dev_root)


def test_no_dongle_on_the_bus_is_10_and_names_the_device_node_row(tree):
    _add_usb(tree[0], '1-1', '1d6b', '0002')
    code, text = _doctor(tree)
    assert code == 10
    assert 'no RTL2832U' in text and doctor.ROWS[10] in text
    assert '--device /dev/bus/usb' in text


def test_no_usb_sysfs_at_all_is_10(tmp_path):
    lines = []
    code = doctor.run_doctor(str(tmp_path / 'nosys'), str(tmp_path), str(tmp_path / 'c'),
                             out=lines.append)
    assert code == 10


def test_dongle_on_host_but_node_not_passed_in_is_10(tree):
    _add_usb(tree[0], '1-1.2', '0bda', '2832')
    code, text = _doctor(tree)
    assert code == 10
    assert '/bus/usb/001/004' in text and 'is not in this container' in text


def test_tv_driver_bound_is_11(tree):
    _healthy(tree, driver='dvb_usb_rtl28xxu')
    code, text = _doctor(tree)
    assert code == 11
    assert 'dvb_usb_rtl28xxu' in text and doctor.ROWS[11] in text


def test_usbfs_driver_is_not_the_tv_driver(tree):
    _healthy(tree, driver='usbfs')
    code, _ = _doctor(tree)
    assert code == 0


def test_node_not_writable_is_12_with_uid_and_mode(tree):
    _healthy(tree)
    code, text = _doctor(tree, access=lambda p, m: False)
    assert code == 12
    assert 'uid 1000' in text and 'mode 0o' in text and 'udev rule' in text
    assert doctor.ROWS[12] in text


def test_no_tuner_is_13_and_shows_rtl_test_output(tree):
    _healthy(tree)
    code, text = _doctor(tree, run=_runner('No supported devices found.\n', rc=1))
    assert code == 13
    assert doctor.ROWS[13] in text and '| No supported devices found.' in text


def test_busy_dongle_is_13_and_points_at_a_running_container(tree):
    _healthy(tree)
    code, text = _doctor(tree, run=_runner(BUSY_OUTPUT, rc=1))
    assert code == 13
    assert 'another program holds it' in text and '| usb_claim_interface error -6' in text


def test_rtl_test_missing_is_13(tree):
    _healthy(tree)

    def run(cmd, **kw):
        raise FileNotFoundError(cmd[0])
    code, text = _doctor(tree, run=run)
    assert code == 13 and 'not installed' in text


def test_r820t_abort_counts_as_success_and_runs_with_a_timeout(tree):
    _healthy(tree)
    run = _runner(R820T_OUTPUT, rc=1)
    code, text = _doctor(tree, run=run)
    assert code == 0
    assert run.calls == [['timeout', '3', 'rtl_test', '-t']]
    assert 'Rafael Micro R820T tuner' in text


def test_success_without_config_says_not_seeded(tree):
    _healthy(tree)
    code, text = _doctor(tree)
    assert code == 0
    assert 'not seeded yet; the first `weewxd` start writes it' in text
    assert text.splitlines()[-1] == 'doctor: ok'


def test_success_prints_the_radio_values(tree):
    pytest.importorskip('configobj')
    _healthy(tree)
    tree[2].write_text(CONF)
    code, text = _doctor(tree)
    assert code == 0
    assert 'band US, ISS channel 5, rain bucket 0, gain 372' in text
    assert str(tree[2]) in text
    assert text.splitlines()[-1] == 'doctor: ok'


def test_unreadable_config_is_14(tree):
    pytest.importorskip('configobj')
    _healthy(tree)
    tree[2].write_text('[Rtldavis\n    broken = "\n')
    code, text = _doctor(tree)
    assert code == 14 and 'cannot read' in text


def test_every_row_doctor_names_is_in_the_quickstart_table():
    with open(os.path.join(ROOT, 'docs', 'QUICKSTART.md')) as f:
        first_cells = [ln.split('|')[1] for ln in f if ln.startswith('| ') and ln.count('|') >= 3]
    for code, row in doctor.ROWS.items():
        assert any(row in cell for cell in first_cells), \
            'exit %d names %r, which is not in QUICKSTART.md\'s table' % (code, row)
