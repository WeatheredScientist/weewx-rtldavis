#!/usr/bin/env python3
# recover_sweep_results.py
# Reconstructs gain_sweep_v5 results from weewx_monitor.log WINDOW lines.
# Run on NAS after the sweep completes (or any time) to get real reception data.

import re
from datetime import datetime
from collections import defaultdict

MONITOR_LOG = "/volume1/docker/weewx-rtldavis/logs/weewx_monitor.log"
OUTPUT_CSV  = "/volume1/docker/weewx-rtldavis/gain_sweep_v5_recovered.csv"

fmt = "%Y-%m-%d %H:%M:%S"

# ── Collection windows from gain_sweep_v5.log ─────────────────────────────────
# (gain, rep, start, end)
windows = [
    (100, 1, "2026-06-04 01:07:03", "2026-06-04 01:27:03"),
    (100, 2, "2026-06-04 01:29:12", "2026-06-04 01:49:12"),
    (100, 3, "2026-06-04 01:51:24", "2026-06-04 02:11:24"),
    (150, 1, "2026-06-04 02:13:41", "2026-06-04 02:33:41"),
    (150, 2, "2026-06-04 02:35:51", "2026-06-04 02:55:51"),
    (150, 3, "2026-06-04 02:58:00", "2026-06-04 03:18:00"),
    (200, 1, "2026-06-04 03:20:14", "2026-06-04 03:40:14"),
    (200, 2, "2026-06-04 03:42:23", "2026-06-04 04:02:23"),
    (200, 3, "2026-06-04 04:04:33", "2026-06-04 04:24:33"),
    (250, 1, "2026-06-04 04:26:43", "2026-06-04 04:46:43"),
    (250, 2, "2026-06-04 04:48:53", "2026-06-04 05:08:54"),
    (250, 3, "2026-06-04 05:11:06", "2026-06-04 05:31:06"),
    (300, 1, "2026-06-04 05:33:18", "2026-06-04 05:53:18"),
    (300, 2, "2026-06-04 05:55:28", "2026-06-04 06:15:28"),
    (300, 3, "2026-06-04 06:17:38", "2026-06-04 06:37:38"),
    (350, 1, "2026-06-04 06:39:48", "2026-06-04 06:59:48"),
    (350, 2, "2026-06-04 07:01:58", "2026-06-04 07:21:58"),  # estimated end
    (350, 3, "2026-06-04 07:24:08", "2026-06-04 07:44:08"),  # estimated
    (400, 1, "2026-06-04 07:46:18", "2026-06-04 08:06:18"),  # estimated
    (400, 2, "2026-06-04 08:08:28", "2026-06-04 08:28:28"),  # estimated
    (400, 3, "2026-06-04 08:30:38", "2026-06-04 08:50:38"),  # estimated
]

windows_parsed = [
    (g, r, datetime.strptime(s, fmt), datetime.strptime(e, fmt))
    for g, r, s, e in windows
]

# ── Parse weewx_monitor.log for WINDOW lines ──────────────────────────────────
# Format: "2026-06-04 01:08:50 WINDOW: 15/24 (62%)"
window_re = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) WINDOW: (\d+)/(\d+) \((\d+)%\)')

monitor_windows = []  # list of (ts, received, possible, pct)
with open(MONITOR_LOG) as f:
    for line in f:
        m = window_re.match(line.strip())
        if m:
            ts = datetime.strptime(m.group(1), fmt)
            received = int(m.group(2))
            possible = int(m.group(3))
            pct = int(m.group(4))
            monitor_windows.append((ts, received, possible, pct))

print(f"Found {len(monitor_windows)} WINDOW entries in monitor log")
print(f"  First: {monitor_windows[0][0] if monitor_windows else 'none'}")
print(f"  Last:  {monitor_windows[-1][0] if monitor_windows else 'none'}")
print()

# ── Match WINDOW lines to collection windows ──────────────────────────────────
results = []

for gain, rep, start, end in windows_parsed:
    matching = [(ts, recv, poss, pct) for ts, recv, poss, pct in monitor_windows
                if start <= ts <= end]

    if not matching:
        print(f"  gain={gain} rep={rep}: NO WINDOW lines found in [{start} -> {end}]")
        results.append((gain, rep, start.strftime(fmt), 0, 0, 0, "NO_DATA"))
        continue

    total_received = sum(r for _, r, _, _ in matching)
    total_possible = sum(p for _, _, p, _ in matching)
    mean_pct = total_received * 100 / total_possible if total_possible > 0 else 0
    n_windows = len(matching)

    print(f"  gain={gain} rep={rep}: {n_windows} windows, "
          f"{total_received}/{total_possible} = {mean_pct:.1f}%")
    results.append((gain, rep, start.strftime(fmt), total_received, total_possible,
                    round(mean_pct, 1), n_windows))

# ── Write CSV ─────────────────────────────────────────────────────────────────
with open(OUTPUT_CSV, 'w') as f:
    f.write("gain,rep,timestamp,received,possible,pct,n_windows\n")
    for row in results:
        f.write(",".join(str(x) for x in row) + "\n")

print(f"\nWrote {len(results)} rows to {OUTPUT_CSV}")

# ── Summary table ─────────────────────────────────────────────────────────────
print()
print(f"{'gain':>6}  {'reps':>4}  {'mean_pct':>8}  {'min':>6}  {'max':>6}  {'range':>6}  {'stddev':>7}")
print("-" * 55)

by_gain = defaultdict(list)
for gain, rep, ts, recv, poss, pct, nw in results:
    if nw != "NO_DATA" and poss > 0:
        by_gain[gain].append(pct)

best_gain, best_mean = None, -1.0
for gain in sorted(by_gain.keys()):
    pcts = by_gain[gain]
    n = len(pcts)
    if n == 0:
        continue
    mean = sum(pcts) / n
    mn, mx = min(pcts), max(pcts)
    rng = mx - mn
    std = (sum((p - mean)**2 for p in pcts) / (n - 1)) ** 0.5 if n > 1 else 0.0
    if mean > best_mean:
        best_mean, best_gain = mean, gain
    marker = " <-- LEADER" if gain == best_gain else ""
    print(f"{gain:>6}  {n:>4}  {mean:>8.1f}  {mn:>6.1f}  {mx:>6.1f}  {rng:>6.1f}  {std:>7.2f}{marker}")

print()
if best_gain:
    print(f"Current leader: gain={best_gain} at {best_mean:.1f}% mean reception")
else:
    print("No complete data yet.")
