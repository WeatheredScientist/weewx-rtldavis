#!/bin/bash
# Start syslog with daily rotation
mkdir -p /var/log/weewx
syslogd -n -O /var/log/weewx/weewx.log &
sleep 1
echo "Starting weewx..."
exec /opt/weewx-venv/bin/weewxd /opt/weewx-data/weewx.conf
