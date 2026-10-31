#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Summarize one image reference for scripts/join_multiarch.sh (DEC-0215).

Reads `docker buildx imagetools inspect <ref> --format '{{json .}}'` on stdin and prints JSON:

    {"digest": "<the reference's own digest>",
     "platforms": {"linux/amd64": {"digest": "<platform manifest digest>",
                                   "revision": "<org.opencontainers.image.revision or null>"}}}

BuildKit attestation manifests (platform unknown/unknown) are left out. Platform keys drop the
variant (`linux/arm64/v8` -> `linux/arm64`; imagetools itself keys arm64 configs without it), except
for 32-bit `arm`, where v6 and v7 are different images.
"""
import json
import sys

REVISION = "org.opencontainers.image.revision"
INDEX_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
)


def _key(os_name, arch, variant=None):
    if arch == "arm" and variant:
        return "%s/%s/%s" % (os_name, arch, variant)
    return "%s/%s" % (os_name, arch)


def _revision(config):
    if not isinstance(config, dict):
        return None
    labels = (config.get("config") or {}).get("Labels") or {}
    return labels.get(REVISION)


def summarize(inspect):
    manifest = inspect["manifest"]
    image = inspect.get("image")
    platforms = {}
    if manifest.get("mediaType") in INDEX_TYPES:
        entries = [m for m in manifest.get("manifests", [])
                   if (m.get("platform") or {}).get("os") not in (None, "unknown")]
        # One platform: imagetools gives a single config. Several: a map keyed "os/arch[/variant]".
        if len(entries) == 1 and isinstance(image, dict) and "architecture" in image:
            configs = {_key(image.get("os"), image.get("architecture"), image.get("variant")): image}
        else:
            configs = {}
            for k, v in (image or {}).items():
                parts = k.split("/") + ["", ""]
                configs[_key(parts[0], parts[1], parts[2])] = v
        for m in entries:
            p = m["platform"]
            key = _key(p.get("os"), p.get("architecture"), p.get("variant"))
            platforms[key] = {"digest": m["digest"], "revision": _revision(configs.get(key))}
    else:
        # A single image manifest (no index): the platform comes from its config.
        key = _key(image.get("os"), image.get("architecture"), image.get("variant"))
        platforms[key] = {"digest": manifest["digest"], "revision": _revision(image)}
    return {"digest": manifest["digest"], "platforms": platforms}


def main():
    print(json.dumps(summarize(json.load(sys.stdin)), sort_keys=True))


if __name__ == "__main__":
    main()
