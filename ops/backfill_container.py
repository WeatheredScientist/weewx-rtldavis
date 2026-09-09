#!/usr/bin/env python3
"""
backfill_container.py - Eagle Hunt PWS
Backfill WeeWX archive -> InfluxDB 2.x, run INSIDE the live weewx container
(paths hardcoded for that environment; DEC-0151/153/155 all reimplemented this
ad hoc rather than running a checked-in tool -- this is that tool, fixed).

Reads server_url/org/bucket/token directly from the container's own mounted
weewx.conf ([[Influx]], via configobj -- already a weewx dependency) so the
token never has to be typed, exported, or otherwise cross a transcript
(MARVIN-DEC-0128). Opens the archive read-only: this runs against the LIVE
production database.

Invocation (argv must be whitespace-free tokens for `marvinctl exec`, so the
script body is piped over stdin instead of run from a mounted path):

    cat ops/backfill_container.py | marvinctl --tenant weewx exec \
        weewx-rtldavis-v2 -- /opt/weewx-venv/bin/python3 - \
        --start 2026-09-07T17:09:00 --end 2026-09-07T20:52:00 --dry-run

Drop --dry-run once the range and record count look right.
"""
import sqlite3
import urllib.request
import urllib.error
import argparse
import datetime
import time
import sys

import configobj

WEEWX_CONF  = "/opt/weewx-data/weewx.conf"
DB_PATH     = "/opt/weewx-data/archive/weewx.sdb"
MEASUREMENT = "record"
BATCH_SIZE  = 500

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


def find_section(conf, name):
    """Depth-first search for a section by name, wherever it's nested."""
    for key, val in conf.items():
        if not hasattr(val, "keys"):
            continue
        if key == name:
            return val
        found = find_section(val, name)
        if found is not None:
            return found
    return None


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


def post_batch(lines, token, org, bucket, server_url, dry_run):
    body = "\n".join(lines).encode("utf-8")
    url = (server_url + "/api/v2/write?org=" + org
           + "&bucket=" + bucket + "&precision=ns")
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
    p = argparse.ArgumentParser(
        description="Backfill WeeWX archive to InfluxDB (run inside the live container)")
    p.add_argument("--start", required=True, help="Start datetime, local, e.g. 2026-09-07T17:09:00")
    p.add_argument("--end", required=True, help="End datetime, local, e.g. 2026-09-07T20:52:00")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    conf = configobj.ConfigObj(WEEWX_CONF)
    influx = find_section(conf, "Influx")
    if influx is None:
        p.error(f"no [[Influx]] section found in {WEEWX_CONF}")
    server_url = influx["server_url"]
    org = influx["org"]
    bucket = influx["bucket"]
    token = influx["token"]

    start_ts = int(datetime.datetime.fromisoformat(args.start).timestamp())
    end_ts   = int(datetime.datetime.fromisoformat(args.end).timestamp())

    print("Range: " + args.start + " -> " + args.end)
    print("DB: " + DB_PATH)
    print("InfluxDB: " + server_url + " org=" + org + " bucket=" + bucket)
    print("Dry run: " + str(args.dry_run))

    # Read-only: this is the LIVE production archive, still being written by
    # weewx every archive interval. A plain connect() opens read-write and
    # risks exactly the lock contention DEC-0070/DEC-0071 had to fix for the
    # main process (weedb's own 30s timeout doesn't apply to this connection).
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("PRAGMA table_info(archive)")
    cols = [r[1] for r in c.fetchall()]

    c.execute("SELECT COUNT(*) FROM archive WHERE dateTime>=? AND dateTime<=?",
              (start_ts, end_ts))
    total = c.fetchone()[0]
    print("Records to post: " + str(total))
    if total == 0:
        print("Nothing to do.")
        return

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
            if post_batch(batch, token, org, bucket, server_url, args.dry_run):
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
        if post_batch(batch, token, org, bucket, server_url, args.dry_run):
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
