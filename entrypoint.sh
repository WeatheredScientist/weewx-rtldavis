#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# The first argument picks what runs (DEC-0228, the felddy pattern). No argument, or `weewxd`, is
# the station itself: the path below this block, unchanged, and what prod's unit runs.
case "${1:-weewxd}" in
    weewxd)
        ;;
    doctor)
        # Checks the dongle, the kernel driver, the device node and the radio, then prints the
        # config's radio values. A non-zero exit names the troubleshooting row that applies.
        exec /opt/weewx-venv/bin/python3 /opt/doctor.py
        ;;
    weectl)
        exec /opt/weewx-venv/bin/weectl "${@:2}"
        ;;
    *)
        # Anything else runs as given, so `docker run <image> uname -m` keeps working.
        exec "$@"
        ;;
esac
mkdir -p /var/log/weewx
echo "Starting weewx..."
# An empty data mount gets a starter weewx.conf and the first-run values from the environment
# (DEC-0225). With a weewx.conf already there this does nothing. A bad value stops the start.
/opt/weewx-venv/bin/python3 /opt/seed_config.py || exit 1
if [ -z "${TZ:-}" ]; then
    echo "WARNING: TZ is not set, so times are UTC and daily rain resets at 00:00 UTC. Set TZ, e.g. TZ=America/New_York."
fi
# BIAS_TEE=1 powers an inline LNA through the RTL-SDR v3 bias tee. The default is 0, the safe
# state: some antennas are DC-shorted and would load the tee. The off branch drives it off
# explicitly rather than relying on the power-on default -- tee state can survive a warm restart.
BIAS_TEE="${BIAS_TEE:-0}"
if [ "$BIAS_TEE" = "1" ]; then
    echo "Enabling RTL-SDR bias-tee for LNA..."
    rtl_biast -b 1 || echo "WARNING: rtl_biast failed or not found"
else
    echo "Bias-tee disabled (BIAS_TEE=$BIAS_TEE), driving it off..."
    rtl_biast -b 0 || echo "WARNING: rtl_biast failed or not found"
fi
exec /opt/weewx-venv/bin/weewxd /opt/weewx-data/weewx.conf
