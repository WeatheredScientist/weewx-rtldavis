#!/usr/bin/env python3
"""
backfill_influx.py — Eagle Hunt PWS
Reads WeeWX SQLite archive and writes missing records to InfluxDB 2.x
via direct HTTP line protocol POST.

Usage:
    python3 backfill_influx.py --token YOUR_TOKEN [--start 2026-05-19] [--end 2026-06-19T15:28:00] [--dry-run]

Fields are mapped from WeeWX US units to the suffixed names already in InfluxDB
(e.g. outTemp -> outTemp_F, windSpeed -> windSpeed_mph, etc.)
matching the existing schema established by the influx2 uploader.
"""

import sqlite3
import urllib.request
import urllib.error
import argparse
import datetime
import time
import sys

# ── Configuration ────────────────────────────────────────────────────────────

INFLUX_URL   = "http://localhost:8086"
INFLUX_ORG   = "YOUR_INFLUX_ORG"
INFLUX_BUCKET = "weewx"
DB_PATH      = "/volume1/docker/weewx-rtldavis/weewx-data/archive/weewx.sdb"
MEASUREMENT  = "record"
BATCH_SIZE   = 500   # records per POST

# Fields to backfill and their InfluxDB names + unit suffixes.
# Only fields that are non-NULL and in the existing dashboard schema.
# WeeWX stores in US units: F, inHg, mph, inches, W/m2
FIELD_MAP = {
    "outTemp":      "outTemp_F",
    "dewpoint":     "dewpoint_F",
    "outHumidity":  "outHumidity",
    "barometer":    "barometer_inHg",
    "windSpeed":    "windSpeed_mph",
    "windGust":     "windGust_mph",
    "windDir":      "windDir",
    "windGustDir":  "windGustDir",
    "rainRate":     "rainRate_inch_per_hour",
    "rain":         "rain_in",
    "radiation":    "radiation_Wpm2",
    "UV":           "UV",
    "ET":           "ET_in",
    "heatindex":    "heatindex_F",
    "windchill":    "windchill_F",
    "inTemp":       "inTemp_F",
    "inHumidity":   "inHumidity",
    "rxCheckPercent": "rxCheckPercent",
    "pressure":     "pressure_inHg",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def to_line_protocol(row, col_names, timestamp_ns):
    """Convert a SQLite row to InfluxDB line protocol string."""
    fields = []
    row_dict = dict(zip(col_names, row))
    for sqlite_name, influx_name in FIELD_MAP.items():
        val = row_dict.get(sqlite_name)
        if val is None:
            continue
        try:
            fval = float(val)
        except (TypeError, ValueError):
            continue
        fields.append(f"{influx_name}={fval}")
    if not fields:
        return None
    field_str = ",".join(fields)
    return f"{MEASUREMENT},binding=archive {field_str} {timestamp_ns}"


def post_batch(lines, token, dry_run=False):
    """POST a batch of line protocol lines to InfluxDB."""
    body = "\n".join(lines).encode("utf-8")
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns"
    if dry_run:
        print(f"  [dry-run] Would POST {len(lines)} lines ({len(body)} bytes)")
        return True
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 204
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  ERROR {e.code}: {err[:200]}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return False


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Backfill WeeWX archive to InfluxDB")
    parser.add_argument("--token", required=True, help="InfluxDB auth token")
    parser.add_argument("--start", default="2026-05-19T00:00:00",
                        help="Start datetime (local, default: 2026-05-19T00:00:00)")
    parser.add_argument("--end", default=None,
                        help="End datetime (local, default: 2026-06-19T15:28:00)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without writing to InfluxDB")
    args = parser.parse_args()

    start_dt = datetime.datetime.fromisoformat(args.start)
    end_dt   = datetime.datetime.fromisoformat(args.end) if args.end \
               else datetime.datetime(2026, 6, 19, 15, 28, 0)

    start_ts = int(start_dt.timestamp())
    end_ts   = int(end_dt.timestamp())

    print(f"Backfill range: {start_dt} → {end_dt}")
    print(f"Database: {DB_PATH}")
    print(f"Dry run: {args.dry_run}")
    print()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get column names
    c.execute("PRAGMA table_info(archive)")
    col_names = [r[1] for r in c.fetchall()]

    # Count records in range
    c.execute("SELECT COUNT(*) FROM archive WHERE dateTime >= ? AND dateTime <= ?",
              (start_ts, end_ts))
    total = c.fetchone()[0]
    print(f"Records to backfill: {total}")
    if total == 0:
        print("Nothing to do.")
        return

    # Fetch and post in batches
    c.execute("SELECT * FROM archive WHERE dateTime >= ? AND dateTime <= ? ORDER BY dateTime",
              (start_ts, end_ts))

    batch = []
    posted = 0
    skipped = 0
    errors = 0
    batch_num = 0

    for row in c:
        ts_sec = row[0]
        ts_ns  = ts_sec * 1_000_000_000
        line = to_line_protocol(row, col_names, ts_ns)
        if line is None:
            skipped += 1
            continue
        batch.append(line)
        if len(batch) >= BATCH_SIZE:
            batch_num += 1
            dt = datetime.datetime.fromtimestamp(ts_sec)
            print(f"  Batch {batch_num}: {len(batch)} records through {dt}...", end=" ")
            ok = post_batch(batch, args.token, args.dry_run)
            if ok:
                posted += len(batch)
                print("OK")
            else:
                errors += len(batch)
                print("FAILED")
            batch = []
            time.sleep(0.1)  # gentle rate limiting

    # Final partial batch
    if batch:
        batch_num += 1
        print(f"  Batch {batch_num}: {len(batch)} records (final)...", end=" ")
        ok = post_batch(batch, args.token, args.dry_run)
        if ok:
            posted += len(batch)
            print("OK")
        else:
            errors += len(batch)
            print("FAILED")

    conn.close()
    print()
    print(f"Done. Posted: {posted} | Skipped (null): {skipped} | Errors: {errors}")


if __name__ == "__main__":
    main()
