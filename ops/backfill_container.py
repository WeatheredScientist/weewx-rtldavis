#!/usr/bin/env python3
"""
backfill_container.py - Run INSIDE weewx container
Paths hardcoded for container environment.
"""
import sqlite3
import urllib.request
import urllib.error
import argparse
import datetime
import time
import sys

INFLUX_URL    = "http://influxdb:8086"
INFLUX_ORG    = "YOUR_INFLUX_ORG"
INFLUX_BUCKET = "weewx"
DB_PATH       = "/opt/weewx-data/archive/weewx.sdb"
MEASUREMENT   = "record"
BATCH_SIZE    = 500

FIELD_MAP = {
    "outTemp":        "outTemp_F",
    "dewpoint":       "dewpoint_F",
    "outHumidity":    "outHumidity",
    "barometer":      "barometer_inHg",
    "windSpeed":      "windSpeed_mph",
    "windGust":       "windGust_mph",
    "windDir":        "windDir",
    "windGustDir":    "windGustDir",
    "rainRate":       "rainRate_inch_per_hour",
    "rain":           "rain_in",
    "radiation":      "radiation_Wpm2",
    "UV":             "UV",
    "ET":             "ET_in",
    "heatindex":      "heatindex_F",
    "windchill":      "windchill_F",
    "inTemp":         "inTemp_F",
    "inHumidity":     "inHumidity",
    "rxCheckPercent": "rxCheckPercent",
    "pressure":       "pressure_inHg",
}

def to_line(row, cols, ts_ns):
    d = dict(zip(cols, row))
    fields = []
    for sqlite_name, influx_name in FIELD_MAP.items():
        v = d.get(sqlite_name)
        if v is None:
            continue
        try:
            fields.append(influx_name + "=" + str(float(v)))
        except (TypeError, ValueError):
            pass
    if not fields:
        return None
    return MEASUREMENT + ",binding=archive " + ",".join(fields) + " " + str(ts_ns)

def post_batch(lines, token, dry_run):
    body = "\n".join(lines).encode("utf-8")
    url = (INFLUX_URL + "/api/v2/write?org=" + INFLUX_ORG
           + "&bucket=" + INFLUX_BUCKET + "&precision=ns")
    if dry_run:
        print("  [dry-run] " + str(len(lines)) + " lines")
        return True
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": "Token " + token,
            "Content-Type": "text/plain; charset=utf-8",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 204
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        print("  ERROR " + str(e.code) + ": " + msg[:200], file=sys.stderr)
        return False
    except Exception as e:
        print("  ERROR: " + str(e), file=sys.stderr)
        return False

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--token", required=True)
    p.add_argument("--start", default="2026-05-19T00:00:00")
    p.add_argument("--end",   default="2026-06-19T15:28:00")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    start_ts = int(datetime.datetime.fromisoformat(args.start).timestamp())
    end_ts   = int(datetime.datetime.fromisoformat(args.end).timestamp())

    print("Range: " + args.start + " -> " + args.end)
    print("DB: " + DB_PATH)
    print("Dry run: " + str(args.dry_run))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(archive)")
    cols = [r[1] for r in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM archive WHERE dateTime>=? AND dateTime<=?",
              (start_ts, end_ts))
    total = c.fetchone()[0]
    print("Records to post: " + str(total))

    c.execute(
        "SELECT * FROM archive WHERE dateTime>=? AND dateTime<=? ORDER BY dateTime",
        (start_ts, end_ts)
    )

    batch = []
    posted = 0
    errors = 0
    bn = 0

    for row in c:
        line = to_line(row, cols, row[0] * 1000000000)
        if not line:
            continue
        batch.append(line)
        if len(batch) >= BATCH_SIZE:
            bn += 1
            dt = str(datetime.datetime.fromtimestamp(row[0]))
            print("  Batch " + str(bn) + " through " + dt + "...", end=" ", flush=True)
            if post_batch(batch, args.token, args.dry_run):
                posted += len(batch)
                print("OK")
            else:
                errors += len(batch)
                print("FAILED")
            batch = []
            time.sleep(0.05)

    if batch:
        bn += 1
        print("  Batch " + str(bn) + " (final " + str(len(batch)) + ")...", end=" ", flush=True)
        if post_batch(batch, args.token, args.dry_run):
            posted += len(batch)
            print("OK")
        else:
            errors += len(batch)
            print("FAILED")

    conn.close()
    print("")
    print("Done. Posted: " + str(posted) + "  Errors: " + str(errors))

if __name__ == "__main__":
    main()
