# Interfaces — weewx-rtldavis

**Status:** Source of truth (the contract consumers depend on)
**Last updated:** 2026-08-14 (S82b)

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
`/opt/weewx-data/loop-data.txt` **and** `/opt/weewx-data/current.json` on **every LOOP packet
(~2.5 s** for the VP2+), via atomic tmp-write + `os.replace`. Both files carry identical content —
only the path differs. `loop-data.txt` is served to the dashboard's ongoing polling at `/loopdata`
by the eh-proxy (which lives in the dashboard's deployment, not this repo); `current.json` is what
the dashboard fetches **first at boot**, so a first-time visitor doesn't see em-dashes before the
polling loop's first response lands (Cold-load Fix B). Serving `current.json` with the right cache
headers (`no-store`) is the dashboard/eh-proxy's responsibility, not this repo's.

**Contract:**
- **Units are US/imperial**, encoded in the key names. The packet is `to_US()`-normalized before
  extraction, so `outTemp_F` is always °F regardless of WeeWX's internal unit config.
- **Sparse fields are cached-forward, but the cache is BOUNDED (S48, DEC-0053).** The VP2+ rotates
  fields across packets (not every field in every packet), so the writer keeps the last non-None
  value per field and includes it in every write. `dateTime` is always the current packet's
  timestamp — which means a cached value is *implicitly claiming to be current*. It may therefore
  only be served for a bounded time:
  - **300 s** for ISS-rotated fields (rotation is ~25–60 s at this station), matching
    `dewpoint_service.CACHE_TIMEOUT_SECONDS`. Overridable via `[LoopJsonWriter] ttl_default`.
  - **2 × `[DavisPressure] fetch_interval`** (7200 s at the shipped hourly setting) for
    `barometer_inHg`, which comes from the WeatherLink API fetch, *not* the ISS rotation. Derived
    from that service's own config so the two cannot drift apart.
- **`barometer_inHg` is a corrected-upstream passthrough, not an ISS decode (S77).** The VP2+ ISS
  never transmits pressure over 915 MHz. `pressure_service.py`'s `DavisPressureFetcher` polls
  `api.weatherlink.com/v2/current/<station_id>` directly and prefers `bar_sea_level` — **already
  sea-level-corrected by WeatherLink's own cloud side**. This repo applies no correction of its own;
  it relays that value as-is. Unlike `rain`/`rainRate`, **no `_qc` flag marks this** (§2's mechanism
  covers only those two fields today), so a consumer cannot tell from the packet alone that
  `barometer_inHg`'s correction happened entirely upstream, unlike every RF-derived field beside it.
- **`barometer_fetch_epoch` — the relay's own freshness (S82b, #172; lands in prod with v2.0.14).**
  The Unix epoch of the last WeatherLink fetch that actually *succeeded* (a failed or empty poll
  does not advance it). It bypasses the TTL machinery on purpose — its job is to *reveal*
  staleness, so it is published verbatim however old it is, and omitted only when no fetch has
  ever succeeded this run. Consumers wanting a staleness gate compare it to `dateTime` (both are
  epoch seconds); `barometer_inHg` itself still expires from the feed at 2 × `fetch_interval` as
  above.
- **`pressure` and `altimeter` are honest nulls, not backfilled (S82b, #144; lands with v2.0.14).**
  The fetched sea-level value used to also backfill the internal `pressure` (station) and
  `altimeter` loop-packet keys — different quantities, so the archive's station-pressure column
  carried sea-level numbers at this site's elevation (hlf#302). Per DEC-0006 they now stay null
  (the ISS never transmits them), and the **archive columns go NULL from the v2.0.14 deploy
  onward**. Neither key was ever part of this published loop-JSON contract; archive readers
  (hyperlocal-forecast) get honest absence instead of a mislabeled value.

  Past its TTL a field is **omitted rather than frozen**, and the writer logs a `WARNING` naming the
  field. Before S48 the cache was unbounded, so a dead or SensorQC-rejected sensor emitted its last
  value indefinitely under a live timestamp — indistinguishable from a live reading (DEC-0006).
- A field absent from the cache — never yet seen this run, **or expired** — is simply omitted;
  consumers must treat any field as possibly-missing. **A missing field means "no current value,"
  never "value unchanged."**

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
| `windchill_F` | windchill | °F |
| `barometer_inHg` | barometer | inHg |
| `rainRate_inch_per_hour` | rainRate | in/hr |
| `radiation_Wpm2` | radiation | W/m² |
| `UV` | UV | index |
| `cloudbase_foot` | cloudbase | ft |
| `dateTime` | dateTime | Unix epoch (s) |
| `barometer_fetch_epoch` | (pressure_service, S82b) | Unix epoch (s) — optional; no TTL |

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
- **Series key:** `record,binding=archive` (measurement `record`, one tag `binding`). A correction or
  backfill MUST reuse this exact series key, or it forks a parallel series instead of overwriting.
- **QC flag fields (`<field>_qc`) — sparse, added S36 (DEC-0032).** A retrospectively corrected point
  carries an integer flag at the *same* timestamp and series. Currently **`rain_qc = 1`** (3 points) and
  **`rainRate_qc = 1`** (33 points) = "this value was corrected; see `docs/DATA_ERRATA.md`". Note the two
  are **independent**: `rain` and `rainRate` are decoded from *different* ISS messages (counter = type
  0xE, rate = type 0x5 via `time_between_tips`), so a correction to one does **not** imply the other —
  S36 corrected `rain` first and had to come back for `rainRate`. Flags are written **only at corrected
  timestamps** (36 points in all of history), never on normal records — InfluxDB is schemaless, so an
  absent field costs nothing and normal queries never see it. **Consumers must treat `*_qc` as optional**: its absence is
  the common case and means "not corrected". It is a *pointer* to the errata log, not a substitute for
  it — the flag says *that* a point was corrected, DATA_ERRATA says *what, why, and how far it spread*.

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
