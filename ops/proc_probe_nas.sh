#!/bin/bash
# proc_probe_nas.sh -- the job-6 sampler, running ON the NAS instead of the laptop.
#
# WHY THIS EXISTS (and why the laptop version was not enough)
# -----------------------------------------------------------
# BOOT job 6 scoped the probe "read-only from the laptop over ssh, no NAS write",
# and ops/proc_probe.py honours that. But the windows worth sampling are the
# evening (18:00-21:00, DEC-0094's freeze cluster) and 00:00-04:00 (DEC-0097's
# RF-dead cluster) -- so a faithful run needs the operator's laptop awake through
# the night. That is not a limitation to document, it is an infeasible design:
# nothing local runs while a laptop is asleep, and the overnight window can never
# be captured that way at all.
#
# The NAS is already always-on and already running the campaign. Sampling from
# here costs one Class C write (this file plus its output) and removes ~2,700 ssh
# round-trips, so the load on the box goes DOWN relative to driving it remotely.
#
# Output format is byte-identical to the pipe-delimited stream ops/proc_probe.py
# already parses, so there is exactly ONE parser for both paths:
#     <epoch>|sys|<pid>|<load1>|<procs_blocked>|<procs_running>|<md2_w>|<md2_inflight>
#     <epoch>|thr|<pid>|<tid>|<state>|<cpu_ns>|<runq_ns>|<slices>|<iowait_sum>|...
# Pull it down read-only and fold it in with:  ops/proc_probe.py --ingest FILE
#
# Deliberately NOT reinvented here: the CSV column padding. The laptop version's
# first cut mis-aligned system rows by two columns because it padded with literal
# `|` runs; emitting the same tagged stream and letting one Python parser place
# the fields is what stops that bug having a second home.
#
# Usage (normally launched detached by the deploy command, not by hand):
#     nohup ./proc_probe_nas.sh <end_epoch> [interval_s] >> proc_probe_nas.err 2>&1 &
#
# Stop early by creating the sentinel; the loop checks it every cycle:
#     <project root>/proc_probe.STOP
set -u

BASE="/volume1/docker/weewx-rtldavis"
OUT="$BASE/logs/proc_probe_nas.log"
STOP="$BASE/proc_probe.STOP"
PIDFILE="$BASE/proc_probe_nas.pid"

END="${1:-0}"
INTERVAL="${2:-15}"

if [ "$END" -le "$(date '+%s')" ]; then
  echo "end epoch $END is not in the future -- refusing to start" >&2
  exit 1
fi

echo $$ > "$PIDFILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') proc_probe_nas start pid=$$ end=$END interval=$INTERVAL" >&2

while [ "$(date '+%s')" -lt "$END" ]; do
  [ -f "$STOP" ] && { echo "$(date '+%Y-%m-%d %H:%M:%S') STOP sentinel -- exiting" >&2; break; }

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
  # $12 ios_in_progress, $14 weighted_ms_doing_io. Named explicitly: $(NF-2)
  # resolves to $12 on this kernel, which silently collapsed the two into one.
  MDW=$(awk '$3=="md2"{print $14}' /proc/diskstats)
  MDI=$(awk '$3=="md2"{print $12}' /proc/diskstats)
  echo "$NOW|sys|${MAIN:-0}|${LOAD}|${PB}|${PR}|${MDW:-}|${MDI:-}" >> "$OUT"

  if [ -n "$MAIN" ] && [ -d "/proc/$MAIN/task" ]; then
    for t in /proc/$MAIN/task/*; do
      tid=${t##*/}
      [ -r "$t/stat" ] || continue
      ST=$(awk '{print $3}' "$t/stat" 2>/dev/null)
      SS=$(cat "$t/schedstat" 2>/dev/null)
      [ -z "$SS" ] && SS="0 0 0"
      # Anchored on the field name: a bare /wait_sum/ ALSO matches iowait_sum
      # and returns two lines, which blanked both columns in the first cut.
      IOS=$(awk '$1=="se.statistics.iowait_sum"{print $3}' "$t/sched" 2>/dev/null)
      IOC=$(awk '$1=="se.statistics.iowait_count"{print $3}' "$t/sched" 2>/dev/null)
      BMX=$(awk '$1=="se.statistics.block_max"{print $3}' "$t/sched" 2>/dev/null)
      WSM=$(awk '$1=="se.statistics.wait_sum"{print $3}' "$t/sched" 2>/dev/null)
      INV=$(awk '$1=="nr_involuntary_switches"{print $3}' "$t/sched" 2>/dev/null)
      echo "$NOW|thr|$MAIN|$tid|$ST|$(echo "$SS" | tr ' ' '|')|${IOS:-}|${IOC:-}|${BMX:-}|${WSM:-}|${INV:-}" >> "$OUT"
    done
  fi

  sleep "$INTERVAL"
done

echo "$(date '+%Y-%m-%d %H:%M:%S') proc_probe_nas done pid=$$" >&2
rm -f "$PIDFILE"
