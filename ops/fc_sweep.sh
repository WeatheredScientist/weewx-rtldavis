#!/bin/bash
# fc_sweep.sh
# Sweeps rtldavis -fc parameter to find optimal frequency correction.
# Holds gain=207 constant (confirmed best from gain sweep).
# Counts RAW_DATAPACKET_MATCH lines as the reception metric.
# Thermal-aware: long warmup on first step, short stabilization on subsequent steps.
# SSH-disconnect safe: run with: nohup bash fc_sweep.sh > /tmp/fc_sweep_nohup.log 2>&1 &

# --- Parameters ---
FC_VALUES="-4000 -3000 -2000 -1000 0 1000 2000"
GAIN=207

WEEWX_CONF=/volume1/docker/weewx-rtldavis/weewx-data/weewx.conf
WEEWX_LOG=/volume1/docker/weewx-rtldavis/logs/weewx.log
RESULTS=/volume1/docker/weewx-rtldavis/fc_sweep_results.csv
SWEEP_LOG=/volume1/docker/weewx-rtldavis/logs/fc_sweep.log

# Timing (seconds)
COLD_WARMUP=600       # 10 min first step: dongle may be cold
HOT_STABILIZE=120     # 2 min subsequent steps: dongle stays warm across restart
COLLECT_DURATION=600  # 10 min of data collection per fc value
RESTART_PAUSE=5       # seconds between docker kill and docker start

# --- Helpers ---
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$SWEEP_LOG"
}

count_packets_since() {
    # Count RAW_DATAPACKET_MATCH lines added after line number $1
    local from_line=$1
    local total
    total=$(wc -l < "$WEEWX_LOG")
    if [ "$total" -le "$from_line" ]; then
        echo 0
        return
    fi
    tail -n "+$((from_line + 1))" "$WEEWX_LOG" | grep -c 'RAW_DATAPACKET_MATCH' || echo 0
}

set_fc_in_conf() {
    local fc=$1
    python3 -c "
import re
with open('$WEEWX_CONF') as f:
    c = f.read()
# Update -fc value; handle both positive and negative
c = re.sub(r'-fc\s+-?[0-9]+', '-fc $fc', c)
with open('$WEEWX_CONF', 'w') as f:
    f.write(c)
print('fc set to $fc')
"
}

restart_container() {
    log "Stopping container..."
    docker kill weewx-rtldavis-v2 2>/dev/null
    sleep "$RESTART_PAUSE"
    log "Starting container..."
    docker start weewx-rtldavis-v2
}

wait_for_log_activity() {
    # Wait until weewx log is receiving new lines (container is up and running)
    local baseline
    baseline=$(wc -l < "$WEEWX_LOG")
    local waited=0
    while true; do
        sleep 5
        waited=$((waited + 5))
        local current
        current=$(wc -l < "$WEEWX_LOG")
        if [ "$current" -gt "$baseline" ]; then
            log "Container active after ${waited}s"
            return
        fi
        if [ "$waited" -ge 60 ]; then
            log "WARNING: container may not have started cleanly after 60s"
            return
        fi
    done
}

# --- Setup ---
mkdir -p "$(dirname "$SWEEP_LOG")"
log "========================================"
log "FC SWEEP STARTED"
log "Gain: $GAIN (fixed)"
log "FC values: $FC_VALUES"
log "Cold warmup: ${COLD_WARMUP}s  Hot stabilize: ${HOT_STABILIZE}s  Collect: ${COLLECT_DURATION}s"
log "Results: $RESULTS"
log "========================================"

echo "timestamp_start,fc,collect_duration_s,packets_received,packets_possible,pct_good,avg_gap_s" > "$RESULTS"

# --- Sweep ---
STEP=0
for FC in $FC_VALUES; do
    STEP=$((STEP + 1))
    TOTAL=$(echo $FC_VALUES | wc -w)
    log ""
    log "=== Step $STEP/$TOTAL: fc=$FC gain=$GAIN ==="

    # Update config
    set_fc_in_conf "$FC"
    log "weewx.conf updated: -gain $GAIN -fc $FC"

    # Restart container
    restart_container
    wait_for_log_activity

    # Thermal warmup
    if [ "$STEP" -eq 1 ]; then
        log "Cold warmup: sleeping ${COLD_WARMUP}s to allow dongle to thermalize..."
        sleep "$COLD_WARMUP"
    else
        log "Hot stabilize: sleeping ${HOT_STABILIZE}s (dongle retains heat)..."
        sleep "$HOT_STABILIZE"
    fi

    # Log freqError snapshot to verify thermal stability before collecting
    log "Pre-collection freqError snapshot:"
    tail -n 50 "$WEEWX_LOG" | grep 'STORE_FREQERROR_MOD5' | tail -5 | while read -r line; do
        log "  $line"
    done

    # Collect
    TS=$(date '+%Y-%m-%d %H:%M:%S')
    BASELINE_LINE=$(wc -l < "$WEEWX_LOG")
    BASELINE_TIME=$(date +%s)
    log "Collecting for ${COLLECT_DURATION}s from log line $BASELINE_LINE..."

    sleep "$COLLECT_DURATION"

    END_TIME=$(date +%s)
    ACTUAL_DURATION=$((END_TIME - BASELINE_TIME))
    PACKETS=$(count_packets_since "$BASELINE_LINE")

    # Expected packets: 1 per 2.5625s (Davis VP2 ISS interval)
    POSSIBLE=$(python3 -c "print(int($ACTUAL_DURATION / 2.5625))")
    PCT=$(python3 -c "print(round($PACKETS * 100.0 / max($POSSIBLE, 1), 1))")
    AVG_GAP=$(python3 -c "print(round($ACTUAL_DURATION / max($PACKETS, 1), 2))")

    log "RESULT: fc=$FC  packets=$PACKETS/$POSSIBLE ($PCT%)  avg_gap=${AVG_GAP}s  duration=${ACTUAL_DURATION}s"
    echo "$TS,$FC,$ACTUAL_DURATION,$PACKETS,$POSSIBLE,$PCT,$AVG_GAP" >> "$RESULTS"
done

log ""
log "========================================"
log "FC SWEEP COMPLETE"
log "========================================"
log ""
log "Results summary:"
cat "$RESULTS" | column -t -s','
