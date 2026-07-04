# Interfaces — weewx-rtldavis

**Status:** Source of truth (the contract consumers depend on)
**Last updated:** 2026-07-04 (S17)

This repo's real product is **data**, not weewx internals. Two published surfaces make up the
contract; changing either can break downstream consumers (currently: the Eagle Hunt dashboard, dev
and prod) — treat both as versioned interfaces, and keep them source-agnostic so non-Davis WeeWX and
eventually CumulusMX can satisfy them (PRINCIPLES §1, DEC-0010).

> **Change discipline:** a change to a field name, unit, or the InfluxDB schema here is an
> interface break. Note it in CHANGELOG, update this doc, and confirm the dashboard side before
> shipping. Adding a new optional field is safe; renaming/removing/reunit-ing an existing one is not.

---

## 1. Loop-JSON — real-time surface

Written by `loop_json_writer.py` (a WeeWX `data_service`, DEC-0005) to
`/opt/weewx-data/loop-data.txt` on **every LOOP packet (~2.5 s** for the VP2+), via atomic
tmp-write + `os.replace`. Served to the dashboard at `/loopdata` by the eh-proxy (which lives in the
dashboard's deployment, not this repo).

**Contract:**
- **Units are US/imperial**, encoded in the key names. The packet is `to_US()`-normalized before
  extraction, so `outTemp_F` is always °F regardless of WeeWX's internal unit config.
- **Sparse fields are cached-forward.** The VP2+ rotates fields across packets (not every field in
  every packet). The writer keeps the last non-None value per field and includes it in every write,
  so consumers always see a full-ish object. `dateTime` is always the current packet's timestamp.
- A field absent from the cache (never yet seen this run) is simply omitted — consumers must treat
  any field as possibly-missing.

**Fields** (`packet_key → output_key`):

| Output key | Source | Unit |
|---|---|---|
| `windSpeed_mph` | windSpeed | mph |
| `windGust_mph` | windGust | mph |
| `windDir` | windDir | degrees |
| `outTemp_F` | outTemp | °F |
| `dewpoint_F` | dewpoint | °F |
| `outHumidity` | outHumidity | % |
| `heatindex_F` | heatindex | °F |
| `barometer_inHg` | barometer | inHg |
| `rainRate_inch_per_hour` | rainRate | in/hr |
| `radiation_Wpm2` | radiation | W/m² |
| `UV` | UV | index |
| `cloudbase_foot` | cloudbase | ft |
| `dateTime` | dateTime | Unix epoch (s) |

**Live example** (a sparse packet — gust/dewpoint/barometer/cloudbase served from cache, omitted here
only because not yet seen this run):
```json
{"windSpeed_mph": 0.0, "windDir": 265.83, "rainRate_inch_per_hour": 0.0,
 "outTemp_F": 94.8, "outHumidity": 44.1, "radiation_Wpm2": 442.99, "UV": 2.22,
 "dateTime": 1783200318}
```

## 2. InfluxDB — archive/time-series surface

Written by `influx.py` (`user.influx.Influx`, a RESTThread uploader — the david-lutz weewx-influx2
fork with a Python-3.14 `e.read().decode()` patch, DEC-0007) using **InfluxDB 2.x line protocol**.

**Contract:**
- Config keys in `weewx.conf [[Influx]]`: `server_url`, `org`, `bucket`, `token`. In the running
  system these resolve to an InfluxDB reachable over the Docker `weather-net` network; the example
  ships generic placeholders (`http://influxdb:8086`, `YOUR_INFLUX_ORG`, `weewx`, `YOUR_INFLUXDB_TOKEN`).
- Field **names are suffixed by unit** matching the WeeWX US schema (the same naming the backfill
  tooling in `ops/backfill_influx.py` maps to). The dashboard's Flux queries are written against these
  suffixed names — renaming a field is a breaking change.
- `ops/backfill_influx.py` / `backfill_container.py` write **missing** archive rows to InfluxDB from
  the WeeWX SQLite archive using this same schema — use them to repair gaps, never to duplicate.

> The dashboard reads InfluxDB only through its own `eh-proxy` (token injected server-side there);
> this repo never sees the dashboard's read path. Our responsibility ends at writing the documented
> schema.

## 3. Upload services (outbound, third-party)

11 RESTful uploaders post the same archive record outward: Wunderground (RapidFire), PWSweather,
CWOP, WOW, WOW-BE, AWEKAS, WeatherCloud, Windy, OWM, InfluxDB, OgoxeUploader. Each is configured in
`weewx.conf` with `YOUR_*` placeholders in the committed example (DEC-0012). These are outputs, not a
contract other code depends on — but they are the reason secret hygiene is non-negotiable.

## 4. Reference: gold standard

A Davis WeatherLink Live console (6313) runs in parallel as the ground-truth reference for validating
our intercepted readings (notably for the rain-spike work — the console shows whether the bucket
actually tipped).
