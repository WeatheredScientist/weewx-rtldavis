# SPDX-License-Identifier: GPL-3.0-or-later
"""`doctor`: is the dongle usable from inside this container? (DEC-0225 item 5, DEC-0228)

Run by entrypoint.sh for `docker compose run --rm weewx-rtldavis doctor`, as the container's own
user. The checks run in the order a fresh install fails them, and the first failure stops the run
with its own exit code and a one-line verdict naming the matching row of the troubleshooting table
in docs/QUICKSTART.md:

    10  no RTL2832U visible, or its device node is not in the container   `not a device node`
    11  the kernel's TV driver has the dongle                               `usb_claim_interface error -6`
    12  the device node is not readable and writable by this uid            `Permission denied`
    13  rtl_test found no tuner (or another program holds the dongle)       no `LOOP` after ten minutes
    14  weewx.conf exists but cannot be read or parsed

Exit 0 prints the radio values from weewx.conf and ends with `doctor: ok`. A missing weewx.conf
is not an error: the first weewxd start writes it (seed_config.py).

    python3 doctor.py

Every probe takes its root (/sys, /dev) or its runner as an argument, so the tests point it at a
temporary tree and a fake rtl_test.
"""
import glob
import os
import re
import stat
import subprocess
import sys

RTL_VENDOR = '0bda'
RTL_PRODUCTS = ('2838', '2832')
CONF_PATH = '/opt/weewx-data/weewx.conf'

# Exit code -> the first-column wording of its row in docs/QUICKSTART.md. tests/test_doctor.py
# checks each one is still in that table, so the two cannot drift apart silently.
ROWS = {
    10: '`not a device node`',
    11: '`usb_claim_interface error -6`',
    12: '`Permission denied`',
    13: 'no `LOOP` after ten minutes',
}

_TUNER = re.compile(r'^Found (.+ tuner)\s*$', re.MULTILINE)
_BUSY = re.compile(r'usb_claim_interface error|resource busy', re.IGNORECASE)
_GAIN = re.compile(r'-gain\s+(\S+)')


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def find_dongles(sys_root):
    """Return the sysfs device directories of every RTL2832U on the USB bus, sorted."""
    found = []
    for vendor_file in sorted(glob.glob(os.path.join(sys_root, 'bus', 'usb', 'devices', '*', 'idVendor'))):
        dev = os.path.dirname(vendor_file)
        if _read(vendor_file) == RTL_VENDOR and _read(os.path.join(dev, 'idProduct')) in RTL_PRODUCTS:
            found.append(dev)
    return found


def tv_driver(dev_dir):
    """Return the name of a DVB/TV kernel driver bound to the dongle's interface 0, or None."""
    for link in glob.glob(os.path.join(dev_dir, '*:1.0', 'driver')):
        name = os.path.basename(os.path.realpath(link))
        if 'dvb' in name or 'rtl28' in name:
            return name
    return None


def device_node(dev_root, dev_dir):
    """Return /dev/bus/usb/BBB/DDD for a sysfs device directory, or None if busnum/devnum are unreadable."""
    bus, num = _read(os.path.join(dev_dir, 'busnum')), _read(os.path.join(dev_dir, 'devnum'))
    try:
        return os.path.join(dev_root, 'bus', 'usb', '%03d' % int(bus or ''), '%03d' % int(num or ''))
    except ValueError:
        return None


def node_access(node, access=os.access):
    """Return 'missing', 'denied' or 'ok' for the device node and the current uid."""
    if not os.path.exists(node):
        return 'missing'
    return 'ok' if access(node, os.R_OK | os.W_OK) else 'denied'


def probe_radio(run=subprocess.run):
    """Run `timeout 3 rtl_test -t`; return (tuner name or None, its output).

    rtl_test exits on its own after the tuner line for an R820T ('No E4000 tuner found,
    aborting'), so the exit code says nothing: a `Found ... tuner` line is the success test.
    """
    try:
        res = run(['timeout', '3', 'rtl_test', '-t'], stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT, text=True, timeout=10)
        output = res.stdout or ''
    except FileNotFoundError:
        return None, 'rtl_test is not installed in this image'
    except subprocess.TimeoutExpired as e:
        output = e.stdout if isinstance(e.stdout, str) else (e.stdout or b'').decode('utf-8', 'replace')
    m = _TUNER.search(output)
    return (m.group(1) if m else None), output


def read_radio_config(conf_path):
    """Return the [Rtldavis] values doctor prints, or None if conf_path does not exist.

    Raises OSError or configobj's error when the file exists but cannot be read or parsed.
    """
    if not os.path.exists(conf_path):
        return None
    import configobj  # the venv has it (weewx depends on it); the system python may not

    conf = configobj.ConfigObj(conf_path, encoding='utf-8', file_error=True)
    rtl = conf.get('Rtldavis', {})
    gain = _GAIN.search(rtl.get('cmd', ''))
    return {
        'transceiver_frequency': rtl.get('transceiver_frequency', '(not set)'),
        'iss_channel': rtl.get('iss_channel', '(not set)'),
        'rain_bucket_type': rtl.get('rain_bucket_type', '(not set)'),
        'gain': gain.group(1) if gain else '(no -gain on cmd)',
    }


def _fail(out, code, what, fix):
    out('doctor: FAIL (%d): %s' % (code, what))
    if fix:
        out('  %s' % fix)
    if code in ROWS:
        out('  See the %s row of "Something wrong?" in docs/QUICKSTART.md.' % ROWS[code])
    return code


def run_doctor(sys_root='/sys', dev_root='/dev', conf_path=CONF_PATH, run=subprocess.run,
               access=os.access, uid=None, out=print):
    uid = os.getuid() if uid is None else uid

    dongles = find_dongles(sys_root)
    if not dongles:
        return _fail(out, 10, 'no RTL2832U (USB 0bda:2838 or 0bda:2832) is visible on the USB bus',
                     'Plug the dongle in; with `docker run`, pass `--device /dev/bus/usb`; '
                     'a VM needs a USB controller with the dongle attached.')
    dev = dongles[0]
    out('doctor: RTL2832U at %s%s' % (os.path.basename(dev),
                                       ' (and %d more; using the first)' % (len(dongles) - 1)
                                       if len(dongles) > 1 else ''))

    driver = tv_driver(dev)
    if driver:
        return _fail(out, 11, 'the kernel TV driver %s has the dongle' % driver,
                     'Re-run host-setup.sh on the host (it blacklists the TV driver), then reboot.')

    node = device_node(dev_root, dev)
    state = node_access(node, access) if node else 'missing'
    if state == 'missing':
        return _fail(out, 10, 'the dongle is on the host bus but %s is not in this container'
                     % (node or 'its device node'),
                     'Pass `--device /dev/bus/usb` (compose: `devices: - /dev/bus/usb:/dev/bus/usb`).')
    if state == 'denied':
        st = os.stat(node)
        return _fail(out, 12, '%s is not readable and writable by uid %d (owner %d:%d, mode %s)'
                     % (node, uid, st.st_uid, st.st_gid, oct(stat.S_IMODE(st.st_mode))),
                     'The udev rule did not apply: re-run host-setup.sh, unplug and re-plug the '
                     'dongle, and check PUID/PGID in .env match `id -u` and `id -g`.')
    out('doctor: %s is readable and writable by uid %d' % (node, uid))

    tuner, output = probe_radio(run)
    if not tuner:
        head = [ln for ln in output.splitlines() if ln.strip()][:6]
        if _BUSY.search(output):
            code = _fail(out, 13, 'rtl_test could not claim the dongle; another program holds it',
                         'A running weewx container counts: stop it first, then run doctor again. '
                         'If nothing else is running, see the %s row.' % ROWS[11])
        else:
            code = _fail(out, 13, 'rtl_test found no tuner',
                         'Check the USB cable and extension, then re-plug the dongle.')
        for ln in head:
            out('  | %s' % ln)
        return code
    out('doctor: rtl_test found the %s' % tuner)

    try:
        radio = read_radio_config(conf_path)
    except Exception as e:  # OSError or configobj.ConfigObjError: report either the same way
        return _fail(out, 14, 'cannot read %s: %s' % (conf_path, e),
                     'Give uid %d the weewx-data folder, e.g. sudo chown -R %d <your weewx-data folder>'
                     % (uid, uid))
    if radio is None:
        out('doctor: config %s: not seeded yet; the first `weewxd` start writes it' % conf_path)
    else:
        out('doctor: config %s' % conf_path)
        out('doctor: band %(transceiver_frequency)s, ISS channel %(iss_channel)s, '
            'rain bucket %(rain_bucket_type)s, gain %(gain)s' % radio)
    out('doctor: ok')
    return 0


if __name__ == '__main__':
    sys.exit(run_doctor())
