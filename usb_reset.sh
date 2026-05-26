#!/bin/sh
# USB reset script for RTL-SDR dongle
# This script is intentionally minimal — only USB unbind/rebind
# Owned by root, not writable by weewx-monitor
echo '1-3' > /sys/bus/usb/drivers/usb/unbind
sleep 3
echo '1-3' > /sys/bus/usb/drivers/usb/bind
