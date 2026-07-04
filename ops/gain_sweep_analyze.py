#!/usr/bin/env python3
"""
gain_sweep_analyze.py — Analyze and display results from gain_sweep.sh

Usage:
    python3 gain_sweep_analyze.py [path/to/gain_sweep_results.csv]

Prints a ranked table and recommends the optimal gain setting.
Optionally plots a chart if matplotlib is available.
"""

import sys
import csv
import os
from datetime import datetime

DEFAULT_CSV = "/volume1/docker/weewx-rtldavis/gain_sweep_results.csv"


def load_results(path):
    results = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                results.append({
                    "timestamp_start": row["timestamp_start"],
                    "gain_raw":        int(row["gain_raw"]),
                    "gain_db":         float(row["gain_db"]),
                    "windows":         int(row["windows_collected"]),
                    "received":        int(row["total_received"]),
                    "possible":        int(row["total_possible"]),
                    "pct_good":        int(row["pct_good"]),
                    "notes":           row["notes"],
                })
            except (ValueError, KeyError) as e:
                print(f"  Skipping malformed row: {row} ({e})")
    return results


def summarize(results):
    if not results:
        print("No results to analyze.")
        return

    # Sort by pct_good descending
    ranked = sorted(results, key=lambda r: r["pct_good"], reverse=True)

    print()
    print("=" * 65)
    print("  GAIN SWEEP RESULTS — RANKED BY RECEPTION %")
    print("=" * 65)
    print(f"  {'Rank':<5} {'Gain (dB)':<12} {'Recv/Poss':<14} {'Pct Good':<12} {'Windows'}")
    print("  " + "-" * 60)

    for i, r in enumerate(ranked, 1):
        marker = " ◄ BEST" if i == 1 else ""
        print(f"  {i:<5} {r['gain_db']:<12.1f} "
              f"{r['received']}/{r['possible']:<10} "
              f"{r['pct_good']:<12}% "
              f"{r['windows']}{marker}")

    print()
    best = ranked[0]
    worst = ranked[-1]
    improvement = best["pct_good"] - worst["pct_good"]

    print(f"  Best gain:   {best['gain_db']} dB  →  {best['pct_good']}%")
    print(f"  Worst gain:  {worst['gain_db']} dB  →  {worst['pct_good']}%")
    print(f"  Range:       {improvement} percentage points")
    print()

    # Recommendation
    print("  RECOMMENDATION:")
    print(f"    cmd = /usr/local/bin/rtldavis -gain {best['gain_raw']}")
    print()

    # Warn if results are too close to distinguish (< 5 pp spread)
    if improvement < 5:
        print("  NOTE: Spread < 5 pp — results may be within noise margin.")
        print("        Consider running overnight mode for more windows per gain value.")
    elif best["windows"] < 10:
        print(f"  NOTE: Only {best['windows']} windows collected for best gain.")
        print("        Consider running overnight mode to confirm.")

    print("=" * 65)
    print()


def plot(results):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  (matplotlib not available — skipping chart)")
        return

    gains = [r["gain_db"] for r in results]
    pcts  = [r["pct_good"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(gains, pcts, width=0.8, color="steelblue", edgecolor="white")

    # Highlight best
    best_pct = max(pcts)
    for bar, pct in zip(bars, pcts):
        if pct == best_pct:
            bar.set_color("darkorange")

    ax.set_xlabel("SDR Gain (dB)", fontsize=12)
    ax.set_ylabel("Reception % (packets received / possible)", fontsize=12)
    ax.set_title("weewx-rtldavis — Gain Sweep Reception Results", fontsize=13)
    ax.set_ylim(0, 105)
    ax.axhline(y=best_pct, color="darkorange", linestyle="--", alpha=0.5, label=f"Best: {best_pct}%")
    ax.legend()

    # Value labels on bars
    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{pct}%", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out_path = os.path.splitext(DEFAULT_CSV)[0] + "_chart.png"
    plt.savefig(out_path, dpi=150)
    print(f"  Chart saved: {out_path}")
    plt.show()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    if not os.path.exists(path):
        print(f"CSV not found: {path}")
        sys.exit(1)

    print(f"Loading: {path}")
    results = load_results(path)
    print(f"Loaded {len(results)} gain measurements.")

    summarize(results)
    plot(results)


if __name__ == "__main__":
    main()
