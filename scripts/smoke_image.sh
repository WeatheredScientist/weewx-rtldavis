#!/usr/bin/env bash
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
