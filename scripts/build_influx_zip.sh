#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Build dist/weewx-influx-VERSION.zip (DEC-0219). One root directory, as
# `weectl extension install` requires. Fails if the VERSION in influx.py,
# extensions/influx/install.py and (when given) the release tag disagree.
# Usage: scripts/build_influx_zip.sh [influx-vVERSION]
set -euo pipefail
cd "$(dirname "$0")/.."

mod_ver=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' influx.py)
install_ver=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' extensions/influx/install.py)
[ -n "$mod_ver" ] || { echo "no VERSION in influx.py" >&2; exit 1; }
if [ "$mod_ver" != "$install_ver" ]; then
  echo "version mismatch: influx.py=$mod_ver install.py=$install_ver" >&2
  exit 1
fi
if [ $# -ge 1 ]; then
  tag_ver=${1#influx-v}
  if [ "$tag_ver" != "$mod_ver" ]; then
    echo "version mismatch: tag=$1 module=$mod_ver" >&2
    exit 1
  fi
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
root="$stage/weewx-influx"
mkdir -p "$root/bin/user" dist
cp extensions/influx/install.py extensions/influx/README.md "$root/"
cp influx.py "$root/bin/user/"
out="dist/weewx-influx-$mod_ver.zip"
rm -f "$out"
(cd "$stage" && zip -qr "$OLDPWD/$out" weewx-influx)
echo "$out"
