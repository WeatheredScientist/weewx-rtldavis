# Handoff — weewx-rtldavis S71 → next session (design work, suggested Fable/escalated)

**Written:** 2026-08-10, weewx-rtldavis session **S71**.
**Audience:** whoever picks this up next — written to be read cold, no assumption you have this
session's transcript.
**Status:** **problem fully diagnosed, fix NOT yet applied.** Two candidate designs are drafted
below; the decision between them is the open work. This is judgment work (a real tradeoff, not a
locked design to execute) — the owner asked for it to be picked up in a fresh session, deliberately
on a higher-tier model.

> **RESOLVED S72 — this handoff is now historical.** DEC-0080 chose **option A** (exact-code
> `StdCalibrate` zero, now versioned in `weewx.conf.example`); option B declined, design preserved
> below. NAS apply deferred to post-GATE 2 — live steps in `BOOT.md`.

---

## The problem

The Davis VP2+ ISS solar radiation sensor has a non-zero diode dark-current floor. At true zero
irradiance (night), the sensor still reports a small photocurrent that the decode math turns into a
**stable, repeatable ~1.8 W/m² reading** — not noise, not a decode error, a real property of the
analog sensor circuit.

**The exact mechanism, in this repo's code** ([rtldavis.py:1591-1599](../../rtldavis.py)):
```python
sr_raw = ((pkt[3] << 2) + (pkt[4] >> 6)) & 0x3FF
if sr_raw < 0x3FE:
    data['solar_radiation'] = sr_raw * 1.757936
```
`sr_raw` is an integer. The only values representable near zero are **exactly** `0` (sr_raw=0),
`1.757936` (sr_raw=1 — the artifact), and `3.515872` (sr_raw=2). There is nothing physically
representable in between. This quantization fact is the key to both designs below.

**Consequence if uncorrected:** the raw 1.8 W/m² flows into the SQLite archive, InfluxDB, and every
RESTful upload (WU, CWOP, AWEKAS, WOW, WOW-BE, WeatherCloud, Windy, OWM, Ogoxe) — inflating any daily
solar-energy integral by a constant offset across every dark hour.

## Provenance — why this looked like a regression

The owner recalled fixing this before. It was **not** in this repo's history (verified: this git
repo and the SQLite archive both start 2026-05-19, the same day — see `git log --reverse` and the
archive's `MIN(dateTime)`; nothing here predates the fix). It was found instead by searching the
owner's own claude.ai history: a **dashboard-only, presentation-layer fix**, June 17-18 2026, in
`eaglehunt-weather-dashboard`'s `eh-ui.js` — narrow-window filter `Math.abs(sol - 1.8) < 0.15 ? 0 :
sol`, applied to two display paths (stat card, live strip).

**That fix has since partially regressed.** Verified against the *current* dashboard code (2026-08-10):
- `eh-ui.js:2126-2130` still filters correctly — live numeric displays (live strip, "Sun panel") are fine.
- `eh-charts.js:489` queries `radiation_Wpm2` from InfluxDB directly for the 24h chart panel, with
  **no filter at all**. The chart is currently plotting the raw 1.8 W/m² nighttime floor.

Root cause of the regression: the dashboard's supercard refactor (`DEC-0156`→`DEC-0188`, July 26-31)
rebuilt chart rendering and the filter didn't carry over — the exact fragility the original June 18
handoff warned about in its own text ("a fresh opportunity to reintroduce the defect"). This is the
**second** time a per-path filter has been dropped on refactor.

**Decision already made (this session, with the owner): fix at the source, in this repo, not by
patching the dashboard chart a second time.** A source-side fix corrects the archive, every upload
service, and the dashboard (all of it, chart included) in one place, permanently — no per-consumer
filter to keep reintroducing. Traded cost, accepted by the owner: applying it creates a step-change
discontinuity in the historical InfluxDB series (1.8 → 0 at night, from whenever it's deployed
forward). No retroactive rewrite requested.

## Design option A — `StdCalibrate` expression (drafted, ready to apply)

Config-only change, no image rebuild — `weewx.conf` is a **mounted** file (`CONSTANTS.md` deploy
layers), live-edit + restart only.

```
[StdCalibrate]
    [[Corrections]]
        # DIODE_FLOOR: the solar sensor's dark-current floor decodes to exactly
        # sr_raw=1 * 1.757936 W/m^2 (rtldavis.py) at true zero irradiance. Matched
        # on the exact known constant, not a loose ~1.8 window -- this layer can
        # see the raw quantization, InfluxDB-only analysis (the original dashboard
        # fix) could not. None-guarded: radiation is absent from some packets (ISS
        # message-type rotation) and can be null after SensorQC rejection.
        radiation = radiation if radiation is None else (0 if 1.75 < radiation < 1.77 else radiation)
```

Verified this session:
- `radiation` passes `SensorQC`'s decode-layer bounds check (`0..1800 W/m²`, DEC-0029) unrejected,
  so it reaches `StdCalibrate` intact.
- Live `[Engine][[Services]]` order: `StdConvert, StdCalibrate, StdQC, StdWXCalculate,
  DewpointCacher, DavisPressureFetcher, LoopJsonWriter` — `StdCalibrate` runs before
  `LoopJsonWriter`, so the fix reaches the live-tick file the dashboard's live strip reads, not just
  the archive. `restful_services` all run later still. One change, every consumer — confirmed
  against the actual live config, not assumed.
- Range-comparison form (`1.75 < radiation < 1.77`) used instead of `abs()` to sidestep any
  uncertainty about whether `abs` is in `StdCalibrate`'s eval namespace (only `math.*` is confirmed
  available there); equally precise.

**Known limitation, not a bug to fix:** this is magnitude-only. A genuine dawn/dusk irradiance
reading that happens to quantize to `sr_raw=1` (true irradiance roughly 1.5-2.6 W/m², the whole
range that rounds to that raw code) is **bit-for-bit indistinguishable** from the artifact and would
also read 0. The original dashboard fix's stated rationale ("narrow enough not to swallow genuine
readings") isn't quite right — narrower doesn't fix an exact collision. What actually makes this
acceptable in practice is exposure, not precision: the artifact fires every dark minute for ~12
hours; a genuine sr_raw=1 reading only exists for a couple of transition minutes at dawn/dusk.

## Design option B — sun-elevation-gated service (not built)

Only truly fixes option A's limitation. Uses `weewx.almanac.Almanac` — **already built into weewx
core** (this is not a port of the dashboard's `eh-astro.js` JS; weewx ships its own sun-position
math, used internally for `StdWXCalculate`'s `maxSolarRad` software option) — to gate the correction
on actual sun position instead of magnitude alone:

```python
alt = almanac(packet['dateTime']).sun.alt   # degrees
if alt < -6 and 1.75 < radiation < 1.77:    # civil twilight: genuinely dark
    radiation = 0.0
# else: leave it, even at the diode-floor value -- sun's up enough this could be real
```

Shape: a new service following the exact pattern of `dewpoint_service.py` / `pressure_service.py`
(both already in this repo, both good templates). Needs `[Station]` lat/lon wiring (already
available to any `StdService` via `engine.stn_info`), a decision on the elevation threshold (-6°
civil twilight suggested, not settled), and test coverage matching this repo's convention
(`tests/test_dewpoint_timeout_null.py` etc. as the pattern to follow).

**Cost vs. option A:** new code (not a config edit), needs its own tests, and — since it'd live
alongside the other baked driver-adjacent services — requires a **NAS-native image rebuild +
deploy** (`CONSTANTS.md` deploy layers), not a hot config edit.

## The actual decision to make

Option A fixes ~99%+ of the problem (everything except a few minutes/day at dawn/dusk, and even
then the "error" is showing 0 instead of ~1.76 — a small absolute difference) with zero new code and
an instant config-only deploy. Option B is fully correct at the edge case, using a facility already
sitting unused in the venv, but costs a new service, tests, and a rebuild for a benefit measured in
minutes per day.

Neither is implemented. **Discuss design before coding** (this repo's non-negotiable rule) still
applies — whichever way this goes, it's a real decision, not a foregone one just because option A is
drafted.

## Where to look, if you need more than this doc

- `rtldavis.py:1591-1599` — the raw decode, the source of the `1.757936` constant.
- `docs/DECISIONS-FULL.md` DEC-0029 — the existing `SensorQC` bounds/delta filter (radiation
  deliberately has no delta filter; explains why 1.8 sails through today).
- `CONSTANTS.md` §Deploy layers — mounted-config vs. baked-image, the reason option A is cheap and
  option B is not.
- `dewpoint_service.py`, `pressure_service.py` — the two existing service patterns option B would
  follow.
- This session's full reasoning (including the dashboard code verification) is in this session's
  transcript if a deeper read is ever needed, but this doc should be sufficient on its own.
