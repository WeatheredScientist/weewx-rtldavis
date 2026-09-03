# Data Errata — weewx-rtldavis

**Status:** Source of truth for *known-bad observations* · Append-only · Governed by
[DEC-0025](DECISIONS.md#dec-0025--known-bad-data-preserve-and-flag-never-delete)

This log records observations we *know* are wrong (sensor/RF glitches, decode faults) — what the
value was, why it's wrong, what the corrected value is, and how far the bad value propagated. We
**never delete** a bad observation; we preserve it and flag it. This mirrors how observational
networks (WMO, NOAA MADIS) handle suspect data: keep the raw value, attach a quality assessment.

## Why a bad reading has more than one "correct" answer

A single glitch can be the right answer to one question and the wrong answer to another. Reconciliation
is not about picking a winner — it's about **preserving the mapping** so each question still resolves:

| Question | Honest answer | Where it lives |
|---|---|---|
| What did the receiver decode? | the bad value | our raw `weewx.log` — an immutable fact about the *system* |
| What did we broadcast? | the bad value | downstream networks (Weather Underground, CWOP→MADIS) — **immutable, external** |
| How much *actually* happened? | corrected value | physical reality |
| What is our *best estimate*? | corrected value | our WeeWX archive + InfluxDB (the dashboard's source) |

## Three layers

1. **As-transmitted** — never mutated. Our raw log + the copies already sent to external networks.
2. **This errata log** — the reconciliation bridge: the bad value, cause, correction, and how far it spread.
3. **Corrected best-estimate** — what our archive / InfluxDB / totals should read. Corrected = raw with
   errata applied. We **never fabricate** a value. Per [DEC-0032](DECISIONS.md) the corrected value is
   the *known* one where we have positive evidence (e.g. rain bracketed by zeros → `0.0`, a fact), and
   **NULL** wherever the true value is genuinely unknown (an honest gap). [DEC-0006](DECISIONS.md)'s
   null-on-rejection rule governs the **runtime filter** — what the driver emits when it rejects a live
   reading — and is not a constraint on retrospective correction. In InfluxDB a corrected point also
   carries a sparse **`rain_qc`** flag, so the correction is visible in the data itself, not only here.

## Correction status legend

- **local-archive:** the WeeWX SQLite archive (`weewx.sdb`) — our editable source of truth.
- **influxdb:** the line-protocol series the dashboard reads — editable, separate from the archive.
- **external:** copies already sent to Weather Underground / CWOP → NOAA MADIS — **immutable** (we cannot
  retract them; this log is the only reconciliation).

---

## Entries

### ERR-0001 — 2026-07-04 phantom rain (+1.28")

| Field | Value |
|---|---|
| **Observed (bad)** | `rain = 0.64"` at 07:04 UTC **and** 07:05 UTC (03:04 + 03:05 EDT) — a **+1.28" phantom** at ~3 AM. July 4's recorded day total was **1.84"** (= 1.28" phantom + 0.56" genuine evening rain). |
| **Corrected** | `rain = 0.0` for the two 3 AM records. Corrected July-4 day total = **0.56"** (the genuine rain is untouched). *(Amended S36: was `NULL` from 2026-07-05 to 2026-07-12. Now `0.0` per DEC-0032 — the records are bracketed by zeros, so "no rain" is a **known fact**, not a guess, and `NULL` understated our knowledge. Day total is identical either way.)* |
| **Actual weather** | No rain at 3 AM (the two records are bracketed by zeros). The day's **real** rain — **0.56"**, distributed in ≤0.05" increments over ~20:31–22:39 EDT — is genuine and preserved. |
| **Root cause** | [DEC-0021](DECISIONS.md#dec-0021--rain-counter-glitch-filter-the-false-rain-fix) rain-counter RF glitch. The driver logged `rain counter wraparound detected rain_count=-64`; the **old** wraparound handler unconditionally added 128 → +64 tips → +0.64" per record, recorded across two archive intervals. |
| **Why the filter didn't catch it** | This event is what **inspired** the DEC-0021 fix — the fix was written and deployed *after* 2026-07-04. The buggy handler was live at 03:04. The filter now nulls any such delta going forward (verified live; 0 further glitches to date). |

**Propagation & correction status:**

- **local-archive:** ✅ **applied 2026-07-05, amended 2026-07-12 (S36)** — originally
  `UPDATE archive SET rain=NULL WHERE dateTime IN (1783148640, 1783148700)`; S36 re-applied as
  `rain=0.0` (DEC-0032), then `weectl database rebuild-daily --date=2026-07-04`. Verified: July-4
  daily rain 1.84" → **0.56"** (unchanged by the NULL→0.0 amendment; both sum identically). Backups:
  `weewx.sdb.bak-err0001-20260705-165813`, `weewx.sdb.bak-err0002-20260712-160724`.
- **influxdb:** ✅ **applied 2026-07-12 (S36)** — `rain_in = 0.0` written at both timestamps on series
  `record,binding=archive`, plus a sparse **`rain_qc = 1`** flag at each corrected point (DEC-0032).
  Verified: InfluxDB's July-4 total 1.84" → **0.56"**, now matching the archive exactly; no `rain_in`
  point anywhere in history exceeds 0.3". *(The earlier "no `influx` CLI on the NAS" blocker was
  false — there is one inside the `influxdb` container, and the HTTP API works with the `proxy.env`
  token.)*
- **external:** ⛔ immutable — **confirmed present** in the Weather Underground record (the PWS history
  for 2026-07-04 shows 0.64" @ 03:04 → 1.28" @ 03:09, then flat, day total **1.84"**; our archive now
  reads 0.56" — the 1.28" divergence is exactly this phantom). Almost certainly also
  ingested by **NOAA MADIS** via CWOP: MADIS/CWOP QC concentrates its consistency/buddy checks on
  temperature, dew point, pressure and wind — **precipitation is barely quality-controlled** (rain is
  genuinely patchy and hard to spatially validate), and 0.64"/5-min, while extreme, is not *grossly*
  impossible, so a jump-then-flat accumulation reads as legitimate rain. Treat as in the external record.

**rainRate — corrected 2026-07-12 (S36), a SECOND pass.** The first S36 correction fixed `rain` and
missed `rainRate`: they are **separate fields decoded from separate ISS messages** (rain counter =
type 0xE; rain rate = type 0x5, from `time_between_tips`), so nulling the accumulation left the rate
standing. 17 archive rows (07:04–07:20 UTC) carried a phantom rate peaking at **4.736 in/hr** with
`rain = 0.0` throughout — a rate that, sustained, implies ~1.15" that never accumulated. All set to
`0.0` in the archive (+ `weectl rebuild-daily`) and in InfluxDB (+ sparse `rainRate_qc = 1`). Daily max
rainRate for 2026-07-04 is now **1.482 in/hr**, which is the genuine evening rain. *Found by the owner
looking at the public dashboard — the fix had to be checked at the consumer, not just at the source.*

**⚠️ OPEN — the rate's 15-minute hold is NOT yet explained (S37).** A single corrupt packet explains one
bad reading. It does **not** explain ~16 minutes of a *stable* rate (raw tip-interval drifting only
~7.6 s → 9.6 s). Random per-packet corruption would scatter; this holds steady, then stops. That shape
resembles the **Davis rain-rate timeout** (the ISS holds a computed rate ~15 min after tips, then
resets), which would imply the ISS itself held a non-zero rate state — something our
spurious-frame model (DEC-0033) does not account for. It happened at the *exact* timestamps as the
counter corruption, twice, so the two almost certainly share a cause. **Do not guess it; investigate.**
The `debug_rtld = 2` capture now running will record the raw type-0x5 frames if it recurs.

**Lesson (2026 is a learning year):** the rain counter is the highest-risk field for RF glitches, and
downstream rain QC will not save us — our own filter is the only guard. Watch for the same pattern in
cold-weather failure modes (sensor freeze / stuck counters) we have not yet designed for.

---

### ERR-0002 — 2026-05-25 phantom rain (+1.28")

| Field | Value |
|---|---|
| **Observed (bad)** | `rain = 1.28"` in the single archive record at **2026-05-26 03:22 UTC** (= **2026-05-25 23:22 EDT**, epoch `1779765720`). |
| **Corrected** | `rain = 0.0` (DEC-0032). Corrected local-day (2026-05-25) total = **0.06"**; was **1.34"**. |
| **Actual weather** | No rain. The phantom is **completely isolated**: every archive minute for ±20 min around it reads exactly `0.0`. The day's genuine rain was **0.06"** of trace, elsewhere in the day. |
| **Root cause** | Same RF failure class as ERR-0001 — a rain-counter bit-flip that **passes CRC**. 1.28" = 0.01" × **128** → a clean **bit-7** flip (ERR-0001 was 0.64" = 0.01" × 64, a bit-6 flip). |
| **Why the filter didn't catch it** | **It predates every guard we have.** Verified in git: the driver's `rain_delta_tips` filter *and* the StdQC `rain = 0, 1.0` backstop were introduced in the **same** commit (`be72832`, S18/DEC-0021, 2026-07-04) — over five weeks *after* this event. On 2026-05-25 the rain field had **no decode filter and no StdQC bound at all**, so a 128-tip bit-flip had nothing standing between it and the archive. (The later 1.0" bound would have caught this 1.28" flip had it existed; it was ERR-0001's 0.64" bit-6 flip that exposed 1.0" as too loose, which is why S36 tightened it to 0.3".) |

**Provenance:** found 2026-07-12 by an InfluxDB full-history sweep during dashboard session S69, which
flagged it as an unlogged third phantom. Independently re-verified in weewx S36 against both InfluxDB
and the SQLite archive before any correction was applied. A full-history sweep of **both** stores finds
**exactly three** implausible rain points ever: this one, plus ERR-0001's two.

**Propagation & correction status:**

- **local-archive:** ✅ **applied 2026-07-12 (S36)** — `UPDATE archive SET rain=0.0 WHERE dateTime =
  1779765720`, then `weectl database rebuild-daily --date=2026-05-25` (**note the LOCAL date** — the
  record is 03:22 *UTC*, which is the previous evening in EDT; rebuilding 2026-05-26 would have left
  the daily summary stale). Verified: local-day total 1.34" → **0.06"**. Backup:
  `weewx-data/archive/weewx.sdb.bak-err0002-20260712-160724`.
- **influxdb:** ✅ **applied 2026-07-12 (S36)** — `rain_in = 0.0` + sparse `rain_qc = 1` flag on series
  `record,binding=archive`. Verified against the daily aggregate.
- **external:** ⛔ **immutable** — almost certainly present in the Weather Underground and CWOP → NOAA
  MADIS record, on the same reasoning as ERR-0001 (MADIS barely quality-controls precipitation). Not
  retractable; this entry is the only reconciliation. **This is the harm the v2.0.4 deploy exists to
  stop:** every glitch that reached an external network before 2026-07-12 is permanent.

**rainRate — corrected 2026-07-12 (S36), same second pass as ERR-0001.** 16 archive rows
(03:22–03:37 UTC) carried a phantom rate peaking at **4.216 in/hr** with `rain = 0.0` throughout
(~0.98" implied, never accumulated). Set to `0.0` in the archive (+ `weectl rebuild-daily --date=2026-05-25`,
the LOCAL date) and in InfluxDB (+ sparse `rainRate_qc = 1`). Daily max rainRate for 2026-05-25 is now
**0.039 in/hr**. Same open question as ERR-0001 about the 15-minute hold. Backup:
`weewx.sdb.bak-rainrate-*`.

**Lesson:** two of the three phantoms fired in the small hours (03:04 and 23:22 local) — consistent
with the nocturnal clustering noted for the humidity glitches (DEC-0029). Nothing about the rain
counter is special; it is simply the field where a single bit-flip is most *visible*, because rain is
a monotonic accumulator and a bad tip never averages out.

---

## ERR-0003 — 7h18m data gap (weewx froze), backfilled from the WeatherLink→WU path

**Window:** 2026-07-12 23:54 → 2026-07-13 07:11 EDT (7 h 18 m) · **Logged:** 2026-07-13 (S37)
**Cause:** not a sensor or decode fault — a **software freeze**. See [DEC-0036](DECISIONS.md).

| | |
|---|---|
| **What happened** | weewx's main thread blocked on a pipe at 23:53:45 and never resumed. Both processes stayed alive, the container still reported "Up", no error and no traceback was ever written. The last archive record is `2026-07-12 23:53:00`; the next is `2026-07-13 07:12:00`. **Zero** records in between (~438 one-minute records missing). |
| **Detected** | `weewx_monitor.py` emailed at **00:15** — 22 min after the freeze. The monitor worked. The outage ran long only because it was overnight. |
| **Was anything cached?** | **No.** weewx never read a loop packet during the window, so nothing was buffered and nothing was lost in the restart — the data was never captured at all. Uploads (WU rapidfire, CWOP, Influx) did not run either. |

**Correction applied — backfilled, with different provenance.** The same ISS was also being received by
the co-located **Davis WeatherLink Live** console, which uploads to Weather Underground independently of
us. We pulled that window back from the WU PWS history API and inserted it:

- **weewx archive DB:** 29 records, `interval = 15` (**not** our usual 1 — recorded honestly, because
  these are 15-minute observations, not our 1-minute cadence). Daily summaries rebuilt for 2026-07-13.
- **InfluxDB:** 29 points, each carrying an in-band **`backfill = 1`** flag (the [DEC-0032](DECISIONS.md)
  `rain_qc` pattern), so the dashboard can mark them without keeping a parallel list.
- DB backed up first: `weewx.sdb.bak-S37-preBackfill-*`.

**What the backfilled data is, precisely:** the same physical ISS, seen by a **different receiver**, at a
**coarser cadence**. It is not our RTL-SDR path. Anyone analyzing this window must know the resolution
differs — hence the flag and this entry.

**Conditions during the gap (why the loss is small):** dry (`precipTotal` flat at 0.0 across the whole
window, owner-confirmed no rain), dead calm (`windSpeed = 0` on all 29), overcast-free nocturnal cooling
66 °F → 61 °F with humidity 82 % → 91 %. A smooth, featureless night — the 15-minute cadence loses very
little. CWOP/NOAA-MADIS will not accept retroactive data, so that gap is permanent and external.

---

## ERR-0001 (amendment) — the correction did not propagate to the derived cumulative fields

**Logged:** 2026-07-13 (S37) · **Found by:** eaglehunt-dashboard S70 handoff (they verified it and
correctly declined to patch our store themselves)

ERR-0001 corrected the *primary* rain fields (`rain`, `rainRate`) for the 2026-07-04 phantom. It did
**not** recompute the fields **derived** from them. Cumulative fields do not self-heal — a running total
absorbs a bad tip permanently.

| local day 2026-07-04 | before | after |
|---|---|---|
| `sum(rain_in)` (primary) | 0.56″ | 0.56″ — was always right |
| `max(dayRain_in)` | **1.84″** | **0.56″** |
| `max(rain24_in)` | **1.84″** | **0.56″** |
| `max(hourRain_in)` | **1.28″** | **0.47″** |

`1.84 − 0.56 = 1.28` — precisely the phantom, carried to local midnight. The dashboard flagged
`dayRain_in`; auditing the rest found **`rain24_in` and `hourRain_in` were wrong too** — and
`hourRain_in`'s entire 1.28″ *was* the phantom. The corrected `hourRain_in` peak of 0.47″ is the real
evening storm (20:31–22:39), which is physically sensible; 1.28″ in one hour was not.

**Fix applied (S37):** all three fields recomputed from the corrected `rain` series in the **SQLite
archive** (the system of record, verified to agree with InfluxDB at 0.56″) and rewritten in InfluxDB for
every existing point across 2026-07-04 00:00 → 2026-07-05 06:00 local — a window wide enough to cover
all three rolling lookbacks (daily, 24 h, 1 h). 5,394 points rewritten in place (same measurement, same
`binding=archive` tag, same timestamps), so no duplicate series was created. The operation is idempotent.

These fields are **not** in our archive schema and are **not** produced by our driver — weewx derives
them via XTypes by summing `rain` over a trailing window, and the influx uploader froze those
computations into the bucket. `rain` in SQLite is now correct, so they compute correctly going forward;
only the historical InfluxDB snapshots were stale.

**The general rule this earns — see [DEC-0037](DECISIONS.md):** *a retrospective correction to a primary
field must be propagated to every field derived from it.* Correcting `rain` and stopping there left
wrong data in an infinite-retention bucket for eight days, in the field a reader would most naturally
reach for as "the daily total."

---

## ERR-0001 + ERR-0002 — independently corroborated by the WeatherLink console (S48)

**Logged:** 2026-07-25 (S48) · **Source:** dashboard S76 reconciliation, filed here as issue #48

An external cross-check confirms both corrections were **right**. Reconciling the WeatherLink Live
console's install-to-date total (7.26″ since May 1, owner-confirmed) against the corrected archive
(6.11″ since May 19) leaves 1.15″, which decomposes to ≈0.79″ of real May 1–18 rain (ERA5 at station
coords) plus ≈0.35″ lost to early-archive capture gaps — **residual 0.01″**.

The books balance *only* if the console excludes the 2.56″ we corrected (ERR-0002's 1.28″ +
ERR-0001's 2 × 0.64″). Had the console logged the same tips, implied May 1–18 rainfall would be
**−1.41″** — impossible. This is what both root causes predict: ERR-0001 was our own wraparound
handler adding 128 to a logged `rain_count=-64`, ERR-0002 a bit-7 flip passing CRC — faults strictly
downstream of the shared RF broadcast, which a console decoding its own copy could never reproduce.

**Does not bear on [DEC-0042](DECISIONS.md)** (the phantom *rainRate*), which is a separate class:
33 `rainRate_qc` points carrying `rain = 0.0` throughout, contributing 0″ to any total. See DEC-0042's
"Challenged and upheld (S48)" note — the two flags are independent by design (INTERFACES §2).

---

## ERR-0004 — 2026-07-27 phantom 39 mph wind gust (calm afternoon)

| Field | Value |
|---|---|
| **Observed (bad)** | `windGust = 39 mph` (windGustDir 209°) in the single archive record at **2026-07-27 18:56:00 UTC** (14:56 EDT, epoch `1785178560`); `windSpeed = 2.87 mph` (the interval mean, contaminated by the same ~1 sample at 39). New all-time max on record at the time (prior real peak: 24.0 mph, 2026-07-04). |
| **Corrected** | `windSpeed`, `windDir`, `windGust`, `windGustDir` → **NULL**, plus the derived `ET`, `appTemp`, `windrun` (DEC-0037). NULL, not a substituted value: calm brackets don't *prove* a max/mean the way zero brackets prove rain (DEC-0032 — never fabricate). The true gust that minute was ~2–3 mph, but that is inference. |
| **Actual weather** | Dead calm. Every surrounding minute 18:30–19:30Z: gust 0–5 mph, mean ≤ 2.9 mph. KMQS (~12 mi reference): 6 kt, no gusts flagged anywhere 17:15–21:15Z. A 39 mph sheltered gust implies ≈105 mph in the open per the dashboard's DEC-0095 shelter factor — nothing remotely near it occurred. |
| **Root cause** | The DEC-0033 failure class, caught red-handed at frame level: during an `rxCheckPercent` collapse to **13.2%**, one multi-bit-corrupt-but-CRC-valid frame carried `humidity_raw 2b32 → 59a9` (56.2% → 144.9 %RH, **rejected by SensorQC bounds**) *and* the wind byte that decoded to 39 mph. Same 8-byte frame: the humidity rejection was positive proof of corruption, and the wind field of that proven-corrupt frame was still trusted. The frame was also the last decode before a ~3.7-min outage (14:55:51–14:59:34). |
| **Why the filter didn't catch it** | SensorQC checked fields independently. 39 mph = 17.4 m/s is inside the 6410's 0–200 mph spec (bounds pass), and +16.5 m/s from a calm baseline is under the 20 m/s delta cap that was calibrated against high-bit flips (the 201 mph class). Mid-magnitude corruption threads that needle — and a genuine 25–35 mph first squall gust from calm is routine, so tightening the cap can't close the gap. **Fixed properly in v2.0.9: frame-level co-rejection (DEC-0054)** — a bounds failure now nulls every weather field of its frame. A verbatim replay of this frame is in the test suite. |

**Provenance:** found by the owner on the public dashboard hours after publication (like ERR-0001's
rainRate pass — the consumer surface is where these get seen). Externally diagnosed in parallel by
dashboard S149 ([weewx-rtldavis#76](https://github.com/WeatheredScientist/weewx-rtldavis/issues/76),
InfluxDB + KMQS evidence) and an eaglehunt-ops intermediary session (ops#103, log forensics + code-level
cause). Independently re-verified in weewx S52 against `weewx.log` and the driver source before any
correction: every load-bearing claim held.

**Propagation & correction status:**

- **local-archive:** ✅ **applied 2026-07-27 (S52)** — guarded
  `UPDATE archive SET windSpeed=NULL, windDir=NULL, windGust=NULL, windGustDir=NULL, ET=NULL WHERE
  dateTime=1785178560 AND windGust>38` (rows_changed=1), follow-up `appTemp=NULL, windrun=NULL`
  (the archive is the **wview-extended** schema — the derived fields live in the row, DEC-0037),
  then `weectl database rebuild-daily --date=2026-07-27` (local date). Verified: row reads all-NULL;
  day-max gust now **12 mph** (22:55Z, genuine). Backup: `weewx.sdb.bak-err0004-20260727`.
- **influxdb:** ✅ **applied 2026-07-27 (S52)** — point at `record,binding=archive` 18:56:00Z deleted
  (fields can't be deleted individually) and rewritten minus `windGust_mph`, `windGustDir`,
  `windSpeed_mph`, `windDir`, `appTemp_F`, `ET_in`, `windrun_mile`, with sparse **`windGust_qc = 1`**
  and **`windSpeed_qc = 1`** flags (the DEC-0032/DEC-0099 contract). `windchill_F` kept — at 84.8 °F
  it is wind-independent (weewx returns temperature above 50 °F). Verified via the public `/query`
  proxy: 24 fields, both flags present, `max(windGust_mph)` for the local day = 12.
- **external:** ⛔ immutable — published 14:59:34 EDT to **all ten sinks**: Wunderground (PWS *and*
  the 14:55:51 RapidFire packet at the corrupt frame's own timestamp), InfluxDB (now corrected),
  PWSWeather, OWM, CWOP → NOAA MADIS, AWEKAS, Windy, WOW, WOW-BE, Ogoxe. **Unlike precipitation,
  MADIS does buddy-check wind** (temperature/dew point/pressure/wind get the consistency checks), so
  CWOP's copy stands a real chance of being auto-flagged downstream — the first errata event where
  the external network may partially self-correct. The WU/RapidFire and other copies stand.

**Lesson:** the phantom's magnitude sat in the blind spot *between* the bounds check and the delta
cap — and the proof that would have caught it was already computed, in the same function, for a
different field of the same frame. Evidence available at the choke point must be applied to the whole
frame, not per-field (DEC-0054). Also: 14:57–14:59 have no archive rows (the decode outage) — an
honest 3-minute gap, no backfill warranted.

---

## ERR-0005 — 2026-08-02 receiver outage, ~1h45m gap (two segments)

**Window:** 2026-08-02 00:05:05 → 01:50:13 EDT (1 h 45 m 08 s) · **Logged:** 2026-08-02 (S62)
**Cause:** not a sensor or decode fault — an **RF/receiver outage of unestablished origin**, compounded
mid-incident by the monitor's own USB watchdog. Resolved by a full container recreate.

### Structure — not one gap, but two, with brief islands of life

| Segment | Span | Duration |
|---|---|---|
| Gap 1 | 00:05:05 → 00:07:26 | 2 m 21 s |
| *island* | 00:07:26 → 00:08:22 | ~56 s — reception **71%** |
| **Gap 2 (the main one)** | 00:08:22 → 01:23:56 | **1 h 15 m 34 s** |
| *island* | 01:23:56 → 01:24:32 | ~36 s — reception **43%**; PWSWeather, CWOP, AWEKAS and WOW all recovered, so an archive record landed |
| Gap 3 | 01:24:32 → 01:50:13 | **25 m 41 s** |

Approximately **102 one-minute archive records missing**. Reception was `0/21` on every window across
both gaps — a total loss on all channels, not a degradation.

### Timeline of causes

| Time | Event |
|---|---|
| 00:05:03 | Campaign A ticks `swapping B -> D` (gain 207, `-ex 50`); container restarts. Reception → 0 |
| 00:07:26–00:08:22 | Loop data flows again at **71%** — arm D *was* working |
| 00:08:21 | Apparatus declares `ABORT: container did not produce records after swapping to arm D`; restores baseline, drops STOP sentinel |
| 00:08:33 | Restore restarts the container. Reception → 0 and stays there for 75 minutes |
| 00:11–01:10 | Monitor watchdog fires **9 USB unbind/rebind resets**. None restore reception |
| ~01:23 | Owner physically reseats the dongle → ~36 s of reception, then dead again |
| 01:27:17 | Watchdog reset **#10** |
| 01:28:03 | Failure mode **changes**: `rtldavis process is not running` — the binary now exits immediately, retrying every 60 s |
| ~01:33 | Owner removes the LNA (bypass). Reception stays 0 — the LNA was **not** the blocker |
| 01:48:41 | **Full container recreate** (`kill` → `rm` → `run`, v2.0.11, config derived from `docker inspect`) |
| 01:50:13 | Data flows. Stable since — 468 windows, zero faults, through 09:40 |

**Was anything cached?** **No** — same as ERR-0003. weewx read no loop packets during the gaps, so
nothing was buffered and nothing was lost in the restarts; the data was never captured at all. Uploads
(WU RapidFire, CWOP, InfluxDB, and the other seven sinks) did not run either.

### Two findings this incident earns

**1. The abort was CORRECT — checked and cleared (S62).** It first looked like a near-miss of the
DEC-0061 class: the apparatus declared "did not produce records" at 00:08:21 while loop data was
flowing at 71% and a RapidFire record published at 00:08:22. It was not. The health check waits for a
new **archive** record (`Added record` in `weewx.log`), and the log is unambiguous:

| Last archive record before the abort | Next archive record |
|---|---|
| **00:04:20** | **01:24:24** (80 minutes later) |

`HEALTH_TRIES=36` (~180 s) ran its full budget against a genuine absence. RapidFire loop publications
are **not** archive records — the ~56 s reception island was both too short and too late to close a
60 s archive interval and clear the write lag. The DEC-0061 budget arithmetic holds. **The check is
sound and will not spuriously abort campaign B.**

**2. The auto-remediation made things worse.** Nine USB unbind/rebind resets accomplished nothing
across 75 minutes, and reset #10 at 01:27:17 preceded, by 46 seconds, a *new and worse* failure mode in
which the RTL-SDR still enumerated for `rtl_biast` (device found, R820T tuner found, bias-tee command
returning success) while `rtldavis` could no longer claim it for streaming. The stall-recovery loop had
also killed and respawned `rtldavis` ~18 times to no effect. What resolved it was the container
recreate — a strictly larger hammer than anything the watchdog can swing.
**Addressed in [DEC-0065](DECISIONS.md)**: the watchdog now verifies its own remedy, stops after
3 ineffective attempts, and escalates to a human rather than acquiring a bigger hammer. Auto-recreate
was deliberately *not* built — see that decision for why n=1 does not meet the "proven fix" bar.

### Correction status

- **local-archive:** ✅ **applied 2026-08-10 (S71)** — 7 records inserted at `interval = 15`
  (`dateTime` 1785644100–1785649500, i.e. 00:15–01:45 EDT), backed up first:
  `weewx.sdb.bak-S71-preBackfill-20260810-124656`. `weectl database rebuild-daily --date=2026-08-02`
  (local date) run immediately after. **Source: read manually off the WeatherLink/WU history table
  for the station** (owner-supplied) — **both machine paths failed first**: WU's
  `v2/pws/history/all` returned `401 Unauthorized` with the station's own upload key (the same key
  `wxcheck.sh`'s *current-conditions* query uses successfully), and WeatherLink v2's
  `v2/historic/{id}` — tried next, using the `[DavisPressure]` credentials `pressure_service.py`
  itself uses hourly in prod — returned an empty `{}` with a 200 status. Neither credential carries
  historical-read entitlement on this account, even though both work for current-conditions reads;
  the website UI does (a common API-tier split). **A future backfill should expect the same and go
  straight to a manual read** rather than re-trying either API.
- **influxdb:** ✅ **applied 2026-08-10 (S71)** — same 7 points, `record,binding=archive`, each
  carrying the in-band **`backfill = 1.0`** flag (the DEC-0032 `rain_qc` pattern), written via the
  `proxy.env` InfluxDB token (the same token weewx's own uploader writes with — `POST
  /api/v2/write`, HTTP 204).
- **external:** ⛔ unchanged — immaterial, nothing was ever published for this window.

**Conditions during the gap, now characterized:** calm and dry throughout — 76.1°F cooling to
75.5°F, dewpoint 68–70°F, humidity 77–82%, wind ≤1 mph from W/SW, pressure steady 29.97–29.98 inHg,
zero rain, zero solar (fully overnight). A featureless night, same character as ERR-0003's gap.

**Lesson:** the two failure modes were distinguishable in the logs the whole time — `stalled` means the
process runs and yields nothing; `not running` means it dies on start — and telling them apart was what
finally pointed at the container rather than the hardware. But the driver **swallowed the one piece of
evidence that would have shortened this**: `user.rtldavis ERROR err: <generator object
ProcManager.get_stderr at 0x...>` logs the *repr of a generator* instead of iterating it, discarding
rtldavis's actual stderr at the exact moment it was needed. **Fixed S62** (`drain_stderr()`); the
fix is baked into the image, so it lands with the v2.0.12 rebuild, not before.

### Addendum (S63, 2026-08-03) — ERR-0005 is confirmed a GENUINE RF loss, and is a single incident

[DEC-0067](DECISIONS.md) established a log-level discriminator between a real receiver outage and a
freeze of the weewx process: `genLoopPackets()` raises `rtldavis process stalled` at 150 s **only if
the main thread is executing**. Applied to ERR-0005 it fires **21 times on 2026-08-02** — so the main
thread was running throughout and genuinely heard nothing. **This erratum is correctly filed as an RF
outage.**

Applied to every other day measured (07-30, 07-31, 08-01, 08-03): **zero** detections. ERR-0005 is
therefore a *single incident*, not the first of a series — which is a materially different thing to
carry forward than "the receiver is intermittently unreliable". Its root cause is still
unestablished.

**The 3-minute event at 13:47 the same day is NOT of this kind** and should not be read as a smaller
ERR-0005. Its 209 s gap raised no stall exception, so the receiver was fine and the *process* was
frozen. That class is recurring (~1/day), pre-dates the LNA removal, and is not an RF fault at all.

**Data-integrity note for anyone analyzing a freeze window.** Packets are stamped at *parse* time,
not receive time, so packets buffered during a freeze all collapse onto the resume instant. The
minutes inside a freeze have **no records at all**, and the first record after it absorbs the whole
backlog — its packet counts and `rxCheckPercent` are inflated. Both artifacts are software, not
weather, and neither is corrected in the archive. Treat freeze-adjacent records as suspect rather
than nulling them: the underlying observations are real, only their timestamps are wrong. Known
freezes so far: **2026-07-30 08:04 (218 s), 2026-08-02 13:46 (209 s), 2026-08-03 02:59 (208 s)**.

---

## ERR-0006 — 2026-08-20 phantom 37 mph wind gust (calm, light rain)

| Field | Value |
|---|---|
| **Observed (bad)** | `windGust = 37 mph` (windGustDir 175.3°) in the single archive record at **2026-08-20 11:12:00 EDT** (epoch `1787238720`); `windSpeed = 3.64 mph` (the interval mean, contaminated by the same ~1 sample at 37). Surrounding minutes both sides: 1–2 mph. |
| **Corrected** | `windSpeed`, `windDir`, `windGust`, `windGustDir` → **NULL**, plus the derived `ET`, `appTemp`, `windrun` (DEC-0037). Day-max `windGust` for 2026-08-20 now **19 mph**, genuine. |
| **Actual weather** | Light, continuous rain throughout (rainRate 0.2–0.4 in/h, `rain` accumulating 0.01–0.02 in/min) — a real shower, but **rainRate itself shows no corruption signature**: no absurd spike, no gap, no StdQC nulling. Wind baseline 0–2 mph both sides of the event; no supporting pressure jump or temperature drop in the same record — the signature of an isolated corrupt sample, not a squall front (a genuine gust front usually perturbs at least one other field). |
| **Root cause** | Same class as `ERR-0004`: `rxCheckPercent` for this one minute collapsed to **9.2%** (vs. 60–90% every surrounding minute) — a reception collapse. `weewx.log` is silent 11:11:35→11:15:22 (3 min 47 s), confirmed RF-dead (no restart banner anywhere near the window — checked directly, this is not a container/process restart). Among the few packets that passed CRC that minute, at least one carried a corrupted wind byte; every *other* field in the archive row (temp, humidity, pressure, rainRate) reads normally, so nothing else in the frame tripped a bounds check for DEC-0054's frame co-rejection to catch. |
| **Why the filter didn't catch it** | Identical gap to `ERR-0004`, confirmed still open: 37 mph is inside the 6410's 0–200 mph spec (bounds pass), and the ~35 mph delta from a calm baseline is under `dewpoint_service.py`'s 75 mph/packet delta cap (deliberately loose so a genuine squall gust is never false-rejected). **Investigated and ruled out as the mechanism here:** issue `#225` item 2 (rain-rate corruption failing to co-reject sibling wind fields, fixed same-day in PR #260/dev, not yet deployed to prod) — checked `rainRate` directly for this exact window and it's clean, so that specific gap is not what happened this time. This is `ERR-0004`'s already-documented residual risk (mid-magnitude, single-field corruption during a reception collapse) recurring independently — not a new bug, and tightening thresholds still can't close it without risking false rejection of real squall gusts. |

**Provenance:** found by the owner directly on the dashboard, ~5 h after publication. Cross-checked independently in parallel by an eaglehunt-weather-dashboard session (InfluxDB via its own query path — exact same 37.0/3.64 values, confirming two independent read paths agree) and an eaglehunt-ops session (raised issue `#225` item 2 as a candidate mechanism and a possible container-restart confound; both checked directly and ruled out for this specific incident — see cross-repo thread, ops issue `#192`). No new code shipped; this is a straight data correction against an already-understood, already-accepted gap.

**Propagation & correction status:**

- **local-archive:** ✅ **applied 2026-08-20 (S98)** — guarded `UPDATE archive SET windSpeed=NULL,
  windDir=NULL, windGust=NULL, windGustDir=NULL, ET=NULL, appTemp=NULL, windrun=NULL WHERE
  dateTime=1787238720 AND windGust>30` (rows_changed=1), then `weectl database rebuild-daily
  --date=2026-08-20`. Verified: row reads all-NULL; day-max gust now 19 mph. Backup:
  `weewx.sdb.bak-err0006-20260820`.
- **influxdb:** ✅ **applied 2026-08-20 (S98)** — point at `record,binding=archive` 15:12:00Z deleted
  and rewritten minus `windGust_mph`, `windGustDir`, `windSpeed_mph`, `windDir`, `appTemp_F`, `ET_in`,
  `windrun_mile`, with sparse **`windGust_qc = 1`** and **`windSpeed_qc = 1`** flags (the
  DEC-0032/DEC-0099 contract). `windchill_F` kept — at 70.1 °F it is wind-independent (weewx returns
  temperature above 50 °F). **Note:** the dashboard's own read-only proxy token cannot write/delete
  (403, confirmed) — the correction used `weewx.conf`'s `[[Influx]]` uploader token instead. Verified
  via direct query: 24 fields, both flags present, matches `ERR-0004`'s own field count exactly.
- **external:** ⛔ immutable — published within minutes to all configured sinks: Wunderground (PWS
  *and* RapidFire, at the corrupt frame's own near-instant cadence — RapidFire is a live ticker, not
  an archive of record, so it isn't reachable by this correction regardless), PWSWeather, OWM,
  CWOP → NOAA MADIS, AWEKAS, Windy, WOW, WOW-BE, Ogoxe. As with `ERR-0004`, MADIS's buddy-check on
  wind gives CWOP's copy a real chance of being auto-flagged downstream; every other external copy
  stands permanently.

**Lesson:** the exact same blind spot as `ERR-0004` — bounds-and-delta-only wind QC cannot
distinguish a genuine sudden gust from a corrupted single sample of similar magnitude, and no other
field happened to co-fail this time either. The one signal that WOULD discriminate the two cases and
isn't yet used: `rxCheckPercent` collapsed to 9.2% (`ERR-0004`: 13.2%) in the exact same minute as
the bad reading, against a 60–90% baseline every other minute — reception quality is an independent,
already-computed corroborating signal that neither the driver's frame co-rejection nor
`dewpoint_service.py`'s delta filter currently consults. See `BACKLOG.md` for a proposed
reception-quality-correlated wind guard raised in response to this incident.

---

## DISC-0001 — `rxCheckPercent` steps ~73% → ~99% at the DEC-0135 deploy (not an error)

**Not an `ERR-####`.** No observation is wrong, before or after. This is a **metric-definition
discontinuity**, recorded here because it is the file anyone consults when a stored series does
something abrupt, and because a step of ~26 points in a field that is written into **every archive
record** will otherwise be re-discovered later as a real event.

**What changed.** Until the DEC-0135 deploy, the Go demodulator discarded the transmitter's
byte-identical re-sent packets and the pending timer booked each as `packet missed` (DEC-0134).
`rxCheckPercent` is derived from those counters, so it under-reported a ~99% link as ~73% —
**for the entire life of the receiver**, across both hosts and every gain setting. After the fix
the repeats are counted as the receptions they always were.

- **Direction:** a step **up**, at the deploy timestamp. Not a reception improvement — the RF link
  did not change, and no weather value in any record before or after this point is affected.
- **Scope:** `rxCheckPercent` only. Sensor fields, rain, wind and every derived quantity are
  untouched — the discarded packets were byte-identical, so nothing was ever lost.
- **Correction status:** ⛔ **not corrected, deliberately.** Historical values are honest reports
  of what the driver measured at the time; rewriting them would destroy the record of a real
  instrument fault. Compare across the boundary only with the offset in mind.

**Consumers whose thresholds are keyed to the old baseline** and go stale at the same instant:
`weewx_monitor.py`'s reception alerting, `BACKLOG.md` and `docs/ROADMAP.md`'s stated figures, the
dashboard's (via eaglehunt-ops#256, DEC-0010) — **and the proposed reception-quality-correlated
wind guard raised under `ERR-0004`/`ERR-0006` below**, whose "collapsed to 9.2% / 13.2% against a
60–90% baseline" discriminator is stated in the pre-fix scale. That guard is not yet built; when it
is, its thresholds must be derived from post-fix data, and the *pre*-fix incident figures it cites
must be read against the pre-fix baseline, not the new one. The signal itself survives — a
reception collapse during a corrupt frame is still a collapse — but every number in it moves.
