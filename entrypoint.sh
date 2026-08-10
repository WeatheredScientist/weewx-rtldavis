#!/bin/bash
mkdir -p /var/log/weewx
echo "Starting weewx..."
# BIAS_TEE=1 (default) powers an inline LNA through the RTL-SDR v3 bias tee.
# Set BIAS_TEE=0 when no LNA is in circuit: some antennas are DC-shorted and
# would load the tee. The off branch drives it off explicitly rather than
# relying on the power-on default -- tee state can survive a warm restart.
BIAS_TEE="${BIAS_TEE:-1}"
if [ "$BIAS_TEE" = "1" ]; then
    echo "Enabling RTL-SDR bias-tee for LNA..."
    rtl_biast -b 1 || echo "WARNING: rtl_biast failed or not found"
else
    echo "Bias-tee disabled (BIAS_TEE=$BIAS_TEE), driving it off..."
    rtl_biast -b 0 || echo "WARNING: rtl_biast failed or not found"
fi
exec /opt/weewx-venv/bin/weewxd /opt/weewx-data/weewx.conf
