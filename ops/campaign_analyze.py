#!/usr/bin/env python3
"""Freeze-aware reception analysis for the RX campaigns (DEC-0069).

WHY THIS EXISTS
---------------
The campaign apparatus (ops/rx_experiment.sh) harvests the monitor's 5-minute
`RECEPTION: NN%` aggregate. A process freeze (DEC-0067/DEC-0068) lands inside one
of those buckets and drags the WHOLE bucket down -- measured 16% and 27% on
2026-08-04 against a ~72% neighbourhood -- so one bad minute destroys four good
ones. Across a 6 h arm block (72 such samples) that is ~0.6-0.8 points against a
2.0-point adoption threshold (DEC-0059). That is the defect this closes.

The archive DB carries the same measurement at PER-MINUTE resolution:
`rxCheckPercent`, the driver's own good-CRC-decodes over theoretical-max, which
S31 established as the honest metric (the WU-publish scrape measures publish
liveness). At per-minute resolution a freeze damages ONE record instead of five,
so changing the source is most of the fix before any exclusion logic runs.

THE MEASURED FREEZE SIGNATURE
-----------------------------
Scanned 2026-07-29 -> 2026-08-05: 10988 records, 33 gaps. Every gap falls into
one of three classes, and they do not overlap:

  freeze        rx BEFORE the gap is 4-17% (p01 of the whole population is 56.5)
                and rx AFTER is normal and non-NULL. Matches every freeze in the
                DEC-0067/0068 record, and retro-finds one nobody had logged
                (07-29 22:12).
  arm swap      rx BEFORE is normal; rx AFTER is NULL. These are the HH:04
                cluster -- campaign A's own swaps, as DEC-0067 identified.
  lock/outage   same shape as a swap (rx AFTER NULL): the two `database is
                locked` events and ERR-0005.

So the contaminated record is THE ONE ADJACENT TO THE GAP, not the minutes
inside it -- those are simply absent rows and need no handling at all. The
freeze record reads low because weewx assembled it from a truncated
accumulation period but still divided by the full nominal interval; `interval`
stays 1, so the row CANNOT identify itself as contaminated. Detection has to be
structural.

WHY NOT A VALUE THRESHOLD
-------------------------
"Drop anything under 20%" would be simpler and is WRONG. The campaign exists to
MEASURE reception; a rule keyed on magnitude discards genuine deep fades and
biases every arm upward -- exactly the confound the Latin square was built to
avoid. Structure identifies artifacts; magnitude does not.

THE 200% RECORD
---------------
2026-07-29 03:10 carries rxCheckPercent = 200.0 -- a record that absorbed a
2-minute span while still stamped interval=1. This is DEC-0067's predicted
post-freeze inflation. It is rare (weewx usually advances past the gap and
starts a fresh accumulator instead) but it is real, and it is non-physical:
weewx_monitor.summarize_reception_rows() applies no cap, so such a record
contributes twice its expected packets. Excluding the record on BOTH sides of
every gap catches truncation and absorption without having to know which
occurred; `rx > 100` is kept as a second, independent backstop.

CAMPAIGN ARM LABELS mean different settings in each campaign -- see --campaign.
Campaign A's arm A and campaign B's arm A are the SAME settings (gain 372, ex 0)
on purpose: that pair is the cross-campaign LNA anchor, and it is the reason
this tool recomputes A rather than reusing A's originally-harvested numbers.

Usage:
    python3 ops/campaign_analyze.py --campaign A --since 1785384300
    python3 ops/campaign_analyze.py --campaign B --settle 900
    python3 ops/campaign_analyze.py --campaign A --raw-dump rows.csv

Campaign A NEEDS that `--since`: its aborted 2026-07-29 attempt shares the same
apparatus log, and without a cutoff those blocks join the arm means. The tool warns
and names the epoch, but it will not refuse — pass it.

Connection facts come from the environment or ~/.claude/nas.env, never from this
PUBLIC repo (DEC-0012): NAS_PORT / NAS_USER / NAS_HOST.
"""

from __future__ import annotations

import argparse
import os
import re
import statistics
import subprocess
import sys
import time
from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple

# Arm legends. Labels are reused between campaigns with DIFFERENT meanings, so a
# bare "arm B" number is ambiguous across campaigns; printing the legend in the
# header is what stops that becoming a silent comparison error.
LEGENDS: Dict[str, Dict[str, str]] = {
    "A": {"A": "gain 372 ex 0", "B": "gain 207 ex 0",
          "C": "gain 372 ex 50", "D": "gain 207 ex 50"},
    "B": {"A": "gain 372 ex 0", "B": "gain 496 ex 0",
          "C": "gain 372 ex 50", "D": "gain 496 ex 50",
          "H": "gain 372 ex 0 (hold)",
          "P496": "pilot gain 496", "P449": "pilot gain 449",
          "P402": "pilot gain 402", "P372": "pilot gain 372",
          "P328": "pilot gain 328"},
}

DEFAULT_LOG = "/volume1/docker/weewx-rtldavis/logs/rx_experiment.log"
CONTAINER = "weewx-rtldavis-v2"
ARCHIVE_DB = "/opt/weewx-data/archive/weewx.sdb"
DOCKER = "/usr/local/bin/docker"
VENV_PY = "/opt/weewx-venv/bin/python3"

# The apparatus writes these; both carry a leading local timestamp. `nasctl grep`
# prefixes a line number, so tolerate an optional "NNN:" -- a tool that only
# worked against one of the two ways we read the log would be a trap.
_TS = r"(?:\d+:)?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
SWAP_RE = re.compile(_TS + r" tick: swapping \S+ -> (\S+)")
STOP_RE = re.compile(_TS + r" (?:ABORT|CAMPAIGN COMPLETE)")


class Rec(NamedTuple):
    """One archive row. `rx` is None for the NULL-rxCheckPercent restart artifact."""

    ts: int
    interval: Optional[int]
    rx: Optional[float]


class Excl(NamedTuple):
    ts: int
    reason: str


class Block(NamedTuple):
    """One arm block. `start` has the settle window already applied; `raw_start`
    is the actual swap instant, kept so the report can show what settle cost."""

    arm: str
    start: int
    end: int
    raw_start: int


# ── Pure analysis (no I/O -- this is the unit-tested core) ────────────────────

def gap_adjacent(recs: Sequence[Rec]) -> Set[int]:
    """Indices of records sitting immediately before or after a sequence gap.

    Expected spacing is the earlier record's own `interval` (minutes). WeeWX
    stamps archive records on exact interval boundaries, so normal spacing is
    exact and a strict `>` needs no tolerance -- verified across 10988 records,
    where every non-gap delta was exactly 60 s.
    """
    bad: Set[int] = set()
    for i in range(1, len(recs)):
        prev, cur = recs[i - 1], recs[i]
        expected = (prev.interval or 1) * 60
        if cur.ts - prev.ts > expected:
            bad.add(i - 1)
            bad.add(i)
    return bad


def partition(recs: Sequence[Rec]) -> Tuple[List[Rec], List[Excl]]:
    """Split records into (usable, excluded-with-reason).

    Three independent rules, deliberately not collapsed into one: each catches a
    different failure and each can be argued with separately.
    """
    gaps = gap_adjacent(recs)
    keep: List[Rec] = []
    drop: List[Excl] = []
    for i, r in enumerate(recs):
        if r.rx is None:
            drop.append(Excl(r.ts, "null"))
        elif r.rx > 100.0:
            drop.append(Excl(r.ts, "nonphysical"))
        elif i in gaps:
            drop.append(Excl(r.ts, "gap-adjacent"))
        else:
            keep.append(r)
    return keep, drop


def parse_blocks(lines: Sequence[str], settle_s: int,
                 now: Optional[int] = None) -> List[Block]:
    """Turn the apparatus log's swap/stop events into settled arm blocks.

    Timestamps in that log are NAS-local; this converts with the LOCAL clock, so
    the dev machine and the NAS must share a timezone. They do (same house), but
    the assumption is stated rather than hidden -- a silent one-hour shear would
    misattribute a whole block and look like a result.
    """
    events: List[Tuple[int, Optional[str]]] = []
    for line in lines:
        m = SWAP_RE.search(line)
        if m:
            events.append((_epoch(m.group(1)), m.group(2)))
            continue
        m = STOP_RE.search(line)
        if m:
            events.append((_epoch(m.group(1)), None))
    events.sort(key=lambda e: e[0])

    end_of_time = now if now is not None else int(time.time())
    blocks: List[Block] = []
    for i, (ts, arm) in enumerate(events):
        if arm is None or arm == "BASELINE":
            continue
        nxt = events[i + 1][0] if i + 1 < len(events) else end_of_time
        start = ts + settle_s
        if start < nxt:
            blocks.append(Block(arm, start, nxt, ts))
    return blocks


def _epoch(stamp: str) -> int:
    return int(time.mktime(time.strptime(stamp, "%Y-%m-%d %H:%M:%S")))


def attempt_starts(lines: Sequence[str]) -> List[int]:
    """Epochs at which a distinct campaign ATTEMPT begins.

    The apparatus log accumulates across attempts. Campaign A aborted on
    2026-07-29 after 75 minutes of arm B and restarted clean on 07-30, so a bare
    run pools that aborted block with the campaign proper -- which silently
    unbalances the Latin square (arm B carried ~60 extra records) while still
    printing a tidy four-row table. Nothing in the output said so.

    A docstring warning would not have caught it: prose does not execute
    (DEC-0040). So the tool detects the condition and says it out loud, and the
    operator picks a `--since`.
    """
    events: List[Tuple[int, bool]] = []
    for line in lines:
        m = SWAP_RE.search(line)
        if m:
            events.append((_epoch(m.group(1)), True))
            continue
        m = STOP_RE.search(line)
        if m:
            events.append((_epoch(m.group(1)), False))
    events.sort(key=lambda e: e[0])

    starts: List[int] = []
    fresh = True
    for ts, is_swap in events:
        if not is_swap:
            fresh = True
        elif fresh:
            starts.append(ts)
            fresh = False
    return starts


class ArmStat(NamedTuple):
    arm: str
    n: int
    mean: float
    sd: float
    raw_n: int
    raw_mean: float


def summarize(recs: Sequence[Rec], blocks: Sequence[Block]) -> List[ArmStat]:
    """Per-arm cleaned mean, with the uncleaned mean alongside.

    `raw_*` is what the same window yields with NO freeze-aware treatment and no
    settle -- only NULLs dropped, because a NULL cannot be averaged at all. It is
    reported so the size of the correction is visible instead of asserted.
    """
    keep, _ = partition(recs)
    kept_by_ts = {r.ts: r for r in keep}

    clean: Dict[str, List[float]] = {}
    raw: Dict[str, List[float]] = {}
    for b in blocks:
        for r in recs:
            if b.raw_start <= r.ts < b.end and r.rx is not None:
                raw.setdefault(b.arm, []).append(r.rx)
            if b.start <= r.ts < b.end and r.ts in kept_by_ts:
                clean.setdefault(b.arm, []).append(r.rx)  # type: ignore[arg-type]

    out: List[ArmStat] = []
    for arm in sorted(set(list(clean) + list(raw))):
        cv, rv = clean.get(arm, []), raw.get(arm, [])
        out.append(ArmStat(
            arm=arm,
            n=len(cv),
            mean=statistics.fmean(cv) if cv else float("nan"),
            sd=statistics.stdev(cv) if len(cv) > 1 else float("nan"),
            raw_n=len(rv),
            raw_mean=statistics.fmean(rv) if rv else float("nan"),
        ))
    return out


# ── I/O ──────────────────────────────────────────────────────────────────────

# The lower bound is resolved ON THE NAS, before the query runs. Resolving it
# locally would mean asking for `dateTime>=0` and dragging the ENTIRE archive
# across ssh to throw almost all of it away -- measured: that read does not
# finish inside a 120 s timeout. The apparatus log's first timestamp is the
# earliest a campaign row can exist, so it is the natural floor.
REMOTE = r"""
set -u
LOG='@LOG@'
SINCE=@LO@
echo '===SWAPS==='
grep -E 'swapping|ABORT|CAMPAIGN COMPLETE' "$LOG" 2>/dev/null || true
if [ "$SINCE" -le 0 ]; then
  first=$(grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}' "$LOG" \
          2>/dev/null | head -1)
  SINCE=$(date -d "$first" +%s 2>/dev/null || echo 0)
fi
echo "===SINCE=$SINCE==="
echo '===ROWS==='
@DOCKER@ exec @CONTAINER@ @VENV_PY@ -c "
import sqlite3
db = sqlite3.connect('file:@DB@?mode=ro', uri=True)
q = 'SELECT dateTime,interval,rxCheckPercent FROM archive WHERE dateTime>=$SINCE ORDER BY dateTime'
for dt, iv, pct in db.execute(q):
    print('%d,%s,%s' % (dt, '' if iv is None else iv, '' if pct is None else pct))
"
"""


def fetch(log_path: str, lo: int) -> Tuple[List[str], List[Rec]]:
    """One ssh round-trip for both the apparatus log and the archive rows.

    Batched deliberately: CONVENTIONS warns that SSH to this box flakes on rapid
    reconnects. Read-only throughout -- the DB is opened `mode=ro`.
    """
    port, user, host = (os.environ.get("NAS_PORT"), os.environ.get("NAS_USER"),
                        os.environ.get("NAS_HOST"))
    if not (port and user and host):
        sys.exit("NAS_PORT/NAS_USER/NAS_HOST unset -- export them or create "
                 "~/.claude/nas.env (see gitignored docs/LOCAL_INFRA.md).")

    script = (REMOTE
              .replace("@LOG@", log_path)
              .replace("@DOCKER@", DOCKER)
              .replace("@CONTAINER@", CONTAINER)
              .replace("@VENV_PY@", VENV_PY)
              .replace("@DB@", ARCHIVE_DB)
              .replace("@LO@", str(lo)))
    proc = subprocess.run(
        ["ssh", "-p", port, f"{user}@{host}", "bash -s"],
        input=script, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        sys.exit(f"ssh failed (rc={proc.returncode}): {proc.stderr.strip()[:400]}")

    swaps: List[str] = []
    recs: List[Rec] = []
    section = ""
    for line in proc.stdout.splitlines():
        if line.startswith("==="):
            section = line
            continue
        if section.startswith("===SINCE="):
            continue
        if section == "===SWAPS===":
            swaps.append(line)
        elif section == "===ROWS===" and line:
            parts = line.split(",")
            if len(parts) == 3:
                recs.append(Rec(int(parts[0]),
                                int(parts[1]) if parts[1] else None,
                                float(parts[2]) if parts[2] else None))
    return swaps, recs


# ── Report ───────────────────────────────────────────────────────────────────

def report(campaign: str, blocks: Sequence[Block], recs: Sequence[Rec],
           settle_s: int) -> None:
    legend = LEGENDS.get(campaign, {})
    _, dropped = partition(recs)
    in_blocks = [r for r in recs
                 if any(b.raw_start <= r.ts < b.end for b in blocks)]
    settled_out = sum(1 for r in recs
                      for b in blocks if b.raw_start <= r.ts < b.start)

    print(f"── CAMPAIGN {campaign} — freeze-aware reception analysis ─────────────")
    print(f"   source: archive rxCheckPercent (per-minute) · settle {settle_s}s "
          f"· DEC-0069")
    if blocks:
        span = (time.strftime('%Y-%m-%d %H:%M', time.localtime(blocks[0].raw_start)),
                time.strftime('%Y-%m-%d %H:%M', time.localtime(blocks[-1].end)))
        print(f"   {len(blocks)} blocks · {span[0]} → {span[1]}")
    print()

    counts: Dict[str, int] = {}
    for e in dropped:
        counts[e.reason] = counts.get(e.reason, 0) + 1
    print("   EXCLUSIONS (whole fetched window)")
    labels = {"null": "NULL rxCheckPercent (restart artifact)",
              "gap-adjacent": "gap-adjacent (freeze/restart truncation)",
              "nonphysical": "non-physical (rx > 100)"}
    for reason, label in labels.items():
        print(f"     {label:<44} {counts.get(reason, 0):>6}")
    print(f"     {'post-swap settle window':<44} {settled_out:>6}")
    print(f"     {'':-<44} {'':->6}")
    tot = sum(counts.values()) + settled_out
    print(f"     {'total excluded':<44} {tot:>6}   of {len(recs)} fetched, "
          f"{len(in_blocks)} in-block")
    print()

    print("   ARM RESULTS")
    print(f"     {'arm':<5} {'settings':<22} {'n':>5} {'mean':>7} {'sd':>6} "
          f"{'raw n':>6} {'raw mean':>9} {'delta':>7}")
    for s in summarize(recs, blocks):
        delta = s.mean - s.raw_mean
        print(f"     {s.arm:<5} {legend.get(s.arm, '?'):<22} {s.n:>5} "
              f"{s.mean:>6.2f}% {s.sd:>5.2f} {s.raw_n:>6} {s.raw_mean:>8.2f}% "
              f"{delta:>+7.2f}")
    print()
    print("   delta = cleaned minus uncleaned, in reception points. The adoption")
    print("   bar is ≥2.0 points over the incumbent (DEC-0059).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--campaign", default="A", help="A or B (selects the arm legend)")
    ap.add_argument("--log", default=DEFAULT_LOG, help="apparatus log on the NAS")
    ap.add_argument("--settle", type=int, default=600,
                    help="seconds to drop after each swap (default 600, matching "
                         "rx_experiment.sh SETTLE_SECS)")
    ap.add_argument("--since", type=int, default=0,
                    help="epoch lower bound; 0 = derive from the first swap")
    args = ap.parse_args()

    swaps, recs = fetch(args.log, args.since)
    blocks = parse_blocks(swaps, args.settle)
    # Drop blocks that ended before the analysis window opens -- otherwise the
    # header reports a span the numbers below do not actually cover (e.g. a
    # `--since` past campaign A's aborted 07-29 attempt still listed that block).
    # Provenance a reader would have to verify by hand is provenance that lies.
    blocks = [b for b in blocks if b.end > args.since]
    if not blocks:
        print("No arm blocks found in the apparatus log — nothing to analyze.")
        return 1

    live = [t for t in attempt_starts(swaps) if t >= args.since]
    if len(live) > 1:
        print("WARNING: this log holds %d campaign attempts, and they are being "
              "POOLED:" % len(live))
        for t in live:
            print("           %s" % time.strftime("%Y-%m-%d %H:%M",
                                                  time.localtime(t)))
        print("         An aborted attempt unbalances the square while still "
              "printing a tidy\n"
              "         table. Re-run with --since <epoch of the attempt you "
              "want>.\n")
    if not args.since:
        lo = blocks[0].raw_start
        recs = [r for r in recs if r.ts >= lo]
    report(args.campaign, blocks, recs, args.settle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
