# SPDX-License-Identifier: GPL-3.0-or-later
"""`doctor`: is the dongle usable from inside this container? (DEC-0225 item 5, DEC-0228, DEC-0235)

Run by entrypoint.sh for `docker compose run --rm weewx-rtldavis doctor`, as the container's own
user. It lists every RTL-SDR dongle it can see (port, maker, product, serial, model), picks the one
the station will use, and checks that one in the order a fresh install fails. The first failure
stops the run with its own exit code and a one-line verdict naming the matching row of the
troubleshooting table in docs/QUICKSTART.md:

    10  no RTL2832U visible, or its device node is not in the container   `not a device node`
    11  the kernel's TV driver has the dongle                               `usb_claim_interface error -6`
    12  the device node is not readable and writable by this uid            `Permission denied`
    13  rtl_test found no tuner (or another program holds the dongle)       no `LOOP` after ten minutes
    14  weewx.conf exists but cannot be read or parsed
    15  which dongle is ambiguous: more than one and RTLSDR_DEVICE unset,   `more than one dongle`
        or RTLSDR_DEVICE matching none or several

Exit 0 prints the radio values from weewx.conf and ends with `doctor: ok`. A missing weewx.conf
is not an error: the first weewxd start writes it (seed_config.py).

    python3 doctor.py              the check
    python3 doctor.py --resolve    print the librtlsdr index RTLSDR_DEVICE names (entrypoint.sh
                                   hands it to rtl_biast, so the bias tee acts on the stick the
                                   decoder opens); exit 15 with the reason on stderr otherwise

Which dongle (DEC-0235): RTLSDR_DEVICE, a serial (recommended) or an index. select_dongle applies
the rule the Go decoder's devsel.Pick applies, and both are tested against one case table
(tests/go/devsel_cases.json). The listing reads sysfs, which needs no USB open, so it works while
a running station holds the dongle; an index is librtlsdr's order, read through librtlsdr itself.

Every probe takes its root (/sys, /dev), its runner or its librtlsdr lister as an argument, so the
tests point it at a temporary tree, a fake rtl_test and a fake dongle list.
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
    15: '`more than one dongle`',
}

_TUNER = re.compile(r'^Found (.+ tuner)\s*$', re.MULTILINE)
_BUSY = re.compile(r'usb_claim_interface error|resource busy', re.IGNORECASE)
_GAIN = re.compile(r'-gain\s+(\S+)')

V4 = ('RTLSDRBlog', 'Blog V4')
V4L = ('RTLSDRBlog', 'Blog V4L')
UNIQUE_SERIAL_FIX = ('Give each dongle a unique serial that contains a letter, with only that '
                     'dongle plugged in: rtl_eeprom -d 0 -s <NEWSERIAL>, answer y, then re-plug '
                     '(docs/QUICKSTART.md, "More than one dongle"). On a Blog V4 never pass '
                     '-m, -p or -g.')


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


def usb_strings(dev_dir):
    """Return (manufacturer, product, serial) from sysfs; a missing one is ''."""
    return tuple(_read(os.path.join(dev_dir, f)) or '' for f in ('manufacturer', 'product', 'serial'))


def model(manufacturer, product):
    """Name the dongle from its EEPROM strings, the way librtlsdr itself recognizes a Blog V4."""
    if (manufacturer, product) == V4:
        return 'RTL-SDR Blog V4'
    if (manufacturer, product) == V4L:
        return 'RTL-SDR Blog V4L (not specifically supported by this image\'s librtlsdr 2.0.2)'
    return 'RTL-SDR Blog V3 or another RTL2832U'


def select_dongle(arg, given, serials):
    """Return (index, warning, error) for -d / RTLSDR_DEVICE `arg` over dongles listed by serial.

    The same rule as the Go decoder's devsel.Pick (patch/rtldavis-devsel.patch): an empty arg is an
    error; a serial matching exactly one dongle wins; a serial matching several is an error;
    otherwise plain decimal digits in range are an index; anything else is an error. With more
    than one dongle an index, or no arg at all, comes with a warning. tests/test_devsel.py runs
    this against the case table the Go tests use.
    """
    if not serials:
        return None, '', 'no RTL-SDR dongle found'
    if arg == '':
        return None, '', 'the dongle setting is empty; give a serial or an index'
    hits = [i for i, s in enumerate(serials) if s == arg]
    if len(hits) > 1:
        return None, '', ('%s matches the serial of %d dongles (indexes %s)'
                          % (arg, len(hits), ', '.join(str(i) for i in hits)))
    if len(hits) == 1:
        return hits[0], '', None
    if not re.fullmatch(r'[0-9]+', arg) or int(arg) >= len(serials):
        return None, '', ('%s is neither the serial nor the index of any of the %d dongle(s) present'
                          % (arg, len(serials)))
    index = int(arg)
    if len(serials) > 1 and not given:
        return index, ('%d dongles present and none chosen, so index %d; the order can change at '
                       'a re-plug or reboot' % (len(serials), index)), None
    if len(serials) > 1:
        return index, ('%s is an index, and with %d dongles the order can change at a re-plug or '
                       'reboot' % (arg, len(serials))), None
    return index, '', None


def librtlsdr_dongles():
    """Return [(manufacturer, product, serial)] in librtlsdr's own index order, the decoder's, or
    None when librtlsdr cannot be loaded. Reading the strings opens each device briefly; a dongle
    the uid cannot open comes back with empty strings."""
    import ctypes
    lib = None
    for name in ('librtlsdr.so.0', 'librtlsdr.so', 'librtlsdr.dylib'):
        try:
            lib = ctypes.CDLL(name)
            break
        except OSError:
            continue
    if lib is None:
        return None
    lib.rtlsdr_get_device_count.restype = ctypes.c_uint32
    lib.rtlsdr_get_device_usb_strings.argtypes = [ctypes.c_uint32, ctypes.c_char_p,
                                                  ctypes.c_char_p, ctypes.c_char_p]
    found = []
    for i in range(lib.rtlsdr_get_device_count()):
        bufs = [ctypes.create_string_buffer(257) for _ in range(3)]
        lib.rtlsdr_get_device_usb_strings(i, *bufs)
        found.append(tuple(b.value.decode('utf-8', 'replace') for b in bufs))
    return found


def choose(device, dongles, lister):
    """Pick the dongle doctor checks: the one the decoder will open.

    `dongles` are sysfs directories, `device` is RTLSDR_DEVICE ('' or None when unset), `lister`
    returns librtlsdr's list (see librtlsdr_dongles). Returns (sysfs dir, librtlsdr index or None,
    warning, error). A serial is matched in sysfs, which needs no USB open; an index means
    librtlsdr's order, so it is resolved through librtlsdr and mapped back to sysfs by its strings.
    """
    strings = [usb_strings(d) for d in dongles]
    if not device:
        if len(dongles) == 1:
            return dongles[0], None, '', None
        return None, None, '', ('%d dongles present and RTLSDR_DEVICE is not set, so the station '
                                'would open whichever librtlsdr lists first' % len(dongles))
    index, warning, error = select_dongle(device, True, [s[2] for s in strings])
    if error:
        return None, None, '', error
    if strings[index][2] == device:  # matched as a serial
        lib_index = None
        if len(dongles) > 1:
            listed = lister()
            if listed is not None:
                hits = [i for i, s in enumerate(listed) if s[2] == device]
                lib_index = hits[0] if len(hits) == 1 else None
        return dongles[index], lib_index, '', None
    if len(dongles) == 1:  # index 0 of one: the same in every order
        return dongles[0], 0, '', None
    listed = lister()
    if listed is None:
        return None, None, '', ('RTLSDR_DEVICE=%s is an index, which cannot be checked without '
                                'librtlsdr; set it to a serial' % device)
    lib_index, warning, error = select_dongle(device, True, [s[2] for s in listed])
    if error:
        return None, None, '', error
    same = [d for d, s in zip(dongles, strings) if s == listed[lib_index]]
    if len(same) != 1:
        return None, None, '', ('RTLSDR_DEVICE=%s is librtlsdr index %d (%s %s SN %s), which '
                                'matches %d dongles here; set RTLSDR_DEVICE to a unique serial'
                                % ((device, lib_index) + tuple(listed[lib_index]) + (len(same),)))
    return same[0], lib_index, warning, None


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


def probe_radio(run=subprocess.run, device_args=()):
    """Run `timeout 3 rtl_test [-d N] -t`; return (tuner name or None, its output).

    rtl_test exits on its own after the tuner line for an R820T ('No E4000 tuner found,
    aborting'), so the exit code says nothing: a `Found ... tuner` line is the success test.
    """
    try:
        res = run(['timeout', '3', 'rtl_test'] + list(device_args) + ['-t'], stdout=subprocess.PIPE,
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


def _describe(dev_dir):
    m, p, s = usb_strings(dev_dir)
    return '%s: %s %s, SN %s (%s)' % (os.path.basename(dev_dir), m or '?', p or '?', s or '?',
                                      model(m, p))


def run_doctor(sys_root='/sys', dev_root='/dev', conf_path=CONF_PATH, run=subprocess.run,
               access=os.access, uid=None, out=print, device=None, lister=librtlsdr_dongles):
    uid = os.getuid() if uid is None else uid
    device = (os.environ.get('RTLSDR_DEVICE', '') if device is None else device).strip()

    dongles = find_dongles(sys_root)
    if not dongles:
        return _fail(out, 10, 'no RTL2832U (USB 0bda:2838 or 0bda:2832) is visible on the USB bus',
                     'Plug the dongle in; with `docker run`, pass `--device /dev/bus/usb`; '
                     'a VM needs a USB controller with the dongle attached.')
    for d in dongles:
        out('doctor: dongle at %s' % _describe(d))
    if len(dongles) > 1:
        serials = [usb_strings(d)[2] for d in dongles]
        shared = sorted({s for s in serials if serials.count(s) > 1})
        if shared:
            out('doctor: WARNING: %d dongles share the serial %s, so a serial cannot tell them '
                'apart. %s' % (sum(serials.count(s) for s in shared), ', '.join(shared),
                               UNIQUE_SERIAL_FIX))
        digits = [s for s in serials if re.fullmatch(r'[0-9]+', s or '')]
        if digits:
            out('doctor: WARNING: the serial(s) %s are all digits; the rtl_* tools read a number as '
                'an index, so a serial with a letter in it is safer' % ', '.join(sorted(set(digits))))

    dev, lib_index, warning, error = choose(device, dongles, lister)
    if error:
        return _fail(out, 15, error,
                     'Set RTLSDR_DEVICE in .env to the serial of the dongle the station should use '
                     '(the list above). %s' % UNIQUE_SERIAL_FIX)
    if warning:
        out('doctor: WARNING: %s. Set RTLSDR_DEVICE to a serial.' % warning)
    if len(dongles) > 1 or device:
        out('doctor: the station uses %s%s' % (os.path.basename(dev),
                                               ' (RTLSDR_DEVICE=%s)' % device if device else ''))

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

    if lib_index is not None:
        device_args = ['-d', str(lib_index)]
    elif len(dongles) > 1:
        device_args = ['-d', device]  # a serial librtlsdr could not be asked about
    else:
        device_args = []
    tuner, output = probe_radio(run, device_args)
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
    if 'R828D' in tuner and usb_strings(dev)[:2] != V4:
        out('doctor: WARNING: an R828D tuner without the Blog V4 strings (RTLSDRBlog / Blog V4). '
            'If this is an RTL-SDR Blog V4, its EEPROM strings were changed and librtlsdr no '
            'longer treats it as one; restore them with: rtl_eeprom -m RTLSDRBlog -p "Blog V4", '
            'then re-plug.')

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


def resolve(device=None, lister=librtlsdr_dongles, err=None):
    """`--resolve`: print the librtlsdr index RTLSDR_DEVICE names; return 0, or 15 with the reason."""
    err = err or (lambda m: print(m, file=sys.stderr))
    device = (os.environ.get('RTLSDR_DEVICE', '') if device is None else device).strip()
    listed = lister()
    if listed is None:
        err('doctor --resolve: librtlsdr cannot be loaded')
        return 15
    index, warning, error = select_dongle(device, True, [s[2] for s in listed])
    if error:
        err('doctor --resolve: RTLSDR_DEVICE: %s' % error)
        return 15
    if warning:
        err('doctor --resolve: WARNING: %s' % warning)
    print(index)
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--resolve']:
        sys.exit(resolve())
    sys.exit(run_doctor())
