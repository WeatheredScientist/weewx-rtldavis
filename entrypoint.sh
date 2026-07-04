#!/bin/bash
mkdir -p /var/log/weewx
echo "Starting weewx..."
echo "Enabling RTL-SDR bias-tee for LNA..."
rtl_biast -b 1 || echo "WARNING: rtl_biast failed or not found"
exec /opt/weewx-venv/bin/weewxd /opt/weewx-data/weewx.conf
