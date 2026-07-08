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
   errata applied. Per [DEC-0006](DECISIONS.md) we correct to **NULL** (honest gap), never to a fabricated number.

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
| **Corrected** | `rain = NULL` for the two 3 AM records (honest-null, DEC-0006). Corrected July-4 day total = **0.56"** (the genuine rain is untouched). |
| **Actual weather** | No rain at 3 AM (the two records are bracketed by zeros). The day's **real** rain — **0.56"**, distributed in ≤0.05" increments over ~20:31–22:39 EDT — is genuine and preserved. |
| **Root cause** | [DEC-0021](DECISIONS.md#dec-0021--rain-counter-glitch-filter-the-false-rain-fix) rain-counter RF glitch. The driver logged `rain counter wraparound detected rain_count=-64`; the **old** wraparound handler unconditionally added 128 → +64 tips → +0.64" per record, recorded across two archive intervals. |
| **Why the filter didn't catch it** | This event is what **inspired** the DEC-0021 fix — the fix was written and deployed *after* 2026-07-04. The buggy handler was live at 03:04. The filter now nulls any such delta going forward (verified live; 0 further glitches to date). |

**Propagation & correction status:**

- **local-archive:** ✅ **applied 2026-07-05** — `UPDATE archive SET rain=NULL WHERE dateTime IN
  (1783148640, 1783148700)` (2 rows), then `weectl database rebuild-daily --date=2026-07-04`. Verified:
  July-4 daily rain 1.84" → **0.56"**; raw archive sum agrees. Backup:
  `weewx-data/archive/weewx.sdb.bak-err0001-20260705-165813`.
- **influxdb:** ⬜ pending — the dashboard reads InfluxDB, so its rain total still shows the phantom until
  the matching points are nulled there. InfluxDB tooling lives on the dashboard side
  ([DEC-0010](DECISIONS.md)); tracked as a cross-repo follow-up.
- **external:** ⛔ immutable — **confirmed present** in the Weather Underground record (the PWS history
  for 2026-07-04 shows 0.64" @ 03:04 → 1.28" @ 03:09, then flat, day total **1.84"**; our archive now
  reads 0.56" — the 1.28" divergence is exactly this phantom). Almost certainly also
  ingested by **NOAA MADIS** via CWOP: MADIS/CWOP QC concentrates its consistency/buddy checks on
  temperature, dew point, pressure and wind — **precipitation is barely quality-controlled** (rain is
  genuinely patchy and hard to spatially validate), and 0.64"/5-min, while extreme, is not *grossly*
  impossible, so a jump-then-flat accumulation reads as legitimate rain. Treat as in the external record.

**Lesson (2026 is a learning year):** the rain counter is the highest-risk field for RF glitches, and
downstream rain QC will not save us — our own filter is the only guard. Watch for the same pattern in
cold-weather failure modes (sensor freeze / stuck counters) we have not yet designed for.
