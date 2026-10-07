#!/usr/bin/env python3
"""Baseline-measure the RF-dead stall rate, instead of eyeballing it (DEC-0083).

WHY THIS EXISTS
---------------
S75 looked at `logs/episodes.log` growing from 2 rows to 4 in ~18 h and called
the stall rate "trending hot, not settling". That reading was RIGHT -- and it
was reached by a method that could not have known it. The ledger had only
existed for 19 hours, so its emptiness before that measured the age of the
instrument, not the quiet of the station. The same look would have produced the
same alarm on a station that had just been perfectly healthy for a month.

This script exists so the claim is answered by the record instead of the eye.
It is the ops#159 "baseline-measured, not eyeballed" pattern made executable,
because prose does not execute (DEC-0040).

THE UNIT IS AN EPISODE, NOT A STALL LINE
----------------------------------------
This is the trap that makes a naive count meaningless. When RF goes dead the
driver's 150 s watchdog raises `rtldavis process stalled`, weewx waits ~60 s,
respawns a fresh child, and the child hears nothing either -- so a SINGLE
episode emits one stall line every ~3 m 40 s for as long as it lasts. The
2026-08-02 episode (ERR-0005) is 21 lines over 75.8 minutes. Counting lines
would score it as 21 events and swamp every real comparison.

So stalls are clustered into episodes on an inter-stall gap. The cluster count
is stable at 15 for thresholds of 30, 45 and 60 minutes, and the clustering was
validated against DEC-0081's independently-derived episode boundaries for the
2026-08-10/11 night (23:52->00:01 and 01:49->02:14): both recovered exactly.

WHAT IS DELIBERATELY EXCLUDED
-----------------------------
`rtldavis process is not running` is a DIFFERENT class -- the driver process
gone entirely, the strictly-worse dies-on-startup mode ERR-0005 hit after reset
#10, and the no-reset path per DEC-0081/S62. It appears 20 times on 2026-08-02
and NOWHERE else in the record. Folding it in would merge two failure modes
that the whole DEC-0081 diagnosis separates. Counted and reported, never
clustered in.

TWO INSTRUMENTS, NOT ONE -- DO NOT COMPARE THEM
-----------------------------------------------
`episodes.log` (ws.5+) records an episode when the monitor sees ALERT->RECOVERY,
including RF-quiet episodes that never trip the 150 s watchdog at all (hop
packets keep resetting it) and surface only as `DATA DROUGHT`. `DATA DROUGHT`
appears ZERO times in every pre-ws.5 rotated log. So a drought-only episode was
structurally invisible before ws.5, and the ledger's row count is NOT
commensurable with anything computed from log history. Only stall-bearing
ledger rows are. The script reports both so the mismatch stays visible.

THE WINDOW IS LEFT-CENSORED, AND SAYS SO
----------------------------------------
Coverage starts at the oldest surviving daily rotation -- that is the log
retention policy, not the onset of the phenomenon. A check that greps a
rotating log must span the rotation or state its window (ops#147 item 8); this
one states it on every run.

USAGE
-----
    ops/stall_baseline.py                # full report
    ops/stall_baseline.py --gap-min 45   # re-cluster at a different threshold

Transport is `marvinctl --tenant weewx` (own-tenant self-service, DEC-0125/DEC-0128's
proven shape, ported from the now-dead NAS-ssh transport at ops#286) -- no connection
secrets, no env vars, nothing from this PUBLIC repo to manage (DEC-0012).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta

LOGDIR = "/srv/docker/weewx/logs"  # marvin path; DEC-0118 moved the tenant off the NAS
STALL_SIG = "rtldavis process stalled"
NOTRUN_SIG = "rtldavis process is not running"
# `marvinctl grep` refuses any pattern containing whitespace (a space becomes two
# remote tokens) -- `.` stands in for the literal space in each signature above,
# same trick campaign_analyze.py's transport note documents.
STALL_GREP = "rtldavis.process.stalled"
NOTRUN_GREP = "rtldavis.process.is.not.running"
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def _marvinctl(*args: str, input: str | None = None, timeout: int = 60) -> str:
    """One `marvinctl --tenant weewx` call. Read-only throughout."""
    proc = subprocess.run(
        ["marvinctl", "--tenant", "weewx", *args],
        input=input, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        sys.exit(f"stall_baseline: marvinctl {args[0]} failed (rc={proc.returncode}): "
                 f"{proc.stderr.strip()[:400]}")
    return proc.stdout


def _grep(pattern: str, path: str) -> list[str]:
    """One `marvinctl grep` call, matching server-side (only hits cross the wire).

    Exit code 1 means either zero matches or a missing path -- marvinctl reports
    both that way. Either is zero lines here, matching the old ssh
    `grep -h ... 2>/dev/null`'s tolerance for a rotated file that has aged out.
    """
    proc = subprocess.run(
        ["marvinctl", "--tenant", "weewx", "grep", pattern, path],
        capture_output=True, text=True, timeout=60)
    if proc.returncode == 1:
        return []
    if proc.returncode != 0:
        sys.exit(f"stall_baseline: marvinctl grep failed (rc={proc.returncode}): "
                 f"{proc.stderr.strip()[:400]}")
    return proc.stdout.splitlines()


def _log_files(prefix: str) -> list[str]:
    """Filenames directly under LOGDIR starting with `prefix`.

    `marvinctl ls` takes one directory, no glob -- filter an `ls -la`-style
    listing client-side instead of the old shell glob (`weewx.log.20*`).
    """
    names = []
    for line in _marvinctl("ls", LOGDIR).splitlines():
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue
        name = parts[8]
        if name.startswith(prefix):
            names.append(name)
    return sorted(names)


def fetch() -> tuple[list[str], list[str], list[str], list[str]]:
    """One `ls` plus a `grep` per rotated file, per signature. Ported from the
    NAS-ssh transport (dead since DEC-0118's host move) to `marvinctl --tenant
    weewx` (ops#286): grep still runs server-side, same as the old ssh form.
    """
    files = _log_files("weewx.log")
    if not files:
        sys.exit("stall_baseline: no log files found — is LOGDIR correct?")
    stalls: list[str] = []
    notrun: list[str] = []
    for f in files:
        path = f"{LOGDIR}/{f}"
        stalls += _grep(STALL_GREP, path)
        notrun += _grep(NOTRUN_GREP, path)
    now = [ln[:19] for ln in _marvinctl("tail", f"{LOGDIR}/weewx.log", "1").splitlines()]
    return files, stalls, notrun, now


def stamps(lines: list[str]) -> list[datetime]:
    out = []
    for ln in lines:
        m = TS_RE.match(ln)
        if m:
            out.append(datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
    return sorted(out)


def window_start(files: list[str], stalls: list[datetime]) -> datetime:
    """Left-censored at the oldest surviving log rotation -- the retention
    policy, not the onset of the phenomenon. Shared with ops/freeze_baseline.py
    so both tools agree on where history starts (STANDARD rule 5)."""
    dated = sorted(f for f in files if f != "weewx.log")
    return (datetime.strptime(dated[0].split(".")[-1], "%Y-%m-%d")
            if dated else stalls[0])


def cluster(ts: list[datetime], gap_min: int) -> list[list[datetime]]:
    if not ts:
        return []
    out, cur = [], [ts[0]]
    for a, b in zip(ts, ts[1:]):
        if (b - a) <= timedelta(minutes=gap_min):
            cur.append(b)
        else:
            out.append(cur)
            cur = [b]
    out.append(cur)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap-min", type=int, default=30,
                    help="inter-stall gap that separates episodes (default 30)")
    args = ap.parse_args()

    files, stall_lines, notrun_lines, now_lines = fetch()
    stalls = stamps(stall_lines)
    notrun = stamps(notrun_lines)
    if not stalls:
        print("stall_baseline: ZERO stall lines matched.")
        print("  This is a suspicious result, not a clean bill of health — the")
        print("  signature or the log path may have changed. Positive-control it")
        print("  before believing it (DEC-0045).")
        return 1

    # Window END is NOW -- the newest line in the live log -- never the last
    # stall. Anchoring on the last event guarantees the window contains it and
    # makes the check read hot immediately after every episode, which is the
    # exact bias this script exists to remove.
    win_start = window_start(files, stalls)
    win_end = max(stalls + notrun)
    if now_lines:
        try:
            win_end = max(win_end,
                          datetime.strptime(now_lines[0].strip(),
                                            "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            pass

    eps = cluster(stalls, args.gap_min)
    onsets = [e[0] for e in eps]
    span_d = (win_end - win_start).total_seconds() / 86400

    print("=" * 74)
    print("OBSERVATION WINDOW")
    print("=" * 74)
    print(f"  {win_start:%Y-%m-%d} -> {win_end:%Y-%m-%d %H:%M}  ({span_d:.1f} days)")
    print(f"  log files: {len(files)}   stall lines: {len(stalls)}   "
          f"episodes: {len(eps)} (gap<={args.gap_min}min)")
    print(f"  '{NOTRUN_SIG}': {len(notrun)} lines — SEPARATE class, not clustered in")
    print("  LEFT-CENSORED: window starts at the oldest surviving rotation, which")
    print("  is the retention policy — NOT the onset of the phenomenon.")
    print()

    print("=" * 74)
    print("THRESHOLD SENSITIVITY — the verdict must not rest on one cut")
    print("=" * 74)
    for th in (15, 20, 30, 45, 60, 90):
        n = len(cluster(stalls, th))
        mark = "  <-- reported" if th == args.gap_min else ""
        print(f"  gap<={th:>3d}min -> {n:>3d} episodes{mark}")
    print()

    print("=" * 74)
    print("ROLLING-WINDOW PLACEMENT — rank the current run in its own history")
    print("=" * 74)
    for hours in (24, 36, 48, 72):
        counts = []
        t = win_start + timedelta(hours=hours)
        while t <= win_end:
            counts.append(sum(1 for o in onsets
                              if t - timedelta(hours=hours) < o <= t))
            t += timedelta(hours=1)
        cur = sum(1 for o in onsets
                  if win_end - timedelta(hours=hours) < o <= win_end)
        # The hourly walk may not land exactly on win_end, so the current window
        # is appended explicitly -- otherwise it is ranked against a series it
        # is not a member of, and record_max can read BELOW current.
        counts.append(cur)
        if not counts:
            continue
        below = sum(1 for c in counts if c < cur)
        pct = 100.0 * below / len(counts)
        verdict = ("AT RECORD MAX" if cur >= max(counts)
                   else "elevated" if pct >= 90 else "unremarkable")
        print(f"  {hours:>3d}h: current={cur:>2d}  record_max={max(counts):>2d}  "
              f"{pct:>5.1f}th pct of {len(counts)} windows   {verdict}")
    print()

    print("=" * 74)
    print("EPISODES")
    print("=" * 74)
    for e in eps:
        mins = (e[-1] - e[0]).total_seconds() / 60
        print(f"  {e[0]:%Y-%m-%d %H:%M}  stalls={len(e):>2d}  span={mins:>5.1f}min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
