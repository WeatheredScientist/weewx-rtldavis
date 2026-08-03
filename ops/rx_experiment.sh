#!/usr/bin/env bash
# rx_experiment.sh — the DEC-0048 designed RX experiment, as an apparatus.
#
# DEC-0048 said a proper RX test is "a stated hypothesis, a fixed observation
# window long enough to average out propagation and weather, a control arm, and a
# pre-registered success metric" — not a pile of image tags. This script IS that
# apparatus. The schedule table below is the pre-registration: it is fixed, static,
# and reviewable before a single block runs.
#
# WHY NOT ops/gain_sweep.sh (DEC-0014 documented cause for not extending it):
#   1. It is SEQUENTIAL — all reps of a gain run back to back, so every arm is
#      confounded with time-of-day and weather. That is the precise flaw DEC-0048
#      exists to replace.
#   2. Its metric is DEAD. It counts RAW_DATAPACKET_MATCH in weewx.log; that
#      logging moved behind debug_rtld and prod runs with it off (S52: zero RAW_
#      lines live). It would report 0.0% for every arm and look like it worked.
#   3. Its denominator is wrong — hardcoded 2.5s transmit period; this ISS
#      (transmitter 4) is ~2.8125s. Same ~13% error S29 fixed in the monitor.
#   4. No verification, no rollback, no abort, no container health check.
#
# WHAT THIS DOES NOT DO, on purpose:
#   no image build · no docker run/rm (only kill/start on the existing container)
#   no Docker Hub · no git · no deletions · no writes to the archive DB or InfluxDB
#
# SAFETY MODEL (the six properties that make an autonomous prod-config writer OK):
#   1. Arms are COMPLETE LITERAL command strings. The script never assembles a
#      command from parts. A bug can only ever select the wrong known-good arm,
#      never synthesize a malformed one.
#   2. The revert is a WHOLE-FILE snapshot restore, not line surgery. Byte-exact.
#   3. Writes are atomic (temp file + rename) and verified by re-reading before
#      the container is ever restarted.
#   4. The abort tripwire is STICKY — it drops a STOP sentinel that halts the
#      campaign until a human clears it. A later scheduled tick cannot override it.
#   5. The schedule SELF-TERMINATES into the production baseline. If everyone
#      forgets this is running, it ends at prod-normal, not on an experimental arm.
#   6. Every failure path restores the baseline snapshot and emails.
#
# Usage:
#   ops/rx_experiment.sh schedule     # print the block table and exit (review this)
#   ops/rx_experiment.sh install      # snapshot baseline, write state, arm nothing
#   ops/rx_experiment.sh tick         # scheduled entry point (every 5 min)
#   ops/rx_experiment.sh guard        # abort tripwire check (every 5 min)
#   ops/rx_experiment.sh status       # where are we
#   ops/rx_experiment.sh abort        # manual emergency stop -> restore baseline
#   DRY_RUN=1 ops/rx_experiment.sh tick    # print actions, touch nothing
#
# Exit 0 = nothing wrong. Exit 1 = a human needs to look.
set -uo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
# RX_BASE exists only so the dry-run harness can point at a fixture directory.
# Production always uses the default.
BASE="${RX_BASE:-/volume1/docker/weewx-rtldavis}"
CONF="$BASE/weewx-data/weewx.conf"
BASELINE_SNAP="$BASE/weewx.conf.rx-baseline"
STATE="$BASE/rx_experiment.state"
STOP="$BASE/rx_experiment.STOP"
XLOG="$BASE/logs/rx_experiment.log"
DATALOG="$BASE/logs/rx_experiment_data.log"
MONLOG="$BASE/logs/weewx_monitor.log"
WXLOG="$BASE/logs/weewx.log"
ENVFILE="$BASE/monitor.env"
DOCKER=/usr/local/bin/docker
CONTAINER=weewx-rtldavis-v2

DRY_RUN="${DRY_RUN:-0}"

# Abort tripwire — CAMPAIGN B (no LNA). The no-LNA baseline is genuinely unknown:
# the June plateau (rxCheckPercent 67.45, sd 3.22 on 5-min bins, n=4321) is the
# nearest anchor, but the record is ambiguous about its LNA state (DEC-0064), and
# the overnight pilot on 08-07 is the first honest no-LNA measurement. So the
# floor is deliberately forgiving: 50% sits ~5 SE below even a pessimistic 62%
# baseline on a 30-min mean. The pilot runs its gain arms HIGH -> LOW on purpose:
# if a low arm finds the cliff and trips this, the high arms are already
# harvested, prod restores to baseline, and the sticky STOP waits for morning —
# an overnight abort IS a pilot result, not a failure.
ABORT_PCT=50
ABORT_SAMPLES=6          # 6 x 5-min samples = 30 min
SETTLE_SECS=600          # ignore the first 10 min after a swap (restart transient)

# ── The arms ──────────────────────────────────────────────────────────────────
# CAMPAIGN B — LNA PHYSICALLY REMOVED (antenna -> coax -> dongle, bias tee OFF
# via the v2.0.12 image's BIAS_TEE=0). DEC-0064; campaign A was DEC-0059/0061.
#
# Three arm families, all spelled as complete literals (safety property #1):
#
#   P*  — the OVERNIGHT PILOT (08-07 00:35-04:20): gain-only, HIGH -> LOW, 45 min
#         each. Bounds the no-LNA gain curve and shakes down the whole apparatus
#         before the 8-day campaign commits. Pre-registered as ARM-SELECTION
#         INPUT ONLY — sequential and hour-confounded, never adoption evidence.
#   H   — the FRIDAY HOLD: identical settings to arm A but a distinct label, so
#         the daylong baseline-verification window harvests under its own tag
#         and can never contaminate arm A's campaign samples (the S60
#         phantom-block lesson, applied forward).
#   A-D — the campaign square. 2x2 factorial: gain {372, 496} x ex {0, 50}.
#         372 = incumbent and the CROSS-CAMPAIGN ANCHOR (same value ran in
#         campaign A, so the LNA contrast is measured at identical settings).
#         496 = R820T max (49.6 dB): with ~20 dB of front-end gain gone the
#         optimum moves up (do not reuse A's 207 — both its points would sit too
#         low). ex semantics unchanged from A: ex N == receiveWindow 300+N,
#         upstream sums them (verified lheijst/rtldavis master, DEC-0059).
#         -fc 0 -ppm 0 everywhere: changing them between campaigns would
#         confound the LNA contrast (DEC-0064).
arm_cmd() {
  case "$1" in
    P496) echo "    cmd = /usr/local/bin/rtldavis -gain 496 -v -fc 0 -ppm 0 -ex 0" ;;
    P449) echo "    cmd = /usr/local/bin/rtldavis -gain 449 -v -fc 0 -ppm 0 -ex 0" ;;
    P402) echo "    cmd = /usr/local/bin/rtldavis -gain 402 -v -fc 0 -ppm 0 -ex 0" ;;
    P372) echo "    cmd = /usr/local/bin/rtldavis -gain 372 -v -fc 0 -ppm 0 -ex 0" ;;
    P328) echo "    cmd = /usr/local/bin/rtldavis -gain 328 -v -fc 0 -ppm 0 -ex 0" ;;
    H)    echo "    cmd = /usr/local/bin/rtldavis -gain 372 -v -fc 0 -ppm 0 -ex 0" ;;
    A)    echo "    cmd = /usr/local/bin/rtldavis -gain 372 -v -fc 0 -ppm 0 -ex 0"  ;;
    B)    echo "    cmd = /usr/local/bin/rtldavis -gain 496 -v -fc 0 -ppm 0 -ex 0"  ;;
    C)    echo "    cmd = /usr/local/bin/rtldavis -gain 372 -v -fc 0 -ppm 0 -ex 50" ;;
    D)    echo "    cmd = /usr/local/bin/rtldavis -gain 496 -v -fc 0 -ppm 0 -ex 50" ;;
    *) return 1 ;;
  esac
}

# ── The schedule (THE PRE-REGISTRATION) ───────────────────────────────────────
# Three phases in one table; the tick machinery treats them identically.
#
# PHASE 1 — overnight pilot, Friday 08-07 00:35-04:20. Five 45-min gain blocks,
# HIGH -> LOW (see the arms comment for why), landing entirely inside the
# 00-06 best-reception hours and finishing before the site's hour-07 notch
# (BACKLOG §Durable RF findings). First row 00:35 leaves ~25 min after campaign
# A's 00:05 self-termination for: archiving A's artifacts, deploying the
# v2.0.12 image (bias tee off) on the owner's in-chat GO, the 20-40s physical
# LNA removal, health check, and `install`. due_arm() self-heals a late start —
# a slip shortens pilot block 1 rather than skipping it.
#
# PHASE 2 — the H hold, 04:20 Friday through Saturday 00:05. Baseline settings
# under a distinct label: the daylong no-LNA baseline-verification window,
# including how the hour-07/19 notch presents without the LNA.
#
# PHASE 3 — the campaign square, 08-08 00:05 -> 08-16 00:05. Latin square: each
# arm visits each 6h slot exactly twice over 8 days, so time-of-day and diurnal
# drift cancel instead of confounding.
#   Day 1: A B C D    Day 3: C D A B    Day 5: A B C D    Day 7: C D A B
#   Day 2: B C D A    Day 4: D A B C    Day 6: B C D A    Day 8: D A B C
# Slots are :05 past 00/06/12/18 local, so the monitor's 6h reception summary
# (which fires on the hour) has already closed the preceding block cleanly.
# Starting on a clean day boundary is the S57 lesson (the 07-29 mid-day start
# damaged three cells). The H->A swap at 08-08T00:05 is a real swap (different
# label, same settings): it restarts the container and harvests the hold under
# its own tag, so the square's arm-A samples start clean.
#
# NOTE: there is no `schedule --generate` mode — the comment that used to sit
# here promised one and the code never had it. The table is generated dev-side
# (never on the NAS, whose `date` lacks GNU semantics) by:
#   rows = ["A B C D","B C D A","C D A B","D A B C"] * 2
#   slots = ["00:05","06:05","12:05","18:05"]        # start + i days, zip(slots,row)
#   then one final "<start + 8 days>T00:05|BASELINE" self-terminator row.
# tests/test_rx_experiment.py machine-checks the balance, order, pilot
# structure, hold placement and terminator.
# LAST ROW IS THE SELF-TERMINATOR — arm "BASELINE" restores prod and stops.
SCHEDULE="
2026-08-10T00:35|P496
2026-08-10T01:20|P449
2026-08-10T02:05|P402
2026-08-10T02:50|P372
2026-08-10T03:35|P328
2026-08-10T04:20|H
2026-08-11T00:05|A
2026-08-11T06:05|B
2026-08-11T12:05|C
2026-08-11T18:05|D
2026-08-12T00:05|B
2026-08-12T06:05|C
2026-08-12T12:05|D
2026-08-12T18:05|A
2026-08-13T00:05|C
2026-08-13T06:05|D
2026-08-13T12:05|A
2026-08-13T18:05|B
2026-08-14T00:05|D
2026-08-14T06:05|A
2026-08-14T12:05|B
2026-08-14T18:05|C
2026-08-15T00:05|A
2026-08-15T06:05|B
2026-08-15T12:05|C
2026-08-15T18:05|D
2026-08-16T00:05|B
2026-08-16T06:05|C
2026-08-16T12:05|D
2026-08-16T18:05|A
2026-08-17T00:05|C
2026-08-17T06:05|D
2026-08-17T12:05|A
2026-08-17T18:05|B
2026-08-18T00:05|D
2026-08-18T06:05|A
2026-08-18T12:05|B
2026-08-18T18:05|C
2026-08-19T00:05|BASELINE
"

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$XLOG"; }

say_dry() { [ "$DRY_RUN" = "1" ] && printf 'DRY-RUN would: %s\n' "$*" && return 0; return 1; }

# Independent of weewx_monitor.py on purpose: if the monitor is wedged, the abort
# path must still be able to reach a human.
# S57: `. "$ENVFILE"` sets shell variables but does NOT export them, so the
# python3 heredoc below — a CHILD process — saw none of them and died on
# KeyError: 'ALERT_FROM'. Every alert this script could ever send was silently
# broken, including the abort notification, which is the one that matters most
# (measured 2026-07-29: the campaign aborted, restored baseline correctly, and
# told nobody). `set -a` marks subsequent assignments for export; `set +a`
# restores. Keep them paired around the source.
load_env() {
  [ -f "$ENVFILE" ] || return 1
  set -a
  # shellcheck disable=SC1090
  . "$ENVFILE"
  set +a
}

send_mail() {
  local subj="$1" body="$2"
  say_dry "email '$subj'" && return 0
  load_env || { log "MAIL SKIPPED (no $ENVFILE)"; return 1; }
  python3 - "$subj" "$body" <<'PYEOF' 2>>"$XLOG" || log "MAIL FAILED"
import os, smtplib, sys
from email.message import EmailMessage
m = EmailMessage()
m['Subject'] = f"{os.environ.get('STATION_NAME','PWS')} RX-EXPERIMENT: {sys.argv[1]}"
m['From'] = os.environ['ALERT_FROM']; m['To'] = os.environ['ALERT_TO']
m.set_content(sys.argv[2])
s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls()
s.login(os.environ['ALERT_FROM'], os.environ['GMAIL_PASS']); s.send_message(m); s.quit()
PYEOF
}

# State is ARM|EPOCH|HUMAN. The epoch is stored rather than parsed back out of a
# formatted string because `date -d` is GNU-only and DSM cannot be relied on for
# it — a silently-failing settle check would let the guard abort on the restart
# transient it is specifically supposed to ignore.
current_arm()     { [ -f "$STATE" ] && cut -d'|' -f1 "$STATE" || echo "NONE"; }
last_swap_epoch() { [ -f "$STATE" ] && cut -d'|' -f2 "$STATE" || echo "0"; }
last_swap_human() { [ -f "$STATE" ] && cut -d'|' -f3 "$STATE" || echo "1970-01-01 00:00:00"; }
write_state()     { echo "$1|$(date '+%s')|$(date '+%Y-%m-%d %H:%M:%S')" > "$STATE"; }

# Which arm should be live right now? Latest schedule row whose time <= now.
# Self-healing: a missed scheduler run swaps late rather than skipping a block.
# True (0) when the schedule's FIRST row has already passed -- i.e. installing
# now would join a campaign already in flight. S62/DEC-0066.
#
# due_arm() below picks the LATEST row whose time has passed, so a stale schedule
# does not fail loudly: it silently starts mid-square (no pilot, wrong block
# sequence), or, past the last row, returns BASELINE and records the campaign
# complete without ever running it. Both look like success.
#
# This exists because campaign B was prepared with dates that then went stale
# when the launch was held. A warning in BOOT.md would not have stopped it --
# prose does not execute (DEC-0040). Takes `now` as an optional argument purely
# so tests can pin a clock.
schedule_started() {
  local first now
  first="$(echo "$SCHEDULE" | grep -v '^$' | head -1 | cut -d'|' -f1)"
  now="${1:-$(date '+%Y-%m-%dT%H:%M')}"
  [ -z "$first" ] && return 1
  [[ "$first" > "$now" ]] && return 1
  return 0
}

due_arm() {
  local now; now="$(date '+%Y-%m-%dT%H:%M')"
  local want="NONE" line t a
  while IFS='|' read -r t a; do
    [ -z "$t" ] && continue
    [[ "$t" > "$now" ]] && break
    want="$a"
  done <<< "$(echo "$SCHEDULE" | grep -v '^$')"
  echo "$want"
}

# Whole-file atomic replacement of the single [Rtldavis] cmd line, then verify by
# re-reading. Never partial surgery; never a write left unverified.
write_arm() {
  local want_line="$1"
  python3 - "$CONF" "$want_line" <<'PYEOF'
import os, sys, tempfile
conf, want = sys.argv[1], sys.argv[2]
lines = open(conf).read().split('\n')
idx = [i for i, l in enumerate(lines)
       if l.strip().startswith('cmd = /usr/local/bin/rtldavis')]
if len(idx) != 1:
    sys.exit(f"ABORT: expected exactly 1 rtldavis cmd line, found {len(idx)}")
lines[idx[0]] = want
d = os.path.dirname(conf)
fd, tmp = tempfile.mkstemp(dir=d)
with os.fdopen(fd, 'w') as f:
    f.write('\n'.join(lines))
os.replace(tmp, conf)                      # atomic
check = [l for l in open(conf).read().split('\n')
         if l.strip().startswith('cmd = /usr/local/bin/rtldavis')]
if len(check) != 1 or check[0] != want:
    sys.exit("ABORT: post-write verification failed")
PYEOF
}

restore_baseline() {
  log "RESTORING baseline snapshot"
  say_dry "cp $BASELINE_SNAP $CONF; restart" && return 0
  [ -f "$BASELINE_SNAP" ] || { log "FATAL: no baseline snapshot at $BASELINE_SNAP"; return 1; }
  cp "$BASELINE_SNAP" "$CONF" || return 1
  restart_container
}

restart_container() {
  say_dry "$DOCKER kill $CONTAINER; sleep 3; $DOCKER start $CONTAINER" && return 0
  "$DOCKER" kill "$CONTAINER" >/dev/null 2>&1     # kill, never stop (DEC-0008)
  sleep 3                                          # S47: let the USB dongle release
  "$DOCKER" start "$CONTAINER" >/dev/null 2>&1
}

# Up is not healthy (DEC-0036 froze for 7h18m while reporting Up). Require a NEW
# archive record to appear — proof the driver is actually producing.
#
# HEALTH_TRIES budget, S57 — the original 18 (~90s) was too small BY CONSTRUCTION
# and aborted a live campaign 3 seconds early. A restart cannot produce a record
# faster than: weewx boot (~25s to "Starting main packet loop") + up to a full
# ARCHIVE_INTERVAL (60s) until the next archive boundary + the write lag after
# that boundary (~15-30s observed). Worst case ~115s; 90s could not cover it, so
# the check was a coin flip that arm B won and arm C lost. Measured on the real
# failure: weewxd init 12:11:46, first record 12:13:30 = 104s, abort at 12:13:27.
# 36 tries (~180s) clears the worst case with margin. Do not lower this without
# redoing that arithmetic — and note the loop is ALSO slower than its nominal
# sleep, because each pass greps a multi-MB log.
HEALTH_TRIES=36
health_ok() {
  say_dry "health check" && return 0
  local before after i
  before="$(grep -c 'Added record' "$WXLOG" 2>/dev/null || echo 0)"
  for i in $(seq 1 "$HEALTH_TRIES"); do
    sleep 5
    [ "$("$DOCKER" inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" = "true" ] || continue
    after="$(grep -c 'Added record' "$WXLOG" 2>/dev/null || echo 0)"
    [ "$after" -gt "$before" ] && return 0
  done
  return 1
}

# Tag the just-finished block's samples into a dedicated file that never rotates,
# so analysis reads ONE file and cannot be defeated by log rotation/compression.
harvest() {
  local arm="$1" from="$2"
  say_dry "harvest samples for arm $arm since $from" && return 0
  python3 - "$arm" "$from" "$MONLOG" "$MONLOG.1" "$WXLOG" >> "$DATALOG" <<'PYEOF'
import os, re, sys
arm, since = sys.argv[1], sys.argv[2]
for path in (sys.argv[3], sys.argv[4]):
    if not os.path.exists(path): continue
    for line in open(path, errors='replace'):
        m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) RECEPTION: (\d+)%', line)
        if m and m.group(1) >= since:
            print(f"{m.group(1)}|{arm}|rx|{m.group(2)}")
if os.path.exists(sys.argv[5]):
    for line in open(sys.argv[5], errors='replace'):
        m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .*duplicate frames this period: (\d+)', line)
        if m and m.group(1) >= since:
            print(f"{m.group(1)}|{arm}|dup|{m.group(2)}")
PYEOF
}

trip_abort() {
  local why="$1"
  log "ABORT: $why"
  say_dry "write STOP sentinel" || echo "$(date '+%F %T') $why" > "$STOP"
  restore_baseline
  send_mail "ABORTED — campaign halted" \
"The RX experiment aborted and prod was restored to the baseline config.

Reason: $why

The campaign is HALTED and will not resume: a STOP sentinel is in place at
  $STOP
Clear that file by hand once you have looked at why. Nothing will swap until
you do.

Experiment log: $XLOG"
}

# ── Modes ─────────────────────────────────────────────────────────────────────
mode="${1:-status}"

case "$mode" in

schedule)
  printf '%-18s %-9s %s\n' "WHEN (local)" "ARM" "COMMAND"
  printf '%-18s %-9s %s\n' "------------------" "---------" "-------"
  while IFS='|' read -r t a; do
    [ -z "$t" ] && continue
    if [ "$a" = "BASELINE" ]; then
      printf '%-18s %-9s %s\n' "$t" "$a" "<restore snapshot, self-terminate>"
    else
      printf '%-18s %-9s %s\n' "$t" "$a" "$(arm_cmd "$a" | sed 's/^ *cmd = //')"
    fi
  done <<< "$(echo "$SCHEDULE" | grep -v '^$')"
  echo
  echo "Pilot (08-07, 45 min each, HIGH->LOW): P496 P449 P402 P372 P328 — arm-selection input only"
  echo "H = Friday hold, baseline settings under their own harvest tag"
  echo "Square: A=gain372/ex0 (control/anchor)  B=gain496/ex0  C=gain372/ex50  D=gain496/ex50"
  echo "32 blocks, 8 blocks per arm, 48h accumulated per arm."
  ;;

install)
  [ -f "$BASELINE_SNAP" ] && { echo "Baseline snapshot already exists: $BASELINE_SNAP"; exit 1; }
  if schedule_started; then
    echo "REFUSING to install: the schedule has already started." >&2
    echo "  first row: $(echo "$SCHEDULE" | grep -v '^$' | head -1 | cut -d'|' -f1)" >&2
    echo "  now:       $(date '+%Y-%m-%dT%H:%M')" >&2
    echo "Installing now would join the campaign mid-flight -- due_arm() selects the" >&2
    echo "LATEST row already passed, so you would skip the pilot and start on the wrong" >&2
    echo "block, or (past the last row) record the campaign complete without running it." >&2
    echo "Regenerate the SCHEDULE= block with future dates first (DEC-0066)." >&2
    exit 1
  fi
  say_dry "snapshot $CONF -> $BASELINE_SNAP and write state" && exit 0
  cp "$CONF" "$BASELINE_SNAP" || exit 1
  echo "NONE|0|1970-01-01 00:00:00" > "$STATE"
  log "INSTALLED. Baseline snapshotted. No arm set; first tick will start the campaign."
  ;;

tick)
  [ -f "$STOP" ] && { log "tick: STOP sentinel present, refusing"; exit 1; }
  [ -f "$BASELINE_SNAP" ] || { log "tick: not installed (no baseline snapshot)"; exit 1; }
  want="$(due_arm)"; have="$(current_arm)"
  [ "$want" = "NONE" ] && { log "tick: campaign not started yet"; exit 0; }
  [ "$want" = "$have" ] && exit 0                       # idempotent no-op

  log "tick: swapping $have -> $want"
  [ "$have" != "NONE" ] && harvest "$have" "$(last_swap_human)"

  if [ "$want" = "BASELINE" ]; then
    restore_baseline
    say_dry "record campaign complete" || write_state BASELINE
    log "CAMPAIGN COMPLETE — prod restored to baseline."
    send_mail "campaign complete" "All 32 blocks ran. Prod is back on the baseline config. Data: $DATALOG"
    exit 0
  fi

  line="$(arm_cmd "$want")" || { log "tick: unknown arm $want"; exit 1; }
  if say_dry "set arm $want -> $line"; then :; else
    if ! write_arm "$line" 2>>"$XLOG"; then
      log "WRITE FAILED — restoring, not restarting"
      restore_baseline; trip_abort "config write/verify failed for arm $want"; exit 1
    fi
  fi
  restart_container
  if ! health_ok; then
    trip_abort "container did not produce records after swapping to arm $want"
    exit 1
  fi
  say_dry "record state $want" || write_state "$want"
  log "tick: arm $want live and healthy"
  ;;

guard)
  [ -f "$STOP" ] && exit 0                              # already halted; stay quiet
  [ -f "$STATE" ] || exit 0
  [ "$(current_arm)" = "NONE" ] && exit 0
  # Don't judge during the restart transient.
  swept="$(last_swap_epoch)"
  if [ "$swept" != "0" ]; then
    age=$(( $(date '+%s') - swept ))
    [ "$age" -lt "$SETTLE_SECS" ] && exit 0
  fi
  read -r n mean <<< "$(grep -oE 'RECEPTION: [0-9]+%' "$MONLOG" 2>/dev/null \
      | grep -oE '[0-9]+' | tail -n "$ABORT_SAMPLES" \
      | awk '{s+=$1; n++} END {print n+0, (n? int(s/n) : -1)}')"
  # Too few samples means the monitor is quiet, not that reception collapsed —
  # never abort on absence of evidence.
  [ "${n:-0}" -lt "$ABORT_SAMPLES" ] && exit 0
  if [ "${mean:-100}" -lt "$ABORT_PCT" ]; then
    trip_abort "30-min mean reception ${mean}% < ${ABORT_PCT}% floor (arm $(current_arm))"
    exit 1
  fi
  ;;

status)
  echo "arm:        $(current_arm)   (since $(last_swap_human))"
  echo "due now:    $(due_arm)"
  echo "stopped:    $([ -f "$STOP" ] && cat "$STOP" || echo no)"
  echo "installed:  $([ -f "$BASELINE_SNAP" ] && echo yes || echo no)"
  echo "samples:    $([ -f "$DATALOG" ] && wc -l < "$DATALOG" || echo 0)"
  ;;

abort)
  trip_abort "manual abort requested"
  ;;

*) echo "unknown mode: $mode (schedule|install|tick|guard|status|abort)"; exit 1 ;;
esac
