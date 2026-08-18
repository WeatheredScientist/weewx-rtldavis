#!/usr/bin/env python3
"""Sample weewxd's kernel scheduler counters across a window (BOOT job 6, DEC-0068).

WHY THIS EXISTS
---------------
DEC-0094 established WHEN freezes happen (18:00-21:00 holds 12 vs 5.0 expected,
P=0.0027) but not WHY. DEC-0068 looked for the mechanism and reported the main
thread in `S`, never `D` -- so tenant load was established as present and never
as *blocking* us. S87 caught the load live (loadavg 9.05 on 4 cores, ~220% CPU
of a sibling tenant, ~14 MB/s on md2) and still found every weewxd thread in
`S`, records still arriving.

THE REASON THAT EVIDENCE WAS NEVER GOING TO SETTLE IT
------------------------------------------------------
Instantaneous state is the wrong instrument. A thread that blocks 50 ms at a
time, twenty times a second, loses a full second per second of wall clock and
will still be caught in `S` by essentially every periodic sample -- `D` is only
visible if a sample lands inside a block. Sampling `/proc/<pid>/stat` harder
does not fix this; it is a coverage problem, not a resolution problem.

The kernel already keeps the cumulative answer per task, and this box exposes
it (verified before this tool was written, 2026-08-18):

    /proc/<pid>/task/<tid>/schedstat   cpu_ns, runqueue_wait_ns, timeslices
    /proc/<pid>/task/<tid>/sched       se.statistics.iowait_sum   (ms, cumulative)
                                       se.statistics.iowait_count
                                       se.statistics.block_max    (ms, running MAX)
                                       se.statistics.wait_sum     (ms, cumulative)
                                       nr_involuntary_switches

Deltas between samples measure blocking that happened BETWEEN the samples, so
short blocks are counted rather than missed. That is the whole point of the
tool: it cannot be fooled by the sampling artifact that has stalled this
question twice.

WHAT THIS KERNEL DOES NOT HAVE -- MEASURED, NOT ASSUMED
--------------------------------------------------------
  * `/proc/pressure/*` (PSI) does not exist. Kernel is 4.4.302+; PSI landed in
    4.20. PSI would have been the single decisive instrument; it is not available
    and no amount of sampling substitutes for it.
  * `/proc/<pid>/wchan` reads `0`, not a symbol -- it cannot say WHAT we block on.
  * `/proc/<pid>/io` is 0400 and we are not root: permission denied. No
    per-process byte counts. md2's system-wide diskstats line is the substitute.

A CONTROL WINDOW IS PART OF THE MEASUREMENT, NOT A NICETY
----------------------------------------------------------
"weewxd accumulated N seconds of iowait during 18:00-21:00" answers nothing on
its own -- the first capability probe already found `block_max` at 4041 ms in a
four-hour span containing no evening at all, so blocking happens at baseline.
The claim under test is that the evening window is WORSE, which needs flanking
hours from the same night, same process, same tenant mix. Default span is
therefore 15:00-23:00: three control hours, the window, then two more.

THE ARM SWAP IS INSIDE THE WINDOW
----------------------------------
Campaign B swaps at 18:05 local, which kills and restarts the container -- a new
weewxd pid, and every counter above resets to zero. A delta across that boundary
is meaningless and a naive run would read the reset as a huge negative or as a
quiet stretch. Every row carries its pid; `--analyze` refuses to difference
across a pid change and reports the restart as its own row instead.

IT MUST SURVIVE A DROPPED CONNECTION AND A CLOSED SHELL
--------------------------------------------------------
The sampling loop necessarily runs on the LAPTOP: parking it on the NAS would
mean a NAS write, which this probe is scoped never to do. So the laptop is a
single point of failure for a window that only happens once a night, and a run
that dies at 19:00 silently loses the measurement it exists to take.

Three separate guards, because they fail differently:

  * ssh drop / NAS flake -- one batch is lost, not the run. `--batch` bounds the
    blast radius (default 300 s) and the driver logs the failure and continues.
  * driver process death (crash, kill, closed shell) -- `ops/proc_probe_watch.sh`
    relaunches it until the window's end time, and every relaunch resumes.
  * laptop sleep -- nothing local can run while asleep. This is stated, not
    solved: on wake, ONE command (`--resume`) picks the window back up.

Resume is safe by construction rather than by bookkeeping: every row carries an
absolute timestamp, the CSV is append-only, and `--analyze` de-duplicates on
(ts, kind, pid, tid). So re-running over a span already covered costs nothing and
corrupts nothing -- overlapping runs are idempotent. The window being served is
written to a state file so a resume never depends on the operator remembering
the original arguments, and coverage is reported per hour so a gap shows up as a
gap instead of quietly reshaping the result.

USAGE
    ops/proc_probe.py --start 15:00 --end 23:00      # sample (long-running)
    ops/proc_probe.py --resume                       # continue the saved window
    ops/proc_probe.py --duration 900                 # sample from now, 15 min
    ops/proc_probe.py --analyze logs/proc_probe.csv  # summarize a completed run
    ops/proc_probe_watch.sh --start 15:00 --end 23:00   # supervised (preferred)

Output is append-only CSV under `logs/` (gitignored: probe data must never reach
this PUBLIC repo). Read-only against the NAS throughout -- no write of any kind,
so this needs no Class C confirmation.

Connection facts come from ~/.claude/nas.env or the environment, same posture as
ops/soak_check.sh -- never from this repo (DEC-0012).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import sys
import time
from collections import defaultdict

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "logs", "proc_probe.csv")
DEFAULT_STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "logs", "proc_probe.state")
FIELDS = ["ts", "kind", "pid", "tid", "state", "cpu_ns", "runq_ns", "slices",
          "iowait_sum_ms", "iowait_count", "block_max_ms", "wait_sum_ms",
          "invol", "load1", "procs_blocked", "procs_running",
          "md2_weighted_ms", "md2_inflight"]

REMOTE = r"""
set -u
END=$(( $(date '+%s') + @BATCH@ ))
while [ "$(date '+%s')" -lt "$END" ]; do
  NOW=$(date '+%s')
  MAIN=""
  for p in /proc/[0-9]*; do
    pid=${p#/proc/}
    case "$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)" in
      *weewxd*) MAIN="$pid"; break ;;
    esac
  done
  LOAD=$(cut -d' ' -f1 /proc/loadavg)
  PB=$(awk '/^procs_blocked/{print $2}' /proc/stat)
  PR=$(awk '/^procs_running/{print $2}' /proc/stat)
  # /proc/diskstats after the name: $12 ios_in_progress, $13 ms_doing_io,
  # $14 weighted_ms_doing_io. $(NF-2) is $12 again on this kernel -- naming the
  # columns is what stops the two collapsing into one value.
  MDW=$(awk '$3=="md2"{print $14}' /proc/diskstats)
  MDI=$(awk '$3=="md2"{print $12}' /proc/diskstats)
  echo "$NOW|sys|${MAIN:-0}|${LOAD}|${PB}|${PR}|${MDW:-}|${MDI:-}"
  if [ -n "$MAIN" ] && [ -d "/proc/$MAIN/task" ]; then
    for t in /proc/$MAIN/task/*; do
      tid=${t##*/}
      [ -r "$t/stat" ] || continue
      ST=$(awk '{print $3}' "$t/stat" 2>/dev/null)
      SS=$(cat "$t/schedstat" 2>/dev/null)
      [ -z "$SS" ] && SS="0 0 0"
      # Anchor on the field name: a bare /wait_sum/ ALSO matches iowait_sum and
      # returns two lines, which silently blanked both columns in the first cut.
      IOS=$(awk '$1=="se.statistics.iowait_sum"{print $3}' "$t/sched" 2>/dev/null)
      IOC=$(awk '$1=="se.statistics.iowait_count"{print $3}' "$t/sched" 2>/dev/null)
      BMX=$(awk '$1=="se.statistics.block_max"{print $3}' "$t/sched" 2>/dev/null)
      WSM=$(awk '$1=="se.statistics.wait_sum"{print $3}' "$t/sched" 2>/dev/null)
      INV=$(awk '$1=="nr_involuntary_switches"{print $3}' "$t/sched" 2>/dev/null)
      echo "$NOW|thr|$MAIN|$tid|$ST|$(echo "$SS" | tr ' ' '|')|${IOS:-}|${IOC:-}|${BMX:-}|${WSM:-}|${INV:-}"
    done
  fi
  sleep @INTERVAL@
done
"""


def load_env():
    path = os.path.expanduser("~/.claude/nas.env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            line = line[7:].strip() if line.startswith("export ") else line
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    port, user, host = (os.environ.get("NAS_PORT"), os.environ.get("NAS_USER"),
                        os.environ.get("NAS_HOST"))
    if not (port and user and host):
        sys.exit("NAS_PORT/NAS_USER/NAS_HOST unset -- export them or create "
                 "~/.claude/nas.env (see the gitignored local-infra doc).")
    return port, user, host


# Each row kind emits only its own columns, named here rather than padded to a
# common width on the remote side. The first cut padded with literal `|` runs and
# put loadavg in the wait_sum column -- a silent two-column shift that the CSV
# header made look correct.
SYS_COLS = ["ts", "kind", "pid", "load1", "procs_blocked", "procs_running",
            "md2_weighted_ms", "md2_inflight"]
THR_COLS = ["ts", "kind", "pid", "tid", "state", "cpu_ns", "runq_ns", "slices",
            "iowait_sum_ms", "iowait_count", "block_max_ms", "wait_sum_ms", "invol"]


def parse_line(line):
    parts = line.rstrip("\n").split("|")
    if len(parts) < 3:
        return None
    cols = SYS_COLS if parts[1] == "sys" else THR_COLS if parts[1] == "thr" else None
    if cols is None or len(parts) != len(cols):
        return None
    return dict(zip(cols, parts))


def run_batch(port, user, host, batch_s, interval_s):
    script = REMOTE.replace("@BATCH@", str(batch_s)).replace("@INTERVAL@", str(interval_s))
    proc = subprocess.run(["ssh", "-p", port, f"{user}@{host}", "bash -s"],
                          input=script, capture_output=True, text=True,
                          timeout=batch_s + 120)
    if proc.returncode != 0:
        return None, proc.stderr.strip()[:200]
    return proc.stdout.splitlines(), None


def last_row_ts(path):
    """Newest timestamp already on disk, so a resume can report its own gap."""
    newest = 0
    try:
        with open(path) as f:
            for r in csv.DictReader(f):
                try:
                    newest = max(newest, int(r["ts"]))
                except (TypeError, ValueError, KeyError):
                    continue
    except OSError:
        return 0
    return newest


def sample(args):
    port, user, host = load_env()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    if args.resume:
        try:
            st = json.load(open(args.state))
        except (OSError, ValueError) as e:
            sys.exit(f"--resume: cannot read {args.state} ({e}). Start a fresh run "
                     f"with --start/--end instead.")
        args.out = st.get("out", args.out)
        end = float(st["end"])
        if time.time() >= end:
            print(f"window already ended at "
                  f"{dt.datetime.fromtimestamp(end):%Y-%m-%d %H:%M} -- nothing to resume.")
            return
    elif args.duration:
        end = time.time() + args.duration
    else:
        now = dt.datetime.now()
        sh, sm = map(int, args.start.split(":"))
        eh, em = map(int, args.end.split(":"))
        start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        end_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        if end_dt <= start_dt:
            end_dt += dt.timedelta(days=1)
        if start_dt > now:
            wait = (start_dt - now).total_seconds()
            print(f"waiting {wait/60:.1f} min until {args.start} local", flush=True)
            time.sleep(wait)
        end = end_dt.timestamp()

    # The window is persisted so a resume never depends on the operator recalling
    # the original arguments -- that recall is exactly what fails at 02:00.
    try:
        os.makedirs(os.path.dirname(args.state), exist_ok=True)
        with open(args.state, "w") as sf:
            json.dump({"end": end, "out": os.path.abspath(args.out),
                       "interval": args.interval, "batch": args.batch}, sf)
    except OSError as e:
        print(f"warning: could not write state file ({e}); --resume will not work",
              flush=True)

    fresh = not os.path.exists(args.out) or os.path.getsize(args.out) == 0
    if not fresh:
        prev = last_row_ts(args.out)
        if prev:
            gap = time.time() - prev
            print(f"resuming into {args.out}; last row "
                  f"{dt.datetime.fromtimestamp(prev):%H:%M:%S}, gap {gap/60:.1f} min "
                  f"({'no data lost' if gap < args.interval * 3 else 'GAP -- those minutes are absent'})",
                  flush=True)

    with open(args.out, "a", newline="") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(FIELDS)
        f.flush()
        batches = fails = rows = 0
        while time.time() < end:
            remaining = end - time.time()
            batch = int(min(args.batch, remaining))
            if batch < args.interval:
                break
            lines, err = run_batch(port, user, host, batch, args.interval)
            batches += 1
            if lines is None:
                fails += 1
                print(f"[{dt.datetime.now():%H:%M:%S}] batch failed ({err}) -- "
                      f"continuing", flush=True)
                time.sleep(5)
                continue
            for line in lines:
                rec = parse_line(line)
                if rec is None:
                    continue
                w.writerow([rec.get(k, "") for k in FIELDS])
                rows += 1
            f.flush()
            print(f"[{dt.datetime.now():%H:%M:%S}] batch {batches} ok, "
                  f"{rows} rows total", flush=True)
    print(f"done: {batches} batches ({fails} failed), {rows} rows -> {args.out}")


def analyze(path):
    # De-duplicate on (ts, kind, pid, tid): a resumed or overlapping run may
    # re-cover a span already on disk, and double-counting one sample's delta
    # would inflate exactly the quantity under test. Idempotence is what makes
    # "just run it again" a safe recovery instruction.
    seen = {}
    dupes = 0
    with open(path) as f:
        for r in csv.DictReader(f):
            key = (r.get("ts"), r.get("kind"), r.get("pid"), r.get("tid"))
            if key in seen:
                dupes += 1
                continue
            seen[key] = r
    sysrows, thr = [], defaultdict(list)
    for r in seen.values():
        if r["kind"] == "sys":
            sysrows.append(r)
        elif r["kind"] == "thr":
            thr[(r["pid"], r["tid"])].append(r)
    sysrows.sort(key=lambda r: int(r["ts"]))
    if not sysrows:
        sys.exit("no samples in file")
    if dupes:
        print(f"note: {dupes} duplicate rows collapsed (overlapping runs) -- "
              f"deltas counted once")

    def fl(x, d=0.0):
        try:
            return float(x)
        except (TypeError, ValueError):
            return d

    pids = sorted({r["pid"] for r in sysrows if r["pid"] not in ("", "0")})
    t0 = dt.datetime.fromtimestamp(int(sysrows[0]["ts"]))
    t1 = dt.datetime.fromtimestamp(int(sysrows[-1]["ts"]))
    print(f"span {t0:%Y-%m-%d %H:%M} -> {t1:%H:%M} local, {len(sysrows)} system samples")
    print(f"weewxd pids seen: {', '.join(pids)}"
          f"{'  <-- RESTART inside the span; deltas are not differenced across it'
             if len(pids) > 1 else ''}")

    # Sampling interval, inferred rather than assumed -- the file may span runs
    # started with different --interval values.
    deltas = sorted({int(b["ts"]) - int(a["ts"])
                     for a, b in zip(sysrows, sysrows[1:])
                     if int(b["ts"]) > int(a["ts"])})
    interval = deltas[len(deltas) // 2] if deltas else 15
    max_gap = interval * 3

    # Per-hour aggregates. iowait/wait are cumulative per (pid,tid): sum the
    # positive deltas only, never across a pid change (the counters reset), and
    # NEVER across a sampling gap -- a resume after two hours would otherwise
    # charge two hours of accumulated iowait to the single hour it landed in,
    # inflating exactly the quantity under test.
    per_hour = defaultdict(lambda: {"iowait": 0.0, "runq": 0.0, "blockmax": 0.0,
                                    "d": 0, "n": 0, "load": [], "pb": [],
                                    "spanned": 0})
    for (pid, tid), rows in thr.items():
        rows.sort(key=lambda r: int(r["ts"]))
        for a, b in zip(rows, rows[1:]):
            h = dt.datetime.fromtimestamp(int(b["ts"])).hour
            if int(b["ts"]) - int(a["ts"]) > max_gap:
                per_hour[h]["spanned"] += 1
                continue
            di = fl(b["iowait_sum_ms"]) - fl(a["iowait_sum_ms"])
            dr = fl(b["runq_ns"]) - fl(a["runq_ns"])
            if di > 0:
                per_hour[h]["iowait"] += di
            if dr > 0:
                per_hour[h]["runq"] += dr / 1e6
            per_hour[h]["blockmax"] = max(per_hour[h]["blockmax"], fl(b["block_max_ms"]))
    for r in sysrows:
        h = dt.datetime.fromtimestamp(int(r["ts"])).hour
        per_hour[h]["n"] += 1
        per_hour[h]["load"].append(fl(r["load1"]))
        per_hour[h]["pb"].append(fl(r["procs_blocked"]))
    for (pid, tid), rows in thr.items():
        for r in rows:
            if r["state"] == "D":
                per_hour[dt.datetime.fromtimestamp(int(r["ts"])).hour]["d"] += 1

    expected = 3600 // interval if interval else 0
    print(f"\nsampling interval {interval}s -> {expected} samples/hour at full coverage")
    print(f"{'hour':<6}{'samples':>8}{'cover':>7}{'load1 avg':>11}{'procs_blkd':>12}"
          f"{'iowait s':>10}{'runq s':>9}{'D hits':>8}")
    for h in sorted(per_hour):
        v = per_hour[h]
        lo = sum(v["load"]) / len(v["load"]) if v["load"] else 0
        pb = sum(v["pb"]) / len(v["pb"]) if v["pb"] else 0
        cov = (100.0 * v["n"] / expected) if expected else 0.0
        mark = "  <== evening window" if 18 <= h < 21 else ""
        if v["spanned"]:
            mark += f"  [{v['spanned']} gap-spanning deltas dropped]"
        print(f"{h:02d}:00{v['n']:>8}{cov:>6.0f}%{lo:>11.2f}{pb:>12.2f}"
              f"{v['iowait']/1000:>10.1f}{v['runq']/1000:>9.1f}{v['d']:>8}{mark}")
    thin = [h for h in per_hour if expected and per_hour[h]["n"] < 0.5 * expected]
    if thin:
        print(f"  WARNING: hours with under 50% coverage: "
              f"{', '.join(f'{h:02d}:00' for h in sorted(thin))} -- rates per sample")
        print("  remain comparable, but treat these hours as weakly measured.")

    win = [h for h in per_hour if 18 <= h < 21]
    ctl = [h for h in per_hour if h not in win]
    if win and ctl:
        def rate(hs, key):
            tot = sum(per_hour[h][key] for h in hs)
            n = sum(per_hour[h]["n"] for h in hs)
            return tot / n if n else 0.0
        print("\nEVENING WINDOW vs CONTROL HOURS (per system sample)")
        for key, label, div in (("iowait", "iowait ms/sample", 1),
                                ("runq", "runq-wait ms/sample", 1)):
            w_, c_ = rate(win, key) / div, rate(ctl, key) / div
            ratio = (w_ / c_) if c_ else float("inf")
            print(f"  {label:<24} window {w_:9.1f}   control {c_:9.1f}   "
                  f"ratio {ratio:5.2f}x")
        wl = [x for h in win for x in per_hour[h]["load"]]
        cl = [x for h in ctl for x in per_hour[h]["load"]]
        print(f"  {'loadavg1':<24} window {sum(wl)/len(wl):9.2f}   "
              f"control {sum(cl)/len(cl):9.2f}")
        print("\n  Interpretation is NOT automatic: high load with a flat iowait ratio")
        print("  means the tenant is loud but not blocking us -- DEC-0068's open")
        print("  question answered NEGATIVE, which is a real result. Only a raised")
        print("  iowait/runq ratio supports the blocking mechanism.")


def ingest(src, out):
    """Fold a NAS-side run's pipe-delimited stream into the CSV.

    ops/proc_probe_nas.sh emits exactly the stream the ssh loop emits, so this
    reuses parse_line() rather than introducing a second format. Merging is
    idempotent: --analyze de-duplicates on (ts, kind, pid, tid), so ingesting the
    same file twice, or a file overlapping a laptop-side run, cannot double-count.
    """
    fresh = not os.path.exists(out) or os.path.getsize(out) == 0
    kept = skipped = 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "a", newline="") as f:
        w = csv.writer(f)
        if fresh:
            w.writerow(FIELDS)
        for line in open(src, errors="replace"):
            rec = parse_line(line)
            if rec is None:
                skipped += 1
                continue
            w.writerow([rec.get(k, "") for k in FIELDS])
            kept += 1
    print(f"ingested {kept} rows from {src} -> {out}"
          f"{f' ({skipped} unparseable lines skipped)' if skipped else ''}")
    print("run --analyze next; duplicates across runs are collapsed there.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", default="15:00", help="local start HH:MM")
    ap.add_argument("--end", default="23:00", help="local end HH:MM")
    ap.add_argument("--duration", type=int, default=0,
                    help="sample N seconds from now instead of a clock window")
    ap.add_argument("--interval", type=int, default=15, help="seconds between samples")
    ap.add_argument("--batch", type=int, default=300,
                    help="seconds per ssh connection (bounds the loss of one drop)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--state", default=DEFAULT_STATE,
                    help="where the served window is persisted for --resume")
    ap.add_argument("--resume", action="store_true",
                    help="continue the window saved in --state (after a crash, "
                         "a dropped shell, or laptop sleep)")
    ap.add_argument("--analyze", metavar="CSV", help="summarize a completed run")
    ap.add_argument("--ingest", metavar="FILE",
                    help="fold a NAS-side proc_probe_nas.log into --out (idempotent)")
    args = ap.parse_args()
    if args.analyze:
        analyze(args.analyze)
        return 0
    if args.ingest:
        ingest(args.ingest, args.out)
        return 0
    sample(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
