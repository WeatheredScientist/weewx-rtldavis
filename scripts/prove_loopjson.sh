#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Install a built weewx-loopjson zip into a fresh WeeWX and prove it works with
# the Simulator driver, i.e. without the rtldavis driver (DEC-0211 item 6).
# Needs `weectl` and `weewxd` on PATH (pip install weewx==5.5.2).
# Usage: scripts/prove_loopjson.sh dist/weewx-loopjson-X.Y.Z.zip
set -euo pipefail
zip=$(realpath "$1")
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
st="$work/station"
conf="$st/weewx.conf"

weectl station create "$st" --no-prompt --driver=weewx.drivers.simulator >/dev/null
weectl extension install "$zip" --config "$conf" --yes >/dev/null

# Last in process_services: it must see StdQC's and StdWXCalculate's output.
last=$(sed -n 's/^ *process_services *= *//p' "$conf" | awk -F', *' '{print $NF}')
[ "$last" = "user.loop_json_writer.LoopJsonWriter" ] ||
  { echo "FAIL: last process_services entry is '$last'" >&2; exit 1; }
grep -q '^\[LoopJsonWriter\]' "$conf" || { echo "FAIL: no [LoopJsonWriter] stanza" >&2; exit 1; }

# DEC-0220: opt in to one state (inTemp) and one per-packet delta (rain). The Simulator
# puts rain: 0 in every packet and the writer keeps any non-None value, so an unrefused
# rain would show as rain_in: 0. Its absence below is the refusal, not missing data.
python3 - "$conf" <<'PY'
import sys
path = sys.argv[1]
lines = open(path).read().split('\n')
at = lines.index('[LoopJsonWriter]') + 1
lines.insert(at, '    extra_fields = inTemp, rain')
open(path, 'w').write('\n'.join(lines))
PY

# A real run: the Simulator emits a LOOP packet every few seconds.
timeout 20 weewxd --config "$conf" >"$work/weewxd.out" 2>&1 || true
feed="$st/feed/loop-data.txt"
[ -s "$feed" ] || { echo "FAIL: $feed missing or empty" >&2; cat "$work/weewxd.out" >&2; exit 1; }
python3 - "$feed" "$st/feed/current.json" <<'PY'
import json, re, sys
for path in sys.argv[1:]:
    d = json.load(open(path))
    assert d.get('dateTime'), path + ': no dateTime'
    assert re.fullmatch(r'loop_json_writer/\d+\.\d+\.\d+', d.get('writer', '')), path + ': bad writer'
    assert 'inTemp_F' in d, path + ': the opted-in state inTemp_F is missing'
    assert 'rain_in' not in d and 'rain' not in d, path + ': a per-packet delta was written'
    assert 'outTemp_F' in d, path + ': the standard fields are gone'
feed = json.load(open(sys.argv[1]))
assert 1 <= feed.get('loop_interval_s', 0) <= 3600, 'loop_interval_s missing or out of range'
print('ok:', d['writer'], 'loop_interval_s', feed['loop_interval_s'])
PY
if grep -qi 'traceback' "$work/weewxd.out"; then
  echo "FAIL: traceback in weewxd output" >&2; cat "$work/weewxd.out" >&2; exit 1
fi
