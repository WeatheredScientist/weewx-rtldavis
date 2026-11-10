# Interfaces audit — what it takes to be generalized (S197, 2026-11-10)

Status: findings and a proposed decision. No code, config or contract text was changed. Nothing was
posted to another repo's tracker. The decision at the end is a proposal, not a logged DEC.

Question (ROADMAP P3, PRINCIPLES §1): is `docs/INTERFACES.md` enough for a different producer, a
non-Davis WeeWX station or CumulusMX, to feed the same consumers?

Short answer: for any WeeWX driver the code is mostly there, and the document is not. It records
this station's history; it does not specify a contract. For a producer that is not WeeWX nothing
exists yet, because the contract is written in WeeWX's vocabulary.

## Method

- Read here: `docs/INTERFACES.md`, `loop_json_writer.py`, `influx.py`, both extension READMEs and
  installers, `weewx.conf.example`, the driver's field map.
- Measured live, read-only, through the dashboard's public proxy: the loop feed's keys (three
  samples) and the InfluxDB bucket's field, tag and measurement names over 7 days.
- Two read-only surveys of the consumers, `eaglehunt-weather-dashboard` and `hyperlocal-forecast`
  (HLF), by subagents. Their file and line citations are not repeated here.

Legend: [V] verified by this session, in code or against live data. [S] reported by a consumer
survey; the load-bearing ones were spot-checked and are marked [V]. [I] inference.

## What is already general

- [V] Both extensions install on any WeeWX driver. `loopjson` normalizes each packet to US units,
  reports its own cadence (`loop_interval_s`), and passes opt-in extra observations under the name
  weewx-influx2 would give them. `influx` installs standalone and keeps upstream's class path.
- [S] The dashboard reads a US, METRIC or METRICWX archive (`data.units_stored`, per-field
  `data.field_map`), has an absent-sensor switch (`data.absent_fields`), and sizes its liveness gate
  from the feed's cadence. Its stated design test is a non-Davis WeeWX station stored in metric
  units outside the US.

## Findings: the document

1. [V] Section 2 has no field table. It says names are "suffixed by unit matching the WeeWX US
   schema" and names three fields. The live bucket holds 36 fields in measurement `record` with one
   tag, `binding`. The dashboard reads 17 of them plus the sparse `rain_qc` [S]. The other 19 are
   written and documented nowhere:
   `altimeter_inHg`, `appTemp_F`, `barometer_fetch_epoch`, `hourRain_in`, `humidex_F`,
   `maxSolarRad_Wpm2`, `pressure_inHg`, `rain24_in`, `rxCheckPercent`, `txBatteryStatus`,
   `windGustDir`, `windrun_mile`, and seven driver internals under borrowed column names:
   `consBatteryVoltage_hertz`, `hail_hertz`, `hailRate_hertz`, `heatingTemp_hertz`,
   `heatingVoltage_hertz` (the five frequency-error channels), `supplyVoltage_volt` (supercap) and
   `referenceVoltage_volt` (solar power). A second producer cannot tell which fields are contract
   and which are this driver's diagnostics.
2. [V] Section 1's field table has no required or optional column and no types. In practice only
   `dateTime` is required, as a JSON number: the dashboard's proxy answers 503 without it, and the
   page reads that 503 as "station offline". Every other key is optional, and absent and null mean
   the same thing [S]. `writer` and `loop_interval_s` are described in bullets and missing from the
   table.
3. [V] The table lists two keys this station never emits. Three live samples carried no
   `cloudbase_foot` and no `windGust_mph`, and the prod log has no cloudbase line. [I] WeeWX derives
   cloud base only when temperature and humidity arrive in the same packet, which a Davis ISS never
   does. The table reads as "what is in the file"; it is really "what a writer may put there".
4. [S] Field meanings a producer must match are unstated. The consumers depend on all of these:
   - `barometer` is sea-level pressure (the dashboard compares it with model MSLP).
   - `rain` is each record's own increment; HLF sums it per hour and never scales by `interval`.
   - `dayRain` and `ET` accumulate from local midnight.
   - `heatindex` and `windchill` equal the air temperature outside their formula's range.
   - `radiation` is W/m². Several other platforms report lux, which is not convertible by renaming.
   - `windGust` is the peak of loop samples within the record; `windGust10` is the sensor's own
     10-minute gust and is never an alias for it.
   - `dateTime` is whole epoch seconds, UTC, non-decreasing, on a clock within about a second of
     the consumer's.
   - Calm air: `windSpeed` is written as 0 and `windDir` is omitted. [V] The last 24 hours hold
     1,440 of 1,440 `windSpeed_mph` records, 275 of them zero, and 1,165 `windDir` records.
5. [S] The archive interval is not in the contract, and the dashboard assumes 60 s in several
   places (event detection's minute accounting, a 1-minute lookup for Records, 5- and 10-minute
   "latest value" windows). `interval` is not written to InfluxDB at all [V] (`OBS_TO_SKIP`).
6. [V] The SQLite archive is a third published surface that the document disowns ("SQLite isn't
   one of this doc's two published surfaces"). HLF reads nothing else: 16 `archive` columns plus
   `archive_day_rain.sum`. It selects `usUnits` and `interval` and never checks either, so a metric
   archive would import mislabeled as °F and mph. It relies on `journal_mode = DELETE` for a
   read-only mount, on the archive keeping every row, and on a hard date for when `pressure` became
   a measurement [S]. DEC-0222 already counts "archive column meanings" as contract.
7. [V] The unit rule is wrong for an adopter. Section 2 says US. The `influx` installer writes no
   `unit_system`, so the uploader follows the database: a metric WeeWX station writes `outTemp_C`.
   The dashboard handles that; the document does not say it is allowed.
8. [V] The series-key rule is stated as a trap, not as a rule: one station per bucket, measurement
   `record`, tag `binding=archive`, no station tag.
9. [V] Spec and history are mixed. The header says "Last updated: 2026-10-14 (S155)" over text
   dated through S187. The consumer list names the dashboard and omits HLF. About 25 lines on the
   `pressure` column's history sit inside the contract bullets. Section 1 quotes a 7,200 s barometer
   TTL "at the shipped hourly setting"; prod's `fetch_interval` is 300 (DEC-0113).
10. [V] Nothing is machine-checkable. There is no schema file, no sample fixtures, and no test that
    ties the writer's output to the document's table. [S] The dashboard's own doctor script checks
    archive field names only.

## Findings: code

11. [V] One non-finite value takes the station "offline". `json.dump` writes a bare `NaN`, which is
    not JSON; the consumer's parse fails and the whole feed returns 503. WeeWX uses `None` for
    missing values, so this needs a driver or service that emits NaN [I]. The writer is the right
    place to guarantee strict JSON.
12. [V] `writer` names an implementation (`loop_json_writer/1.1.0`), not a contract version. A
    writer that is not ours has no way to say which contract it satisfies. The InfluxDB and SQLite
    surfaces carry no version at all; DEC-0222's image tags are the only signal, and they do not
    exist for a producer that does not run the image.
13. [V] Two Davis couplings sit in the generic writer: the barometer TTL read from
    `[DavisPressure]`, and `barometer_fetch_epoch`. Both are harmless without that section. They
    should be documented as an optional extension, not as core keys.
14. [V] Value QC lives inside the Davis driver, so another producer gets none. This is #475, parked
    on purpose; listed here because the contract promises "honest nulls" (PRINCIPLES §2) and only
    one driver can keep the promise today.

## Findings: beyond WeeWX

15. [V] The contract is expressed in WeeWX terms: observation names, the unit registry's labels,
    accumulator extractors ("a delta is refused"), `to_US()`. A CumulusMX producer needs the same
    content stated without them: a JSON Schema for the loop file, a field table with meanings for
    the archive, sample files, and a checker it can run against its own output.
16. [S] The dashboard has only paper adapters for SQLite and CumulusMX, and its roadmap says to
    record a decision before any code depends on one. Nobody is waiting on this.

## Cross-repo drift (to raise through ops; nothing posted)

- [V] The dashboard's documents disagree about what this repo emits. Live: `windchill_F` is in the
  feed, though comments there say it is not; `cloudbase_foot` and `windGust_mph` are not.
- [V] Its "rtldavis omits zero-speed packets" note is stale (finding 4, calm air).
- [S] Its barometer-relay chip uses a fixed 3,600 s; ours fetches every 300 s.
- [S] Its own review says the loop contract is "owned by nobody yet" and plans an `ADOPTING.md`
  to state the key list. The owner should be this file, with theirs linking to it.
- [S] HLF's unchecked `usUnits` (finding 6) is theirs to fix.
- [S] The dashboard's Davis-tuned guards (rain under 1.0 in per record, a 25 mph gust-over-speed
  spike filter) and its 60 s assumptions are theirs; finding 5 is the producer half.

## Proposed decision (not logged; needs the owner's go)

INTERFACES.md becomes a specification with three surfaces, a contract version, and a check that
can be run. Eight parts, each separable:

1. Name the SQLite archive as the third surface, scoped to what a consumer may rely on: the
   columns in finding 6, `archive_day_rain`, `usUnits`, the journal mode and retention.
2. Split specification from station history. The file keeps tables and rules; this station's
   provenance and dated corrections move, verbatim, to `docs/DATA_ERRATA.md` or a "Reference
   deployment" appendix. Text is moved, never deleted.
3. Give every field a row: name, unit, type, required or optional, meaning, and which sensor class
   it belongs to. Core is `dateTime` plus the archive interval; everything else is optional by
   class. Driver diagnostics (finding 1) are listed as outside the contract.
4. State the rules now implied: strict JSON, flat object, omit rather than null or zero, calm-air
   wind, one station per bucket, the unit systems an archive may use and the loop feed's fixed US
   keys, whole-second UTC timestamps, the feed's cadence keys.
5. Add a contract version that is independent of the writer's name, as a new optional loop key
   (a minor release of `loopjson`), and say how the other two surfaces are versioned.
6. Make the writer omit non-finite values (finding 11), in the same release.
7. Ship a JSON Schema for the loop file, sample fixtures, and a small checker that validates a
   loop file and a list of bucket field names. A test ties the writer's output to the schema.
8. Record ownership: this file is the contract's one owner; consumers link to it.

Not proposed: any CumulusMX code, a station tag, renaming the seven diagnostic fields (a breaking
change with no consumer asking), or moving QC out of the driver (#475 stays parked).

## Suggested order

1. Parts 1 to 4 and 8: documentation only, one PR, one DEC. Nothing baked or mounted changes.
2. Parts 5 to 7: a `loopjson` minor release; prod's mounted writer updates by copy and restart.
3. The cross-repo list, as one ops issue, once part 8 is agreed.
4. CumulusMX: nothing until someone wants it. Parts 3, 4 and 7 are what would make it possible.
