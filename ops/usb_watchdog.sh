#!/bin/bash
# USB watchdog for RTL-SDR dongle on Synology NAS
# Monitors weewx log for rtldavis stalls and resets USB power

LOG=/volume1/docker/weewx-rtldavis/logs/weewx_watchdog.log
WEEWX_LOG=/volume1/docker/weewx-rtldavis/logs/weewx.log
USB_DEVICE=/sys/bus/usb/devices/1-3/syno_vbus_reset
STALL_PATTERN="rtldavis process stalled"
RESET_COOLDOWN=300  # minimum seconds between resets

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

log "Watchdog started, monitoring $WEEWX_LOG"

# Monitor log for stall messages
tail -F $WEEWX_LOG 2>/dev/null | while read line; do
    if echo "$line" | grep -q "$STALL_PATTERN"; then
        log "STALL detected: $line"
        reset_dongle
    fi
done
