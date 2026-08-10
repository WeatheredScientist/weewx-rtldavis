#!/bin/sh
# usb_forensics.sh — read-only USB/handle capture around a watchdog reset (S68).
#
# WHY IT EXISTS: the USB resets FIRE but do not WORK (BOOT blocker 4, DEC-0074).
# 3/3 failed on 2026-08-06, 9/9 on 2026-08-02. The standing hypothesis — NOT
# established — is that the reset treats the DEVICE while the fault is the
# CONSUMER's grip on it: usb_reset.sh is a driver unbind/rebind, not a power
# cycle, so the dongle stays enumerated and nothing makes the stalled rtldavis
# inside the container drop its open libusb handle. That predicts one of two
# observable things after a reset, and this script is built to see either:
#
#   (a) STALE CONTAINER VIEW — the host's /dev/bus/usb/001/ changes (new devnum
#       after rebind) while the container's view still shows the old node; or
#   (b) SURVIVING GRIP — rtldavis still holds an fd onto the pre-reset device
#       node after the rebind.
#
# If BOTH look clean across a real stall, the stall is not a USB fault at all and
# the reset is treating the wrong thing entirely. That is a real answer too.
#
# WHY NOT `docker exec`: this fires during a stall, and a wedged container can
# block an exec indefinitely — the capture would hang on exactly the event it
# exists to record. Every read below is host-side through /proc instead:
# /proc/<pid>/root reaches the container's mount namespace and /proc/<pid>/fd its
# open handles, neither of which depends on the container being responsive. One
# discovered pid yields all of it, and rtldavis being ABSENT is itself a finding
# (that is the "process is not running" mode, a different fault — see
# watchdog_not_running in weewx_monitor.py).
#
# ⚠️ NEVER capture /proc/<pid>/environ, and never dump container env. This repo
# is public and, more immediately, a capture file that a later session reads with
# `nasctl cat` lands in a Claude transcript in plaintext (DEC-0047 — the
# transcript is an egress path). Device nodes, fds and cmdlines carry no
# credentials; environ carries all of them. tests/test_usb_forensics.py pins
# this and will fail if environ is ever added.
#
# READ-ONLY: nothing here mutates anything. It does not perform the reset, does
# not touch the container, and does not write outside its own capture directory.
#
# USAGE:  usb_forensics.sh <phase>        # phase is a free label: pre, post, verify-*
#   Writes  $BASE/logs/usb-forensics/<utc>-<phase>.txt  and echoes the path.
# Called automatically by weewx_monitor.py around every reset. Safe to run by
# hand on a healthy system to bank a known-good baseline to diff a stall against.

set -u

PHASE="${1:-manual}"
BASE="${WEEWX_RTLDAVIS_DIR:-/volume1/docker/weewx-rtldavis}"
OUTDIR="${USB_FORENSICS_DIR:-$BASE/logs/usb-forensics}"
# The port the reset acts on. Kept in step with usb_reset.sh by hand: if that
# script's node ever changes, change this too, or the capture documents a
# different port from the one being reset.
USB_PORT="${USB_RESET_PORT:-1-3}"
KEEP=200                     # newest capture files retained; older ones pruned

mkdir -p "$OUTDIR" 2>/dev/null || true
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$OUTDIR/$STAMP-$PHASE.txt"

say() { printf '%s\n' "$*" >> "$OUT"; }
sec() { printf '\n--- %s\n' "$*" >> "$OUT"; }
# Bounded, never-fatal command capture: a missing tool or an unreadable path
# records itself instead of aborting the run. A partial capture beats none.
run() { { "$@" 2>&1 || printf '(command failed: %s)\n' "$*"; } >> "$OUT"; }

say "=== usb-forensics phase=$PHASE utc=$STAMP port=$USB_PORT ==="
# Every capture states its own privilege. The two decisive reads below
# (/proc/<pid>/fd and /proc/<pid>/root) need root, and weewx_monitor.py runs as
# the unprivileged weewx-monitor user -- which is why it shells the reset out via
# sudo. So a capture taken from the monitor directly is DEGRADED (host-side only)
# while one taken from inside usb_reset.sh, under the existing sudo grant, is
# FULL. Recording it per file means nobody ever has to reason about which it was:
# an empty fd section could otherwise be read as "the handle was released", which
# is the opposite of what a permission denial means.
say "euid=$(id -u 2>/dev/null) user=$(id -un 2>/dev/null)"

# ---------- host view ----------
sec "host: ls -l /dev/bus/usb/001/"
run ls -l /dev/bus/usb/001/

sec "host: /sys/bus/usb/devices/$USB_PORT (the node usb_reset.sh unbinds)"
for f in busnum devnum idVendor idProduct manufacturer product serial version; do
    p="/sys/bus/usb/devices/$USB_PORT/$f"
    if [ -r "$p" ]; then
        say "$f=$(cat "$p" 2>/dev/null)"
    else
        say "$f=(absent)"
    fi
done
say "realpath=$(readlink -f "/sys/bus/usb/devices/$USB_PORT" 2>/dev/null)"

sec "host: every enumerated usb device (path vendor:product devnum)"
for d in /sys/bus/usb/devices/*/; do
    [ -r "$d/idVendor" ] || continue
    say "$(basename "$d") $(cat "$d/idVendor" 2>/dev/null):$(cat "$d/idProduct" 2>/dev/null) devnum=$(cat "$d/devnum" 2>/dev/null)"
done

# ---------- the consumer ----------
# Found by comm rather than by asking Docker: it costs no daemon round-trip, and
# it stays correct across a container recreate. comm is truncated to 15 chars by
# the kernel; "rtldavis" is 8, so an exact match is safe here.
PIDS=""
for p in /proc/[0-9]*; do
    c=$(cat "$p/comm" 2>/dev/null) || continue
    [ "$c" = "rtldavis" ] || continue
    PIDS="$PIDS ${p#/proc/}"
done

sec "consumer: rtldavis host pids"
if [ -z "$PIDS" ]; then
    say "(none — rtldavis is NOT RUNNING on this host)"
    say "That is a DIFFERENT fault from a stall: the binary is not merely mute,"
    say "it is gone. A USB reset does not fix that mode (ERR-0005)."
else
    say "pids:$PIDS"
fi

for pid in $PIDS; do
    sec "rtldavis pid $pid: state"
    run sh -c "grep -E '^(Name|State|PPid|Threads):' /proc/$pid/status"
    say "wchan=$(cat "/proc/$pid/wchan" 2>/dev/null)"
    say "cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)"

    # Age from /proc/<pid>/stat field 22 (starttime, in jiffies since boot)
    # against /proc/uptime -- the canonical source.
    #
    # NOT from `stat -c %y /proc/<pid>`. That directory's mtime tracks recent
    # ACCESS, not process start, and this script reads several files under it
    # moments earlier -- so the mtime reads as "just now" for a process that has
    # been up for days. Measured on this NAS 2026-08-09: the mtime said 17
    # seconds old while field 22 said 2.88 days, and the container had been up 3
    # days with unbroken output. In a stall capture the wrong version would have
    # said "rtldavis just restarted" about a process that never did.
    #
    # HZ is 100 here (confirmed: 250 or 1000 both date rtldavis to before the
    # container that spawned it). No `bc` on this box, so integer arithmetic
    # only; the age in seconds is the reliable field and the wall-clock line is
    # best-effort on top of it.
    _st=$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)
    _up=$(awk '{print $1}' /proc/uptime 2>/dev/null)
    if [ -n "$_st" ] && [ -n "$_up" ]; then
        _age=$(( ${_up%%.*} - _st / 100 ))
        say "age=${_age}s  (from /proc/$pid/stat field 22 vs /proc/uptime)"
        say "started=$(date -d "@$(( $(date +%s) - _age ))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null)"
    else
        say "age=(unreadable)"
    fi
    say "proc-dir-mtime=$(stat -c %y "/proc/$pid" 2>/dev/null) <- ACCESS time, NOT start"

    # Stated before the reads, not inferred after them. An EMPTY fd section from a
    # permission denial looks identical to one from a released handle, and those
    # two mean opposite things.
    if [ -r "/proc/$pid/fd" ]; then
        say "capture-fidelity=FULL (privileged reads below are real)"
    else
        say "capture-fidelity=DEGRADED (not root: fd and container-view sections"
        say "  below are UNREADABLE, not empty. Absence here proves nothing.)"
    fi

    # (b) SURVIVING GRIP. An fd still pointing at a /dev/bus/usb node after the
    # rebind is the hypothesis confirmed: the reset re-probed the driver and the
    # consumer never let go.
    sec "rtldavis pid $pid: open fds (a surviving /dev/bus/usb fd is the finding)"
    run ls -l "/proc/$pid/fd"

    # (a) STALE CONTAINER VIEW. /proc/<pid>/root is the container's mount
    # namespace as the host sees it — no exec, so a wedged container cannot
    # block this. Diff it against the host listing above: same nodes means the
    # views agree, a mismatch is the hypothesis confirmed from the other side.
    sec "rtldavis pid $pid: CONTAINER view of /dev/bus/usb/001/ (via /proc/$pid/root)"
    run ls -l "/proc/$pid/root/dev/bus/usb/001/"
done

# ---------- kernel ----------
# Bounded on purpose. An unbounded log read is what wedged this NAS for 7h18m
# once already (DEC-0036) — that was `docker logs`, a different path, but the
# lesson generalizes: never read a log without a limit on this box.
sec "kernel: dmesg tail"
run sh -c "dmesg 2>/dev/null | tail -n 40"

say ""
say "=== end phase=$PHASE ==="

# Retention: these are small, but nothing else prunes them and the watchdog can
# fire repeatedly during one outage.
ls -1t "$OUTDIR"/*.txt 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
    rm -f "$old" 2>/dev/null || true
done

printf '%s\n' "$OUT"
