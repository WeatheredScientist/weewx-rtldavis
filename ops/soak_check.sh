#!/usr/bin/env bash
# soak_check.sh — is the station actually healthy, or does it just look "Up"?
#
# A soak is not "keep an eye on it". Prose does not execute (DEC-0040), and a soak
# with no stated acceptance criteria is a soak nobody runs and nobody can fail. This
# script IS the criteria: every claim we made when deploying is re-asserted here as a
# check that can go red.
#
# It exists because "the container reports Up" has lied to us twice:
#   - DEC-0036: weewx froze for 7h18m mid-log-write. Container: "Up". No crash, no
#     traceback, no error. The only symptom was data that stopped arriving.
#   - DEC-0031: the image ran the STOCK driver for weeks. Version tag: correct.
#     Logs: normal. The filters were simply inert.
# Both would be caught below (archive continuity; driver identity).
#
# Usage:
#   ops/soak_check.sh              # check since the container started
#   ops/soak_check.sh 3600         # check only the last N seconds
#
# EXPECT_IMAGE names the VERSIONED tag actually deployed RIGHT NOW (e.g. v2.0.16),
# but is compared by IMAGE ID, never by string: marvin's deploy flow
# (`marvinctl set-image`) runs the live container under a local alias tag
# ("marvin-live" today), so `Config.Image` never reads back a versioned tag at all
# post-move — a straight string compare would fail permanently, on a healthy
# station, forever (ops#287's own finding). Bump EXPECT_IMAGE as part of the
# deploy, never before and never after — same rule as always, just resolved
# through `marvinctl check-image` instead of a string match.
#
# Transport is `marvinctl --tenant weewx` (ops#287) — NAS-ssh reached nothing real
# since DEC-0118 moved the tenant to marvin. Each check that used to be one remote
# awk/grep clause inside a single ssh round trip is now its own `marvinctl` call
# (tier 1, read-only, own-tenant); a rotated log needed for windowed counts is
# `cat`'d once and filtered locally rather than re-fetched per signature.
#
# Exit 0 = all green. Exit 1 = something needs a human.
set -uo pipefail

WINDOW="${1:-0}"          # seconds; 0 = since container start
CONTAINER=weewx-rtldavis-v2
MONITOR_UNIT=weewx-monitor.service
LOGDIR=/srv/docker/weewx/logs
ARCHIVE_DB=/srv/docker/weewx/weewx-data/archive/weewx.sdb
VENV_PY=/opt/weewx-venv/bin/python3
EXPECT_IMAGE="${EXPECT_IMAGE:-weatheredscientist/weewx-rtldavis:v2.0.16}"
# The DEC-0031 canary. Same rule as EXPECT_IMAGE above: this is what prod is
# running NOW, not what the repo is on.
EXPECT_DRIVER="${EXPECT_DRIVER:-0.20+ws.5}"

pass=0; fail=0; warn=0
ok()   { printf '  \033[32mPASS\033[0m  %-34s %s\n' "$1" "${2:-}"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %-34s %s\n' "$1" "${2:-}"; fail=$((fail+1)); }
note() { printf '  \033[33mWARN\033[0m  %-34s %s\n' "$1" "${2:-}"; warn=$((warn+1)); }

# GNU date is required for the window math: StartedAt comes back UTC ISO8601 from
# `marvinctl inspect`, and it has to be converted to marvin-local wall-clock (the
# log lines' own timestamp format) to compute a cutoff — BSD `date` (macOS's
# default) has no `-d`. `brew install coreutils` provides `gdate`.
if date -d "@0" >/dev/null 2>&1; then DATECMD=date
elif command -v gdate >/dev/null 2>&1; then DATECMD=gdate
else echo "SOAK: need GNU date (-d support) — install coreutils for gdate, or run on Linux." >&2; exit 1
fi

ERRF="$(mktemp)"; trap 'rm -f "$ERRF"' EXIT

mc() { marvinctl --tenant weewx "$@" 2>"$ERRF"; }

mreq() {  # a call that MUST succeed
  local out rc
  out="$(mc "$@")"; rc=$?
  if [ $rc -ne 0 ]; then echo "SOAK: marvinctl $1 failed: $(cat "$ERRF")" >&2; exit 1; fi
  printf '%s' "$out"
}

mcat() {  # tolerant read: '' for a rotated file that has aged out, hard exit on
          # any other failure — matches the old ssh form's `2>/dev/null` tolerance
  local out rc
  out="$(mc cat "$1")"; rc=$?
  if [ $rc -eq 0 ]; then printf '%s' "$out"; return 0; fi
  if grep -q "does not exist" "$ERRF" 2>/dev/null; then printf ''; return 0; fi
  echo "SOAK: marvinctl cat $1 failed: $(cat "$ERRF")" >&2; exit 1
}

if ! INSPECT_JSON="$(mreq inspect "$CONTAINER")"; then exit 1; fi
STATE=$(printf '%s' "$INSPECT_JSON" | jq -r '.[0].State.Status')
IMAGE=$(printf '%s' "$INSPECT_JSON" | jq -r '.[0].Config.Image')
IMAGE_ID=$(printf '%s' "$INSPECT_JSON" | jq -r '.[0].Image')
RESTARTS=$(printf '%s' "$INSPECT_JSON" | jq -r '.[0].RestartCount')
STARTED_AT=$(printf '%s' "$INSPECT_JSON" | jq -r '.[0].State.StartedAt')

now_epoch=$($DATECMD +%s)
start_epoch=$($DATECMD -d "$STARTED_AT" +%s)
up_s=$(( now_epoch - start_epoch ))
up_h=$(( up_s / 3600 ))
if [ "$WINDOW" -gt 0 ]; then t0=$(( now_epoch - WINDOW )); else t0=$start_epoch; fi
cutoff="$($DATECMD -d "@$t0" '+%Y-%m-%d %H:%M:%S')"

echo "── SOAK CHECK — $CONTAINER (via marvinctl) ─────────────────────────────"
echo "   image $IMAGE · up ${up_h}h · window: $([ "$WINDOW" -gt 0 ] && echo "last $((WINDOW/3600))h" || echo "since container start")"
echo

# 1. The container itself
[ "$STATE" = "running" ] && ok "container running" || bad "container running" "state=$STATE"
if EXPECT_ID="$(mc check-image "$EXPECT_IMAGE")" && [ -n "$EXPECT_ID" ]; then
  if [ "$IMAGE_ID" = "$EXPECT_ID" ]; then
    ok "image is the expected build" "$EXPECT_IMAGE"
  else
    bad "IMAGE MISMATCH" "running $IMAGE_ID, want $EXPECT_IMAGE ($EXPECT_ID) — is the baked driver the one you built? (DEC-0031)"
  fi
else
  note "cannot resolve EXPECT_IMAGE locally" "$EXPECT_IMAGE not present as a local image — bump it as part of the deploy"
fi
[ "$RESTARTS" = "0" ] && ok "no container restarts" || note "container has restarted" "count=$RESTARTS"

# --- fetch the two log files windowing needs, once each ---
# weewx.log rotates daily, so any window reaching before "today" needs
# yesterday's rotated file too, or it silently misses everything before
# midnight (#252). Yesterday first, so the merged content stays chronological.
YESTERDAY="$($DATECMD -d yesterday '+%Y-%m-%d')"
L="$LOGDIR/weewx.log"
LY="$L.$YESTERDAY"
raw_y="$(mcat "$LY")"
raw_t="$(mreq cat "$L")"
both=""
[ -n "$raw_y" ] && both="$raw_y"$'\n'
both="${both}${raw_t}"

# cheap window: filter by string comparison — log timestamps are zero-padded
# ISO ("YYYY-MM-DD HH:MM:SS..."), which sorts correctly as plain text, so no
# date parsing is needed per line (only the cutoff itself needed one).
win="$(printf '%s\n' "$both" | awk -v c="$cutoff" 'substr($0,1,19) >= c')"

# --- stdout: must be silent (DEC-0041) and traceback-free (DEC-0043) ---
# excludes entrypoint.sh's own known boot lines (#253): those accumulate across
# every restart on a long-lived container object and would swamp the count
# with routine noise DEC-0041 doesn't actually care about.
so="$(mreq logs "$CONTAINER" 200)"
stdout_lines=$(printf '%s\n' "$so" | grep -vE '^(Starting weewx\.\.\.|Enabling RTL-SDR bias-tee for LNA\.\.\.|Bias-tee disabled \(BIAS_TEE=.*\), driving it off\.\.\.|Found [0-9]+ device\(s\):|  [0-9]+:  .*|Using device [0-9]+: .*|Found Rafael Micro R820T tuner)$' | grep -c . || true)
stdout_logerr=$(printf '%s\n' "$so" | grep -c -- '--- Logging error ---' || true)

banner=$(printf '%s\n' "$win" | grep -c 'weewxd .*Initializing weewxd version' || true)

# --- restart-loop detector (S95, #245) ---
# Deliberately NOT windowed to container start: entrypoint.sh execs weewxd, so
# weewxd IS pid 1 and its death takes the container with it — every container
# lifetime holds exactly ONE startup banner. A restart loop is therefore
# structurally invisible inside the default window; it only shows ACROSS
# container lifetimes. Reads $both (yesterday + today): a 6h window run just
# after midnight spans two files and would silently under-count from one.
loop_t0=$(( now_epoch - 21600 ))
mapfile -t restart_lines < <(printf '%s\n' "$both" | grep 'Initializing weewxd version')
restart_times=()
for ln in "${restart_lines[@]:-}"; do
  [ -z "$ln" ] && continue
  tt=$($DATECMD -d "${ln:0:19}" +%s 2>/dev/null || echo 0)
  [ "$tt" -ge "$loop_t0" ] && restart_times+=("$tt")
done

drv_ver=$(printf '%s\n' "$win" | grep -o 'driver version is [^ ]*' | tail -1 | sed 's/.* //')
qc_ok=$(printf '%s\n' "$win" | grep -c 'sensor_qc True' || true)
hraw_on=$(printf '%s\n' "$win" | grep -c 'log_humidity_raw True' || true)
hraw_n=$(printf '%s\n' "$win" | grep -c 'humidity_raw=' || true)
stalls=$(printf '%s\n' "$win" | grep -c 'process stalled' || true)
tracebacks=$(printf '%s\n' "$win" | grep -c 'Traceback' || true)
published=$(printf '%s\n' "$win" | grep -c 'Published record' || true)
influx=$(printf '%s\n' "$win" | grep -c 'Influx' || true)

# --- archive continuity: the DEC-0036 freeze detector ---
last_record=$(mreq grep "Added.record" "$L" | grep -v daily | tail -1 | cut -c1-19)
if [ -n "$last_record" ]; then
  lt=$($DATECMD -d "$last_record" +%s 2>/dev/null || echo 0)
else
  lt=0
fi
record_age_s=$(( $($DATECMD +%s) - lt ))

# --- reception ---
ML="$LOGDIR/weewx_monitor.log"
window_pct=$(mc grep "WINDOW:" "$ML" | tail -1 | grep -oE '\([0-9]+%\)' | tr -d '()%')
rxl=$(mc grep "RECEPTION:" "$ML" | tail -1)
rx_avg=$(printf '%s' "$rxl" | awk -F'RECEPTION: ' '{print $2}' | awk '{print $1}' | tr -d '%')
rx_verdict=$(printf '%s' "$rxl" | awk -F'[][]' '{print $2}')

# --- the monitor IS the USB watchdog (DEC-0074) ---
# Two independent signals, not one: `marvinctl unit` gives the OS-level verdict
# (is the process alive at all?) but not whether it is WEDGED — alive with a
# stale log is exactly the DEC-0036 shape a pure "active (running)" check would
# miss. The log-mtime freshness check below is kept for that reason, alongside
# the new unit check rather than instead of the old pid-file one (which can't
# work post-move anyway: the monitor is a HOST systemd unit, invisible to
# `exec-ro`'s own container).
unit_status="$(mc unit "$MONITOR_UNIT")"
if printf '%s' "$unit_status" | grep -q 'Active: active (running)'; then
  mon_proc=alive
else
  mon_proc=dead
fi
mstat="$(mc stat "$ML")"
if [ -n "$mstat" ]; then
  mtime_line=$(printf '%s' "$mstat" | awk -F': ' '/^Modify:/{print $2}')
  mtime_epoch=$($DATECMD -d "${mtime_line%%.*} ${mtime_line##* }" +%s 2>/dev/null || echo 0)
  mon_log_age=$(( $($DATECMD +%s) - mtime_epoch ))
else
  mon_log_age=-1
fi
# 'RESET: running' fires exactly once per attempt. Both the current log and the
# previous one: weewx_monitor.log rotates daily at 00:05.
mon_resets=$(( $(mc grep "RESET:.running" "$ML" | grep -c . || true) + $(mc grep "RESET:.running" "$ML.1" | grep -c . || true) ))
mon_reset_bad=$(( $(mc grep "RESET.ineffective" "$ML" | grep -c . || true) + $(mc grep "RESET.ineffective" "$ML.1" | grep -c . || true) ))

# --- retention tripwire (DEC-0095 / ops#175) ---
dbstat="$(mc stat "$ARCHIVE_DB")"
# `Size:` is indented under `File:` in GNU stat's default layout, not anchored
# at column 0 like `Modify:` -- an anchored match silently found nothing.
db_bytes=$(printf '%s' "$dbstat" | grep -oE 'Size: [0-9]+' | awk '{print $2}')
mem_total_kb=$(mc proc meminfo | awk '/^MemTotal/{print $2}')

# --- phantom rain: the DEC-0042 signature, auto-detected ---
# A raw rainRate>0/rain=0 row is NOT itself the signature: the ISS's own
# rain-rate message reports "time since last tip" for a while after a REAL tip,
# decaying to 0 on its own. Only rows with NO real tip in the preceding
# DECAY_S are counted (S44).
PHANTOM_QUERY="
import sqlite3
db = sqlite3.connect('file:${ARCHIVE_DB}?mode=ro', uri=True)
DECAY_S = 3600
rows = db.execute('SELECT dateTime FROM archive WHERE dateTime > ? AND rainRate > 0 AND (rain IS NULL OR rain = 0)', (${t0},)).fetchall()
n = 0
for (dt,) in rows:
    tip = db.execute('SELECT COUNT(*) FROM archive WHERE dateTime <= ? AND dateTime > ? AND rain > 0', (dt, dt - DECAY_S)).fetchone()[0]
    if tip == 0:
        n += 1
t = db.execute('SELECT COUNT(*) FROM archive WHERE dateTime > ?', (${t0},)).fetchone()[0]
print('phantom_rain=%d' % n)
print('archive_rows=%d' % t)
"
phantom_out="$(printf '%s' "$PHANTOM_QUERY" | mc exec-ro "$IMAGE" -- "$VENV_PY" -)"
phantom_rain=$(printf '%s\n' "$phantom_out" | awk -F= '/^phantom_rain=/{print $2}')
archive_rows=$(printf '%s\n' "$phantom_out" | awk -F= '/^archive_rows=/{print $2}')

echo "── HEALTH ──────────────────────────────────────────────────────────────"

# 2. The DEC-0036 freeze detector. "Up" is not health — data arriving is.
if [ "${record_age_s:-9999}" -le 180 ]; then ok "archive records still arriving" "last ${record_age_s}s ago"
else bad "ARCHIVE STALLED" "last record ${record_age_s}s ago — this is the DEC-0036 signature"; fi

# 3. Logging (DEC-0043 / DEC-0041)
[ "$stdout_logerr" = "0" ] && ok "no logging-error tracebacks" "(DEC-0043)" || bad "logging-error tracebacks on stdout" "$stdout_logerr blocks — DEC-0043 regressed"
[ "${stdout_lines:-999}" -lt 50 ] && ok "stdout quiet" "${stdout_lines} lines (DEC-0041)" || note "stdout is chatty" "${stdout_lines} lines — the freeze fuel is back?"
[ "$banner" != "0" ] && ok "weewxd startup banner in weewx.log" "(DEC-0043)" || note "no startup banner in window" "(only expected right after a restart)"

# 3b. Restart-loop detector (S95, #245).
rn=${#restart_times[@]}
if [ "$rn" -le 1 ]; then
  ok "no weewxd restart loop" "${rn} start(s) in 6h"
else
  mapfile -t sorted_times < <(printf '%s\n' "${restart_times[@]}" | sort -n)
  mg=999999
  for i in "${!sorted_times[@]}"; do
    [ "$i" -eq 0 ] && continue
    d=$(( sorted_times[i] - sorted_times[i-1] ))
    [ "$d" -lt "$mg" ] && mg=$d
  done
  if [ "$mg" -lt 1800 ]; then
    bad "WEEWXD RESTART LOOP" "${rn} starts in 6h, closest ${mg}s apart — the 2026-08-06 signature (an attended deploy looks like this too)"
  else
    ok "no weewxd restart loop" "${rn} starts in 6h, closest $((mg/60))min apart (scheduled swaps are 6h)"
  fi
fi

# 4. Driver identity (DEC-0031 — the stock-driver trap)
if [ -z "$drv_ver" ]; then
  note "driver banner not in window" "(only logged at startup — version UNVERIFIED)"
elif [ "$drv_ver" = "$EXPECT_DRIVER" ]; then
  ok "patched driver $EXPECT_DRIVER" "(DEC-0031 canary)"
else
  bad "DRIVER VERSION MISMATCH" "running $drv_ver, want $EXPECT_DRIVER — is the baked driver the one you built? (DEC-0031)"
fi
[ "$qc_ok" != "0" ] && ok "sensor_qc enabled" || note "sensor_qc not seen in window" ""
[ "$hraw_on" != "0" ] && ok "log_humidity_raw ACTIVE" "(DEC-0044 instrument)" || note "log_humidity_raw not seen" ""

# 5. The S41 watch item
if [ "${stalls:-0}" -le 1 ]; then ok "rtldavis stalls" "${stalls:-0} (<=1 startup stall is known)"
else bad "REPEATED rtldavis stalls" "${stalls} — this is now a real startup/USB race"; fi

# 6. Errors
[ "$tracebacks" = "0" ] && ok "no tracebacks" || bad "tracebacks in log" "$tracebacks"

# 7. Uploaders
[ "${published:-0}" -gt 0 ] && ok "uploaders publishing" "${published} records" || bad "no records published" ""
[ "$influx" != "0" ] && ok "InfluxDB receiving" || note "no Influx lines in window" ""

# 8. Reception — the monitor's own verdict, not a second threshold beside it.
_ctx="${window_pct:+ · last window ${window_pct}%}"
if [ "$rx_verdict" = "OK" ]; then ok "reception (monitor 5-window avg)" "${rx_avg}%${_ctx}"
elif [ "$rx_verdict" = "LOW" ]; then note "reception LOW per monitor" "${rx_avg}% avg — below its own floor${_ctx}"
elif [ -n "$window_pct" ]; then note "no monitor reception verdict yet" "raw window ${window_pct}% (aggregate logs every 5 min)"
else note "no reception window reported" ""; fi

# 9. The monitor, which IS the USB watchdog (DEC-0074).
if [ "$mon_proc" != "alive" ]; then
  bad "MONITOR/WATCHDOG DEAD" "weewx-monitor.service not active — USB stalls go unhandled AND unalerted"
elif [ "$mon_log_age" = "-1" ]; then
  bad "MONITOR LOG MISSING" "unit active but no log file — cannot tell wedged from working"
elif [ "$mon_log_age" -lt 0 ] 2>/dev/null; then
  note "monitor log timestamp in the future" "${mon_log_age}s — clock skew, not a wedge"
elif [ "$mon_log_age" -le 300 ] 2>/dev/null; then
  ok "monitor/watchdog alive" "log ${mon_log_age}s ago"
else
  bad "MONITOR LOG STALE" "unit active but log ${mon_log_age}s old — wedged, so stalls go unhandled"
fi

# 9b. Retention tripwire — DEC-0095's reversal condition, ops#175.
if [ "${db_bytes:-0}" -gt 0 ] && [ "${mem_total_kb:-0}" -gt 0 ]; then
  mem_b=$(( mem_total_kb * 1024 )); budget=$(( mem_b / 10 ))
  pctm=$(awk -v d="$db_bytes" -v m="$mem_b" 'BEGIN{printf "%.1f", 100*d/m}')
  if [ "$db_bytes" -lt "$budget" ]; then
    ok "archive within retention budget" "$((db_bytes/1048576)) MB = ${pctm}% of RAM (reopen DEC-0095 at 10%)"
  else
    note "ARCHIVE OVER RETENTION BUDGET" "$((db_bytes/1048576)) MB = ${pctm}% of RAM — DEC-0095's accept-and-monitor is due for review (ops#175)"
  fi
else
  note "retention tripwire unmeasured" "db_bytes/mem_total unavailable — DEC-0095 is unmonitored this run"
fi

if [ "${mon_reset_bad:-0}" -eq 0 ]; then ok "USB resets: none ineffective" "${mon_resets:-0} fired"
else note "USB hedge reset ineffective" "${mon_reset_bad} of ${mon_resets} — expected for RF-dead episodes (S73); check STALL DIAGNOSIS class in weewx.log"; fi

# 10. The two free experiments this soak is really for
echo
echo "── THE TWO OPEN EXPERIMENTS ────────────────────────────────────────────"
if [ "${hraw_n:-0}" -gt 0 ]; then
  printf '  \033[32m●\033[0m  humidity_raw capture: %s samples logged (DEC-0044)\n' "$hraw_n"
  echo "     A midday SPIKE is what settles the nibble question — grep the log for the"
  echo "     spike, invert pkt[4]/pkt[3], re-decode under 0x2/0x8/0xE. Method: DEC-0044."
else
  printf '  \033[33m●\033[0m  humidity_raw capture: NO samples — the instrument is not running\n'
fi
if [ "${phantom_rain:-0}" -eq 0 ]; then
  printf '  \033[32m●\033[0m  phantom rainRate: 0 rows (rainRate>0 while rain=0) in %s archive rows\n' "${archive_rows:-0}"
  echo "     A THIRD event is predicted on the next calm, saturated, cooling night."
  echo "     DEC-0049: the hardware is sound, so the counter must NOT advance."
else
  printf '  \033[31m●\033[0m  PHANTOM RAIN EVENT DETECTED: %s rows with rainRate>0 and rain=0\n' "$phantom_rain"
  echo "     This is the DEC-0042 signature and the third event we predicted."
  echo "     Snapshot the raw rows BEFORE any correction (the S38 lesson), then check:"
  echo "     did the tip counter advance? DEC-0049 says it must not."
fi

echo
if [ "$fail" -eq 0 ]; then
  printf '\033[32mSOAK: %d passed, %d warnings, 0 failures.\033[0m\n' "$pass" "$warn"
  exit 0
else
  printf '\033[31mSOAK: %d passed, %d warnings, %d FAILURES — needs a human.\033[0m\n' "$pass" "$warn" "$fail"
  exit 1
fi
