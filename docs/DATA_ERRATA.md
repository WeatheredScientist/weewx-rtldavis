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

**Lesson:** two of the three phantoms fired in the small hours (03:04 and 23:22 local) — consistent
with the nocturnal clustering noted for the humidity glitches (DEC-0029). Nothing about the rain
counter is special; it is simply the field where a single bit-flip is most *visible*, because rain is
a monotonic accumulator and a bad tip never averages out.
