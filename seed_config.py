# SPDX-License-Identifier: GPL-3.0-or-later
"""First-start config seeding for the image (DEC-0225, v2.2.0).

Run by entrypoint.sh before weewxd, as the container's own user. When the mounted data
directory has no weewx.conf, copy the image's pristine tree in (never overwriting a file) and
apply the first-run values from the environment. When weewx.conf exists this does nothing at
all, so a running install, prod included, is untouched. After the first start weewx.conf is
the only truth: the variables are read once and a later change to them has no effect.

    python3 seed_config.py [DATA_DIR [DIST_DIR]]      (defaults: /opt/weewx-data /opt/weewx-dist)

Exit 0: nothing to do, or seeded. Exit 1: a value is invalid or the directory is not writable;
the reason is printed and weewxd is not started, because a half-configured station is worse than
a stopped one.
"""
import os
import re
import shutil
import sys

ENV_VARS = ('WEEWX_DRIVER', 'WEEWX_LOCATION', 'WEEWX_LATITUDE', 'WEEWX_LONGITUDE', 'WEEWX_ALTITUDE',
            'RTLDAVIS_BAND', 'RTLDAVIS_ISS_CHANNEL', 'RTLDAVIS_RAIN_BUCKET')

_ALTITUDE = re.compile(r'^\s*(-?\d+(?:\.\d+)?)\s*,\s*(foot|meter)\s*$')


def parse_env(env):
    """Return ({conf key: value}, [errors]) for the first-run variables that are set.

    A variable that is unset or empty is skipped. Values are checked here, before anything is
    written, so a typo can never leave a half-edited config behind.
    """
    values, errors = {}, []

    def get(name):
        raw = env.get(name, '').strip()
        return raw or None

    driver = get('WEEWX_DRIVER')
    if driver is not None:
        if driver.lower() not in ('simulator', 'rtldavis'):
            errors.append('WEEWX_DRIVER must be simulator or rtldavis: %r' % driver)
        elif driver.lower() == 'simulator':
            values[('Station', 'station_type')] = 'Simulator'

    loc = get('WEEWX_LOCATION')
    if loc is not None:
        if '\n' in loc or '\r' in loc:
            errors.append('WEEWX_LOCATION must be a single line')
        else:
            values[('Station', 'location')] = loc

    for name, key, low, high in (('WEEWX_LATITUDE', 'latitude', -90.0, 90.0),
                                 ('WEEWX_LONGITUDE', 'longitude', -180.0, 180.0)):
        raw = get(name)
        if raw is None:
            continue
        try:
            num = float(raw)
        except ValueError:
            errors.append('%s is not a number: %r' % (name, raw))
            continue
        if not low <= num <= high:
            errors.append('%s must be between %g and %g: %r' % (name, low, high, raw))
        else:
            values[('Station', key)] = raw

    alt = get('WEEWX_ALTITUDE')
    if alt is not None:
        m = _ALTITUDE.match(alt)
        if not m:
            errors.append('WEEWX_ALTITUDE must look like 120,foot or 36,meter: %r' % alt)
        else:
            values[('Station', 'altitude')] = [m.group(1), m.group(2)]

    band = get('RTLDAVIS_BAND')
    if band is not None:
        if band.upper() not in ('US', 'EU', 'NZ'):
            errors.append('RTLDAVIS_BAND must be US, EU or NZ: %r' % band)
        else:
            values[('Rtldavis', 'transceiver_frequency')] = band.upper()

    for name, key, allowed in (('RTLDAVIS_ISS_CHANNEL', 'iss_channel', range(1, 9)),
                               ('RTLDAVIS_RAIN_BUCKET', 'rain_bucket_type', (0, 1))):
        raw = get(name)
        if raw is None:
            continue
        try:
            num = int(raw)
        except ValueError:
            errors.append('%s is not a whole number: %r' % (name, raw))
            continue
        if num not in allowed:
            errors.append('%s must be one of %s: %r' % (name, list(allowed), raw))
        else:
            values[('Rtldavis', key)] = str(num)

    return values, errors


def copy_missing(src, dst):
    """Copy the tree at src into dst without replacing any file that already exists."""
    for root, _dirs, files in os.walk(src):
        target = os.path.join(dst, os.path.relpath(root, src))
        os.makedirs(target, exist_ok=True)
        for name in files:
            out = os.path.join(target, name)
            if not os.path.lexists(out):
                shutil.copy2(os.path.join(root, name), out)


def apply_values(conf_path, values):
    """Write values into the config, keeping its comments, and return the keys applied."""
    import configobj  # the venv has it (weewx depends on it); the system python may not

    conf = configobj.ConfigObj(conf_path, encoding='utf-8', file_error=True)
    for (section, key), value in values.items():
        if section not in conf or key not in conf[section]:
            raise KeyError('[%s] %s is not in the seeded weewx.conf' % (section, key))
        conf[section][key] = value
    if values.get(('Station', 'station_type')) == 'Simulator' \
            and 'driver' not in conf.get('Simulator', {}):
        raise KeyError('[Simulator] driver is not in the seeded weewx.conf')
    conf.write()
    return sorted('[%s] %s' % sk for sk in values)


def seed(data_dir, dist_dir, env, out=print):
    conf_path = os.path.join(data_dir, 'weewx.conf')
    if os.path.exists(conf_path):
        return 0

    values, errors = parse_env(env)
    if errors:
        for e in errors:
            out('seed: ERROR: %s' % e)
        out('seed: nothing was written. Fix the value in .env and start again.')
        return 1

    if not os.path.isdir(dist_dir):
        out('seed: ERROR: %s is missing from this image' % dist_dir)
        return 1
    os.makedirs(data_dir, exist_ok=True)
    if not os.access(data_dir, os.W_OK | os.X_OK):
        out('seed: ERROR: %s is not writable by uid %d. Give that user the folder, e.g. '
            'sudo chown -R %d %s' % (data_dir, os.getuid(), os.getuid(), '<your weewx-data folder>'))
        return 1

    copy_missing(dist_dir, data_dir)
    os.chmod(conf_path, 0o600)
    out('seed: %s was empty; wrote a starter weewx.conf and its folders' % data_dir)
    if values:
        try:
            applied = apply_values(conf_path, values)
        except (KeyError, OSError) as e:
            os.remove(conf_path)
            out('seed: ERROR: %s; removed the half-seeded config' % e)
            return 1
        out('seed: applied from the environment, once: %s' % ', '.join(applied))
        out('seed: from now on weewx.conf is the only truth; edit it, not the environment')
        if values.get(('Station', 'station_type')) == 'Simulator':
            out('seed: driver is the WeeWX Simulator (made-up weather); delete weewx.conf and '
                'unset WEEWX_DRIVER to switch to the radio')
    if not any(k[1] in ('latitude', 'longitude') for k in values):
        out('seed: WARNING: no WEEWX_LATITUDE/WEEWX_LONGITUDE given; set [Station] in weewx.conf '
            'before trusting sunrise, solar or ET figures')
    return 0


def main(argv):
    data_dir = argv[1] if len(argv) > 1 else '/opt/weewx-data'
    dist_dir = argv[2] if len(argv) > 2 else '/opt/weewx-dist'
    return seed(data_dir, dist_dir, os.environ)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
