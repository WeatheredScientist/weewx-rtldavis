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

#
# WHICH DEVICE (DEC-0217, #453). This script used to unbind a hardcoded port,
# `1-3`, which was the dongle's port on the original Synology. On any other host
# that port can be a different device, and this runs as root. So it now finds the
# port itself: the one USB device whose id is an RTL2832U. If it finds none, or
# more than one, it refuses and exits non-zero; it never guesses. With two dongles
# attached, set PORT below to the one weewx uses. The id check still applies to a
# pinned port, so a wrong PORT is refused rather than reset.
#
# The port is deliberately NOT read from the environment or the command line. The
# sudoers grant is scoped to this path with no arguments, so an input the monitor's
# user controls would let that user unbind any device as root.
PORT=""
RTL_IDS="0bda:2838 0bda:2832"   # RTL-SDR Blog v3 and generic RTL2832U dongles
SYSFS=/sys/bus/usb

HERE=$(cd "$(dirname "$0")" && pwd)
FORENSICS="${USB_FORENSICS_SCRIPT:-$HERE/usb_forensics.sh}"

# ⚠️ THIS SCRIPT RUNS AS ROOT, under a sudoers NOPASSWD grant scoped to exactly
# this path (README "Security Note"). So anything it executes also runs as root,
# and a helper writable by weewx-monitor would convert that narrow grant into
# arbitrary root execution — the precise escalation the dedicated-user setup
# exists to prevent. usb_forensics.sh must therefore be root-owned and writable
# by nobody else, exactly like this file.
#
# Checked here rather than merely documented: prose does not execute (DEC-0040),
# and on bind-mounted or shared volumes mode 777 is common enough that "it will be deployed correctly"
# is not a safe assumption. Refusal is LOUD on stderr — weewx_monitor.py logs
# this script's output — because a security check that silently skips the capture
# is the silent-no-op failure class this repo keeps getting bitten by.
capture() {
    [ -x "$FORENSICS" ] || return 0

    # GNU (Linux/busybox) first, BSD second, so this is testable on a laptop.
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
            # sudo's env_reset drops the caller's environment, so the helper is
            # told the port and the base directory here, not left to its defaults.
            USB_RESET_PORT="$PORT" WEEWX_RTLDAVIS_DIR="${WEEWX_RTLDAVIS_DIR:-$HERE}" \
                "$FORENSICS" "$1" >/dev/null 2>&1 || true
            ;;
    esac
}

# Prints vendor:product for a device directory; empty when it has none (an
# interface, a missing port).
usb_id() {
    [ -r "$1/idVendor" ] && [ -r "$1/idProduct" ] || return 0
    printf '%s:%s' "$(cat "$1/idVendor")" "$(cat "$1/idProduct")"
}

is_rtl() {
    for ok in $RTL_IDS; do
        [ "$1" = "$ok" ] && return 0
    done
    return 1
}

refuse() {
    echo "USB RESET REFUSED: $*; nothing was unbound (DEC-0217)." >&2
    exit 3
}

if [ -n "$PORT" ]; then
    # A bus port name only (1-3, 5-1.2): this string is written into sysfs as root.
    case "$PORT" in
        *[!0-9.-]*|-*|*-|[!0-9]*) refuse "PORT='$PORT' is not a USB port name" ;;
    esac
    case "$PORT" in *-*) ;; *) refuse "PORT='$PORT' is not a USB port name" ;; esac
    ID=$(usb_id "$SYSFS/devices/$PORT")
    is_rtl "$ID" || refuse "port $PORT is ${ID:-not a USB device}, not an RTL2832U ($RTL_IDS)"
else
    FOUND=""
    COUNT=0
    for dev in "$SYSFS"/devices/*; do
        name=${dev##*/}
        case "$name" in *:*|usb*) continue ;; esac   # interfaces and root hubs
        if is_rtl "$(usb_id "$dev")"; then
            FOUND="$FOUND $name"
            COUNT=$((COUNT + 1))
        fi
    done
    [ "$COUNT" -eq 0 ] && refuse "no RTL2832U ($RTL_IDS) found under $SYSFS/devices"
    [ "$COUNT" -gt 1 ] && refuse "$COUNT RTL2832U dongles found (ports:$FOUND); set PORT in $0"
    PORT=${FOUND# }
    ID=$(usb_id "$SYSFS/devices/$PORT")
fi
# weewx_monitor.py's do_reset() parses this line; keep its shape.
echo "usb_reset: port=$PORT id=$ID"

capture pre
echo "$PORT" > "$SYSFS/drivers/usb/unbind"
sleep 3
echo "$PORT" > "$SYSFS/drivers/usb/bind"
# After the rebind, not before it: re-enumeration is the event whose effect on the
# container's view and on rtldavis's open handle we are trying to observe.
capture post
