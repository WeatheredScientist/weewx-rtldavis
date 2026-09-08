# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3 — the "escape the WeatherLink lock" tool. A public, published
WeeWX extension (Docker Hub + GitHub releases), GPLv3. Its real contract is the **data it emits**
(loop-JSON + InfluxDB line-protocol schema), not any one consumer. The dashboard that consumes it
is a **separate repo** — don't make dashboard changes here.

---

## ▶ Resume here (S132 → S133)

### What's settled (do not re-derive)

**ERR-0008 backfilled and documented — DEC-0153. Also closes a documentation gap: an incident
(`#370`/`#373`) ran between S131's close and this session, got tracker issues filed,
but no matching `DATA_ERRATA.md`/`DECISIONS.md`/`BOOT.md` entry until now.**

- **The incident, reconstructed from the tracker (not this repo's own doing — a marvin-side/Fable
  session and whichever session responded to it):** post-case-work USB re-enumeration put the
  RTL2838 on a chipset-xHCI port (`MARVIN-DEC-0064` — breaks hop-tracking on this board),
  degrading reception from ~19:51 ET 2026-09-07 (`#370`). The owner's physical fix (moving the
  dongle back) triggered a harder failure in flight: the container's `/dev/bus/usb` view went
  stale and `rtldavis` crash-looped with zero archive records (`#373`). Confirmed against the
  archive itself: a clean 76-minute gap, **22:29:00 → 23:45:00 EDT**, no partial rows either side.
- **Backfilled from WU's public history table for our own station** (the co-located WeatherLink
  Live console's independent upload, same WU station identity as our own — see DEC-0153 for why
  that's not a coincidence), same method as ERR-0003/ERR-0005. **Both machine-readable history
  APIs tried first, both failed exactly as ERR-0005 already documented** — `v2/pws/history/all`
  401'd with the station's own upload key; this account has no historical-read entitlement,
  confirmed a second time. A future backfill should skip straight to the manual table read.
- **5 records** at `interval=15` inserted into the SQLite archive (`weewx.sdb.bak-S132-
  preBackfill-20260908-084528`, daily summary rebuilt for 2026-09-07) and into InfluxDB
  (`backfill=1` field, DEC-0032 pattern) — cross-validated against the real archive's own
  boundaries at both ends, dropped the one WU row nearest the boundary for missing fields
  (DEC-0069's contamination lesson). Read-verified via the InfluxDB `operator` CLI profile (the
  weewx write-token can't read its own bucket back — expected, CONSTANTS §5).
- **Not addressed:** `#373`'s own ask — whether `weewx_monitor.py` should escalate its alert
  class when a fully-down condition is distinguishable from partial degradation. Design decision,
  left open on the tracker, not this session's to make.
- Full account: `docs/DECISIONS-FULL.md` DEC-0153; erratum: `docs/DATA_ERRATA.md` ERR-0008.
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.

### ▶▶ S133 JOB LIST

1. **Re-run `ops/freeze_baseline.py` after a quiet stretch** (no ops-driven restarts in the window)
   to check whether S131's AT-RECORD-MAX reading (4.03/day vs DEC-0083's ~1.49/day baseline) holds
   or was an artifact of S130/S131's own incident/deploy activity. If it holds, root-cause; if not,
   no further action needed. Still not re-read as of this note.
2. **Fix DEC-0150's own runbook** — [ops#288](https://github.com/WeatheredScientist/eaglehunt-ops/issues/288)
   (filed by ops, carried from S131): derive a tree-swap restore list from every unit's bind-mount
   sources rather than from memory/git-diffing alone.
3. Consider porting `ops/backfill_influx.py` to run natively against marvin (NAS-path and
   `localhost:8086` defaults) — two incidents now (DEC-0151, DEC-0153) have solved this ad hoc
   inside the live container rather than fixing the tool itself; still not filed as its own item.
4. **`#373`** — decide whether `weewx_monitor.py` needs a distinct alert class for a
   full outage vs. partial degradation (carried from this session, not investigated further).
5. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337).
6. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`) exactly
   as S126 left them — none are due, none are blocked on anything weewx can do alone.
7. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
8. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S122 and earlier still inline, past the ~3-session guideline (pre-existing debt,
   carried again, one session closer).

### Current state (S132 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unaffected this session (data backfill only, no config/code touched). `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — healthy; received this session's 5-point ERR-0008 backfill (`backfill=1`), no other change |
| weewx-monitor | unchanged this session — flock-based lock (PR #367) still live and stable; `#373`'s alert-class question still open |
| Reception | recovered per `#370`'s physical fix (dongle moved back) — this session's own archive read confirms clean 60s-ish cadence resuming at 23:45 EDT 09-07, onward |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S132: PR pending for DEC-0153/ERR-0008 docs. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337, #370, #373 open (physical/monitor fixes tracked, not this session's to close) · ops: #288/#265/#110 open, correctly gated/deferred |

## Blockers

1. **weewx process freezes — was 1.31/day median 240s (DEC-0088); S131's live read showed 4.03/day
   AT RECORD MAX, plausibly confounded by that session's own ops-driven restarts.** Root cause
   unproven either way — re-read after a quiet window (job 1 above), still not done.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. **`#373`** — monitor can't distinguish full outage from partial degradation (job 4).
5. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed restored, no action needed.** S132 ran entirely on Sonnet, no `/model` switch.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New this
session:** the InfluxDB write-only token cannot read its own bucket back (404 "bucket not found" —
an authorization-shaped failure that presents as a not-found, not a 403); the `weewx-influxdb`
container's own `influx config` already has an `operator` CLI profile with full access, use that
for read-verification instead. `weectl database rebuild-daily` needs `-y` when run through
`marvinctl exec` (no stdin flows to answer its confirmation prompt, unlike the piped-stdin `python3
-` pattern). `weectl`/`weewx` aren't on `python3`'s default path in the live container — they live
under `/opt/weewx-venv/`.

_Last updated: 2026-09-08 (S132). Session summary: owner asked for a backfill of yesterday's
reception outage from the WeatherLink→WU backup path. Redirected from the dashboard repo (which
owns no InfluxDB write path) to this one; found the outage was actually two tracker issues
(`#370`/`#373`) that had never gotten a matching docs entry here. Confirmed the exact gap
against the live archive (22:29–23:45 EDT), that the WLL relays to our own WU station identity
independently, and that the machine-readable history APIs are dead-ended on this account (ERR-0005
precedent, reconfirmed). Backfilled both stores, cross-
validated against real boundary data, documented as ERR-0008/DEC-0153._
