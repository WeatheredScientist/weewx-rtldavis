#!/usr/bin/env python3
"""Baseline-measure the process-freeze rate, instead of eyeballing it (DEC-0083).

WHY THIS EXISTS
---------------
BOOT.md inherited a "~once/day, ~3.5 min" freeze characterization from gut
feel. DEC-0083 (S76) measured it properly -- 1.49/day, median 240 s, both
figures understating the true rate by ~40% -- but the derivation was a
one-off that lived only in that session's scratch work, so the number decays
the moment nobody re-runs it (BACKLOG.md). This script is that re-run, made
permanent. Companion to ops/stall_baseline.py, which answers "is this
actually unusual?" for the RF-dead side; this answers it for the silent side.

A FREEZE IS DEFINED BY WHAT IT IS NOT
--------------------------------------
BACKLOG's rule (DEC-0067): a >150 s archive gap WITH a `rtldavis process
stalled` line in it is RF-dead -- the driver's own watchdog is the reason
data stopped. A >150 s gap with NO stall line is the process wedged solid
enough that not even the watchdog fired: a freeze. A third class, the
scheduled campaign arm swap (container kill/restart, every 6 h at :05 --
confirmed against ops/rx_experiment.sh's own SCHEDULE table), is expected
downtime and must not inflate either count. Classification order matters:
RF-dead is checked FIRST, so a real outage that happens to land on a swap
slot is never misfiled as "just the swap".

SWAP DETECTION ALSO COVERS AD HOC RESTARTS (S80, 2026-08-13)
--------------------------------------------------------------
The fixed schedule only knows the four scheduled hours -- it cannot see a
restart rx_experiment.sh triggers itself off that schedule: an abort's
baseline restore, a DEC-0087 pause escalating past its ceiling, or (the case
that found this) a tick's own self-heal right after an abort clears. That
exact gap -- 2026-08-13 10:24-10:27, the S79 recovery's own restart -- read
as a freeze under the schedule-only check. So `classify()` also cross-
references every `tick: swapping` / `RESTORING baseline snapshot` line
rx_experiment.sh itself logged: ground truth that a restart happened, not a
guess at when one might. Either signal counts as swap; RF-dead is still
checked first, so a genuine outage landing inside a restart's health-check
window still correctly reads as RF-dead, not swap.

`rtldavis process is not running` (the driver gone entirely, ERR-0005's
mode) is a separate class again -- stall_baseline.py never clusters it into
RF-dead stalls, and BACKLOG's stated freeze rule names only the `stalled`
signature. This script follows that same line exactly, but any freeze that
overlaps a NOTRUN timestamp is flagged inline rather than silently counted,
since a data gap during a genuinely-dead process is not the same claim as a
data gap during a wedged-but-alive one.

TWO TRAPS, BOTH FOUND THE HARD WAY (BACKLOG.md)
------------------------------------------------
1. The 2026-07-13 ERR-0003 backfill wrote archive rows at `interval=15`
   instead of the normal per-minute `interval=1`. A gap computed across one
   of those rows reads as a ~900 s "freeze" that never happened -- 28 of
   them, inflating the naive rate by ~60%. Every row with `interval != 1` is
   dropped before gaps are computed, and the drop count is always printed so
   a future backfill shows up immediately instead of silently corrupting the
   rate again.
2. A summary rate alone hides exactly the confounder above -- the S37 rows
   only became visible because someone printed the individual events and
   noticed a suspicious run of identical ~900 s durations. Individual freeze
   events are therefore always listed, never just the count.

THE WINDOW IS LEFT-CENSORED TO MATCH stall_baseline.py's
----------------------------------------------------------
RF-dead classification needs stall data to check against, and that data
goes back no further than the oldest surviving `weewx.log` rotation. So the
archive query's lower bound is that same date (imported from
stall_baseline.window_start, not recomputed) -- an archive gap older than
that cannot be safely classified and is excluded rather than guessed at.

USAGE
-----
    ops/freeze_baseline.py               # full report
    ops/freeze_baseline.py --pad-min 10  # widen the RF-dead proximity window

Connection facts come from the environment or ~/.claude/nas.env, same posture
as ops/stall_baseline.py -- never from this PUBLIC repo (DEC-0012).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import campaign_analyze as ca  # noqa: E402
import stall_baseline as sb  # noqa: E402

GAP_SEC = 150  # the driver's own watchdog timeout -- a fact, not a tunable
SWAP_HOURS = (0, 6, 12, 18)  # ops/rx_experiment.sh SCHEDULE: every 6h at :05
SWAP_SLACK_MIN = 12  # swap rows are always "<hour>:05"; a few min to complete
RESTART_LOG_FILES = ("rx_experiment.log", "rx_experiment.log.campaignA")
RESTART_PAD_BEFORE_MIN = 3  # last good archive record can land up to one
    # archive interval (60s) before the restart's own log line fires; padded
RESTART_PAD_AFTER_MIN = SWAP_SLACK_MIN  # health_ok()'s own worst-case budget
    # is ~245s; SWAP_SLACK_MIN's 12min is already proven generous, reused here

REMOTE = r"""
set -u
@DOCKER@ exec @CONTAINER@ @VENV_PY@ -c "
import sqlite3
db = sqlite3.connect('file:@DB@?mode=ro', uri=True)
q = 'SELECT dateTime,interval FROM archive WHERE dateTime>=@LO@ ORDER BY dateTime'
for dt, iv in db.execute(q):
    print('%d,%s' % (dt, '' if iv is None else iv))
"
"""


def fetch_archive(query_lo: datetime) -> list[tuple[datetime, str]]:
    """One ssh round trip: dateTime + interval for every archive row on or
    after query_lo. Read-only (`mode=ro`) -- matches ops/campaign_analyze.py.
    """
    port, user, host = sb.nas_env()
    script = (REMOTE.replace("@DOCKER@", ca.DOCKER)
              .replace("@CONTAINER@", ca.CONTAINER)
              .replace("@VENV_PY@", ca.VENV_PY)
              .replace("@DB@", ca.ARCHIVE_DB)
              .replace("@LO@", str(int(query_lo.timestamp()))))
    r = subprocess.run(["ssh", "-p", port, f"{user}@{host}", "bash -s"],
                       input=script, capture_output=True, text=True,
                       timeout=180)
    if r.returncode != 0:
        sys.exit(f"freeze_baseline: ssh failed — {r.stderr.strip()[:300]}")
    rows: list[tuple[datetime, str]] = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if "," not in line:
            continue
        dt_s, iv = line.split(",", 1)
        if not dt_s.isdigit():
            continue
        rows.append((datetime.fromtimestamp(int(dt_s)), iv))
    if not rows:
        sys.exit("freeze_baseline: zero archive rows returned — "
                 "check the DB path/window.")
    return rows


def fetch_restarts() -> list[datetime]:
    """Timestamps of every deliberate restart rx_experiment.sh itself
    triggered: `tick: swapping` (the normal/self-heal arm-change path) and
    `RESTORING baseline snapshot` (every baseline restore -- shared by
    trip_abort() and campaign completion). Ground truth for "expected
    downtime", unlike SWAP_HOURS above, which has no way to see a restart
    landing off its fixed schedule.
    """
    port, user, host = sb.nas_env()
    remote = (f'cd {sb.LOGDIR} 2>/dev/null || exit 1; '
              f'grep -hE "tick: swapping |RESTORING baseline snapshot" '
              f'{" ".join(RESTART_LOG_FILES)} 2>/dev/null')
    r = subprocess.run(["ssh", "-p", port, f"{user}@{host}", remote],
                       capture_output=True, text=True)
    if r.returncode != 0 and not r.stdout:
        sys.exit("freeze_baseline: ssh failed fetching restart log — "
                 f"{r.stderr.strip()[:200]}")
    return sb.stamps(r.stdout.splitlines())


def per_minute(rows: list[tuple[datetime, str]]) -> tuple[list[datetime], int]:
    """Drop non-per-minute rows (interval != 1) -- the S37 backfill trap.
    Returns the clean timestamps (already sorted; the query is ORDER BY
    dateTime) and how many rows were dropped."""
    clean = [dt for dt, iv in rows if iv == "1"]
    return clean, len(rows) - len(clean)


Gap = tuple[datetime, datetime, float]


def find_gaps(ts: list[datetime], gap_sec: int) -> list[Gap]:
    return [(a, b, (b - a).total_seconds())
            for a, b in zip(ts, ts[1:]) if (b - a).total_seconds() > gap_sec]


def is_rf_dead(a: datetime, b: datetime, stalls: list[datetime],
               pad_min: int) -> bool:
    pad = timedelta(minutes=pad_min)
    return any(a - pad <= s <= b + pad for s in stalls)


def is_scheduled_swap_slot(a: datetime) -> bool:
    """Campaign arm swaps land at :05 past 00/06/12/18 (ops/rx_experiment.sh)."""
    return a.hour in SWAP_HOURS and a.minute <= SWAP_SLACK_MIN


def is_logged_restart(a: datetime, restarts: list[datetime]) -> bool:
    """True if a gap starting at `a` lines up with a restart rx_experiment.sh
    actually logged -- catches ad hoc restarts (abort recovery, pause
    escalation, campaign completion) the fixed schedule can't see. Padding is
    asymmetric: a few minutes back for the last good record that could have
    landed before the restart fired, SWAP_SLACK_MIN's already-proven-generous
    12min forward for the restart to produce a new one.
    """
    before = timedelta(minutes=RESTART_PAD_BEFORE_MIN)
    after = timedelta(minutes=RESTART_PAD_AFTER_MIN)
    return any(r - before <= a <= r + after for r in restarts)


def is_swap_slot(a: datetime, restarts: list[datetime]) -> bool:
    return is_scheduled_swap_slot(a) or is_logged_restart(a, restarts)


def classify(
    gaps: list[Gap], stalls: list[datetime], restarts: list[datetime],
    pad_min: int,
) -> tuple[list[Gap], list[Gap], list[Gap]]:
    """RF-dead checked first: a real outage landing on a swap slot must never
    be absorbed into "just the swap" (BACKLOG.md's classification rule)."""
    rf: list[Gap] = []
    swap: list[Gap] = []
    freeze: list[Gap] = []
    for g in gaps:
        a, b, _ = g
        if is_rf_dead(a, b, stalls, pad_min):
            rf.append(g)
        elif is_swap_slot(a, restarts):
            swap.append(g)
        else:
            freeze.append(g)
    return rf, swap, freeze


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pad-min", type=int, default=5,
                    help="minutes either side of a gap to look for a stall "
                         "line before calling it RF-dead (default 5)")
    args = ap.parse_args()

    files, stall_lines, notrun_lines, _now = sb.fetch()
    stalls = sb.stamps(stall_lines)
    notrun = sb.stamps(notrun_lines)
    if not stalls:
        print("freeze_baseline: ZERO stall lines matched — cannot classify "
              "RF-dead vs freeze without them. Positive-control before "
              "believing this (DEC-0045).")
        return 1

    query_lo = sb.window_start(files, stalls)
    raw = fetch_archive(query_lo)
    ts, dropped = per_minute(raw)
    if not ts:
        sys.exit(f"freeze_baseline: all {len(raw)} archive rows were "
                 "non-per-minute (interval != 1) — nothing to analyze.")

    restarts = fetch_restarts()
    span_d = (ts[-1] - ts[0]).total_seconds() / 86400
    gaps = find_gaps(ts, GAP_SEC)
    rf, swap, freeze = classify(gaps, stalls, restarts, args.pad_min)

    print("=" * 74)
    print("OBSERVATION WINDOW")
    print("=" * 74)
    print(f"  {ts[0]:%Y-%m-%d %H:%M} -> {ts[-1]:%Y-%m-%d %H:%M}  "
          f"({span_d:.1f} days)")
    print(f"  archive rows: {len(raw)}   at interval=1: {len(ts)}   "
          f"dropped (non-per-minute, incl. any backfill): {dropped}")
    print("  LEFT-CENSORED to match ops/stall_baseline.py's window: RF-dead")
    print("  classification needs stall data, which goes back no further")
    print("  than the oldest surviving log rotation.")
    print()

    print("=" * 74)
    print(f"GAPS > {GAP_SEC}s")
    print("=" * 74)
    adhoc = sum(1 for a, _, _ in swap
                if not is_scheduled_swap_slot(a) and is_logged_restart(a, restarts))
    print(f"  total: {len(gaps)}")
    print(f"  RF-dead (stall line within +-{args.pad_min}min): {len(rf):>3d}")
    print(f"  arm-swap (scheduled slot OR a logged restart):   {len(swap):>3d}"
          f"   ({adhoc} off-schedule, matched via {len(restarts)} logged "
          "rx_experiment.sh restarts)")
    print(f"  FREEZE (silent, unscheduled, unlogged):    {len(freeze):>3d}")
    print()

    print("=" * 74)
    print("ROLLING-WINDOW PLACEMENT — rank the current freeze rate in its "
          "own history")
    print("=" * 74)
    onsets = [g[0] for g in freeze]
    win_end = ts[-1]
    for hours in (24, 36, 48, 72):
        counts = []
        t = ts[0] + timedelta(hours=hours)
        while t <= win_end:
            counts.append(sum(1 for o in onsets
                              if t - timedelta(hours=hours) < o <= t))
            t += timedelta(hours=1)
        cur = sum(1 for o in onsets
                  if win_end - timedelta(hours=hours) < o <= win_end)
        counts.append(cur)
        below = sum(1 for c in counts if c < cur)
        pct = 100.0 * below / len(counts)
        verdict = ("AT RECORD MAX" if cur >= max(counts)
                   else "elevated" if pct >= 90 else "unremarkable")
        print(f"  {hours:>3d}h: current={cur:>2d}  record_max={max(counts):>2d}"
              f"  {pct:>5.1f}th pct of {len(counts)} windows   {verdict}")
    print()

    print("=" * 74)
    print("FREEZE RATE")
    print("=" * 74)
    if not freeze:
        print("  zero freezes in window.")
        return 0
    rate = len(freeze) / span_d
    durs = sorted(g[2] for g in freeze)
    med = durs[len(durs) // 2]
    print(f"  {len(freeze)} freezes over {span_d:.1f} d  =  {rate:.2f}/day  "
          f"(1 per {span_d / len(freeze):.2f} d)")
    print(f"  duration: min={durs[0]:.0f}s  median={med:.0f}s  "
          f"max={durs[-1]:.0f}s")
    print()

    print("=" * 74)
    print("FREEZE EVENTS")
    print("=" * 74)
    for a, b, d in freeze:
        flag = " [overlaps NOTRUN -- process was gone, not just wedged]" \
            if is_rf_dead(a, b, notrun, args.pad_min) else ""
        print(f"  {a:%Y-%m-%d %H:%M} -> {b:%H:%M}  {d:>6.0f}s{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
