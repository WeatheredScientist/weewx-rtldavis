# Backlog — weewx-rtldavis

Unordered near-term ideas and durable findings not yet scheduled, **plus long-term/uncalendared
direction** (its own section below, moved here from ROADMAP.md's old P4 + "Longer horizon" at
DEC-0058, S56 — keeps ROADMAP.md down to the actively-sequenced P0–P3 plan). Scheduled work lives
in ROADMAP.md; in-flight work in docs/STATUS.md. Carried forward from the pre-governance NAS
`BACKLOG.md`; the open items from the retired root `cleanup_backlog.md` were folded in here (S27,
S23 tail).

## Open ideas
- **Tuning infrastructure (owner idea, S34) — control panel and/or designed sweep plan.** Two
  complementary routes to better RF tuning, framing to be discussed in a future session:
  (a) a **front-end control panel** (in this repo or standalone) for live-changing select runtime
  variables — gain first, potentially receiveWindow etc. — without container rebuilds/restarts;
  (b) a **proper sweep plan** with a sufficient number of acquisitions per setting for statistical
  confidence (the 2026-06-01 sweeps and the pending DEC-0017 gain-372-vs-207 question suffered from
  short, unaveraged samples) — possibly better than (a), possibly both. Ties into DEC-0017 and the
  "Reception improvement beyond ~70%" idea below.
- Reception improvement beyond ~70% (noise-floor limited at ~150 ft through walls).
- Windows/macOS FHSS investigation (Docker Desktop USB passthrough findings for the README).
- ESP32 secondary sensor node — lightning (AS3935), pressure (BMP390), air quality (SEN55);
  solar-powered (parts shopping list done).
- Blitzortung lightning integration (System Blue — the detection-network route; longer term).
- **InfluxDB points carry no station identity (DEC-0053 Finding 2) — do NOT "just add the tag."**
  `influx.py` supports `tags = station=...`; the live config sets none, so every point in an
  infinite-retention bucket is anonymous. Adding a tag **forks the series key** (INTERFACES §2), which
  splits historical continuity and needs dashboard coordination. Harmless with one producer; revisit as
  a coordinated interface change if a second producer ever satisfies the contract (PRINCIPLES §1).
- **SQLite archive carries no correction flag (DEC-0053 Finding 3).** InfluxDB corrected points carry
  `rain_qc`/`rainRate_qc`/`backfill`; the archive carries nothing, so a corrected row is
  indistinguishable from a never-corrected one — the derived store is better provenanced than the
  system of record. Only `DATA_ERRATA.md` records it. Not urgent; a schema change isn't justified yet.
- Credential hygiene follow-ups — tracked in the gitignored local-infra doc, not here (this repo is public). Secrets belong in `monitor.env` as env vars, never inline (DEC-0012, DEC-0047).
- ~~Set `STATION_NAME` in the NAS `monitor.env`~~ — **already done, S31** (`STATION_NAME=
  "Eagle Hunt PWS"`, live-verified S56). This note was stale since S31 (dated "observed S27,"
  before the fix); see CHANGELOG-ARCHIVE `[S31]`. Pruned S56.
- Verify OWM (OpenWeatherMap) measurements propagate into their API over time — a post-integration
  sanity check that the uploader's values actually land.
- Long-term stability watch (uptime / reception drift / memory) — no formal monitor yet.
- ~~Reception-metric over-count (DEC-0024)~~ — **SHIPPED in v2.0.8 (S43):** both layers landed
  (monitor counts unique record epochs; driver no longer publishes dataless freqError packets — see
  CHANGELOG `[S43]`, DEC-0024 fully resolved). Pruned S52.
- ~~`weewx.log` bloat from `RAW_*` debug lines~~ — **resolved in practice:** the RAW logging moved
  behind `debug_rtld` levels (2026-07-05 driver change) and prod runs with it off — S52 grepped the
  live log: zero `RAW_` lines. Log rotation is daily and working. Pruned S52.

## Durable RF findings (from 2026-06-01 tuning sweeps — keep; these guide P2)

**CLI timing sweep (baseline, -ex 25/50/75/100, -maxmissed 25, combos):**
- All clustered ~63–66%; no material improvement over baseline.
- `-maxmissed 15` caused repeated 0/24 windows — **do not use**.

**receiveWindow:**
- rw400-test (300ms → 400ms): ~63%, **worse** than baseline ~65%.
- Larger receiveWindow is not supported by evidence so far; rw350 is the next candidate to test
  properly (24 h averaged), and must be reconciled against the running image tag (ARCHITECTURE §6).

**FreqError / ppm-fc telemetry gap — SUPERSEDED by live evidence (S21):**
- ~~The compiled Go binary emits neither `ChannelIdx` nor `FreqError`.~~ **Contradicted:** the
  *running* binary emits **both** — live `weewx.log` shows `ChannelIdx:37 … FreqError:2765
  Transmitter:4` (S21, DEC-0024). Either the deployed binary changed since this finding, or the
  original `strings` check was against a different/stale binary. **Re-verify** `strings
  /usr/local/bin/rtldavis` in the live container and reconcile with the running image tag
  (rw250-test) — this matters because the emitted `ChannelIdx`/`FreqError` is what drives the
  DEC-0024 reception over-count.
- Upside if confirmed genuine: `-ppm`/`-fc` tuning *can* now be data-driven (freqError telemetry is
  live). Downside: those same channel packets are being published to WU as dataless loop packets
  (DEC-0024 Layer B).
- **Next investigation (still open):** diff the bundled `src.tgz` rtldavis Go source vs upstream
  `lheijst/rtldavis` to understand which version is actually deployed.

## Data integrity
- ~~May monthly rain totals were noted as compromised by dev restarts; reconcile against the Davis
  WeatherLink Live gold standard once the rain-spike fix lands.~~ — **done S48:** the console
  cross-check corroborated both ERR-0001 and ERR-0002, residual 0.01″ (DATA_ERRATA.md). Same fact
  also corrected in ROADMAP.md this session (S56); this was the last stale copy. Pruned S56.
- ~~[PRIORITIZED — owner, S30] Bad-packet root cause for temp/humidity/radiation/UV spikes~~ —
  **DONE (S33, DEC-0029):** root cause confirmed from the archive (bit-flip corruption passing CRC,
  same class as rain; 18 humidity spikes + impossible UV 16.29; loop-JSON path unfiltered) and fixed
  with the decode-layer `SensorQC` filter + the DewpointCacher timeout-null (closes DEC-0022).
  The S30 `MAX_WIND_DELTA` unit-mismatch lead was disproven (post-StdConvert = mph). Ships with the
  v2.0.4 rebuild. Follow-ups live in DEC-0029/STATUS: cross-sensor consistency checks (UV↔radiation),
  monitor alert on the new rejection signature.

## Long-term direction (moved from ROADMAP.md's P4 + "Longer horizon", DEC-0058, S56)

Uncalendared or aspirational — direction, not scheduled work. Nothing here needs attention now;
pull an item into ROADMAP.md's P0–P3 when it's actually about to be worked.

- **Credential hygiene follow-ups** — tracked in the gitignored local-infra doc, not here (this repo
  is public). Secrets belong in `monitor.env` as env vars, never inline (DEC-0012, DEC-0047). (Also
  listed under "Open ideas" above — same item, not duplicated content.)
- **Multi-source adaptability** (PRINCIPLES §1): keep the driver re-pointable so non-Davis WeeWX and
  eventually CumulusMX can rely on the same data contract. Record a DEC before any code depends on it.
- **Generic project-template harvest** (separate buildout): once the Governance Standard is proven
  here and propagated once, harvest it into a versioned GitHub *template repository* for all future
  projects (ASSESSMENT.md §5). Copy-not-link; tracked as its own effort, not part of this repo's
  release path.
- **Winter 2027 sky-state instrumentation** ([ops#110](https://github.com/WeatheredScientist/eaglehunt-ops/issues/110),
  opened S56): IR sky sensor alongside the lightning detector, targeted for the Jan–Feb 2027 winter
  build. Cross-repo with the dashboard (`repo:dashboard, repo:weewx, tier:frontier`). Planning
  horizon only — not scheduled.
