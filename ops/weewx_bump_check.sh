#!/bin/bash
# weewx_bump_check.sh -- does this weewx version work with our runtime modules? (DEC-0011)
#
# There is no dev receiver, so a weewx bump cannot be proven on the live signal. This is the
# substitute: a scratch venv at the version under test, a stock station, our baked modules copied
# in, and weewxd booted on the Simulator driver for ~40 s. Run it on the Dependabot branch (or with
# a version argument) BEFORE the image is built. Nothing leaves the machine: the Wunderground
# target is a closed local port and the credentials are throwaway strings.
#
# What it proves, and what it cannot:
#   proves   the pinned weewx installs; StdWunderground wires the rapidfire thread to its own
#            endpoint (asserted, not just "no error"); weewxd boots with our dewpoint service and
#            loop-JSON writer loaded; the loop feed is written; the driver imports the way the
#            engine imports it; no ERROR line appears beyond the expected dead-port upload failures.
#   cannot   the rtldavis Go binary, real RF frames, the WeatherLink fetch, the uploaders that
#            need live keys, or the amd64 image build. Those stay with soak_check.sh at cutover.
#
# Usage:  ops/weewx_bump_check.sh [weewx-version]      (default: the pin in requirements.txt)
#         BUMP_PYTHON=/path/to/python3.14 ops/weewx_bump_check.sh   (default: python3)
#         BUMP_KEEP=1 ...                                          keep the scratch dir
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="${BUMP_PYTHON:-python3}"
VER="${1:-$(sed -n 's/^weewx==\(.*\)$/\1/p' "$REPO/requirements.txt")}"
[ -n "$VER" ] || { echo "FATAL: no weewx version (pass one, or pin it in requirements.txt)" >&2; exit 2; }
BOOT_SECS="${BUMP_BOOT_SECS:-40}"

T="$(mktemp -d)"
[ "${BUMP_KEEP:-0}" = "1" ] && echo "scratch dir kept: $T" || trap 'rm -rf "$T"' EXIT
FAIL=0
step() { printf '%-58s' "$1"; }
ok()   { echo "ok"; }
bad()  { echo "FAIL${1:+ ($1)}"; FAIL=1; }

echo "weewx $VER under $("$PY" --version 2>&1)  (prod runs Python 3.14)"

step "install weewx==$VER into a scratch venv"
if "$PY" -m venv "$T/venv" && "$T/venv/bin/pip" install -q "weewx==$VER" >"$T/pip.out" 2>&1; then ok; else bad "see $T/pip.out"; exit 1; fi
VPY="$T/venv/bin/python"

step "StdWunderground endpoints (probe)"
if "$VPY" "$HERE/weewx_bump_probe.py" wu >"$T/wu.out" 2>&1; then ok; else bad; fi
sed 's/^/    /' "$T/wu.out"

step "weectl station create (stock config)"
if "$T/venv/bin/weectl" station create "$T/st" --no-prompt >"$T/create.out" 2>&1; then ok; else bad "see $T/create.out"; exit 1; fi

step "our modules into the station's user dir"
if cp "$REPO"/dewpoint_service.py "$REPO"/loop_json_writer.py "$REPO"/rtldavis.py "$T/st/bin/user/"; then ok; else bad; fi

mkdir -p "$T/feed"
step "point the station at the Simulator + dummy target"
if "$VPY" "$HERE/weewx_bump_probe.py" configure "$T/st/weewx.conf" "$T/feed"; then ok; else bad; fi
# stdout logging at INFO, no syslog (a scratch box has none), mirroring logging.additions' shape
cat >>"$T/st/weewx.conf" <<'EOF'
[Logging]
    version = 1
    disable_existing_loggers = False
    [[formatters]]
        [[[standard]]]
            format = %(asctime)s %(name)s %(levelname)s %(message)s
    [[handlers]]
        [[[console]]]
            level = INFO
            formatter = standard
            class = logging.StreamHandler
            stream = ext://sys.stdout
    [[root]]
        level = INFO
        handlers = console,
    [[loggers]]
        [[[weewx]]]
            level = INFO
            handlers = console,
            propagate = 0
        [[[user]]]
            level = INFO
            handlers = console,
            propagate = 0
EOF

step "boot weewxd on the Simulator for ${BOOT_SECS}s"
# `timeout` is absent on stock macOS; fall back to a background kill.
if command -v timeout >/dev/null 2>&1; then
  ( cd "$T/st" && timeout "$BOOT_SECS" "$T/venv/bin/weewxd" --config weewx.conf >"$T/run.out" 2>&1 ); RC=$?
else
  ( cd "$T/st" && "$T/venv/bin/weewxd" --config weewx.conf >"$T/run.out" 2>&1 & P=$!; sleep "$BOOT_SECS"; kill "$P" 2>/dev/null; wait "$P" 2>/dev/null ); RC=124
fi
if [ "$RC" = "124" ] || [ "$RC" = "143" ]; then ok; else bad "exited early, rc=$RC"; sed 's/^/    /' <(tail -8 "$T/run.out"); fi

step "both Wunderground threads announced"
if grep -q 'Wunderground-PWS: Data for station' "$T/run.out" && grep -q 'Wunderground-RF: Data for station' "$T/run.out"; then ok; else bad; fi

step "no ERROR beyond the dead-port upload failures"
UNEXPECTED="$(grep -E ' (ERROR|CRITICAL) ' "$T/run.out" | grep -v -E 'Wunderground-(RF|PWS): Failed to publish record')"
if [ -z "$UNEXPECTED" ]; then ok; else bad; echo "$UNEXPECTED" | sed 's/^/    /'; fi

step "loop feed written by loop_json_writer"
if [ -s "$T/feed/loop-data.txt" ]; then ok; else bad "no $T/feed/loop-data.txt"; fi

step "driver imports as the engine imports it"
if "$VPY" -c "
import sys; sys.path.insert(0, '$T/st/bin')
import importlib; m = importlib.import_module('user.rtldavis'); assert callable(m.loader)" 2>"$T/imp.out"; then ok; else bad "$(tail -1 "$T/imp.out")"; fi

echo
[ "$FAIL" = "0" ] && echo "PASS: weewx $VER" || echo "FAIL: weewx $VER"
exit "$FAIL"
