#!/bin/bash
# gain_sweep_v5.sh
# Eagle Hunt PWS — RTL-SDR gain optimization sweep
#
# Design: 7 gain values × 3 reps × 20min dwell
#   - Detectable difference: ~5-6pp at 80% statistical power
#   - Total runtime: ~7.7 hours (overnight)
#   - Metric: RAW_DATAPACKET_MATCH (true packet count, not WU double-publish)
#
# Usage:
#   nohup ./gain_sweep_v5.sh >> logs/gain_sweep_v5.log 2>&1 &
#   Monitor:  tail -f /volume1/docker/weewx-rtldavis/logs/gain_sweep_v5.log
#   Results:  cat /volume1/docker/weewx-rtldavis/gain_sweep_v5_results.csv

# ── Configuration ─────────────────────────────────────────────────────────────

GAIN_VALUES="100 150 200 250 300 350 400"
REPS=3
STABILIZE_SECS=120
DWELL_SECS=1200

CONTAINER="weewx-rtldavis-v2"
WEEWX_CONF="/volume1/docker/weewx-rtldavis/weewx-data/weewx.conf"
WEEWX_LOG="/volume1/docker/weewx-rtldavis/logs/weewx.log"
RESULTS_CSV="/volume1/docker/weewx-rtldavis/gain_sweep_v5_results.csv"
LOG_PREFIX="[gain_sweep_v5]"

# ── Helpers ───────────────────────────────────────────────────────────────────

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $*"
}

set_gain() {
    local gain=$1
    python3 -c "
import re
with open('$WEEWX_CONF') as f:
    c = f.read()
c = re.sub(r'-gain [0-9]+', '-gain $gain', c)
with open('$WEEWX_CONF', 'w') as f:
    f.write(c)
print('gain set to $gain')
"
}

restart_container() {
    docker kill "$CONTAINER" 2>/dev/null
    sleep 2
    docker start "$CONTAINER" &
    sleep 5
    log "container restarting in background"
}

count_packets() {
    local start_line=$1
    local end_line=$2
    local count
    count=$(sed -n "${start_line},${end_line}p" "$WEEWX_LOG" | grep -c "RAW_DATAPACKET_MATCH")
    # grep -c always returns a number (0 if no match); strip whitespace just in case
    echo "${count//[[:space:]]/}"
}

current_log_line() {
    wc -l < "$WEEWX_LOG" | tr -d ' '
}

# ── Expected packets ──────────────────────────────────────────────────────────
# Davis ISS @ channel 5: 1 packet every ~2.5s
# DWELL_SECS * 10 / 25  avoids floating point
POSSIBLE=$(( DWELL_SECS * 10 / 25 ))

# ── Main ──────────────────────────────────────────────────────────────────────

log "=== gain_sweep_v5 starting ==="
log "Gain values: $GAIN_VALUES"
log "Reps per value: $REPS"
log "Dwell: ${DWELL_SECS}s  stabilize: ${STABILIZE_SECS}s"
log "Expected packets/rep (at 100%): $POSSIBLE"
log "Results -> $RESULTS_CSV"
log ""

# Write CSV header (overwrite any previous run)
echo "timestamp,gain,rep,packets,possible,pct" > "$RESULTS_CSV"

total_gains=0
for g in $GAIN_VALUES; do total_gains=$(( total_gains + 1 )); done
gain_num=0

for gain in $GAIN_VALUES; do
    gain_num=$(( gain_num + 1 ))
    log "── Gain $gain (${gain_num}/${total_gains}) ──────────────────────"

    for rep in $(seq 1 $REPS); do
        log "  Rep ${rep}/${REPS}: setting gain=${gain}"

        set_gain "$gain"
        restart_container

        log "  Stabilizing ${STABILIZE_SECS}s..."
        sleep "$STABILIZE_SECS"

        start_line=$(current_log_line)
        start_time=$(date '+%Y-%m-%d %H:%M:%S')
        log "  Collecting from log line ${start_line} for ${DWELL_SECS}s..."

        sleep "$DWELL_SECS"

        end_line=$(current_log_line)
        packets=$(count_packets "$start_line" "$end_line")

        # Ensure packets is a plain integer (no whitespace or empty)
        packets=$(echo "$packets" | tr -d '[:space:]')
        if [ -z "$packets" ]; then packets=0; fi

        # Integer percentage with one decimal place, no bc needed
        pct_int=$(( packets * 100 / POSSIBLE ))
        pct_frac=$(( (packets * 1000 / POSSIBLE) % 10 ))
        pct_str="${pct_int}.${pct_frac}"

        log "  Rep ${rep} result: gain=${gain} packets=${packets}/${POSSIBLE} (${pct_str}%)"
        echo "${start_time},${gain},${rep},${packets},${POSSIBLE},${pct_str}" >> "$RESULTS_CSV"
    done

    log ""
done

# ── Summary ───────────────────────────────────────────────────────────────────

log "=== Sweep complete. Computing summary ==="

python3 << 'PYEOF'
import csv, sys
from collections import defaultdict

results_file = "/volume1/docker/weewx-rtldavis/gain_sweep_v5_results.csv"

try:
    with open(results_file) as f:
        rows = list(csv.DictReader(f))
except Exception as e:
    print(f"Could not read results: {e}")
    sys.exit(1)

if not rows:
    print("No data rows found in results CSV.")
    sys.exit(1)

by_gain = defaultdict(list)
for row in rows:
    try:
        by_gain[int(row['gain'])].append(float(row['pct']))
    except (ValueError, KeyError):
        pass

print(f"{'gain':>6}  {'reps':>4}  {'mean_pct':>8}  {'min':>6}  {'max':>6}  {'range':>6}  {'stddev':>7}")
print("-" * 55)

best_gain, best_mean = None, -1.0

for gain in sorted(by_gain.keys()):
    pcts = by_gain[gain]
    n = len(pcts)
    mean = sum(pcts) / n
    mn, mx = min(pcts), max(pcts)
    rng = mx - mn
    std = (sum((p - mean)**2 for p in pcts) / (n - 1)) ** 0.5 if n > 1 else 0.0
    if mean > best_mean:
        best_mean, best_gain = mean, gain
    marker = " <-- LEADER" if gain == best_gain else ""
    print(f"{gain:>6}  {n:>4}  {mean:>8.2f}  {mn:>6.1f}  {mx:>6.1f}  {rng:>6.1f}  {std:>7.2f}{marker}")

print()
print(f"Winner: gain={best_gain} at {best_mean:.2f}% mean reception")
PYEOF

log ""
log "=== Done. To restore gain=207 and restart: ==="
log "   python3 -c \"import re; f=open('$WEEWX_CONF'); c=f.read(); f.close(); c=re.sub(r'-gain [0-9]+','-gain 207',c); f=open('$WEEWX_CONF','w'); f.write(c); f.close(); print('done')\""
log "   docker kill $CONTAINER && docker start $CONTAINER &"
