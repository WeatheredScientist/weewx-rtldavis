#!/usr/bin/env bash
# proc_probe_watch.sh -- keep ops/proc_probe.py alive for a whole window.
#
# The probe samples a window that happens once a night (BOOT job 6 / DEC-0068).
# A driver that dies at 19:00 does not fail loudly; it just stops, and the
# measurement is gone until tomorrow. The probe already survives an ssh drop
# (one batch lost, run continues) -- this covers the layer above it: the driver
# PROCESS dying, from a crash, a kill, or the shell that started it going away.
#
# It relaunches with --resume, so the window being served comes from the state
# file rather than from arguments repeated here -- one source of truth, and no
# way for a relaunch to silently serve a different window than the original.
# Resume is idempotent: rows are timestamped and `--analyze` de-duplicates, so a
# relaunch that overlaps already-collected data costs nothing.
#
# WHAT THIS STILL DOES NOT SURVIVE, STATED PLAINLY:
#   Laptop sleep. Nothing scheduled locally runs while the machine is asleep,
#   and parking the loop on the NAS would mean a NAS write, which this probe is
#   scoped never to do. `caffeinate -i` below holds off IDLE sleep; closing the
#   lid still stops everything. On wake, recover with exactly one command:
#       ops/proc_probe.py --resume
#   The per-hour coverage report will show the gap rather than hiding it.
#
# Usage:
#   ops/proc_probe_watch.sh --start 15:00 --end 23:00
#   ops/proc_probe_watch.sh --resume            # after a wake or a manual stop
#
# Run it detached if you want it to outlive this shell:
#   nohup ops/proc_probe_watch.sh --start 15:00 --end 23:00 >> logs/proc_probe_run.log 2>&1 &
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1
PROBE="ops/proc_probe.py"
STATE="logs/proc_probe.state"
LOG="logs/proc_probe_watch.log"
mkdir -p logs

say() { echo "$(date '+%Y-%m-%d %H:%M:%S') watch: $*" | tee -a "$LOG"; }

# First launch takes the caller's arguments; every relaunch uses --resume so the
# window can only come from the state file.
ARGS=("$@")
attempt=0

while :; do
  attempt=$((attempt + 1))
  say "launching attempt $attempt: ${ARGS[*]}"
  caffeinate -i python3 "$PROBE" "${ARGS[@]}"
  rc=$?

  if [ $rc -eq 0 ]; then
    say "probe exited cleanly (rc=0) -- window served, watcher done"
    exit 0
  fi

  if [ ! -f "$STATE" ]; then
    say "probe exited rc=$rc and there is no state file -- cannot resume, giving up"
    exit 1
  fi

  # Past the window's end there is nothing left to serve; relaunching forever
  # would spin.
  END=$(python3 -c "import json,sys;print(int(json.load(open('$STATE'))['end']))" 2>/dev/null)
  NOW=$(date '+%s')
  if [ -n "${END:-}" ] && [ "$NOW" -ge "$END" ]; then
    say "probe exited rc=$rc but the window ended at $(date -r "$END" '+%H:%M') -- done"
    exit 0
  fi

  say "probe died (rc=$rc) with $(( (${END:-$NOW} - NOW) / 60 )) min of window left -- resuming in 10s"
  sleep 10
  ARGS=(--resume)
done
