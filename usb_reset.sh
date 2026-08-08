#!/bin/sh
# USB reset script for RTL-SDR dongle
# This script is intentionally minimal — only USB unbind/rebind
# Owned by root, not writable by weewx-monitor
#
# S68: it now also brackets the reset with a READ-ONLY forensic capture. What it
# DOES to the device is unchanged — still exactly the unbind/rebind below, still
# no power cycle (which is what USB_RESET_ACTION in weewx_monitor.py names).
#
# The capture lives here rather than in the monitor because this is the only step
# that runs as root: weewx_monitor.py runs as the unprivileged weewx-monitor user,
# and the two decisive reads (/proc/<pid>/fd and /proc/<pid>/root, i.e. does the
# stalled rtldavis still hold the device, and does the container still see the old
# node) are root-only. Capturing from here needs NO new sudoers grant and lands the
# evidence at exactly the two moments that matter — immediately before the unbind
# and immediately after the rebind. See ops/usb_forensics.sh for the hypothesis
# this is built to test (BOOT blocker 4, DEC-0074).
#
# The capture must NEVER be able to prevent the reset: the reset is the remedy and
# the capture is only evidence about it. Hence `|| true` on both calls, and no
# `set -e` in this file.

FORENSICS="${USB_FORENSICS_SCRIPT:-/volume1/docker/weewx-rtldavis/usb_forensics.sh}"

# ⚠️ THIS SCRIPT RUNS AS ROOT, under a sudoers NOPASSWD grant scoped to exactly
# this path (README "Security Note"). So anything it executes also runs as root,
# and a helper writable by weewx-monitor would convert that narrow grant into
# arbitrary root execution — the precise escalation the dedicated-user setup
# exists to prevent. usb_forensics.sh must therefore be root-owned and writable
# by nobody else, exactly like this file.
#
# Checked here rather than merely documented: prose does not execute (DEC-0040),
# and on this NAS mode 777 is common enough that "it will be deployed correctly"
# is not a safe assumption. Refusal is LOUD on stderr — weewx_monitor.py logs
# this script's output — because a security check that silently skips the capture
# is the silent-no-op failure class this repo keeps getting bitten by.
capture() {
    [ -x "$FORENSICS" ] || return 0

    # GNU (Synology/busybox) first, BSD second, so this is testable off-NAS.
    f_uid=$(stat -c %u "$FORENSICS" 2>/dev/null || stat -f %u "$FORENSICS" 2>/dev/null)
    f_mode=$(stat -c %a "$FORENSICS" 2>/dev/null || stat -f %OLp "$FORENSICS" 2>/dev/null)
    # Trailing three digits only: a setuid/sticky prefix (4755) would otherwise
    # shift the owner/group/other columns and misread which bits are set.
    f_mode=$(printf '%s' "$f_mode" | tail -c 3)

    if [ "$f_uid" != "0" ]; then
        echo "FORENSICS REFUSED: $FORENSICS is not root-owned (uid=$f_uid);" \
             "running it here would escalate the usb_reset.sh sudo grant." >&2
        return 0
    fi
    # Middle digit = group, last = other; 2/3/6/7 each carry the write bit.
    case "$f_mode" in
        [0-7][2367][0-7]|[0-7][0-7][2367])
            echo "FORENSICS REFUSED: $FORENSICS is writable by non-root" \
                 "(mode=$f_mode); running it here would escalate the" \
                 "usb_reset.sh sudo grant." >&2
            ;;
        *)
            "$FORENSICS" "$1" >/dev/null 2>&1 || true
            ;;
    esac
}

capture pre
echo '1-3' > /sys/bus/usb/drivers/usb/unbind
sleep 3
echo '1-3' > /sys/bus/usb/drivers/usb/bind
# After the rebind, not before it: re-enumeration is the event whose effect on the
# container's view and on rtldavis's open handle we are trying to observe.
capture post
