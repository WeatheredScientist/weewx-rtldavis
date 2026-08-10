#!/usr/bin/env bash
# freeze_watch.sh — read-only diagnostic watcher for the DEC-0067/DEC-0068 process
# freeze (weewxd stops advancing weewx.log for ~2-4 min, roughly once a day, cause
# still not fully explained). Rebuilt from session-transcript archaeology three
# times (S63, S64, S65) before landing here — commit it so a fourth rebuild is
# never needed.
#
# WHAT IT DOES: polls weewx.log's size over SSH (via `nasctl`, read-only). On a
# stall (two consecutive unchanged polls), captures a paired S/D/R thread-state
# sample 20s apart for the 12 named threads, plus loadavg and a `nasctl ps`
# snapshot (to catch coffee-radar's one-shot batch container or anything else
# running at that moment — DEC-0068 found this correlation). Waits for the log
# to regrow before re-arming, so one long freeze can't be double/triple-counted
# as several distinct catches (the exact bug that burned S65's first run's whole
# MAX_CATCH budget on a single ~4 min event). Fires a native macOS notification
# per catch and on exit, so it can run fully unattended (`nohup caffeinate -i
# ./freeze_watch.sh &`) with no Claude session or cloud connectivity needed.
#
# WHAT IT DOES NOT DO: no NAS deploy, no mutation, nothing beyond `nasctl`'s
# read-only surface (cat/stat/grep/ps on fixed, absolute paths).
#
# ⚠️ PIDS/CID BELOW ARE A SNAPSHOT, NOT DISCOVERED AT RUNTIME. They're only
# valid while `weewx-rtldavis-v2` is the same container instance (check with
# `nasctl inspect weewx-rtldavis-v2 | grep -i '"Id"\|StartedAt'` — unchanged CID
# and StartedAt means the PIDs below still apply). If it's been recreated
# (`kill`+`rm`+`run`, not just restarted), regenerate both:
#   CID:  nasctl inspect weewx-rtldavis-v2 | grep '"Id"' (first hit, 64 chars)
#   PIDS: nasctl cat /sys/fs/cgroup/cpuacct/docker/$CID/tasks
#         — for each resulting TID, `nasctl cat /proc/$TID/stat | awk '{print $2,$3}'`
#           to see its (comm) name; hand-pick one representative TID per named
#           worker (weewxd ×1, rtldavis ×N, stderr-thread ×1, one per REST
#           uploader) the same way this list was built — the raw tasks file
#           usually has ~2x as many TIDs as there are named workers.

set -u

CID=7228133a73712c5e4e742cc9b183667de0bb82ebcf294ebe62faa84575ba6c97
PIDS="30384 30439 30460 30485 30506 30588 30651 30654 30680 30687 32355 32493"
LOG=/volume1/docker/weewx-rtldavis/logs/weewx.log
OUT="$(dirname "$0")/stall-capture.txt"
POLL=30
NEED=2
MAX_CATCH=3
DEADLINE=$(( $(date +%s) + 15*3600 ))
RECOVERY_TIMEOUT=1800   # give up waiting for regrowth after 30 min, resume polling anyway

note() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$OUT"; }

notify() {
  local title="$1" body="$2"
  osascript -e "display notification \"$body\" with title \"$title\" sound name \"Glass\"" >/dev/null 2>&1
}

# raw `nasctl ps` output, one line per container (CONTAINER ID/IMAGE/COMMAND/
# CREATED/STATUS/PORTS/NAMES) — kept whole so callers can grep either the IMAGE
# or NAMES column, since a one-shot container run without --name (coffee-radar's
# own scheduled command does this) gets a Docker-random NAME with its real
# identity only visible in IMAGE. Grepping just the NAMES column, as this script
# did through the first half of S65, silently never matches such a container.
nas_ps_raw() {
  nasctl ps 2>&1 | grep -v 'post-quantum\|vulnerable\|upgraded\|openssh.com' | tail -n +2
}

nas_container_names() {
  nas_ps_raw | awk '{print $NF}' | tr '\n' ' '
}

coffee_radar_present() {
  nas_ps_raw | grep -q 'coffee-radar' && echo yes || echo no
}

# sets global SAW_D=1 if any thread reads D (uninterruptible sleep) this sample
SAW_D=0
sample() {
  local label="$1"
  note "--- $label ---"
  local tmpdir
  tmpdir=$(mktemp -d)
  for p in $PIDS; do
    ( nasctl cat "/proc/$p/stat" 2>/dev/null | awk -v p="$p" '{print "  pid="p"  "$2" "$3}' > "$tmpdir/$p" ) &
  done
  wait
  # single retry pass for any straggler (no SSH multiplexing means an occasional
  # one-of-12 connection can drop under load; retrying serially costs nothing
  # when there are 0-1 stragglers, which is the common case)
  for p in $PIDS; do
    if [ ! -s "$tmpdir/$p" ]; then
      nasctl cat "/proc/$p/stat" 2>/dev/null | awk -v p="$p" '{print "  pid="p"  "$2" "$3}' > "$tmpdir/$p"
    fi
  done
  for p in $PIDS; do
    if [ -s "$tmpdir/$p" ]; then
      cat "$tmpdir/$p" >> "$OUT"
      grep -q ' D$' "$tmpdir/$p" && SAW_D=1
    else
      note "  pid=$p  NO-RESPONSE (after retry)"
    fi
  done
  rm -rf "$tmpdir"
}

note "watcher started (freeze_watch.sh). CID=$CID deadline=$(date -u -r "$DEADLINE" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "@$DEADLINE" +%Y-%m-%dT%H:%M:%SZ)"
notify "weewx freeze-watcher" "Started. Watching through $(date -u -r "$DEADLINE" +%H:%M 2>/dev/null || date -u -d "@$DEADLINE" +%H:%M) UTC, up to $MAX_CATCH distinct freezes."

caught=0
same=0
last_sz=""
while [ "$(date +%s)" -lt "$DEADLINE" ] && [ "$caught" -lt "$MAX_CATCH" ]; do
  sz=$(nasctl stat "$LOG" 2>/dev/null | grep -oE 'Size: [0-9]+' | head -1 | awk '{print $2}')
  if [ -n "$sz" ] && [ "$sz" = "$last_sz" ]; then
    same=$((same+1))
  else
    same=0
  fi
  last_sz="$sz"

  if [ "$same" -eq "$NEED" ]; then
    caught=$((caught+1))
    t0=$(date +%s)
    SAW_D=0
    note ""
    note "########## STALL DETECTED (#$caught) — log size frozen at $sz ##########"
    note "loadavg: $(nasctl cat /proc/loadavg 2>/dev/null)"
    note "cpu-jiffies: $(nasctl grep cpu /proc/stat 2>/dev/null | head -1)"
    note "nas containers: $(nas_container_names)"
    cr_before=$(coffee_radar_present)
    sample "sample 1 (t+0s)"
    sleep 20
    sample "sample 2 (t+20s)"
    note "cpu-jiffies: $(nasctl grep cpu /proc/stat 2>/dev/null | head -1)"
    note "nas containers: $(nas_container_names)"
    cr_after=$(coffee_radar_present)
    t1=$(date +%s)
    note "capture wall time: $((t1 - t0))s"

    # wait for recovery (log growth) before re-arming, so a long freeze isn't
    # re-caught as a second/third "distinct" event
    recovered=0
    wait_start=$(date +%s)
    while [ $(( $(date +%s) - wait_start )) -lt "$RECOVERY_TIMEOUT" ] && [ "$(date +%s)" -lt "$DEADLINE" ]; do
      sleep "$POLL"
      newsz=$(nasctl stat "$LOG" 2>/dev/null | grep -oE 'Size: [0-9]+' | head -1 | awk '{print $2}')
      if [ -n "$newsz" ] && [ "$newsz" != "$sz" ]; then
        recovered=1
        recovered_at=$(date +%s)
        note "recovered: size now $newsz, freeze span (detection-to-recovery) ~$((recovered_at - t0))s"
        last_sz="$newsz"
        break
      fi
    done
    [ "$recovered" -eq 0 ] && note "recovery wait timed out after ${RECOVERY_TIMEOUT}s — resuming polling anyway"

    dstate_txt="no D states (all S, consistent with prior captures)"
    [ "$SAW_D" -eq 1 ] && dstate_txt="D STATE SEEN — uninterruptible I/O wait, new finding"
    cr_note=""
    if [ "$cr_before" = "yes" ] || [ "$cr_after" = "yes" ]; then
      cr_note=" coffee-radar container WAS present (DEC-0068)."
    fi
    notify "weewx freeze caught (#$caught)" "Log frozen at $sz. $dstate_txt.$cr_note See stall-capture.txt."

    note "########## end capture #$caught ##########"
    same=0
  fi
  sleep "$POLL"
done

note "watcher exiting: caught=$caught deadline_hit=$([ "$(date +%s)" -ge "$DEADLINE" ] && echo yes || echo no)"
notify "weewx freeze-watcher finished" "Caught $caught distinct freeze(s). $([ "$(date +%s)" -ge "$DEADLINE" ] && echo "Hit the 15h deadline." || echo "Hit the $MAX_CATCH-catch cap.")"
