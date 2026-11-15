#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Pair the frames two receivers decoded from one ISS, and score the pairing (DEC-0236).

WHY THIS EXISTS
---------------
DEC-0236 pre-registers a measured run of a second receiver (the NAS, with an
RTL-SDR Blog V4L) against prod (marvin, the v3), both listening to the same
Davis ISS. Per-minute rxCheckPercent sits near 99.9 % on prod, so a bar on it
cannot tell a good second stream from a poor one. This script compares the
two streams frame by frame instead: of the frames prod decoded, which did the
NAS decode too, and where both decoded a frame in the same transmit slot, were
the bytes the same. It is merged before the run starts so the analysis is
fixed before any data exists; its sha is quoted in the pre-registration.

INPUT
-----
weewx.log files from each side, rotated or live, plain or .gz, or grep
extracts of them. Each side needs the driver at debug_rtld = 2 with a
[[[user.rtldavis]]] logger at DEBUG (DEC-0060), which logs every decoded
data frame as

  2026-11-20 20:31:04,105 user.rtldavis DEBUG data: 20:31:04.102918 E000000505009F3D 9 0 0 0

The Go decoder's own timestamp (the second time, microseconds) is the frame
time; the log line's date supplies the day, and a Go time more than 12 h
away from the log's time of day is taken as the day before or after
(midnight). Both hosts must log in the same local zone (the run is between
DST changes). Two more lines are counted on the --nas side, for the run's
stall and restart conditions:

  ... rtldavis process stalled                 (the driver's 150 s watchdog)
  ... rtldavis: US band, ISS channel 5, ...    (one per driver start)

From marvin, with no shell on the host, fetch prod's lines with the
read-only wrapper (one token, absolute path) and run locally:

  marvinctl --tenant weewx grep data: /srv/docker/weewx/logs/weewx.log.2026-11-20 > prod-1120.txt
  ops/ab_frames.py --prod prod-*.txt --nas nas-*.txt --start '2026-11-21 00:00' --end '2026-11-28 00:00'

METHOD (fixed by DEC-0236; change it only with a new DEC)
---------------------------------------------------------
1. Clock offset: for every prod frame, the NAS frames with identical bytes
   within +/-5 s give a time difference (NAS minus prod); the median of
   those is the offset. It is reported, and it is the NTP check.
2. NAS times are shifted by the offset. Each prod frame is then paired with
   an unused NAS frame within +/-1 s, identical bytes first, else the
   nearest. The ISS sends every (41 + id) / 16 s, 2.8125 s for channel 5,
   so a slot holds at most one frame per side.
3. Each prod frame ends as PAIRED (same bytes), DISAGREE (the NAS decoded a
   different frame in that slot) or PROD-ONLY; unused NAS frames are
   NAS-ONLY.
4. Coverage = PAIRED / prod frames (the bar), and PAIRED / NAS frames (the
   reverse, reported). Disagreement = DISAGREE / (PAIRED + DISAGREE), per
   10,000. Every DISAGREE is listed with both payloads.
5. Frames on either side inside --exclude windows (prod archive gaps,
   declared before the readout) are dropped from both sides.

The bars (DEC-0236): coverage >= 0.90, disagreement <= 1 per 10,000, zero
stalls and zero restarts in the window. Peak container memory under 200 MB
is read on the NAS by the owner and passed with --peak-mem-mb; without it
the verdict says that condition is unread, and cannot be a PASS.

EXIT
----
0 PASS, 1 FAIL or incomplete, 2 bad input (no frames on a side, a bad
window, an unparseable time).
"""

from __future__ import annotations

import argparse
import bisect
import datetime as dt
import gzip
import re
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Iterator

# The bars and method constants DEC-0236 fixes. Tests assert these values.
COVERAGE_BAR = 0.90
DISAGREE_PER_10K_BAR = 1.0
MEM_BAR_MB = 200.0
OFFSET_WINDOW_S = 5.0
PAIR_WINDOW_S = 1.0
MIN_OFFSET_PAIRS = 100

LOG_PREFIX = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d):(\d\d):(\d\d),\d+ ")
DATA = re.compile(r" data: (\d\d):(\d\d):(\d\d)\.(\d{6}) ([0-9A-F]{16})\b")
STALL = "rtldavis process stalled"
START = re.compile(r"rtldavis: \w+ band, ISS channel ")
TIME_FMT = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class Frame:
    t: float          # seconds since the epoch, naive local time read as UTC
    hex: str


@dataclass
class Side:
    frames: list[Frame] = field(default_factory=list)
    stalls: list[float] = field(default_factory=list)
    starts: list[float] = field(default_factory=list)


def _open(path: str) -> Iterator[str]:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as gz:
            yield from gz
    else:
        with open(path, encoding="utf-8", errors="replace") as fh:
            yield from fh


def _epoch(d: dt.datetime) -> float:
    return d.replace(tzinfo=dt.timezone.utc).timestamp()


def parse_lines(lines: Iterable[str]) -> Side:
    """Read one side's log lines. Lines without the weewx log prefix are skipped."""
    side = Side()
    for line in lines:
        m = LOG_PREFIX.match(line)
        if not m:
            continue
        day = dt.date.fromisoformat(m.group(1))
        log_tod = int(m.group(2)) * 3600 + int(m.group(3)) * 60 + int(m.group(4))
        log_t = _epoch(dt.datetime.combine(day, dt.time())) + log_tod
        d = DATA.search(line)
        if d:
            go_tod = (int(d.group(1)) * 3600 + int(d.group(2)) * 60 + int(d.group(3))
                      + int(d.group(4)) / 1e6)
            if go_tod - log_tod > 12 * 3600:
                go_tod -= 86400          # Go stamped before midnight, logged after
            elif log_tod - go_tod > 12 * 3600:
                go_tod += 86400          # cannot happen with a monotone clock; kept symmetric
            side.frames.append(Frame(log_t - log_tod + go_tod, d.group(5)))
        elif STALL in line:
            side.stalls.append(log_t)
        elif START.search(line):
            side.starts.append(log_t)
    side.frames.sort(key=lambda f: f.t)
    # The same file passed twice, or overlapping extracts, must not double-count.
    side.frames = [f for i, f in enumerate(side.frames) if i == 0 or f != side.frames[i - 1]]
    return side


def parse_files(paths: list[str]) -> Side:
    def lines() -> Iterator[str]:
        for p in paths:
            yield from _open(p)
    return parse_lines(lines())


def _inside(t: float, windows: list[tuple[float, float]]) -> bool:
    return any(a <= t < b for a, b in windows)


def restrict(side: Side, start: float, end: float, exclude: list[tuple[float, float]]) -> Side:
    def keep(t: float) -> bool:
        return start <= t < end and not _inside(t, exclude)
    return Side([f for f in side.frames if keep(f.t)],
                [t for t in side.stalls if start <= t < end],
                [t for t in side.starts if start <= t < end])


def estimate_offset(prod: list[Frame], nas: list[Frame]) -> tuple[float, int]:
    """Median (NAS minus prod) over identical-byte frames within OFFSET_WINDOW_S."""
    by_hex: dict[str, list[float]] = defaultdict(list)
    for f in nas:
        by_hex[f.hex].append(f.t)
    diffs = []
    for f in prod:
        ts = by_hex.get(f.hex)
        if not ts:
            continue
        i = bisect.bisect_left(ts, f.t - OFFSET_WINDOW_S)
        best = None
        while i < len(ts) and ts[i] <= f.t + OFFSET_WINDOW_S:
            if best is None or abs(ts[i] - f.t) < abs(best - f.t):
                best = ts[i]
            i += 1
        if best is not None:
            diffs.append(best - f.t)
    if not diffs:
        return 0.0, 0
    return statistics.median(diffs), len(diffs)


@dataclass
class Result:
    offset: float
    offset_pairs: int
    paired: int
    disagree: list[tuple[Frame, Frame]]
    prod_only: int
    nas_only: int
    prod_total: int
    nas_total: int
    per_day: dict[str, list[int]]   # date -> [prod, nas, paired, disagree]

    @property
    def coverage(self) -> float:
        return self.paired / self.prod_total if self.prod_total else 0.0

    @property
    def reverse_coverage(self) -> float:
        return self.paired / self.nas_total if self.nas_total else 0.0

    @property
    def disagree_per_10k(self) -> float:
        slots = self.paired + len(self.disagree)
        return 1e4 * len(self.disagree) / slots if slots else 0.0


def pair(prod: list[Frame], nas: list[Frame]) -> Result:
    offset, n_off = estimate_offset(prod, nas)
    shifted = [Frame(f.t - offset, f.hex) for f in nas]
    times = [f.t for f in shifted]
    used = [False] * len(shifted)
    paired = prod_only = 0
    disagree: list[tuple[Frame, Frame]] = []
    per_day: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])

    def day(t: float) -> str:
        return dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat()

    for f in shifted:
        per_day[day(f.t)][1] += 1
    for f in prod:
        per_day[day(f.t)][0] += 1
        lo = bisect.bisect_left(times, f.t - PAIR_WINDOW_S)
        hi = bisect.bisect_right(times, f.t + PAIR_WINDOW_S)
        cands = [j for j in range(lo, hi) if not used[j]]
        same = [j for j in cands if shifted[j].hex == f.hex]
        pool = same or cands
        if not pool:
            prod_only += 1
            continue
        j = min(pool, key=lambda k: abs(shifted[k].t - f.t))
        used[j] = True
        if shifted[j].hex == f.hex:
            paired += 1
            per_day[day(f.t)][2] += 1
        else:
            disagree.append((f, Frame(nas[j].t, nas[j].hex)))
            per_day[day(f.t)][3] += 1
    return Result(offset, n_off, paired, disagree, prod_only, used.count(False),
                  len(prod), len(nas), dict(per_day))


def verdict(res: Result, nas: Side, peak_mem_mb: float | None) -> tuple[bool, list[str]]:
    checks = [
        ("coverage (NAS of prod) >= %.2f" % COVERAGE_BAR, res.coverage >= COVERAGE_BAR,
         "%.4f" % res.coverage),
        ("disagreement <= %.1f per 10,000" % DISAGREE_PER_10K_BAR,
         res.disagree_per_10k <= DISAGREE_PER_10K_BAR, "%.2f" % res.disagree_per_10k),
        ("NAS stalls == 0", not nas.stalls, str(len(nas.stalls))),
        ("NAS restarts == 0", not nas.starts, str(len(nas.starts))),
    ]
    if peak_mem_mb is None:
        checks.append(("peak memory < %.0f MB" % MEM_BAR_MB, False, "UNREAD"))
    else:
        checks.append(("peak memory < %.0f MB" % MEM_BAR_MB, peak_mem_mb < MEM_BAR_MB,
                       "%.0f MB" % peak_mem_mb))
    if res.offset_pairs < MIN_OFFSET_PAIRS:
        checks.append(("clock offset from >= %d pairs" % MIN_OFFSET_PAIRS, False,
                       str(res.offset_pairs)))
    lines = ["  %-36s %-6s %s" % (name, "ok" if ok else "FAIL", val) for name, ok, val in checks]
    return all(ok for _, ok, _ in checks), lines


def _fmt(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _when(s: str) -> float:
    return _epoch(dt.datetime.strptime(s, TIME_FMT))


def _window(s: str) -> tuple[float, float]:
    a, sep, b = s.partition(",")
    if not sep:
        raise ValueError("an --exclude window is 'START,END', got %r" % s)
    lo, hi = _when(a.strip()), _when(b.strip())
    if hi <= lo:
        raise ValueError("an --exclude window ends before it starts: %r" % s)
    return lo, hi


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prod", nargs="+", required=True, help="prod weewx.log files or extracts")
    ap.add_argument("--nas", nargs="+", required=True, help="NAS weewx.log files or extracts")
    ap.add_argument("--start", required=True, help="window start, local 'YYYY-MM-DD HH:MM'")
    ap.add_argument("--end", required=True, help="window end (exclusive), same format")
    ap.add_argument("--exclude", action="append", default=[],
                    help="'START,END' to drop from both sides; repeatable")
    ap.add_argument("--peak-mem-mb", type=float, help="the NAS container's peak memory")
    a = ap.parse_args(argv)
    try:
        start, end = _when(a.start), _when(a.end)
        exclude = [_window(w) for w in a.exclude]
    except ValueError as e:
        print("ab_frames: %s" % e, file=sys.stderr)
        return 2
    if end <= start:
        print("ab_frames: --end is not after --start", file=sys.stderr)
        return 2
    prod = restrict(parse_files(a.prod), start, end, exclude)
    nas = restrict(parse_files(a.nas), start, end, exclude)
    for name, s in (("prod", prod), ("nas", nas)):
        if not s.frames:
            print("ab_frames: no data frames on the %s side in the window "
                  "(is debug_rtld 2 and the user.rtldavis logger at DEBUG?)" % name,
                  file=sys.stderr)
            return 2
    res = pair(prod.frames, nas.frames)
    ok, checks = verdict(res, nas, a.peak_mem_mb)

    print("window      %s to %s, %d exclusion(s), %.1f h excluded"
          % (a.start, a.end, len(exclude), sum(b - x for x, b in exclude) / 3600))
    print("offset      %+.3f s (NAS minus prod, median of %d identical-byte pairs)"
          % (res.offset, res.offset_pairs))
    print("frames      prod %d, NAS %d" % (res.prod_total, res.nas_total))
    print("outcome     paired %d, disagree %d, prod-only %d, NAS-only %d"
          % (res.paired, len(res.disagree), res.prod_only, res.nas_only))
    print("coverage    NAS of prod %.4f, prod of NAS %.4f (reverse, reported only)"
          % (res.coverage, res.reverse_coverage))
    print("disagree    %.2f per 10,000 paired slots" % res.disagree_per_10k)
    print()
    print("%-10s %8s %8s %8s %8s %9s" % ("date", "prod", "NAS", "paired", "disagree", "coverage"))
    for d in sorted(res.per_day):
        p, n, pr, ds = res.per_day[d]
        print("%-10s %8d %8d %8d %8d %9.4f" % (d, p, n, pr, ds, pr / p if p else 0.0))
    if res.disagree:
        print()
        print("disagreements (prod time, prod bytes, NAS bytes, NAS minus prod after offset):")
        for pf, nf in res.disagree:
            print("  %s  %s  %s  %+.3f s" % (_fmt(pf.t), pf.hex, nf.hex, nf.t - res.offset - pf.t))
    if nas.stalls or nas.starts:
        print()
        for t in nas.stalls:
            print("  NAS stall    %s" % _fmt(t))
        for t in nas.starts:
            print("  NAS restart  %s" % _fmt(t))
    print()
    print("verdict     %s" % ("PASS" if ok else "FAIL"))
    print("\n".join(checks))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
