#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Correlate driver frame rejections with archive-record gaps (DEC-0229, #536).

WHY THIS EXISTS
---------------
S188 measured, from 30 days of prod logs, that 12 of the 15 CRC-valid garbage
frames the driver rejected were followed within seconds by a 2 to 5 minute
loss of the station: the Go decoder re-anchors its hop clock to any accepted
frame, so a noise decode at a random moment costs 51 blind hops and a re-init.
DEC-0229 proposes an arrival-time gate in the decoder. This script is the
measurement, made re-runnable, so the gate's effect can be read the same way
after it ships: expect the "GAP" column to go empty for driver rejections.

INPUT
-----
Any mix of weewx.log files, rotated or live, or grep extracts of them. Only
two kinds of line are read, everything else is ignored:

  <date> <time>,ms user.rtldavis ERROR <key>: rejecting implausible value ...
  <date> <time>,ms user.rtldavis ERROR unknown message type 0x<n>
  <date> <time>,ms weewx.manager INFO Added record <date> <time> ... to database ...

From marvin, with no shell on the host, fetch the extracts with the read-only
wrapper and run locally:

  marvinctl --tenant weewx grep ERROR /srv/docker/weewx/logs/weewx.log.2026-10-30 > err.txt
  marvinctl --tenant weewx grep database /srv/docker/weewx/logs/weewx.log.2026-10-30 > rec.txt
  ops/garbage_gap_corr.py err.txt rec.txt

OUTPUT
------
Three blocks: totals; every archive gap (consecutive records more than one
interval apart) with the last driver rejection in the 10 minutes before it;
every driver rejection with whether a gap started within 5 minutes after it.
The co-rejection line that follows a bounds or message-type proof, and the
baseline-resync reject that follows a delta reject, belong to the same frame;
read the rejection block in pairs. A gap with no rejection before it is one of:
a restart or deploy (the crcstats line shows a slot-0 dwell), an outage, or a
noise decode whose payload passed the filters (not separable at prod's log
level). Restarts are not detected here; cross them off from CONSTANTS.md.

ARCHIVE INTERVAL
----------------
Assumed 60 s (prod). Pass --interval for another station.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys

LINE = re.compile(r"^(\S+) (\S+),\d+ (\S+) (\w+) (.*)$")
RECORD = re.compile(r"Added record (\S+ \S+) ")


def parse(paths: list[str]) -> tuple[list[tuple[dt.datetime, str]], list[dt.datetime]]:
    rejections: list[tuple[dt.datetime, str]] = []
    records: list[dt.datetime] = []
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = LINE.match(line.rstrip())
                if not m:
                    continue
                src, msg = m[3], m[5]
                if src == "user.rtldavis" and ("rejecting" in msg or "unknown message type" in msg):
                    when = dt.datetime.strptime(m[1] + " " + m[2], "%Y-%m-%d %H:%M:%S")
                    rejections.append((when, msg))
                elif src == "weewx.manager" and "to database" in msg:
                    r = RECORD.search(msg)
                    if r:
                        records.append(dt.datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S"))
    rejections.sort()
    records = sorted(set(records))
    return rejections, records


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("paths", nargs="+", help="weewx.log files or grep extracts")
    ap.add_argument("--interval", type=int, default=60, help="archive interval in seconds")
    args = ap.parse_args(argv)

    rejections, records = parse(args.paths)
    gaps: list[tuple[dt.datetime, dt.datetime, int]] = []
    for a, b in zip(records, records[1:]):
        missing = int((b - a).total_seconds() // args.interval) - 1
        if missing >= 1:
            gaps.append((a, b, missing))

    before = dt.timedelta(minutes=10)
    after = dt.timedelta(minutes=5)
    slack = dt.timedelta(minutes=1)

    print(f"records={len(records)} driver_rejections={len(rejections)} gaps={len(gaps)}")
    print("\n== archive gaps: last record, next record, missing, last rejection within 10 min before")
    for a, b, missing in gaps:
        prior = [(t, m) for t, m in rejections if a - slack <= t <= a + before and t < b]
        tag = f"  <- {prior[-1][0].time()} {prior[-1][1][:60]}" if prior else ""
        print(f"{a}  {b.time()}  miss={missing:2d}{tag}")
    print("\n== driver rejections: time, message, gap starting within 5 min after")
    for t, m in rejections:
        hit = [missing for a, _b, missing in gaps if t - slack <= a <= t + after]
        tag = f"GAP {hit[0]} missing" if hit else "-"
        print(f"{t}  {m[:75]:75s}  {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
