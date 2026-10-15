#!/usr/bin/env bash
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
print('ok:', d['writer'])
PY
if grep -qi 'traceback' "$work/weewxd.out"; then
  echo "FAIL: traceback in weewxd output" >&2; cat "$work/weewxd.out" >&2; exit 1
fi
