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
EXPECT_IMAGE="${EXPECT_IMAGE:-weatheredscientist/weewx-rtldavis:v2.0.7}"

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
echo \"drv_ok=\$(printf '%s' \"\$win\" | grep -c 'driver version is 0.20+ws.1')\"
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
echo \"record_age_s=\$((now - lt))\"

# --- reception ---
echo \"window_pct=\$(grep 'WINDOW:' \"\$M\" | tail -1 | grep -oE '\([0-9]+%\)' | tr -d '()%')\"

# --- phantom rain: the DEC-0042 signature, auto-detected ---
\$D exec \$C /opt/weewx-venv/bin/python3 -c \"
import sqlite3
db = sqlite3.connect('/opt/weewx-data/archive/weewx.sdb')
n = db.execute('SELECT COUNT(*) FROM archive WHERE dateTime > ? AND rainRate > 0 AND (rain IS NULL OR rain = 0)', (\$t0,)).fetchone()[0]
t = db.execute('SELECT COUNT(*) FROM archive WHERE dateTime > ?', (\$t0,)).fetchone()[0]
print('phantom_rain=%d' % n); print('archive_rows=%d' % t)
\" 2>/dev/null
" 2>/dev/null | grep -v "WARNING\|post-quantum\|store now")"

get() { printf '%s' "$R" | grep "^$1=" | head -1 | cut -d= -f2-; }

if [ -z "$R" ]; then echo "SOAK: cannot reach the NAS." >&2; exit 1; fi

up_s=$(get uptime_s); up_h=$(( ${up_s:-0} / 3600 ))
echo "── SOAK CHECK — $CONTAINER ─────────────────────────────────────────────"
echo "   image $(get image) · up ${up_h}h · window: $([ "$WINDOW" -gt 0 ] && echo "last $((WINDOW/3600))h" || echo "since container start")"
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

# 4. Driver identity (DEC-0031 — the stock-driver trap)
[ "$(get drv_ok)" != "0" ] && ok "patched driver 0.20+ws.1" "(DEC-0031)" || note "driver banner not in window" "(only logged at startup)"
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

# 8. Reception
wp=$(get window_pct)
if [ -n "$wp" ] && [ "$wp" -ge 80 ] 2>/dev/null; then ok "reception window" "${wp}%"
elif [ -n "$wp" ]; then note "reception window low" "${wp}%"
else note "no reception window reported" ""; fi

# 9. The two free experiments this soak is really for
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
