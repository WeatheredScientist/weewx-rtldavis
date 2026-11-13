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
# RTLSDR_DEVICE (DEC-0235) names the dongle the station uses, by serial (recommended) or index.
# The driver hands it to the decoder as -d; here it picks the stick the bias tee acts on, so the
# tee never powers a different dongle's antenna. rtl_biast reads a number as an index first and
# the decoder reads it as a serial first, so doctor resolves the value with the decoder's own rule
# and rtl_biast gets that index. If it cannot be resolved, the tee is left alone and the decoder
# refuses to start with the reason.
RTLSDR_DEVICE="${RTLSDR_DEVICE:-}"
biast_dev=()
biast_skip=0
if [ -n "$RTLSDR_DEVICE" ]; then
    if biast_idx="$(/opt/weewx-venv/bin/python3 /opt/doctor.py --resolve)"; then
        echo "RTLSDR_DEVICE=$RTLSDR_DEVICE is librtlsdr dongle $biast_idx"
        biast_dev=(-d "$biast_idx")
    else
        echo "WARNING: RTLSDR_DEVICE=$RTLSDR_DEVICE matches no single dongle; leaving the bias tee alone (run doctor)"
        biast_skip=1
    fi
fi
if [ "$biast_skip" = "1" ]; then
    :
elif [ "$BIAS_TEE" = "1" ]; then
    echo "Enabling RTL-SDR bias-tee for LNA..."
    rtl_biast "${biast_dev[@]}" -b 1 || echo "WARNING: rtl_biast failed or not found"
else
    echo "Bias-tee disabled (BIAS_TEE=$BIAS_TEE), driving it off..."
    rtl_biast "${biast_dev[@]}" -b 0 || echo "WARNING: rtl_biast failed or not found"
fi
exec /opt/weewx-venv/bin/weewxd /opt/weewx-data/weewx.conf
