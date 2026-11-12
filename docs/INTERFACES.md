# Interfaces — weewx-rtldavis

**Status:** Specification. The one owner of the data contract (DEC-0233).
**Contract version:** 1.1 · **Last updated:** 2026-11-11 (S199)

This repo's product is data. Three surfaces carry it, and each is specified here: the loop-JSON
file (§1), the InfluxDB bucket (§2) and the SQLite archive (§3). The contract is what a consumer
may rely on, not what this station happens to emit, so any producer that meets it (another WeeWX
driver today, a non-WeeWX program later) can feed the same consumers (PRINCIPLES §1, DEC-0010).
This station's own history, dated corrections and provenance are in Appendix A; they explain the
reference deployment and are not rules.

**Ownership.** This file is the contract's only statement. Consumers (today
`eaglehunt-weather-dashboard` and `hyperlocal-forecast`) link to it rather than restate it; where a
consumer's document disagrees, this file wins and the other is the one to fix.

**Change discipline.** Renaming or removing a key, field or column, or changing its unit, type or
meaning, is a break: a major version, a DEC, a CHANGELOG line, and the consumers confirmed before it
ships. A new optional key is a minor version. A fix that brings behavior back to this text is a
patch.

**Versioning.** The contract has one version, the one above, for all three surfaces. The loop file
states it today through `writer` (`loop_json_writer/1.1.x` meets contract 1.1); a dedicated
contract-version key, independent of the writer's name, is DEC-0233 part 5 and arrives with
`loopjson` 1.2.0 (contract 1.2). InfluxDB and SQLite carry no version of their own: a consumer
learns it here, and for this repo's image DEC-0222's SemVer tags mark when a change shipped.

---

## 0. Rules for every surface

| Rule | Statement |
|---|---|
| Time | `dateTime` is whole seconds of Unix epoch, UTC, non-decreasing, on a clock within about 1 s of the consumer's |
| Absence | A value that is not known is omitted (InfluxDB: no field; SQLite: NULL), never written as 0 or as a placeholder. A missing value means "no current value," never "unchanged" |
| Finite numbers | Every numeric value is finite. NaN and infinity are not values; a producer omits them (see §1, strict JSON) |
| One station | One station per InfluxDB bucket and per SQLite archive. There is no station tag or column |
| Archive interval | Fixed for the life of an archive. The SQLite `interval` column states it in minutes. Consumers are tested against 60 s only; a producer with another interval says so to its consumers before they read it |
| Meanings | The meanings table below. A value under a contract name must mean what the table says, whatever the sensor |

**Meanings a producer must match** (names are WeeWX observation names; each surface adds its own
unit suffix or none):

| Observation | Meaning |
|---|---|
| `barometer` | Sea-level pressure. Not station pressure, not altimeter |
| `pressure` | Station (absolute) pressure, measured. Optional |
| `rain`, `ET` | The record's own increment since the previous record (rain; evapotranspiration). Summed, never scaled by `interval` |
| `rainRate` | Instantaneous rate, per hour |
| `dayRain` | Accumulated since local midnight |
| `windSpeed` | Mean speed for the sample or record. Calm is 0, written, not omitted |
| `windDir` | Direction the wind blows from, degrees. Omitted while calm: no direction exists without wind (loop: see §1's cache rule) |
| `windGust` | Peak of the loop samples within the record |
| `windGust10` | The sensor's own 10-minute gust, when it reports one. Never an alias for `windGust` and never derived from it |
| `heatindex`, `windchill` | Equal to the air temperature outside their formula's range, not omitted |
| `radiation` | Global solar irradiance, W/m². Lux is a different quantity: a lux sensor uses `luminosity` or `illuminance`, never this name |
| `UV` | UV index |
| `dewpoint`, `outTemp`, `outHumidity`, `cloudbase` | As WeeWX defines them |

## 1. Loop-JSON — real-time surface

**Delivery.** `loop_json_writer.py`, a WeeWX `StdService` that runs last in `process_services`
(DEC-0005), writes two files by atomic temporary write plus `os.replace`:

- `loop-data.txt`, rewritten on every LOOP packet. The live feed.
- `current.json`, the same content, rewritten at most once per `[LoopJsonWriter] current_interval`
  (default 60 s; `0` writes it on every packet) and always on a run's first packet. A cold-load
  snapshot for a consumer's first paint, never a liveness source (DEC-0093).

Paths are `[LoopJsonWriter] path` and `current_path`; a relative path resolves against `WEEWX_ROOT`
and the writer creates the directory. Defaults: `loop-data.txt` and `current.json` under
`WEEWX_ROOT`; the extension installs `feed/loop-data.txt` and `feed/current.json`. Anyone running
another driver installs it as a WeeWX extension (DEC-0211): `weectl extension install` on the
`weewx-loopjson-X.Y.Z.zip` asset of a `loopjson-vX.Y.Z` release; its README covers install,
placement and paths, and this section stays the one field table.

**A consumer that bind-mounts these files must mount their directory, not the files.** Every write
replaces a file by rename, and a single-file bind pins the original inode, so the consumer would
read a frozen file forever (DEC-0202). Serving the files, and their cache headers, is the
consumer's job.

**Liveness.** `dateTime` on `loop-data.txt` is a liveness signal, not a change signal. The reference
consumer reports the station offline when `now - dateTime > max(30, 3 × loop_interval_s)` seconds
(dash DEC-0154, DEC-0404), so a producer must not suppress or delay a `loop-data.txt` write past
that bound, even when nothing changed. `current.json`'s `dateTime` may be `current_interval` old on
a healthy station; a consumer must not compute staleness from it.

**Rules:**

- **Strict JSON, one flat object.** Keys are strings, values are JSON numbers or strings; no
  nesting, no arrays, no `null`, no NaN or infinity. (The 1.1.x writer can still write a bare `NaN`
  if a driver puts one in a packet; DEC-0233 part 6 makes it omit non-finite values in 1.2.0.)
- **Fixed US units**, stated in the key names. The writer applies `to_US()` before extraction, so
  `outTemp_F` is °F whatever the station's unit system. This surface does not follow the archive's
  units (contrast §2 and §3).
- **Omit rather than null.** Every key except `dateTime` is optional, and a consumer must treat each
  as possibly missing.
- **Cached forward, bounded.** A station that rotates fields across packets has each field's last
  value carried into every write, for at most its TTL: `[LoopJsonWriter] ttl_default` (300 s), or a
  per-key `[[ttl]]`. Past its TTL a field is omitted, with a WARNING naming it (DEC-0053). So a
  served value is at most one TTL old, under a current `dateTime`.
- **Calm air.** `windSpeed_mph` reads 0. The driver reports no direction, so `windDir` is the last
  direction, cached, until its TTL lapses, and then omitted (#74). A consumer shows no direction
  when `windSpeed_mph` is 0.
- **Deltas are refused.** A per-packet increment (`rain`, `lightning_strike_count`, any observation
  whose accumulator extractor is `sum`) cannot be delivered exactly once by a file overwritten in
  place and read on the consumer's clock. The writer refuses it with a WARNING; list the cumulative
  counterpart (`dayRain`, `lightningcount`) instead.

**Keys.** Type is a JSON number unless stated. "Class" is the sensor class that produces the key;
a station without that class omits it.

| Key | Required | Unit | Class | Meaning and notes |
|---|---|---|---|---|
| `dateTime` | **required** | epoch s, integer | core | The packet's time. Its absence makes the reference consumer answer 503, read as "station offline" |
| `writer` | optional | string | core | `loop_json_writer/<semver>`, the implementation. See Versioning |
| `loop_interval_s` | optional | s | core | Median of the last 32 gaps between successful `loop-data.txt` writes, monotonic clock, one decimal. Omitted, never clamped, outside [1, 3600]. First appears in a run's third file. The file's cadence, not a sensor's: a driver that emits bursts reports the burst cadence |
| `outTemp_F` | optional | °F | thermo-hygro | |
| `outHumidity` | optional | % | thermo-hygro | |
| `dewpoint_F` | optional | °F | thermo-hygro | |
| `heatindex_F` | optional | °F | thermo-hygro | Equals `outTemp_F` outside its range |
| `windchill_F` | optional | °F | thermo-hygro + wind | Equals `outTemp_F` outside its range |
| `windSpeed_mph` | optional | mph | wind | 0 when calm |
| `windDir` | optional | degrees | wind | Calm-air rule above |
| `windGust_mph` | optional | mph | wind | Only from a driver that reports a loop gust; a Davis ISS does not |
| `barometer_inHg` | optional | inHg | barometer | Sea-level |
| `rainRate_inch_per_hour` | optional | in/h | rain | |
| `radiation_Wpm2` | optional | W/m² | solar | |
| `UV` | optional | index | UV | |
| `cloudbase_foot` | optional | ft | derived | Only when WeeWX can derive it on a loop packet, which needs temperature and humidity in the same packet |
| extras | optional | by rule | any | Opt-in, below |

**Extra observations (opt-in, `[LoopJsonWriter] extra_fields`, DEC-0220).** Each named observation
is passed through as `<obs>_<US unit label>` by weewx-influx2's naming rule, read from the live unit
registry; bare when the label reduces to none or the observation has no unit group. The thirteen
standard keys follow the same rule. The name matches the InfluxDB field only while the site's
`[[Influx]]` keeps its defaults (`append_units_label` on, no per-input `name`). Extras share the
cache, TTLs and expiry WARNING above. Keys are computed, not listed; for a US packet on WeeWX 5.5.2:

| Class | Example observations → keys | Kind |
|---|---|---|
| Wind | `windGust10` → `windGust10_mph` (the sensor's 10-minute gust; this driver registers its unit group, DEC-0224) | state. Not `windGust_mph` |
| Light | `luminosity` → `luminosity_lux`, `illuminance` → `illuminance_lux` | state. Not `radiation_Wpm2`; the writer converts nothing |
| Lightning | `lightning_distance` → `lightning_distance_mile`, `lightning_last_det_time` (bare, an epoch), `lightningcount` → `lightningcount_count` (cumulative) | state; `lightning_strike_count` is a delta, refused |
| Air quality | `pm2_5` → `pm2_5_microgram_per_meter_cubed`, `pm10_0` → `pm10_0_microgram_per_meter_cubed`, `co2` → `co2_ppm` | state |
| Soil and leaf | `soilMoist1` → `soilMoist1_centibar`, `soilTemp1` → `soilTemp1_F`, `leafWet1` → `leafWet1_count`, `leafTemp1` → `leafTemp1_F` | state |
| Extra and indoor T/H | `extraTemp1` → `extraTemp1_F`, `extraHumid1`, `inTemp` → `inTemp_F`, `inHumidity` | state |
| Battery and signal | driver-defined names, bare, driver-defined meaning | state |
| Piezo and second rain | `p_rain`, `t_rain`, `rain` refused; `p_rainRate` and cumulative totals pass | delta refused, totals state |

A unit group a driver registers itself (gw1000's `luminosity`, `lightningcount`) is in the registry
only once the driver is imported, which happens before services start; without it the name is bare.

**Optional extension: a relayed barometer.** A producer whose barometer comes from somewhere other
than the station's own radio (this repo's `pressure_service.py` relays WeatherLink's sea-level
value, Appendix A) may add:

| Key | Unit | Meaning |
|---|---|---|
| `barometer_fetch_epoch` | epoch s | Time of the last fetch that succeeded. Published however old it is, outside the TTL rule, so a consumer can compare it with `dateTime`; omitted until one fetch succeeds |

With a `[DavisPressure]` section the writer gives `barometer_inHg` a TTL of 2 × that section's
`fetch_interval`; without one, `ttl_default` applies. Both are harmless on a station without the
service.

**Example** (this station, 2026-11-11):

```json
{"rainRate_inch_per_hour": 0, "radiation_Wpm2": 555.507776, "barometer_inHg": 30.006,
 "windSpeed_mph": 0, "outTemp_F": 59.7, "windchill_F": 59.7, "dewpoint_F": 41.13159559953975,
 "outHumidity": 51.1, "heatindex_F": 57.2217, "UV": 2.2, "windDir": 280.70750988142294,
 "windGust10_mph": 4, "barometer_fetch_epoch": 1794409156, "dateTime": 1794409271,
 "writer": "loop_json_writer/1.1.0", "loop_interval_s": 2.8}
```

Keys a consumer's proxy adds on the way out (the reference dashboard adds `skyState`,
`ongoingEvents`, `loop_cadence_s` and `stale_after_s`) are the consumer's, not this surface's.

## 2. InfluxDB — archive/time-series surface

**Delivery.** `influx.py` (`user.influx.Influx`, a `RESTThread` uploader: the david-lutz
weewx-influx2 fork with a Python 3.14 patch, DEC-0007) writes one point per archive record in
InfluxDB 2.x line protocol. It ships on its own as a WeeWX extension (`influx-v*` releases,
DEC-0219; adopter notes in `extensions/influx/README.md`), with upstream's class path and its
`[StdRESTful][[Influx]]` section. Config keys: `server_url`, `org`, `bucket`, `token`; the example
ships placeholders.

**Rules:**

- **Series key:** measurement `record`, one tag `binding=archive`, no other tag. Any correction or
  backfill reuses this exact key. Adding a tag (a station tag included) forks a parallel series
  rather than annotating the existing one, so it is a break, decided here first (DEC-0053).
- **One point per archive record**, timestamped at the record's `dateTime`, carrying the in-memory
  record (`obs_to_upload = most`). So the bucket can hold fields the SQLite archive has no column
  for.
- **Field names are `<obs>_<unit label>`** in the unit system of the record the uploader sends.
  The installer writes no `unit_system`, so the uploader follows the database: a US archive writes
  `outTemp_F`, a metric one `outTemp_C`, by the same label rule as §1's extras. An adopter may pin
  `unit_system`; a consumer must read the suffix, not assume `_F`. This station is US.
- **Absent, never zero.** A record without a value has no field. `interval` is not written
  (`OBS_TO_SKIP`); §0's fixed-interval rule stands in for it.
- **QC flags, sparse.** `<field>_qc` = 1 at the same timestamp and series means "this value was
  corrected; see `docs/DATA_ERRATA.md`". Today `rain_qc` and `rainRate_qc` exist, and they are
  independent (two ISS messages). Optional: absence, the common case, means "not corrected." The
  flag is a pointer to the errata log, not a substitute for it.
- **Repair:** `ops/backfill_influx.py` and `ops/backfill_container.py` write missing points from the
  SQLite archive with this schema, to fill gaps, never to duplicate.

**Fields** (US labels; this station, 7 days to 2026-11-11). Three tiers:

*Contract fields*, read by a consumer today. Renaming, removing or re-uniting one is a break.

| Field | Unit | Class | Notes |
|---|---|---|---|
| `outTemp_F`, `dewpoint_F`, `heatindex_F`, `windchill_F` | °F | thermo-hygro | |
| `outHumidity` | % | thermo-hygro | |
| `windSpeed_mph`, `windGust_mph` | mph | wind | `windGust_mph` is the record's peak loop sample |
| `windDir` | degrees | wind | Absent when calm |
| `windGust10_mph` | mph | wind | The sensor's 10-minute gust, last value in the record; absent in a minute without one (DEC-0224) |
| `barometer_inHg` | inHg | barometer | Sea-level |
| `rain_in` | in | rain | The record's increment |
| `rainRate_inch_per_hour` | in/h | rain | |
| `dayRain_in` | in | rain | Since local midnight |
| `ET_in` | in | ET | The record's increment, like `rain_in` |
| `radiation_Wpm2` | W/m² | solar | |
| `UV` | index | UV | |
| `cloudbase_foot` | ft | derived | |

*Written, optional*, standard WeeWX observations with standard meanings and no consumer yet. A
producer may omit any of them; adding one is safe.

`altimeter_inHg`, `appTemp_F`, `hourRain_in`, `humidex_F`, `maxSolarRad_Wpm2`, `pressure_inHg`
(station pressure), `rain24_in`, `rxCheckPercent`, `txBatteryStatus`, `windGustDir`,
`windrun_mile`, and `barometer_fetch_epoch` (§1's relayed-barometer extension).

*Outside the contract*: this driver's diagnostics stored under WeeWX column names they borrow. They
may change or vanish without a version step, and no consumer may read them as what the name says:

| Field | Actually holds |
|---|---|
| `consBatteryVoltage_hertz`, `hail_hertz`, `hailRate_hertz`, `heatingTemp_hertz`, `heatingVoltage_hertz` | The decoder's five frequency-error channels |
| `supplyVoltage_volt` | The ISS supercapacitor voltage |
| `referenceVoltage_volt` | The ISS solar-panel voltage |

## 3. SQLite archive — the WeeWX database

**Delivery.** WeeWX's own `archive` table and daily summaries, in the database `[DataBindings]`
names. A consumer opens it read-only, typically through a read-only mount. This repo's image
creates it with the `user.rtldavis.schema` schema, wview_extended plus `windGust10` (DEC-0232).

**Rules:**

- **Units are the archive's own,** stated per row in `usUnits` (1 = US, 16 = METRIC, 17 =
  METRICWX). A consumer must read `usUnits` and convert, or refuse rows it does not handle; column
  names carry no unit.
- **`interval`** per row, in minutes; fixed for the archive (§0).
- **Every row is kept.** No pruning, no retention window: a consumer may read any past row.
- **Rollback journal, not WAL.** The database stays in `journal_mode = DELETE`, so a reader on a
  read-only mount needs no `-wal`/`-shm` files. WAL is a break.
- **No correction flag.** A row corrected after the fact is indistinguishable from one never
  corrected; the provenance lives in InfluxDB's `*_qc` fields and `docs/DATA_ERRATA.md`
  (DEC-0053).

**Columns a consumer may rely on** (meanings per §0; NULL when unknown):

| Column | Notes |
|---|---|
| `dateTime` | Record end time, epoch s, primary key |
| `usUnits`, `interval` | Per-row unit system and interval |
| `outTemp`, `dewpoint`, `outHumidity`, `appTemp`, `heatindex`, `windchill` | |
| `windSpeed`, `windDir`, `windGust` | `windDir` NULL when calm |
| `windGust10` | The sensor's 10-minute gust; NULL in a minute without one, never 0. Not in stock wview_extended: an existing archive adds it with `weectl database add-column windGust10` (DEC-0232) |
| `barometer` | Sea-level |
| `pressure` | Station pressure, measured; NULL if the producer has no measurement. Before a producer measured it, WeeWX derived it from `barometer` (Appendix A) |
| `rain`, `rainRate` | `rain` is the record's increment |
| `radiation`, `UV` | |
| `archive_day_rain` (`dateTime`, `sum`, `count`) | Daily rain total: `sum` per local day |

Other wview_extended columns are present and follow WeeWX's meanings, with no promise beyond that.
The diagnostics of §2's last table are in the same borrowed columns here, and are outside the
contract in the same way.

## 4. Upload services (outbound, third-party)

11 RESTful uploaders post the same archive record outward: Wunderground (RapidFire), PWSweather,
CWOP, WOW, WOW-BE, AWEKAS, WeatherCloud, Windy, OWM, InfluxDB, OgoxeUploader. Each is configured in
`weewx.conf` with `YOUR_*` placeholders in the committed example (DEC-0012). These are outputs, not a
contract other code depends on — but they are the reason secret hygiene is non-negotiable.

## 5. Reference: gold standard

A Davis WeatherLink Live console (6313) runs in parallel as the ground-truth reference for validating
our intercepted readings (notably for the rain-spike work — the console shows whether the bucket
actually tipped).

---

## Appendix A — Reference deployment: history and provenance

Moved verbatim from the S198 version of this file (DEC-0233 part 2); nothing below was rewritten.
It records how this station's data came to be what it is. It is not part of the contract: where it
and §0 to §3 differ, §0 to §3 win. Section references inside it (§1, §2) are to the old numbering,
which §1 and §2 keep.

### A.1 Old header

**Status:** Source of truth (the contract consumers depend on)
**Last updated:** 2026-10-14 (S155)

### A.2 `current.json` history (old §1)

**`current.json` is a cold-load SNAPSHOT on its own slower cadence, not a second live feed
(DEC-0093, S85).** It exists for a boot fetch — so a first-time visitor doesn't see em-dashes before
the polling loop's first response lands (Cold-load Fix B, DEC-0051) — and is rewritten **at most
once per `[LoopJsonWriter] current_interval`, default 60 s**, plus always on the first packet of a
run so a restart republishes immediately. `current_interval = 0` restores the pre-S85
write-on-every-packet behavior.

Content is identical to `loop-data.txt` **when written**; between writes its `dateTime` is simply
older. A consumer must therefore **not** use `current.json` for liveness — see the gate below.
Cadence confirmed by the consumer side in `eaglehunt-weather-dashboard#430`; nothing read the file
at all between S43 and S85, which is why the cadence could be changed with nothing to break.
Serving it with the right cache headers (`no-store`) is the dashboard/eh-proxy's responsibility,
not this repo's.

> *This doc asserted from S43 to S84 that the dashboard fetched `current.json` at boot. That was
> never true — the consumer half was still unbuilt. Corrected S84 (DEC-0093).*

### A.3 The liveness gate as first recorded (old §1)

> **Liveness gate — a consumer expectation this doc did not record until S84.** The eh-proxy
> returns **503 when `Date.now()/1000 - dateTime > 30`**, and the dashboard treats that 503 as its
> single authoritative proof the station is down (dash DEC-0154). So `dateTime` must keep advancing
> at least every 30 s on `loop-data.txt`: it is a **liveness** signal, not a change signal, and it
> is independent of the per-field TTL machinery below. Anything that would suppress or delay a
> `loop-data.txt` write past that bound produces a false "station offline" on a healthy station.
> **The gate applies to `/loopdata` only** — `current.json` is deliberately *not* behind it, which
> is exactly why that path can be throttled and this one cannot. A consumer must not compute
> staleness from `current.json`'s `dateTime`: by design it can be up to `current_interval` old on a
> perfectly healthy station.
>
> **The 30 s is this station's number, not a constant (1.1.0, DEC-0221; dash DEC-0404).** The
> dashboard's gate is now **`dateTime` within `max(30, 3 × loop_interval_s)` s**, where
> `loop_interval_s` is the feed's own key (below). When the key is absent (a 1.0.x writer, or
> before the second write of a run) the consumer falls back to the last value it saw, then its
> site fact `data.loop_cadence_s`, then 2.5 s. Our own station writes every ~2.5 s, so its gate is
> still 30 s. On a slow platform (a 300 s driver), set the consumer's `data.loop_cadence_s` for a
> cold host: until the second write there is no gap to report.

### A.4 Sparse-field cache and `writer` (old §1 contract bullets)

- **Sparse fields are cached-forward, but the cache is BOUNDED (S48, DEC-0053).** The VP2+ rotates
  fields across packets (not every field in every packet), so the writer keeps the last non-None
  value per field and includes it in every write. `dateTime` is always the current packet's
  timestamp — which means a cached value is *implicitly claiming to be current*. It may therefore
  only be served for a bounded time:
  - **300 s** for ISS-rotated fields (rotation is ~25–60 s at this station), matching
    `dewpoint_service.CACHE_TIMEOUT_SECONDS`. Overridable via `[LoopJsonWriter] ttl_default`.
  - **2 × `[DavisPressure] fetch_interval`** (7200 s at the shipped hourly setting) for
    `barometer_inHg`, which comes from the WeatherLink API fetch, *not* the ISS rotation. Derived
    from that service's own config so the two cannot drift apart. **Only when a `[DavisPressure]`
    section exists (DEC-0211):** a station without one gets `ttl_default` for the barometer too, so a
    dead barometer is not served stale for two hours.
- **`writer` — the contract version (DEC-0211; 1.1.0 added `loop_interval_s` and the opt-in extra
  fields, DEC-0220/0221).** Every write to both files carries
  `"writer": "loop_json_writer/<version>"`. Semver against this contract: major when a key is
  renamed, removed or given new units; minor for a new optional key; patch for a behavior fix. A
  consumer passes it through or ignores it.

### A.5 The relayed barometer, `pressure` and `altimeter`, TTL expiry, diode floors (old §1)

- **`barometer_inHg` is a corrected-upstream passthrough, not an ISS decode (S77).** The VP2+ ISS
  never transmits pressure over 915 MHz. `pressure_service.py`'s `DavisPressureFetcher` polls
  `api.weatherlink.com/v2/current/<station_id>` directly and prefers `bar_sea_level` — **already
  sea-level-corrected by WeatherLink's own cloud side**. This repo applies no correction of its own;
  it relays that value as-is. Unlike `rain`/`rainRate`, **no `_qc` flag marks this** (§2's mechanism
  covers only those two fields today), so a consumer cannot tell from the packet alone that
  `barometer_inHg`'s correction happened entirely upstream, unlike every RF-derived field beside it.
- **`barometer_fetch_epoch` — the relay's own freshness (S82b, #172; shipped in v2.0.14).**
  The Unix epoch of the last WeatherLink fetch that actually *succeeded* (a failed or empty poll
  does not advance it). It bypasses the TTL machinery on purpose — its job is to *reveal*
  staleness, so it is published verbatim however old it is, and omitted only when no fetch has
  ever succeeded this run. Consumers wanting a staleness gate compare it to `dateTime` (both are
  epoch seconds); `barometer_inHg` itself still expires from the feed at 2 × `fetch_interval` as
  above.
- **`pressure` is measured from v2.0.20 (DEC-0209, `eaglehunt-ops#357`) and `altimeter` derives
  from it. Before that, weewx derived both (S82b, #144; corrected S146).**
  The fetched sea-level value used to also backfill the internal `pressure` (station) and
  `altimeter` loop-packet keys — different quantities, so the archive's station-pressure column
  carried sea-level numbers at this site's elevation (hlf#302). DEC-0091 stopped that and left both
  keys null in the loop packet. **The archive and InfluxDB columns were never NULL, though:** the
  live conf carries `[StdWXCalculate][[Calculations]] pressure = prefer_hardware` and
  `altimeter = prefer_hardware`, and weewx computes any such key that is `None`
  (`wxservices.py:132`, 5.5.2). `pressure` was `PressureCooker.pressure` (`wxxtypes.py`): the
  sea-level `barometer` run backward through a reduction formula using the station altitude, the
  current temperature, the temperature 12 hours earlier from the archive, and humidity; `altimeter`
  followed from it. Measured 2026-09-29: 10,002 of the last 7 days' 10,055 archive rows carried
  both (29.46 inHg against a 30.04 sea-level `barometer`). The magnitude was right for a station
  pressure, but the value was WeatherLink's own temperature-dependent reduction reversed, not a
  reading. (S82b's text here said the columns "go NULL"; it had been checked against the loop
  packet, never the archive.)
  **From v2.0.20, `pressure_service.py` reads WeatherLink's `bar_absolute`** — the console's raw
  barometer reading, taken from the same record as `bar_sea_level` — and injects it as `pressure`
  when the packet's is null. `prefer_hardware` keeps it, so the archive's `pressure` and InfluxDB's
  `pressure_inHg` are a measurement, and `altimeter`/`altimeter_inHg` derive from that measurement
  (never injected: the station does not measure altimeter). If a response lacks `bar_absolute`, the
  key stays null and weewx derives as before, with one warning per run. The boundary, its level
  shift and its consumers (including CWOP, which posts `altimeter`) are `docs/DATA_ERRATA.md`
  DISC-0002. Neither key is in this loop-JSON contract, and `barometer_inHg` is unchanged.

  Past its TTL a field is **omitted rather than frozen**, and the writer logs a `WARNING` naming the
  field. Before S48 the cache was unbounded, so a dead or SensorQC-rejected sensor emitted its last
  value indefinitely under a live timestamp — indistinguishable from a live reading (DEC-0006).
- A field absent from the cache — never yet seen this run, **or expired** — is simply omitted;
  consumers must treat any field as possibly-missing. **A missing field means "no current value,"
  never "value unchanged."**
- **`radiation` and `UV` read 0 in the dark because of config, not the driver (DEC-0080, DEC-0200).**
  Each diode sensor's dark floor decodes to a small fixed code: radiation 1.758 W/m², UV 0.04 or
  sometimes 0.02. `weewx.conf.example`'s `StdCalibrate` lines zero exactly those codes, and that
  happens before every surface in this document (loop JSON, archive, InfluxDB, uploads). A
  deployment without those lines emits the raw floor. On this station, rows written before each
  line was applied still carry it: radiation before 2026-08-11, UV before 2026-09-27 17:40 ET.

### A.6 Old live example (old §1)

**Live example** (a sparse packet — gust/dewpoint/barometer/cloudbase served from cache, omitted here
only because not yet seen this run):
```json
{"windSpeed_mph": 0.0, "windDir": 265.83, "rainRate_inch_per_hour": 0.0,
 "outTemp_F": 94.8, "outHumidity": 44.1, "radiation_Wpm2": 442.99, "UV": 2.22,
 "dateTime": 1783200318}
```

### A.7 InfluxDB config keys in the reference deployment (old §2)

- Config keys in `weewx.conf [[Influx]]`: `server_url`, `org`, `bucket`, `token`. `server_url` is
  whatever reaches your InfluxDB 2.x — in the reference deployment it is a same-host published port
  (`http://<host>:8086`; InfluxDB moved hosts twice, DEC-0118/DEC-0141, and only this value changed);
  the example ships generic placeholders (`http://influxdb:8086`, `YOUR_INFLUX_ORG`, `weewx`,
  `YOUR_INFLUXDB_TOKEN`).

### A.8 `windGust10` in InfluxDB and in the archive (old §2)

- **A point carries the in-memory archive record, not the SQLite row.** This driver has no hardware
  archive, so WeeWX builds each record from the interval's accumulator, which holds every loop type,
  and the uploader sends every field (`obs_to_upload = most`). So InfluxDB has fields the SQLite
  schema has no column for. **`windGust10_mph`** (DEC-0224, ops#442) is the one consumers read: the
  ISS's own 10-minute gust, written since 2026-10-28 12:30 ET. It is the last value in the interval
  (WeeWX's stock `last` extractor), it inherits the driver's QC on the loop packet, and a minute
  without a message-9 packet has no field at all, never a 0 (about a third of minutes). Unlike
  `windGust_mph` (the per-minute peak of loop samples), a single bad frame cannot move it
  (ERR-0012). A point backfilled from an archive row before the `windGust10` column existed has no
  `windGust10_mph`; `ops/backfill_*.py` copy the column when it is there.
- **The SQLite archive's `windGust10` column (DEC-0232).** The same value gets an archive column,
  so the archive keeps a copy InfluxDB does not have to supply: `REAL`, in the archive's own unit
  system (`group_speed`; mph in a US archive such as this station's), with a scalar daily summary
  `archive_day_windGust10` whose `max` is the day's highest ISS gust. Same extractor (`last`), same
  QC, same NULL for a minute without message 9, never 0. A new install of the image creates it
  (the starter config's `schema = user.rtldavis.schema`, wview_extended plus this column); an
  existing archive takes it with `weectl database add-column windGust10`, which yields the same
  column and day table (tested against WeeWX 5.5.2). Rows before the column was added are NULL
  unless backfilled from InfluxDB (`ops/backfill_windgust10.py`). Additive: it renames, removes
  or re-units nothing, and a consumer that names its columns is unaffected. The archive is not one
  of this document's two surfaces yet; `docs/INTERFACES-AUDIT-S197.md` proposes making it the
  third, and this column belongs in that table when it is written.

### A.9 QC flags and station identity (old §2)

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
  **The SQLite archive itself carries no equivalent flag** (DEC-0053 Finding 3) — a correction lands
  in InfluxDB's `*_qc` field and in `docs/DATA_ERRATA.md`; the archive row it corrects is left
  unchanged and indistinguishable from one that was never corrected. A reader treating the archive as
  ground truth should know the provenance lives downstream of it, not in it. Deliberate, not an
  oversight — a schema change here isn't currently justified, and SQLite isn't one of this doc's two
  published surfaces to begin with.

- **No station identity in the series key (DEC-0053 Finding 2 — decided S48, never actually written
  here until now).** `influx.py` supports `tags = station=...`, but the live config sets none — the
  only tag is `binding=archive`, so every point in this infinite-retention bucket is anonymous.
  **Adding one later is a trap, not a config tweak:** a point's series key is measurement *plus its
  full tag set*, so adding a tag **forks a parallel series** rather than annotating the existing
  one — splitting historical continuity and orphaning every Flux query written against the untagged
  series, the same hazard §2's series-key rule above already states for corrections/backfills.
  Harmless today with one producer, one station. **A second producer writing to this bucket needs a
  coordinated interface change here first**, not a unilateral tag addition on either side — the
  presence or absence of a station tag is part of what makes this a contract.

### A.10 The dashboard's read path (old §2)

> The dashboard reads InfluxDB only through its own `eh-proxy` (token injected server-side there);
> this repo never sees the dashboard's read path. Our responsibility ends at writing the documented
> schema.
