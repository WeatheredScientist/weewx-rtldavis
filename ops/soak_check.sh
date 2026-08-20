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
# EXPECT_IMAGE (below) must name the tag actually deployed RIGHT NOW, not the one
# being prepared. It was set to :v2.0.12 from S62 until S67 while prod ran :v2.0.11
# -- bumped in ANTICIPATION of a release that never deployed, so the identity check
# would have gone red on a perfectly healthy station for five sessions. Nobody ran
# it, which is the only reason it went unnoticed. The mirror-image failure is worse:
# left too high after a rollback, it goes GREEN on the wrong image. Bump it as part
# of the deploy, never before and never after.
#
# Exit 0 = all green. Exit 1 = something needs a human.
set -uo pipefail

# Connection facts live OUTSIDE this PUBLIC repo (DEC-0012 posture): export
# NAS_PORT/NAS_USER/NAS_HOST, or put them in ~/.claude/nas.env (sourced below).
# The tracked defaults are placeholders and fail fast — real values are in the
# gitignored docs/LOCAL_INFRA.md.
NAS_PORT="${NAS_PORT:-<SSH_PORT>}"; NAS_USER="${NAS_USER:-<NAS_USER>}"; NAS_HOST="${NAS_HOST:-<NAS_IP>}"
[ -f "$HOME/.claude/nas.env" ] && . "$HOME/.claude/nas.env"
case "${NAS_PORT}${NAS_USER}${NAS_HOST}" in (*'<'*)
  echo "SOAK: NAS_PORT/NAS_USER/NAS_HOST unset — export them or create ~/.claude/nas.env (see gitignored docs/LOCAL_INFRA.md)." >&2
  exit 1 ;;
esac
WINDOW="${1:-0}"          # seconds; 0 = since container start
CONTAINER=weewx-rtldavis-v2
EXPECT_IMAGE="${EXPECT_IMAGE:-weatheredscientist/weewx-rtldavis:v2.0.13}"
# The DEC-0031 canary. Same rule as EXPECT_IMAGE above: this is what prod is
# running NOW, not what the repo is on. Bumped to v2.0.12 / ws.4 on 2026-08-10
# (S70) IN the deploy that shipped them -- the swap was verified in the running
# system (banner + soak canaries) before this edit landed, per DEC-0046 and this
# header's own rule: as part of the deploy, never before and never after.
EXPECT_DRIVER="${EXPECT_DRIVER:-0.20+ws.5}"

pass=0; fail=0; warn=0
ok()   { printf '  \033[32mPASS\033[0m  %-34s %s\n' "$1" "${2:-}"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %-34s %s\n' "$1" "${2:-}"; fail=$((fail+1)); }
note() { printf '  \033[33mWARN\033[0m  %-34s %s\n' "$1" "${2:-}"; warn=$((warn+1)); }

# One ssh round-trip. Everything below is computed on the NAS and returned as k=v lines.
R="$(ssh -p "$NAS_PORT" "${NAS_USER}@${NAS_HOST}" "
D=/usr/local/bin/docker
L=/volume1/docker/weewx-rtldavis/logs/weewx.log
M=/volume1/docker/weewx-rtldavis/logs/weewx_monitor.log
C=$CONTAINER
W=$WINDOW

echo \"state=\$(\$D inspect \$C --format '{{.State.Status}}' 2>/dev/null)\"
echo \"image=\$(\$D inspect \$C --format '{{.Config.Image}}' 2>/dev/null)\"
echo \"restarts=\$(\$D inspect \$C --format '{{.RestartCount}}' 2>/dev/null)\"
started=\$(\$D inspect \$C --format '{{.State.StartedAt}}' 2>/dev/null)
echo \"started=\$started\"
t0=\$(date -d \"\$started\" +%s 2>/dev/null || echo 0)
now=\$(date +%s)
[ \"\$W\" -gt 0 ] && t0=\$((now - W))
echo \"uptime_s=\$((now - \$(date -d \"\$started\" +%s 2>/dev/null || echo \$now)))\"
echo \"since=\$t0\"

# --- stdout: must be silent (DEC-0041) and traceback-free (DEC-0043) ---
so=\$(\$D logs --tail 200 \$C 2>&1)
echo \"stdout_lines=\$(printf '%s' \"\$so\" | grep -c . )\"
echo \"stdout_logerr=\$(printf '%s' \"\$so\" | grep -c -- '--- Logging error ---')\"

# --- log lines only within the window ---
awkw() { awk -v t0=\"\$1\" '{ cmd=\"date -d \\\"\" substr(\$0,1,19) \"\\\" +%s 2>/dev/null\"; cmd | getline ts; close(cmd); if (ts+0 >= t0) print }' ; }

# cheap window: the log is chronological, so cut from the first line at/after t0
d0=\$(date -d \"@\$t0\" '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
ln=\$(grep -n \"^\$(date -d \"@\$t0\" '+%Y-%m-%d %H' 2>/dev/null)\" \"\$L\" | head -1 | cut -d: -f1)
[ -z \"\$ln\" ] && ln=1
win=\$(tail -n +\$ln \"\$L\")

echo \"banner=\$(printf '%s' \"\$win\" | grep -c 'weewxd .*Initializing weewxd version')\"
# --- restart-loop detector (S95, #245) ---
# Deliberately NOT windowed to container start. entrypoint.sh execs weewxd, so
# weewxd IS pid 1 and its death takes the container with it -- every container
# lifetime holds exactly ONE startup banner. A restart loop is therefore
# structurally invisible inside the default window; it only shows ACROSS
# container lifetimes, which is why this reads the log on its own 6 h window.
# The signature, measured S95: scheduled campaign swaps sit 6 h apart, while
# 2026-08-06's journal_mode crash-loop ran 7 starts in 7 min (60-90 s apart).
# Reads yesterday's rotated file too: weewx.log rotates daily, so a 6 h window
# run just after midnight spans TWO files and would silently under-count from
# one -- the same trap the mon_resets check below already documents, and the
# worst possible one here, since the overnight stall cluster (DEC-0097) sits
# at 00:00-04:00. Yesterday first, so the timestamps stay chronological.
loop_t0=\$((now - 21600))
LY=\$L.\$(date -d yesterday '+%Y-%m-%d' 2>/dev/null)
echo \"restart_times=\$(cat \$LY \$L 2>/dev/null | grep 'Initializing weewxd version' | cut -c1-19 | while read -r ts; do tt=\$(date -d \"\$ts\" +%s 2>/dev/null || echo 0); [ \"\$tt\" -ge \"\$loop_t0\" ] && printf '%s ' \"\$tt\"; done)\"
echo \"drv_ver=\$(printf '%s' \"\$win\" | grep -o 'driver version is [^ ]*' | tail -1 | sed 's/.* //')\"
echo \"qc_ok=\$(printf '%s' \"\$win\" | grep -c 'sensor_qc True')\"
echo \"hraw_on=\$(printf '%s' \"\$win\" | grep -c 'log_humidity_raw True')\"
echo \"hraw_n=\$(printf '%s' \"\$win\" | grep -c 'humidity_raw=')\"
echo \"stalls=\$(printf '%s' \"\$win\" | grep -c 'process stalled')\"
echo \"tracebacks=\$(printf '%s' \"\$win\" | grep -c 'Traceback')\"
echo \"criticals=\$(printf '%s' \"\$win\" | grep -c 'CRITICAL')\"
echo \"published=\$(printf '%s' \"\$win\" | grep -c 'Published record')\"
echo \"influx=\$(printf '%s' \"\$win\" | grep -c 'Influx')\"

# --- archive continuity: the DEC-0036 freeze detector ---
last=\$(grep 'Added record' \"\$L\" | grep -v daily | tail -1 | cut -c1-19)
echo \"last_record=\$last\"
lt=\$(date -d \"\$last\" +%s 2>/dev/null || echo 0)
# Fresh clock read, NOT \$now (S87). \$now is captured at the TOP of this block, before
# docker logs, the log-window read and the sqlite loop below; on a loaded box that is
# 24-100 s earlier. Ages measured against it are understated by exactly the runtime, so
# this detector's 180 s threshold silently became 180+runtime -- least sensitive exactly
# when the box is loaded, which is when the freezes it hunts actually happen (DEC-0088:
# median freeze 240 s). Measured 2026-08-17: 195-280 s effective.
echo \"record_age_s=\$((\$(date +%s) - lt))\"

# --- reception ---
echo \"window_pct=\$(grep 'WINDOW:' \"\$M\" | tail -1 | grep -oE '\([0-9]+%\)' | tr -d '()%')\"
# The monitor's OWN aggregate + verdict, which the soak previously ignored.
rxl=\$(grep 'RECEPTION:' \"\$M\" | tail -1)
echo \"rx_avg=\$(printf '%s' \"\$rxl\" | awk -F'RECEPTION: ' '{print \$2}' | awk '{print \$1}' | tr -d '%')\"
echo \"rx_verdict=\$(printf '%s' \"\$rxl\" | awk -F'[][]' '{print \$2}')\"

# --- the monitor IS the USB watchdog (DEC-0074) ---
# weewx_monitor.py carries reset_dongle()/watchdog_stall() as well as alerting, so
# its liveness is the watchdog's liveness. If it dies, stalls go unhandled AND
# unalerted, and nothing in weewx.log says so.
MP=/volume1/docker/weewx-rtldavis/logs/weewx_monitor.pid
ML=/volume1/docker/weewx-rtldavis/logs/weewx_monitor.log
mp=\$(cat \$MP 2>/dev/null)
echo \"mon_proc=\$([ -n \"\$mp\" ] && [ -d /proc/\$mp ] && echo alive || echo dead)\"
mlog=\$(stat -c %Y \$ML 2>/dev/null || echo 0)
# Fresh clock read, same reason as record_age_s above -- and here it was not merely a
# loss of sensitivity but a guaranteed FALSE ALARM: the monitor writes every 30 s, so
# once this block took longer than that, mtime was always NEWER than \$now, the age went
# negative, and the '\$mla -ge 0' guard below reported a perfectly healthy watchdog as
# 'wedged'. Sentinel -1 still means 'no log file at all' and is handled separately.
echo \"mon_log_age=\$([ \"\$mlog\" -gt 0 ] && echo \$((\$(date +%s) - mlog)) || echo -1)\"
# Both the current log and the previous one: weewx_monitor.log rotates daily at
# 00:05, so a check run just after midnight would otherwise report 0 resets while
# yesterday's sit one file away -- a silent window exactly when a bad night ended.
# 'RESET: running' fires exactly once per attempt. The old pattern here,
# 'RESET: triggering', was retired from the monitor at S67 (DEC-0074 renamed the
# reset messages) and this counter silently read 0 ever after -- found S82 via
# the impossible \"1 ineffective of 0 fired\" it printed. ops#147 item-6 class:
# a consumer grep left behind by a message rename.
echo \"mon_resets=\$(cat \$ML \$ML.1 2>/dev/null | grep -c 'RESET: running')\"
echo \"mon_reset_bad=\$(cat \$ML \$ML.1 2>/dev/null | grep -c 'RESET ineffective')\"

# --- retention tripwire (DEC-0095 / ops#175) ---
# DEC-0095 chose accept-and-monitor over archive-then-prune for the SQLite archive,
# on the measured finding that neither disk nor working set binds. That choice is only
# honest if the \"monitor\" half EXECUTES -- prose does not (DEC-0040), and this very
# script has already demonstrated the failure mode: EXPECT_IMAGE sat wrong for five
# sessions because nobody ran it. So the decision ships its own reversal condition.
echo \"db_bytes=\$(stat -c %s /volume1/docker/weewx-rtldavis/weewx-data/archive/weewx.sdb 2>/dev/null || echo 0)\"
echo \"mem_total_kb=\$(awk '/^MemTotal/{print \$2}' /proc/meminfo 2>/dev/null || echo 0)\"

# --- phantom rain: the DEC-0042 signature, auto-detected ---
# A raw rainRate>0/rain=0 row is NOT itself the signature: the ISS's own rain-rate message
# (rtldavis.py message_type 5) reports 'time since last tip' for a while after a REAL tip,
# decaying to 0 on its own — normal hardware behavior, confirmed against a real storm on
# 2026-07-18 (3 tips, 49 false-flagged decay rows; the tail of one decay ran 38 min past the
# light-rain formula's nominal ~1022s ceiling, so the window below is generous, not exact).
# Only rows with NO real tip in the preceding DECAY_S are counted (S44).
\$D exec \$C /opt/weewx-venv/bin/python3 -c \"
import sqlite3
db = sqlite3.connect('/opt/weewx-data/archive/weewx.sdb')
DECAY_S = 3600  # generous margin above the observed 38-min decay tail
rows = db.execute('SELECT dateTime FROM archive WHERE dateTime > ? AND rainRate > 0 AND (rain IS NULL OR rain = 0)', (\$t0,)).fetchall()
n = 0
for (dt,) in rows:
    tip = db.execute('SELECT COUNT(*) FROM archive WHERE dateTime <= ? AND dateTime > ? AND rain > 0', (dt, dt - DECAY_S)).fetchone()[0]
    if tip == 0:
        n += 1
t = db.execute('SELECT COUNT(*) FROM archive WHERE dateTime > ?', (\$t0,)).fetchone()[0]
print('phantom_rain=%d' % n); print('archive_rows=%d' % t)
\" 2>/dev/null

# How long this block actually took. Reported, not hidden: the runtime is what
# corrupted every age above, and it is itself a NAS-health signal -- ~2 s historically,
# 15-100 s under the evening load window (DEC-0094).
echo \"remote_elapsed_s=\$((\$(date +%s) - now))\"
" 2>/dev/null | grep -v "WARNING\|post-quantum\|store now")"

get() { printf '%s' "$R" | grep "^$1=" | head -1 | cut -d= -f2-; }

if [ -z "$R" ]; then echo "SOAK: cannot reach the NAS." >&2; exit 1; fi

up_s=$(get uptime_s); up_h=$(( ${up_s:-0} / 3600 ))
echo "── SOAK CHECK — $CONTAINER ─────────────────────────────────────────────"
echo "   image $(get image) · up ${up_h}h · window: $([ "$WINDOW" -gt 0 ] && echo "last $((WINDOW/3600))h" || echo "since container start")"
re=$(get remote_elapsed_s)
[ -n "$re" ] && echo "   remote probe took ${re}s$([ "${re:-0}" -ge 20 ] && echo "  ← NAS is loaded; see DEC-0094's evening window" || true)"
echo

# 1. The container itself
[ "$(get state)" = "running" ] && ok "container running" || bad "container running" "state=$(get state)"
[ "$(get image)" = "$EXPECT_IMAGE" ] && ok "image is the expected tag" "$(get image)" || bad "image is the expected tag" "got $(get image), want $EXPECT_IMAGE"
[ "$(get restarts)" = "0" ] && ok "no container restarts" || note "container has restarted" "count=$(get restarts)"

# 2. The DEC-0036 freeze detector. "Up" is not health — data arriving is.
ra=$(get record_age_s)
if [ "${ra:-9999}" -le 180 ]; then ok "archive records still arriving" "last ${ra}s ago"
else bad "ARCHIVE STALLED" "last record ${ra}s ago — this is the DEC-0036 signature"; fi

# 3. Logging (DEC-0043 / DEC-0041)
[ "$(get stdout_logerr)" = "0" ] && ok "no logging-error tracebacks" "(DEC-0043)" || bad "logging-error tracebacks on stdout" "$(get stdout_logerr) blocks — DEC-0043 regressed"
sl=$(get stdout_lines)
[ "${sl:-999}" -lt 50 ] && ok "stdout quiet" "${sl} lines (DEC-0041)" || note "stdout is chatty" "${sl} lines — the freeze fuel is back?"
[ "$(get banner)" != "0" ] && ok "weewxd startup banner in weewx.log" "(DEC-0043)" || note "no startup banner in window" "(only expected right after a restart)"
# 3b. Restart-loop detector (S95, #245). The banner check above passes on PRESENCE:
# it counts with grep -c and then only tests non-zero, so one banner and fifty read
# identically green. That blind spot is why a reported "crash loop" reached the owner
# as a frontier-tier alarm before anything here could tell it from routine swaps --
# and the container's own RestartCount was no help either, since `docker restart`
# never increments it. This asks the question the count was never asked: how close
# together are the restarts? Scheduled swaps are 6 h apart; a real loop is seconds.
rt="$(get restart_times)"
rn=$(printf '%s' "$rt" | wc -w | tr -d ' ')
if [ "${rn:-0}" -le 1 ]; then
  ok "no weewxd restart loop" "${rn:-0} start(s) in 6h"
else
  _mg=999999; _pv=""
  for _t in $rt; do
    [ -n "$_pv" ] && { _d=$((_t - _pv)); [ "$_d" -lt "$_mg" ] && _mg=$_d; }
    _pv=$_t
  done
  if [ "$_mg" -lt 1800 ]; then
    bad "WEEWXD RESTART LOOP" "${rn} starts in 6h, closest ${_mg}s apart — the 2026-08-06 signature (an attended deploy looks like this too)"
  else
    ok "no weewxd restart loop" "${rn} starts in 6h, closest $((_mg/60))min apart (scheduled swaps are 6h)"
  fi
fi

# 4. Driver identity (DEC-0031 — the stock-driver trap)
# Report the version the driver ACTUALLY announces, rather than grepping for an
# expected one. The old form grepped a hardcoded '0.20+ws.1' and fell through to
# a soft note on mismatch -- so from v2.0.10 onward it silently verified nothing,
# and "wrong version" was indistinguishable from "banner not in this window"
# (S62). Three distinct states now, and a mismatch is a FAILURE.
_dv="$(get drv_ver)"
if [ -z "$_dv" ]; then
  note "driver banner not in window" "(only logged at startup — version UNVERIFIED)"
elif [ "$_dv" = "$EXPECT_DRIVER" ]; then
  ok "patched driver $EXPECT_DRIVER" "(DEC-0031 canary)"
else
  bad "DRIVER VERSION MISMATCH" "running $_dv, want $EXPECT_DRIVER — is the baked driver the one you built? (DEC-0031)"
fi
[ "$(get qc_ok)" != "0" ] && ok "sensor_qc enabled" || note "sensor_qc not seen in window" ""
[ "$(get hraw_on)" != "0" ] && ok "log_humidity_raw ACTIVE" "(DEC-0044 instrument)" || note "log_humidity_raw not seen" ""

# 5. The S41 watch item
st=$(get stalls)
if [ "${st:-0}" -le 1 ]; then ok "rtldavis stalls" "${st:-0} (<=1 startup stall is known)"
else bad "REPEATED rtldavis stalls" "${st} — this is now a real startup/USB race"; fi

# 6. Errors
[ "$(get tracebacks)" = "0" ] && ok "no tracebacks" || bad "tracebacks in log" "$(get tracebacks)"

# 7. Uploaders
p=$(get published)
[ "${p:-0}" -gt 0 ] && ok "uploaders publishing" "${p} records" || bad "no records published" ""
[ "$(get influx)" != "0" ] && ok "InfluxDB receiving" || note "no Influx lines in window" ""

# 8. Reception — the monitor's own verdict, not a second threshold beside it (S87).
# The old check read the raw 'WINDOW:' line: ONE 60 s sample of 21 expected packets.
# At this station's measured baseline (73.3%, sd 4.67 — DEC-0059) a single window
# carries sd ~9.7 pts, so a hardcoded 80% floor fired on the MAJORITY of healthy runs,
# and sat 20 pts tighter than the monitor's own considered WU_RF_MIN_PCT=60 ("a real
# >~40% packet loss"). That is ops#147 item-6's cry-wolf shape, and STANDARD rule 5's
# second copy. The monitor already averages five windows and stamps [OK]/[LOW];
# report THAT, and keep the raw window alongside as context only.
rxa=$(get rx_avg); rxv=$(get rx_verdict); wp=$(get window_pct)
_ctx="${wp:+ · last window ${wp}%}"
if [ "$rxv" = "OK" ]; then ok "reception (monitor 5-window avg)" "${rxa}%${_ctx}"
elif [ "$rxv" = "LOW" ]; then note "reception LOW per monitor" "${rxa}% avg — below its own floor${_ctx}"
elif [ -n "$wp" ]; then note "no monitor reception verdict yet" "raw window ${wp}% (aggregate logs every 5 min)"
else note "no reception window reported" ""; fi

# 9. The monitor, which IS the USB watchdog (DEC-0074).
# This script exists to ask "healthy, or does it just look Up?" and had never asked
# it of the process that handles USB stalls. Its 30 s poll makes a 300 s log age
# generous; a live pid with a stale log means wedged, which is not the same as dead.
# S87: the three "alive" outcomes below used to be one. A negative age -- which this
# script MANUFACTURED by measuring against a stale clock -- fell through the '-ge 0'
# guard into the 'wedged' branch and cried wolf on a healthy watchdog for ten days.
# The remote side now reads a fresh clock, so a negative here means a genuine clock
# anomaly, which is its own finding and not a wedge. -1 still means "no log file".
mpr=$(get mon_proc); mla=$(get mon_log_age)
if [ "$mpr" != "alive" ]; then
  bad "MONITOR/WATCHDOG DEAD" "no live pid — USB stalls go unhandled AND unalerted"
elif [ -z "$mla" ] || [ "$mla" = "-1" ]; then
  bad "MONITOR LOG MISSING" "pid alive but no log file — cannot tell wedged from working"
elif [ "$mla" -lt 0 ] 2>/dev/null; then
  note "monitor log timestamp in the future" "${mla}s — NAS clock skew, not a wedge"
elif [ "$mla" -le 300 ] 2>/dev/null; then
  ok "monitor/watchdog alive" "log ${mla}s ago"
else
  bad "MONITOR LOG STALE" "pid alive but log ${mla}s old — wedged, so stalls go unhandled"
fi
# The remedy's own effectiveness — REFRAMED at S73. The original FAIL ("the
# remedy is not working") presumed resets are supposed to fix stalls; the S73
# differential established the stall class as RF-dead episodes, which no USB
# reset can touch, and demoted the watchdog to ONE hedge reset per episode
# (RESET_MAX_TRIES=1). An ineffective hedge during an RF episode is now the
# EXPECTED outcome, not an alarm — a FAIL here would cry wolf on every episode
# and train people to skip the soak (the ops#147 item-6 anti-pattern). The
# genuinely alarming signature is now visible elsewhere: a 'STALL DIAGNOSIS'
# line with raw_stderr_lines=0 (child mute -> a REAL process/USB fault) in
# weewx.log, and the episodes.log ledger row counts.
# 9b. Retention tripwire — DEC-0095's reversal condition, ops#175.
# The budget is a RATIO of RAM, not a fixed MB figure, because the constraint that
# would actually force a prune here is the WORKING SET, not disk: HLF's DEC-0174 hit
# exactly that wall on this same 3.69 GiB box (~8.0 M hot rows) while disk sat at 5.5 TB
# free. Measured at adoption (2026-08-17): archive 33.61 MB = 0.9% of RAM, 125,613 rows
# over 90.2 days = 1,392 rows/day at 275 B = 0.37 MB/day, ~7.3 years to 1 GB. Crossing
# 10% of RAM is the point at which DEC-0095 must be REOPENED, not quietly tolerated.
dbb=$(get db_bytes); mtk=$(get mem_total_kb)
if [ "${dbb:-0}" -gt 0 ] && [ "${mtk:-0}" -gt 0 ]; then
  _mem_b=$(( mtk * 1024 )); _budget=$(( _mem_b / 10 ))
  _pct=$(awk -v d="$dbb" -v m="$_mem_b" 'BEGIN{printf "%.1f", 100*d/m}')
  if [ "$dbb" -lt "$_budget" ]; then
    ok "archive within retention budget" "$((dbb/1048576)) MB = ${_pct}% of RAM (reopen DEC-0095 at 10%)"
  else
    note "ARCHIVE OVER RETENTION BUDGET" "$((dbb/1048576)) MB = ${_pct}% of RAM — DEC-0095's accept-and-monitor is due for review (ops#175)"
  fi
else
  note "retention tripwire unmeasured" "db_bytes/mem_total unavailable — DEC-0095 is unmonitored this run"
fi

mrb=$(get mon_reset_bad)
if [ "${mrb:-0}" -eq 0 ]; then ok "USB resets: none ineffective" "$(get mon_resets) fired"
else note "USB hedge reset ineffective" "${mrb} of $(get mon_resets) — expected for RF-dead episodes (S73); check STALL DIAGNOSIS class in weewx.log"; fi

# 10. The two free experiments this soak is really for
echo
echo "── THE TWO OPEN EXPERIMENTS ────────────────────────────────────────────"
hn=$(get hraw_n)
if [ "${hn:-0}" -gt 0 ]; then
  printf '  \033[32m●\033[0m  humidity_raw capture: %s samples logged (DEC-0044)\n' "$hn"
  echo "     A midday SPIKE is what settles the nibble question — grep the log for the"
  echo "     spike, invert pkt[4]/pkt[3], re-decode under 0x2/0x8/0xE. Method: DEC-0044."
else
  printf '  \033[33m●\033[0m  humidity_raw capture: NO samples — the instrument is not running\n'
fi
pr=$(get phantom_rain)
if [ "${pr:-0}" -eq 0 ]; then
  printf '  \033[32m●\033[0m  phantom rainRate: 0 rows (rainRate>0 while rain=0) in %s archive rows\n' "$(get archive_rows)"
  echo "     A THIRD event is predicted on the next calm, saturated, cooling night."
  echo "     DEC-0049: the hardware is sound, so the counter must NOT advance."
else
  printf '  \033[31m●\033[0m  PHANTOM RAIN EVENT DETECTED: %s rows with rainRate>0 and rain=0\n' "$pr"
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
