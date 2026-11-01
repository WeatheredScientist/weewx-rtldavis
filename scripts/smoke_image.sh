#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Smoke-test a built weewx-rtldavis image on the architecture it was built for (DEC-0214).
#
#   scripts/smoke_image.sh <image> <expected `uname -m`> <requirements.txt>
#
# Shared by .github/workflows/image.yml (proves every PR) and image-publish.yml (checks the arm64
# image before it is pushed, DEC-0215). Runs containers, so it is for CI runners, not for marvin
# or a workstation. Exits non-zero on the first failed check.
set -euo pipefail

[ $# -eq 3 ] || { echo "usage: $0 <image> <uname -m> <requirements.txt>" >&2; exit 2; }
image="$1"; want_arch="$2"; reqs="$3"

echo "== the image runs on this architecture"
got_arch="$(docker run --rm "$image" uname -m)"
[ "$got_arch" = "$want_arch" ] || { echo "uname -m is $got_arch, want $want_arch" >&2; exit 1; }

echo "== the rtldavis binary links"
ldd_out="$(docker run --rm "$image" ldd /usr/local/bin/rtldavis)"
echo "$ldd_out"
if grep -q "not found" <<<"$ldd_out"; then echo "rtldavis has an unresolved library" >&2; exit 1; fi

echo "== WeeWX is the pinned version"
want_weewx="$(sed -n 's/^weewx==//p' "$reqs")"
[ -n "$want_weewx" ] || { echo "no weewx== pin in $reqs" >&2; exit 1; }
version_out="$(docker run --rm "$image" /opt/weewx-venv/bin/weectl --version)"
echo "$version_out"
grep -qF "$want_weewx" <<<"$version_out" || { echo "weectl is not $want_weewx" >&2; exit 1; }

echo "== the patched driver imports"
docker run --rm "$image" /opt/weewx-venv/bin/python3 -c \
  "import user.rtldavis as d; print('driver', d.DRIVER_VERSION)"

echo "== the uploader the baked config names imports (weewxd cannot start without it)"
docker run --rm "$image" /opt/weewx-venv/bin/python3 -c \
  "import user.influx as i; print('influx', i.VERSION)"

echo "== the OWM and Windy uploaders import, with their shared base from the user package"
docker run --rm "$image" /opt/weewx-venv/bin/python3 -c \
  "import user.owm as o, user.windy as w; b = o.OWMThread.__mro__[1].__module__; print('owm', b, 'windy', w.WindyThread.__mro__[1].__module__); assert b == 'user.rest_site'"

echo "== an empty data mount is seeded once, and a second start leaves it alone (DEC-0225)"
seed_dir="$(mktemp -d)"
trap 'rm -rf "$seed_dir"' EXIT
run_seed() {
  docker run --rm --user "$(id -u):$(id -g)" -v "$seed_dir:/opt/weewx-data" \
    -e WEEWX_LATITUDE=40.7 -e WEEWX_LONGITUDE=-74.0 -e RTLDAVIS_BAND=EU \
    "$image" /opt/weewx-venv/bin/python3 /opt/seed_config.py
}
run_seed
[ -s "$seed_dir/weewx.conf" ] || { echo "the first start wrote no weewx.conf" >&2; exit 1; }
grep -Eq '^[[:space:]]*transceiver_frequency = EU$' "$seed_dir/weewx.conf" || { echo "RTLDAVIS_BAND did not land in weewx.conf" >&2; exit 1; }
grep -Eq '^[[:space:]]*latitude = 40.7$' "$seed_dir/weewx.conf" || { echo "WEEWX_LATITUDE did not land in weewx.conf" >&2; exit 1; }
test -d "$seed_dir/bin/user" || { echo "the starter tree is incomplete" >&2; exit 1; }
before="$(sha256sum "$seed_dir/weewx.conf")"
run_seed
[ "$before" = "$(sha256sum "$seed_dir/weewx.conf")" ] || { echo "a second start changed weewx.conf" >&2; exit 1; }
bad_dir="$(mktemp -d)"
if docker run --rm --user "$(id -u):$(id -g)" -v "$bad_dir:/opt/weewx-data" -e RTLDAVIS_BAND=AU \
    "$image" /opt/weewx-venv/bin/python3 /opt/seed_config.py; then
  echo "a bad RTLDAVIS_BAND did not stop the start" >&2; exit 1
fi
[ -z "$(ls -A "$bad_dir")" ] || { echo "a bad value left files behind" >&2; exit 1; }
rm -rf "$bad_dir"

echo "== WEEWX_DRIVER=simulator seeds a config that runs weewxd with no radio (DEC-0225)"
sim_dir="$(mktemp -d)"
sim_log="$(mktemp -d)"
trap 'rm -rf "$seed_dir" "$sim_dir" "$sim_log"' EXIT
docker run --rm --user "$(id -u):$(id -g)" -v "$sim_dir:/opt/weewx-data" \
  -e WEEWX_DRIVER=simulator -e TZ=UTC \
  "$image" /opt/weewx-venv/bin/python3 /opt/seed_config.py
grep -Eq '^[[:space:]]*station_type = Simulator$' "$sim_dir/weewx.conf" || { echo "WEEWX_DRIVER=simulator did not land in weewx.conf" >&2; exit 1; }
timeout 40 docker run --rm --user "$(id -u):$(id -g)" -v "$sim_dir:/opt/weewx-data" \
  -v "$sim_log:/var/log/weewx" -e TZ=UTC \
  "$image" /opt/weewx-venv/bin/weewxd /opt/weewx-data/weewx.conf || true
[ -s "$sim_log/weewx.log" ] || { echo "weewxd wrote no weewx.log" >&2; exit 1; }
grep -qi 'simulator' "$sim_log/weewx.log" || { echo "the Simulator driver did not load" >&2; tail -n 40 "$sim_log/weewx.log" >&2; exit 1; }
if grep -q 'Traceback' "$sim_log/weewx.log"; then
  echo "traceback in weewx.log under the Simulator" >&2; tail -n 60 "$sim_log/weewx.log" >&2; exit 1
fi
[ -s "$sim_dir/archive/weewx.sdb" ] || { echo "the Simulator run created no archive/weewx.sdb" >&2; exit 1; }
