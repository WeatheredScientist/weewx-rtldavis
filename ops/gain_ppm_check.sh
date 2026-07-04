#!/bin/bash
# gain_ppm_check.sh
# Phase 1: 3-point gain check at fc=2000 (197, 207, 217)
# Phase 2: ppm test at fc=0 (ppm=0, 2, 3), then ppm=2 + fc=2000
#
# Usage: nohup bash gain_ppm_check.sh > /tmp/gain_ppm_check_nohup.log 2>&1 &
#
# Results: /volume1/docker/weewx-rtldavis/gain_ppm_check_results.csv
# Log:     /volume1/docker/weewx-rtldavis/logs/gain_ppm_check.log

set -euo pipefail

# --- Config ---
WEEWX_CONF="/volume1/docker/weewx-rtldavis/weewx-data/weewx.conf"
WEEWX_LOG="/volume1/docker/weewx-rtldavis/logs/weewx.log"
RESULTS_CSV="/volume1/docker/weewx-rtldavis/gain_ppm_check_results.csv"
SWEEP_LOG="/volume1/docker/weewx-rtldavis/logs/gain_ppm_check.log"
CONTAINER="weewx-rtldavis-v2"
STABILIZE=120
COLLECT=600

# Phase 1: gain check at fc=2000, ppm=0
# Phase 2: ppm test at fc=0, gain=207
# Phase 3: best ppm + fc=2000, gain=207
# Format: "gain fc ppm label"
STEPS=(
    "197 2000 0 gain=197,fc=2000,ppm=0"
    "207 2000 0 gain=207,fc=2000,ppm=0"
    "217 2000 0 gain=217,fc=2000,ppm=0"
    "207 0 0 gain=207,fc=0,ppm=0"
    "207 0 2 gain=207,fc=0,ppm=2"
    "207 0 3 gain=207,fc=0,ppm=3"
    "207 2000 2 gain=207,fc=2000,ppm=2"
)

TOTAL=${#STEPS[@]}

# --- Logging helper ---
log() {
    local msg="$1"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$ts $msg" | tee -a "$SWEEP_LOG"
}

# --- CSV header ---
if [[ ! -f "$RESULTS_CSV" ]]; then
    echo "timestamp,gain,fc_hz,ppm,packets,possible,pct,avg_gap_s,label" > "$RESULTS_CSV"
fi

log ""
log "========================================"
log "GAIN + PPM CHECK — $(date '+%Y-%m-%d')"
log "Steps: ${TOTAL}"
log "Stabilize: ${STABILIZE}s  Collect: ${COLLECT}s"
log "========================================"
log ""

STEP=0
for ENTRY in "${STEPS[@]}"; do
    STEP=$((STEP + 1))
    GAIN=$(echo "$ENTRY" | awk '{print $1}')
    FC=$(echo "$ENTRY" | awk '{print $2}')
    PPM=$(echo "$ENTRY" | awk '{print $3}')
    LABEL=$(echo "$ENTRY" | awk '{print $4}')

    log ""
    log "=== Step ${STEP}/${TOTAL}: ${LABEL} ==="

    # --- Update weewx.conf cmd line ---
    sed -i "s|cmd = /usr/local/bin/rtldavis.*|cmd = /usr/local/bin/rtldavis -gain ${GAIN} -v -fc ${FC} -ppm ${PPM}|" "$WEEWX_CONF"
    log "weewx.conf updated: -gain ${GAIN} -fc ${FC} -ppm ${PPM}"

    # --- Restart container ---
    log "Stopping container..."
    docker stop "$CONTAINER" >> "$SWEEP_LOG" 2>&1 || true
    sleep 3

    log "Starting container..."
    docker start "$CONTAINER" >> "$SWEEP_LOG" 2>&1

    WAIT=0
    until docker exec "$CONTAINER" echo "" > /dev/null 2>&1; do
        sleep 1
        WAIT=$((WAIT + 1))
        if [[ $WAIT -gt 30 ]]; then
            log "ERROR: Container did not start within 30s — aborting"
            exit 1
        fi
    done
    log "Container active after ${WAIT}s"

    # --- Hot stabilize ---
    log "Hot stabilize: sleeping ${STABILIZE}s (dongle retains heat)..."
    sleep "$STABILIZE"

    # --- Pre-collection freqError snapshot ---
    log "Pre-collection freqError snapshot:"
    grep "STORE_FREQERROR_MOD5" "$WEEWX_LOG" | tail -5 | while read -r line; do
        log "  $line"
    done

    # --- Collect ---
    START_LINE=$(wc -l < "$WEEWX_LOG")
    log "Collecting for ${COLLECT}s from log line ${START_LINE}..."
    sleep "$COLLECT"

    # --- Count packets ---
    PACKETS=$(tail -n +"$START_LINE" "$WEEWX_LOG" | grep -c "RAW_DATAPACKET_MATCH" || true)

    POSSIBLE=$(( COLLECT * 2 / 5 ))
    PCT=$(( PACKETS * 100 / POSSIBLE ))
    PCT_TENTHS=$(( (PACKETS * 1000 / POSSIBLE) % 10 ))
    PCT_FMT="${PCT}.${PCT_TENTHS}"

    if [[ "$PACKETS" -gt 0 ]]; then
        AVG_GAP_INT=$(( COLLECT / PACKETS ))
        AVG_GAP_TENTHS=$(( (COLLECT * 100 / PACKETS) % 100 ))
        AVG_GAP="${AVG_GAP_INT}.${AVG_GAP_TENTHS}"
    else
        AVG_GAP="N/A"
        PCT_FMT="${PCT}.0"
    fi

    TS=$(date '+%Y-%m-%d %H:%M:%S')
    log "RESULT: ${LABEL}  packets=${PACKETS}/${POSSIBLE} (${PCT_FMT}%)  avg_gap=${AVG_GAP}s"
    echo "${TS},${GAIN},${FC},${PPM},${PACKETS},${POSSIBLE},${PCT_FMT},${AVG_GAP},${LABEL}" >> "$RESULTS_CSV"

done

log ""
log "========================================"
log "GAIN + PPM CHECK COMPLETE"
log "========================================"
log ""
log "Results summary:"
cat "$RESULTS_CSV" | tee -a "$SWEEP_LOG"

log ""
log "Next step: review results with operator, commit winning gain/fc/ppm to weewx.conf."
