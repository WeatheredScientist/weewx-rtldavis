#!/usr/bin/env python3
"""Derive the tree-swap restore list from LIVE unit files, not memory (ops#288).

WHY THIS EXISTS
---------------
DEC-0150's tenant-tree swap (ops#257 limb 1) moved the old `/srv/docker/weewx`
tree aside and restored a hand-maintained "landmine list" of paths known to
matter -- weewx.conf, archive/weewx.sdb, the decoy scripts, etc. `influxdb/`
was not on that list (it isn't a git-tracked path, so the SHA-diff sweep never
looked at it either), so it stayed behind in the moved-aside tree and nothing
broke until the next full restart (DEC-0151, the S130 incident this repo just
lived through). ops#288 names the fix: a swap's restore list must be DERIVED
from the units' own bind mounts, not curated from memory, because a curated
list is exactly as complete as whoever wrote it remembered to be.

WHAT "RESTORE LIST" MEANS HERE
-------------------------------
Not every `-v host:container` source is a landmine. Some (`influx.py`,
`loop_json_writer.py`, `sortedcontainers`) are files this very repo tracks in
git -- a tenant-root git checkout (DEC-0150) recreates them for free. The
actual landmines are host paths that are NOT git-tracked: runtime data that
only ever existed on the live box and would be silently lost (or, worse,
silently re-created empty and root-owned by Docker's own bind-mount
auto-create -- MARVIN-DEC-0146's failure mode) if a swap didn't know to carry
them across. So every derived mount is classified against THIS repo's own git
tree:

    TRACKED      -- `git ls-files` finds it. A checkout recreates it. Not a
                    landmine.
    IGNORED      -- matches `.gitignore` (weewx-data/, logs/). A KNOWN data
                    path -- already documented as something to carry across,
                    just not by name in a swap plan.
    UNDOCUMENTED -- neither tracked nor ignored. The influxdb/ shape exactly:
                    nobody told git about it, so nobody told the swap plan
                    either. These are the ones worth a human's eyes before any
                    swap.

CROSS-TENANT DEPENDENTS
------------------------
A weewx-side tree swap can also break OTHER tenants' containers if it moves a
path they read from. `eh-proxy.service` (dashboard) and `hlf-api.service`
(HLF) both bind-mount into weewx's own tree read-only. These are reported
separately -- not weewx's restore list, but paths a weewx swap must not
relocate without warning those tenants.

USAGE
-----
    ops/tenant_mounts.py                       # full report
    ops/tenant_mounts.py --check planned.txt   # flag derived paths NOT in
                                                # planned.txt, one host path
                                                # per line -- the check that
                                                # would have caught DEC-0150's
                                                # missing influxdb/ entry

Transport is `marvinctl --tenant weewx cat <unit-file>` -- unit FILES, not
`marvinctl unit`'s runtime status, because a periodic unit (weewx-rx-experiment,
weewx-influxdb-backup) shows no ExecStart line in `systemctl status` once it
has exited; the file is authoritative regardless of whether anything is
currently running. Per marvin's own ops#288 comment: unit files are readable
over every tenant's read path, box-wide, not just weewx's own -- that is what
makes the cross-tenant half possible from here.

Classification runs against THIS SCRIPT'S OWN local git checkout, not a remote
read -- it assumes you are running it from a `weewx-rtldavis` clone whose
tenant-relative layout matches marvin's `/srv/docker/weewx/` checkout (true by
construction, DEC-0150).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TENANT_ROOT = "/srv/docker/weewx"

# weewx's own units -- the manifest's `images`/`units` glob, read from the unit
# FILES so an inactive periodic unit still contributes its mounts.
OWN_UNITS = [
    "weewx.service",
    "weewx-influxdb.service",
    "weewx-influxdb-backup.service",
    "weewx-rx-experiment.service",
]

# Known cross-tenant consumers that read INTO weewx's tree, discovered live via
# `marvinctl --tenant weewx unit weather.slice`. Hardcoded, not auto-discovered
# -- box-wide unit enumeration isn't a marvinctl verb, and a new consumer
# showing up here needs a human to add it, same as OWN_UNITS above.
EXTERNAL_UNITS = [
    "eh-proxy.service",       # dashboard
    "hlf-api.service",        # hyperlocal-forecast
]

MOUNT_RE = re.compile(r"-v\s+([^\s:]+):([^\s:]+)(?::(\w+))?")
REPO_ROOT = Path(__file__).resolve().parent.parent


def _marvinctl_cat(unit_file: str) -> str | None:
    """`marvinctl --tenant weewx cat /etc/systemd/system/<unit_file>`.

    Read-only, tier 1. Returns None (not a hard failure) if the unit doesn't
    exist on this box -- OWN_UNITS/EXTERNAL_UNITS name what SHOULD exist, and
    a missing one is itself worth reporting, not crashing over.
    """
    proc = subprocess.run(
        ["marvinctl", "--tenant", "weewx", "cat",
         f"/etc/systemd/system/{unit_file}"],
        capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return None
    return proc.stdout


def _join_execstart(unit_text: str) -> str:
    """Join every ExecStart= block's backslash-continued lines into one
    string. A unit can carry more than one ExecStart= (weewx-rx-experiment.service
    has two, `tick` and `guard`) -- all are scanned, concatenated, since a
    mount could in principle live on any of them.
    """
    lines = unit_text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("ExecStart="):
            buf = [line]
            while buf[-1].rstrip().endswith("\\"):
                i += 1
                if i >= len(lines):
                    break
                buf.append(lines[i])
            out.append(" ".join(b.rstrip("\\").strip() for b in buf))
        i += 1
    return "\n".join(out)


def parse_mounts(execstart_text: str) -> list[tuple[str, str, str]]:
    """Every `-v SRC:DST[:MODE]` in the joined ExecStart text."""
    return [(src, dst, mode or "rw")
            for src, dst, mode in MOUNT_RE.findall(execstart_text)]


def classify(src: str) -> str:
    """TRACKED / IGNORED / UNDOCUMENTED, against this repo's OWN git tree."""
    if not src.startswith(TENANT_ROOT + "/") and src != TENANT_ROOT:
        return "N/A"
    rel = src[len(TENANT_ROOT):].lstrip("/")
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", "--", rel],
        capture_output=True, text=True)
    if tracked.returncode == 0:
        return "TRACKED"
    # A directory-only .gitignore pattern ("weewx-data/") only matches
    # check-ignore when the path is spelled with a trailing slash OR git can
    # stat it as a directory locally -- neither holds for a bind-mount source
    # that exists only on the remote box, so both spellings are tried.
    for candidate in (rel, rel + "/"):
        ignored = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", "--", candidate],
            capture_output=True, text=True)
        if ignored.returncode == 0:
            return "IGNORED (known data)"
    return "UNDOCUMENTED"


def own_mounts() -> list[dict]:
    rows = []
    for unit in OWN_UNITS:
        text = _marvinctl_cat(unit)
        if text is None:
            rows.append({"unit": unit, "src": None, "dst": None,
                         "mode": None, "class": "UNIT NOT FOUND"})
            continue
        execstart = _join_execstart(text)
        for src, dst, mode in parse_mounts(execstart):
            rows.append({"unit": unit, "src": src, "dst": dst, "mode": mode,
                         "class": classify(src)})
    return rows


def external_mounts() -> list[dict]:
    rows = []
    for unit in EXTERNAL_UNITS:
        text = _marvinctl_cat(unit)
        if text is None:
            continue
        execstart = _join_execstart(text)
        for src, dst, mode in parse_mounts(execstart):
            if src.startswith(TENANT_ROOT + "/") or src == TENANT_ROOT:
                rows.append({"unit": unit, "src": src, "dst": dst,
                             "mode": mode})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="FILE",
                     help="a swap plan's own restore list, one host path per "
                          "line -- flags any derived path this session found "
                          "that the plan does NOT list")
    args = ap.parse_args()

    own = own_mounts()
    ext = external_mounts()

    print("=" * 78)
    print(f"WEEWX'S OWN BIND MOUNTS -- the restore list ({TENANT_ROOT})")
    print("=" * 78)
    landmines = []
    for r in own:
        if r["src"] is None:
            print(f"  {r['unit']:<32} {r['class']}")
            continue
        print(f"  {r['unit']:<32} {r['src']:<52} {r['mode']:<4} {r['class']}")
        if r["class"] == "UNDOCUMENTED":
            landmines.append(r["src"])
    print()

    if landmines:
        print("=" * 78)
        print("UNDOCUMENTED -- neither git-tracked nor gitignored, review before any swap")
        print("=" * 78)
        for src in sorted(set(landmines)):
            print(f"  {src}")
        print()

    print("=" * 78)
    print("CROSS-TENANT READS INTO WEEWX'S TREE -- do not relocate without warning these")
    print("=" * 78)
    if ext:
        for r in ext:
            print(f"  {r['unit']:<20} reads {r['src']} ({r['mode']})")
    else:
        print("  none found")
    print()

    if args.check:
        planned = {ln.strip() for ln in Path(args.check).read_text().splitlines()
                   if ln.strip()}
        derived = {r["src"] for r in own if r["src"]}
        missing = derived - planned
        print("=" * 78)
        print(f"CHECK AGAINST {args.check}")
        print("=" * 78)
        if missing:
            print("  derived paths NOT in the plan (the DEC-0150 failure shape):")
            for src in sorted(missing):
                print(f"    ⚠ {src}")
            return 1
        print("  every derived path is accounted for in the plan.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
