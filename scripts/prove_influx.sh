#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Install a built weewx-influx zip into a fresh WeeWX and prove it works with the
# Simulator driver, i.e. without the rtldavis driver (DEC-0219).
# Needs `weectl` and `weewxd` on PATH (pip install weewx==5.5.2).
# Usage: scripts/prove_influx.sh dist/weewx-influx-VERSION.zip
set -euo pipefail
zip=$(realpath "$1")
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
st="$work/station"
conf="$st/weewx.conf"

weectl station create "$st" --no-prompt --driver=weewx.drivers.simulator >/dev/null
weectl extension install "$zip" --config "$conf" --yes >/dev/null

grep -q 'user.influx.Influx' "$conf" || { echo "FAIL: user.influx.Influx not in restful_services" >&2; exit 1; }
grep -q '^ *\[\[Influx\]\]' "$conf" || { echo "FAIL: no [[Influx]] stanza" >&2; exit 1; }

# Point it at a closed local port, so nothing is uploaded.
sed -i.bak \
  -e 's|^\( *org *=\).*|\1 proof|' -e 's|^\( *bucket *=\).*|\1 proof|' \
  -e 's|^\( *token *=\).*|\1 proof|' -e 's|^\( *server_url *=\).*|\1 http://127.0.0.1:9|' "$conf"
want=$(unzip -p "$zip" weewx-influx/bin/user/influx.py | sed -n 's/^VERSION = "\(.*\)"/\1/p')
# Build the service from the installed config the way the engine would. weewxd
# logs to syslog, which a CI runner does not keep, so drive the service directly.
python3 - "$conf" "$st/bin" "$want" "$st" <<'PY'
import logging, sys
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
import configobj
sys.path.insert(0, sys.argv[2])
import user.influx as influx

assert influx.VERSION == sys.argv[3], 'installed %s, expected %s' % (influx.VERSION, sys.argv[3])
cfg = configobj.ConfigObj(sys.argv[1])
cfg['WEEWX_ROOT'] = sys.argv[4]  # the engine sets this before services load


class Engine:
    def bind(self, *args):
        pass


svc = influx.Influx(Engine(), cfg)
assert getattr(svc, 'archive_thread', None) is not None, 'no archive thread: service did not configure'
print('ok: influx', influx.VERSION)
PY
