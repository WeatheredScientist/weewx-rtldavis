#!/bin/bash
# usb_watchdog.sh — reset the RTL-SDR dongle's USB power when rtldavis stalls.
#
# WHY THE SUPERVISION MATTERS MORE THAN THE RESET (DEC-0073). The first version of
# this script had no PID guard and no heartbeat. It was deployed 2026-05-22,
# hand-started once, and never ran again -- it did not survive the 2026-07-08 NAS
# reboot, and nobody noticed for ~2.5 months while BOOT.md recorded it as "deployed
# and live". Three qualifying stalls on 2026-08-06 went unhandled.
#
# It hid because its failure mode is SILENT BY CONSTRUCTION: a watchdog that is not
# running writes exactly the same log as one running with nothing to do -- nothing.
# No observation distinguished the two. So this version does two things the old one
# did not, and they matter more than the reset logic:
#
#   1. PID GUARD (DEC-0073a) -- mirrors weewx_monitor.py:102-115. Re-launching is
#      idempotent, so a scheduled task can fire every 5 minutes and simply exit when
#      already running. That is what makes it survive reboots.
#   2. HEARTBEAT (DEC-0073b) -- touches $HEARTBEAT every tick, so liveness is an
#      mtime check rather than an inference. ops/soak_check.sh asserts it, which is
#      the half that catches the CLASS rather than this one instance.
#
# Deliberately NOT a periodic "still alive" log line: that grows the log without
# bound and buries the real events.
#
# This is mitigation, not diagnosis. It does not explain why the stalls happen.

# Paths are env-overridable so this can be exercised by tests/test_usb_watchdog.sh
# without a NAS. The defaults are the live NAS paths and are what runs in prod --
# the old version hardcoded them, which is a large part of why its behaviour was
# never tested and its death went unnoticed for ~2.5 months.
BASE_DIR="${WATCHDOG_BASE_DIR:-/volume1/docker/weewx-rtldavis}"
LOG="${WATCHDOG_LOG:-$BASE_DIR/logs/weewx_watchdog.log}"
WEEWX_LOG="${WEEWX_LOG:-$BASE_DIR/logs/weewx.log}"
HEARTBEAT="${WATCHDOG_HEARTBEAT:-$BASE_DIR/logs/weewx_watchdog.alive}"
PIDFILE="${WATCHDOG_PIDFILE:-$BASE_DIR/logs/weewx_watchdog.pid}"
TICK="${WATCHDOG_TICK:-60}"   # heartbeat cadence, and the read timeout that drives it
USB_DEVICE="${WATCHDOG_USB_DEVICE:-/sys/bus/usb/devices/1-3/syno_vbus_reset}"
PROC_DIR="${WATCHDOG_PROC_DIR:-/proc}"   # overridable so the PID guard is testable off-Linux
STALL_PATTERN="rtldavis process stalled"
RESET_COOLDOWN="${WATCHDOG_RESET_COOLDOWN:-300}"  # minimum seconds between resets

last_reset=0

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> $LOG
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

reset_dongle() {
    now=$(date +%s)
    elapsed=$((now - last_reset))
    if [ $elapsed -lt $RESET_COOLDOWN ]; then
        log "SKIP: reset cooldown active ($elapsed s since last reset, need $RESET_COOLDOWN s)"
        return
    fi
    log "RESET: triggering syno_vbus_reset on $USB_DEVICE"
    echo 1 > $USB_DEVICE
    sleep 5
    last_reset=$(date +%s)
    log "RESET: complete, dongle idVendor=$(cat /sys/bus/usb/devices/1-3/idVendor 2>/dev/null || echo 'not found')"
}

# --- PID guard (DEC-0073a) ---
# Same shape as weewx_monitor.py:102-115. A stale pidfile left by a kill -9 or a
# reboot is harmless: /proc/<pid> will not exist, so we reclaim it.
if [ -f "$PIDFILE" ]; then
    old=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$old" ] && [ -d "$PROC_DIR/$old" ]; then
        echo "Already running (PID $old), exiting"
        exit 0
    fi
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

touch "$HEARTBEAT"
log "Watchdog started, monitoring $WEEWX_LOG (pid $$, tick ${TICK}s)"

# Monitor log for stall messages.
#
# `read -t $TICK` is what lets the heartbeat tick on a QUIET log. A bare `read`
# blocks until a line arrives, so on a silent log the heartbeat would go stale and
# soak_check would report a live watchdog as dead. bash returns >128 on timeout and
# 1 on EOF, which is how a closed tail pipe is told apart from an idle one -- if
# tail dies we must exit rather than spin, so the scheduler can restart us.
tail -F "$WEEWX_LOG" 2>/dev/null | while :; do
    if IFS= read -r -t "$TICK" line; then
        case "$line" in
            *"$STALL_PATTERN"*)
                log "STALL detected: $line"
                reset_dongle
                ;;
        esac
    else
        rc=$?
        if [ "$rc" -le 128 ]; then
            log "EXIT: tail pipe closed (rc=$rc) — exiting so the scheduler can restart us"
            break
        fi
    fi
    touch "$HEARTBEAT"
done
