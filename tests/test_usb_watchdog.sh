#!/usr/bin/env bash
# test_usb_watchdog.sh — prove the watchdog's supervision actually works.
#
# WHY THIS EXISTS (DEC-0073). The previous watchdog had no tests, no PID guard and
# no heartbeat. It was hand-started once on 2026-05-22, died at the 2026-07-08
# reboot, and its absence was invisible for ~2.5 months because a watchdog that is
# not running produces exactly the same log as one with nothing to do. The reset
# logic was never the problem; the supervision was, and it was untested.
#
# So these tests cover the SUPERVISION, not the USB reset (which cannot be
# exercised off-NAS -- there is no syno_vbus_reset node here). The reset path is
# stubbed via WATCHDOG_USB_DEVICE pointing at a temp file, so we can still assert
# that a stall triggers a write and that the cooldown holds.
#
# Run: bash tests/test_usb_watchdog.sh    (exit 0 = all pass)
set -uo pipefail

WD="$(cd "$(dirname "$0")/.." && pwd)/ops/usb_watchdog.sh"
pass=0; fail=0
ok()   { printf '  PASS  %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  FAIL  %s\n    %s\n' "$1" "${2:-}"; fail=$((fail+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/logs" "$TMP/proc"

export WATCHDOG_BASE_DIR="$TMP"
export WATCHDOG_LOG="$TMP/logs/wd.log"
export WEEWX_LOG="$TMP/logs/weewx.log"
export WATCHDOG_HEARTBEAT="$TMP/logs/wd.alive"
export WATCHDOG_PIDFILE="$TMP/logs/wd.pid"
export WATCHDOG_USB_DEVICE="$TMP/logs/vbus_reset"
export WATCHDOG_PROC_DIR="$TMP/proc"
export WATCHDOG_TICK=1
export WATCHDOG_RESET_COOLDOWN=300

: > "$WEEWX_LOG"

start_wd() { bash "$WD" >/dev/null 2>&1 & echo $!; }
stop_wd()  { kill "$1" 2>/dev/null; pkill -P "$1" 2>/dev/null; wait "$1" 2>/dev/null; }

# --- 1. heartbeat ticks on a QUIET log -------------------------------------
# The regression this guards: a bare `read` blocks until a line arrives, so on a
# silent log the heartbeat would go stale and soak_check would call a live
# watchdog dead. Nothing is written to weewx.log during this test on purpose.
pid=$(start_wd); sleep 3
if [ -f "$WATCHDOG_HEARTBEAT" ]; then
  h1=$(stat -f %m "$WATCHDOG_HEARTBEAT" 2>/dev/null || stat -c %Y "$WATCHDOG_HEARTBEAT")
  sleep 2
  h2=$(stat -f %m "$WATCHDOG_HEARTBEAT" 2>/dev/null || stat -c %Y "$WATCHDOG_HEARTBEAT")
  [ "$h2" -gt "$h1" ] && ok "heartbeat advances on a quiet log" \
                      || bad "heartbeat advances on a quiet log" "mtime stuck at $h1"
else
  bad "heartbeat advances on a quiet log" "no heartbeat file created"
fi

# --- 2. pidfile written, and it is OUR pid ---------------------------------
if [ -f "$WATCHDOG_PIDFILE" ]; then
  wrote=$(cat "$WATCHDOG_PIDFILE")
  [ "$wrote" = "$pid" ] && ok "pidfile holds the watchdog pid" \
                        || bad "pidfile holds the watchdog pid" "file=$wrote proc=$pid"
else
  bad "pidfile holds the watchdog pid" "no pidfile"
fi

# --- 3. a stall triggers a reset -------------------------------------------
echo "2026-08-06 09:53:35,971 weewxd CRITICAL Caught WeeWxIOError: rtldavis process stalled" >> "$WEEWX_LOG"
sleep 3
if grep -q 'STALL detected' "$WATCHDOG_LOG" 2>/dev/null; then
  ok "stall line is detected"
else
  bad "stall line is detected" "$(tail -3 "$WATCHDOG_LOG" 2>/dev/null)"
fi
grep -q 'RESET: triggering' "$WATCHDOG_LOG" 2>/dev/null \
  && ok "stall triggers a reset" \
  || bad "stall triggers a reset" "$(tail -3 "$WATCHDOG_LOG" 2>/dev/null)"

# --- 4. cooldown suppresses a second reset ---------------------------------
echo "2026-08-06 09:54:00,000 weewxd CRITICAL Caught WeeWxIOError: rtldavis process stalled" >> "$WEEWX_LOG"
sleep 3
n=$(grep -c 'RESET: triggering' "$WATCHDOG_LOG" 2>/dev/null || echo 0)
if [ "$n" -eq 1 ] && grep -q 'SKIP: reset cooldown active' "$WATCHDOG_LOG"; then
  ok "cooldown suppresses a second reset"
else
  bad "cooldown suppresses a second reset" "resets=$n, no SKIP line"
fi

# --- 5. a NON-matching line does not trigger anything ----------------------
before=$(grep -c 'STALL detected' "$WATCHDOG_LOG" 2>/dev/null || echo 0)
echo "2026-08-06 09:55:00,000 weewxd INFO everything is completely fine" >> "$WEEWX_LOG"
sleep 2
after=$(grep -c 'STALL detected' "$WATCHDOG_LOG" 2>/dev/null || echo 0)
[ "$before" = "$after" ] && ok "an unrelated log line triggers nothing" \
                         || bad "an unrelated log line triggers nothing" "$before -> $after"

# --- 6. THE PID GUARD: a second instance refuses to start ------------------
# This is the whole point of DEC-0073a -- it is what makes a 5-minute scheduled
# re-launch idempotent, and therefore what makes the watchdog survive a reboot.
mkdir -p "$WATCHDOG_PROC_DIR/$pid"       # simulate: the first instance is alive
out=$(bash "$WD" 2>&1); rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q "Already running (PID $pid)"; then
  ok "PID guard: second instance exits 0 while the first lives"
else
  bad "PID guard: second instance exits 0 while the first lives" "rc=$rc out=$out"
fi

# --- 7. a STALE pidfile is reclaimed ---------------------------------------
# A kill -9 or a reboot leaves the pidfile behind. If that blocked startup, the
# watchdog would stay dead forever after one hard stop -- the exact permanence
# this whole DEC exists to prevent.
stop_wd "$pid"; sleep 1
rm -rf "${WATCHDOG_PROC_DIR:?}/${pid:?}"
echo 999999 > "$WATCHDOG_PIDFILE"        # a pid that does not exist in our fake /proc
pid2=$(start_wd); sleep 3
if [ -f "$WATCHDOG_PIDFILE" ] && [ "$(cat "$WATCHDOG_PIDFILE")" = "$pid2" ]; then
  ok "stale pidfile is reclaimed, not fatal"
else
  bad "stale pidfile is reclaimed, not fatal" "pidfile=$(cat "$WATCHDOG_PIDFILE" 2>/dev/null) want=$pid2"
fi
stop_wd "$pid2"

echo
if [ "$fail" -eq 0 ]; then
  printf 'WATCHDOG TESTS: %d passed, 0 failures.\n' "$pass"; exit 0
else
  printf 'WATCHDOG TESTS: %d passed, %d FAILURES.\n' "$pass" "$fail"; exit 1
fi
