#!/usr/bin/env bash
# Build dist/weewx-loopjson-X.Y.Z.zip (DEC-0211). One root directory, as
# `weectl extension install` requires. Fails if the version in
# loop_json_writer.py, extensions/loopjson/install.py and (when given) the
# release tag disagree.
# Usage: scripts/build_loopjson_zip.sh [loopjson-vX.Y.Z]
set -euo pipefail
cd "$(dirname "$0")/.."

writer_ver=$(sed -n "s/^__version__ = '\(.*\)'/\1/p" loop_json_writer.py)
install_ver=$(sed -n "s/^VERSION = '\(.*\)'/\1/p" extensions/loopjson/install.py)
[ -n "$writer_ver" ] || { echo "no __version__ in loop_json_writer.py" >&2; exit 1; }
if [ "$writer_ver" != "$install_ver" ]; then
  echo "version mismatch: loop_json_writer.py=$writer_ver install.py=$install_ver" >&2
  exit 1
fi
if [ $# -ge 1 ]; then
  tag_ver=${1#loopjson-v}
  if [ "$tag_ver" != "$writer_ver" ]; then
    echo "version mismatch: tag=$1 module=$writer_ver" >&2
    exit 1
  fi
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
root="$stage/weewx-loopjson"
mkdir -p "$root/bin/user" dist
cp extensions/loopjson/install.py extensions/loopjson/README.md "$root/"
cp loop_json_writer.py "$root/bin/user/"
out="dist/weewx-loopjson-$writer_ver.zip"
rm -f "$out"
(cd "$stage" && zip -qr "$OLDPWD/$out" weewx-loopjson)
echo "$out"
