#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Prove DEC-0237 on a built image: a decoder that keeps exiting makes the container exit.
#
#   scripts/exit_after_image.sh <image>
#
# A stub stands in for the Go decoder and exits at once, which is what a lost dongle looks like
# to the driver ("rtldavis process is not running", every retry). Two containers run side by side
# from the same seeded config:
#   - default (RTLDAVIS_EXIT_AFTER unset = 3): the container must EXIT NON-ZERO within a few
#     minutes of weewxd's 60 s retry, with the driver's "exited 3 times in a row" line in its log;
#   - RTLDAVIS_EXIT_AFTER=0: the container must still be RUNNING after five minutes.
# Runs containers, so it is for CI runners (image.yml), not marvin or a workstation.
# `docker kill`, never `docker stop` (DEC-0008).
set -euo pipefail

[ $# -eq 1 ] || { echo "usage: $0 <image>" >&2; exit 2; }
image="$1"
tag="eat$$"
work="$(mktemp -d)"
cleanup() {
  docker kill "$tag-on" "$tag-off" >/dev/null 2>&1 || true
  docker rm -f "$tag-on" "$tag-off" >/dev/null 2>&1 || true
  rm -rf "$work" || true
}
trap cleanup EXIT

mkdir -p "$work/stub" "$work/on" "$work/off" "$work/logs-on" "$work/logs-off"
uid="$(id -u):$(id -g)"   # as prod does: a non-root user, so the host can edit and remove what the container wrote
printf '#!/bin/sh\necho "stub decoder: exiting at once" >&2\nexit 1\n' > "$work/stub/decoder.sh"
chmod 0755 "$work/stub" "$work/stub/decoder.sh"

echo "== seed one starter config and point its decoder at the stub"
docker run --rm --user "$uid" -v "$work/on:/opt/weewx-data" "$image" /opt/weewx-venv/bin/python3 /opt/seed_config.py
[ -s "$work/on/weewx.conf" ] || { echo "the seed wrote no weewx.conf" >&2; exit 1; }
sed -i.bak 's|^\([[:space:]]*cmd = \).*|\1/stub/decoder.sh|' "$work/on/weewx.conf"
grep -Eq '^[[:space:]]*cmd = /stub/decoder.sh$' "$work/on/weewx.conf" || { echo "the stub did not land in weewx.conf" >&2; exit 1; }
cp -R "$work/on/." "$work/off/"

echo "== start both containers"
docker run -d --name "$tag-on" --user "$uid" -v "$work/on:/opt/weewx-data" -v "$work/logs-on:/var/log/weewx" -v "$work/stub:/stub:ro" "$image" >/dev/null
docker run -d --name "$tag-off" --user "$uid" -e RTLDAVIS_EXIT_AFTER=0 -v "$work/off:/opt/weewx-data" -v "$work/logs-off:/var/log/weewx" -v "$work/stub:/stub:ro" "$image" >/dev/null
started=$SECONDS

echo "== the default container exits"
deadline=$((started + 420))
while [ "$(docker inspect -f '{{.State.Status}}' "$tag-on")" = "running" ]; do
  [ $SECONDS -lt $deadline ] || { echo "the default container was still running after 420 s" >&2; docker logs --tail 40 "$tag-on" >&2 || true; exit 1; }
  sleep 5
done
code="$(docker inspect -f '{{.State.ExitCode}}' "$tag-on")"
echo "exited $code after $((SECONDS - started)) s"
[ "$code" -ne 0 ] || { echo "the default container exited 0, want non-zero" >&2; exit 1; }
cp "$work/logs-on/weewx.log" "$work/on.log" 2>/dev/null || docker logs --tail 500 "$tag-on" > "$work/on.log" 2>&1
grep -q 'exited 3 times in a row' "$work/on.log" || { echo "no 'exited 3 times in a row' line in the log" >&2; tail -40 "$work/on.log" >&2; exit 1; }

echo "== RTLDAVIS_EXIT_AFTER=0 keeps running"
while [ $((SECONDS - started)) -lt 300 ]; do
  [ "$(docker inspect -f '{{.State.Status}}' "$tag-off")" = "running" ] || { echo "the off container stopped before five minutes" >&2; docker logs --tail 40 "$tag-off" >&2 || true; exit 1; }
  sleep 5
done
[ "$(docker inspect -f '{{.State.Status}}' "$tag-off")" = "running" ] || { echo "the off container stopped" >&2; exit 1; }
cp "$work/logs-off/weewx.log" "$work/off.log" 2>/dev/null || docker logs --tail 500 "$tag-off" > "$work/off.log" 2>&1
if grep -q 'exited [0-9]* times in a row' "$work/off.log"; then echo "the off container logged the fatal line" >&2; exit 1; fi
n="$(grep -c 'rtldavis process is not running' "$work/off.log" || true)"
[ "$n" -ge 3 ] || { echo "the stub was exited from only $n times in five minutes: the test proved nothing" >&2; tail -40 "$work/off.log" >&2; exit 1; }
echo "ok: default exited non-zero, off ran five minutes through $n decoder exits"
