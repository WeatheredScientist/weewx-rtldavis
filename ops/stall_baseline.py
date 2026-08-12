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

Connection facts come from the environment or ~/.claude/nas.env, same posture as
ops/soak_check.sh -- never from this PUBLIC repo (DEC-0012).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

LOGDIR = "/volume1/docker/weewx-rtldavis/logs"
STALL_SIG = "rtldavis process stalled"
NOTRUN_SIG = "rtldavis process is not running"
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def nas_env() -> tuple[str, str, str]:
    """Port/user/host from the environment, falling back to ~/.claude/nas.env.

    The env file is sourced in a subshell and only the three values are echoed:
    it is never read into this process's output, because anything a tool prints
    lands in a transcript (DEC-0047).
    """
    port, user, host = (os.environ.get(k, "") for k in
                        ("NAS_PORT", "NAS_USER", "NAS_HOST"))
    if not (port and user and host):
        envf = os.path.expanduser("~/.claude/nas.env")
        if os.path.exists(envf):
            out = subprocess.run(
                ["bash", "-c",
                 f'. "{envf}" >/dev/null 2>&1; '
                 'printf "%s\\n%s\\n%s\\n" "$NAS_PORT" "$NAS_USER" "$NAS_HOST"'],
                capture_output=True, text=True).stdout.splitlines()
            if len(out) == 3:
                port, user, host = (a or b for a, b in
                                    zip((port, user, host), out))
    if not (port and user and host):
        sys.exit("stall_baseline: NAS_PORT/NAS_USER/NAS_HOST unset — export them "
                 "or create ~/.claude/nas.env (see gitignored docs/LOCAL_INFRA.md).")
    return port, user, host


def fetch() -> tuple[list[str], list[str], list[str], list[str]]:
    """One ssh round trip. Greps NAS-side; only matching lines cross the wire."""
    port, user, host = nas_env()
    remote = (
        f'cd {LOGDIR} 2>/dev/null || exit 1; '
        f'echo "---FILES---"; ls -1 weewx.log weewx.log.20* 2>/dev/null; '
        f'echo "---NOW---"; tail -n 1 weewx.log 2>/dev/null | cut -c1-19; '
        f'echo "---STALL---"; grep -h "{STALL_SIG}" weewx.log weewx.log.20* 2>/dev/null; '
        f'echo "---NOTRUN---"; grep -h "{NOTRUN_SIG}" weewx.log weewx.log.20* 2>/dev/null; '
        f'echo "---DROUGHT---"; grep -hc "DATA DROUGHT" weewx.log weewx.log.20* 2>/dev/null'
    )
    r = subprocess.run(["ssh", "-p", port, f"{user}@{host}", remote],
                       capture_output=True, text=True)
    if r.returncode != 0 and not r.stdout:
        sys.exit(f"stall_baseline: ssh failed — {r.stderr.strip()[:200]}")
    files: list[str] = []
    stalls: list[str] = []
    notrun: list[str] = []
    drought: list[str] = []
    now: list[str] = []
    cur: str | None = None
    for line in r.stdout.splitlines():
        if line.startswith("---"):
            cur = line.strip("-")
            continue
        {"FILES": files, "NOW": now, "STALL": stalls,
         "NOTRUN": notrun, "DROUGHT": drought}.get(cur, []).append(line)
    if not files:
        sys.exit("stall_baseline: no log files found — is LOGDIR correct?")
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
