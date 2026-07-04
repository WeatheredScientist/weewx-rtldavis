#!/bin/sh

CONF="/volume1/docker/weewx-rtldavis/weewx-data/weewx.conf"
LOG="/volume1/docker/weewx-rtldavis/logs/weewx_monitor.log"
OUT="/volume1/docker/weewx-rtldavis/rf_timing_autotest_$(date +%Y%m%d_%H%M).csv"

echo "test,start,end,windows,total,percent" > "$OUT"

run_test() {
  NAME="$1"
  CMD="$2"
  MINUTES="$3"

  echo "=== Starting $NAME : $CMD ==="

  sed -i "/^[[:space:]]*cmd = \/usr\/local\/bin\/rtldavis/c\    cmd = $CMD" "$CONF"
  docker restart weewx-rtldavis-v2 >/dev/null

  sleep 180   # ignore restart/reacquisition

  START=$(date "+%Y-%m-%d %H:%M:%S")
  sleep $((MINUTES * 60))
  END=$(date "+%Y-%m-%d %H:%M:%S")

  DATA=$(awk -v start="$START" -v end="$END" '
    /WINDOW:/ {
      ts=$1 " " $2
      if (ts >= start && ts <= end) {
        split($4,a,"/")
        good += a[1]
        total += a[2]
        n++
      }
    }
    END {
      if (total > 0) printf "%d,%d,%.1f", n,total,(good/total)*100;
      else printf "0,0,0";
    }
  ' "$LOG")

  echo "$NAME,$START,$END,$DATA" >> "$OUT"
}

run_test "baseline" "/usr/local/bin/rtldavis -gain 207 -v" 20
run_test "ex25" "/usr/local/bin/rtldavis -gain 207 -v -ex 25" 20
run_test "ex50" "/usr/local/bin/rtldavis -gain 207 -v -ex 50" 20
run_test "ex75" "/usr/local/bin/rtldavis -gain 207 -v -ex 75" 20
run_test "ex100" "/usr/local/bin/rtldavis -gain 207 -v -ex 100" 20
run_test "maxmissed25" "/usr/local/bin/rtldavis -gain 207 -v -maxmissed 25" 20
run_test "ex50_maxmissed25" "/usr/local/bin/rtldavis -gain 207 -v -ex 50 -maxmissed 25" 20

# restore known-good baseline
sed -i "/^[[:space:]]*cmd = \/usr\/local\/bin\/rtldavis/c\    cmd = /usr/local/bin/rtldavis -gain 207 -v" "$CONF"
docker restart weewx-rtldavis-v2 >/dev/null

echo "DONE. Results: $OUT"
