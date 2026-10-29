#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Join marvin's amd64 image and CI's arm64 image into Docker Hub's multi-arch :vX.Y.Z (DEC-0215).
#
#   scripts/join_multiarch.sh vX.Y.Z [--apply] [--expect-amd64 sha256:...] [--amd64-only]
#                                    [--replace] [--seed-amd64]
#
# Sources: docker.io/weatheredscientist/weewx-rtldavis:vX.Y.Z-amd64 (pushed from marvin with
# `marvinctl push`) and ghcr.io/weatheredscientist/weewx-rtldavis:vX.Y.Z-arm64 (pushed by
# .github/workflows/image-publish.yml on the release tag).
#
# Dry run by default: checks both halves and prints the index it would create. --apply pushes it,
# then re-reads Hub to confirm the result holds exactly the checked manifests. Run it on the
# laptop, which holds the Docker Hub login; --apply publishes, so it runs only after the owner's go
# in chat. It never touches :latest (the owner moves that after prod proof, DEC-0078).
#
#   --expect-amd64 D  Hub's :vX.Y.Z-amd64 must have index digest D: prod's image ID on marvin
#                     (`marvinctl --tenant weewx inspect weewx-rtldavis-v2`, its Image field).
#                     The containerd store's image ID is an index digest, so compare it to the
#                     index digest, never to a config digest (CONSTANTS, Docker Hub row).
#   --amd64-only      no arm64 this release: :vX.Y.Z becomes a carbon copy of :vX.Y.Z-amd64,
#                     so its index digest equals prod's.
#   --replace         allow overwriting an existing :vX.Y.Z (the v2.0.20 backfill only).
#   --seed-amd64      backfill: first create :vX.Y.Z-amd64 as a carbon copy of the existing
#                     amd64-only :vX.Y.Z (same index digest). Needs --replace.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
HUB=docker.io/weatheredscientist/weewx-rtldavis
GHCR=ghcr.io/weatheredscientist/weewx-rtldavis

die() { echo "join_multiarch: $*" >&2; exit 1; }
usage() { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

[ $# -ge 1 ] || usage
version="$1"; shift
grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' <<<"$version" || die "not a release tag: $version"
apply=0; expect=""; amd64_only=0; replace=0; seed=0
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) apply=1 ;;
    --expect-amd64) [ $# -ge 2 ] || usage; expect="$2"; shift ;;
    --amd64-only) amd64_only=1 ;;
    --replace) replace=1 ;;
    --seed-amd64) seed=1 ;;
    *) usage ;;
  esac
  shift
done

summ() {
  local out
  out="$(docker buildx imagetools inspect "$1" --format '{{json .}}' 2>/dev/null)" || return 1
  python3 -I "$here/oci_platforms.py" <<<"$out"
}
exists() { docker buildx imagetools inspect "$1" --raw >/dev/null 2>&1; }
# jget JSON a.b.c -> the value at that path, or empty. Platform keys hold a slash, never a dot.
jget() {
  python3 -I -c '
import json, sys
v = json.loads(sys.argv[1])
for k in sys.argv[2].split("."):
    v = v.get(k) if isinstance(v, dict) else None
print("" if v is None else v)' "$1" "$2"
}
platforms() { python3 -I -c 'import json, sys; print(",".join(sorted(json.loads(sys.argv[1])["platforms"])))' "$1"; }
run() { if [ "$apply" = 1 ]; then "$@"; else echo "dry run, would run: $*"; fi; }

rev="$(git rev-parse --verify --quiet "refs/tags/${version}^{commit}")" \
  || die "no local tag $version (git fetch --tags)"
echo "release $version = commit $rev"

# --- amd64: marvin's image -------------------------------------------------------------------
if [ "$seed" = 1 ]; then
  [ "$replace" = 1 ] || die "--seed-amd64 rewrites :$version afterwards, so it needs --replace"
  exists "$HUB:$version-amd64" && die "$HUB:$version-amd64 already exists; drop --seed-amd64"
  amd="$(summ "$HUB:$version")"
  [ "$(platforms "$amd")" = "linux/amd64" ] \
    || die ":$version is not amd64-only ($(platforms "$amd")); nothing to seed from"
  seed_src="$HUB@$(jget "$amd" digest)"
  echo "seed: $HUB:$version-amd64 <- $seed_src (carbon copy)"
  run docker buildx imagetools create -t "$HUB:$version-amd64" "$seed_src"
  if [ "$apply" = 1 ]; then
    [ "$(jget "$(summ "$HUB:$version-amd64")" digest)" = "$(jget "$amd" digest)" ] \
      || die "seeded :$version-amd64 does not carry :$version's index digest"
  fi
else
  amd="$(summ "$HUB:$version-amd64")" || die "cannot read $HUB:$version-amd64 (marvinctl push it first)"
fi
[ "$(platforms "$amd")" = "linux/amd64" ] || die "amd64 half has platforms $(platforms "$amd")"
amd_index="$(jget "$amd" digest)"
amd_manifest="$(jget "$amd" platforms.linux/amd64.digest)"
if [ -n "$expect" ] && [ "$expect" != "$amd_index" ]; then
  die "amd64 index digest is $amd_index, prod's is $expect"
fi
echo "amd64: index $amd_index, manifest $amd_manifest${expect:+ (= prod)}"
sources=("$HUB@$amd_index")
want_platforms="linux/amd64"

# --- arm64: CI's image -----------------------------------------------------------------------
if [ "$amd64_only" = 0 ]; then
  arm="$(summ "$GHCR:$version-arm64")" || die "cannot read $GHCR:$version-arm64 (did image-publish run?)"
  [ "$(platforms "$arm")" = "linux/arm64" ] || die "arm64 half has platforms $(platforms "$arm")"
  arm_rev="$(jget "$arm" platforms.linux/arm64.revision)"
  [ "$arm_rev" = "$rev" ] || die "arm64 image was built from ${arm_rev:-an unlabeled tree}, not $rev"
  arm_manifest="$(jget "$arm" platforms.linux/arm64.digest)"
  echo "arm64: manifest $arm_manifest, built from $arm_rev"
  sources+=("$GHCR@$(jget "$arm" digest)")
  want_platforms="linux/amd64,linux/arm64"
fi

# --- the joined tag --------------------------------------------------------------------------
if exists "$HUB:$version"; then
  cur="$(summ "$HUB:$version")"
  [ "$replace" = 1 ] || die ":$version already exists ($(jget "$cur" digest), $(platforms "$cur")); pass --replace only for a backfill"
  echo "replacing :$version (was $(jget "$cur" digest), $(platforms "$cur"))"
fi
echo "index to create:"
docker buildx imagetools create --dry-run -t "$HUB:$version" "${sources[@]}"
run docker buildx imagetools create -t "$HUB:$version" "${sources[@]}"

[ "$apply" = 1 ] || { echo "dry run only; re-run with --apply after the go."; exit 0; }
new="$(summ "$HUB:$version")"
[ "$(platforms "$new")" = "$want_platforms" ] || die "Hub :$version has platforms $(platforms "$new")"
[ "$(jget "$new" platforms.linux/amd64.digest)" = "$amd_manifest" ] \
  || die "Hub :$version's amd64 manifest is not marvin's"
if [ "$amd64_only" = 0 ]; then
  [ "$(jget "$new" platforms.linux/arm64.digest)" = "$arm_manifest" ] \
    || die "Hub :$version's arm64 manifest is not CI's"
else
  [ "$(jget "$new" digest)" = "$amd_index" ] || die "carbon copy changed the index digest"
fi
echo "published $HUB:$version = $(jget "$new" digest) [$want_platforms]"
