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

## ▶ Resume here (S136 → S137)

### What's settled (do not re-derive)

**Two independent backlog items closed this session: `ops/backfill_container.py` fixed and
verified live (DEC-0196, BOOT job 2), and `MANIFEST.md` trimmed for `eaglehunt-ops#306`. Plus
`docs/ROADMAP.md`'s own ~10-session reconciliation tripwire, due exactly "by S136," fired and ran
clean.**

- **`ops/backfill_container.py` (DEC-0196) — was broken as committed, not merely stale.** A
  never-filled `INFLUX_ORG = "YOUR_INFLUX_ORG"` placeholder, a dead compose-network hostname
  (`http://influxdb:8086`), and a read-write sqlite connection against the LIVE production
  archive — this is why DEC-0151/DEC-0153/the ERR-0009 attempt near DEC-0155 each reimplemented
  the backfill ad hoc rather than using either checked-in tool. Fixed to read
  `server_url`/`org`/`bucket`/`token` from the container's own mounted `weewx.conf` via
  `configobj` (already a weewx dependency; the container's *plain* `python3` doesn't have it —
  needs `/opt/weewx-venv/bin/python3`), connect read-only, and require `--start`/`--end` instead
  of defaulting to stale one-off incident dates. **Verified live with `--dry-run` against the real
  running container**, not a mock: conf auto-read, read-only connect, batching all worked, 870
  records correctly found for a same-day window, zero writes. PR #382, merged.
- **`MANIFEST.md` trimmed for `eaglehunt-ops#306`'s estate-wide sweep.** Collapsed the one real
  rule-9 violation (`CHANGES-FROM-UPSTREAM.md`'s 9 enumerated filenames → a class description),
  dropped the header's stale S94-specific size arithmetic in favor of pointing at
  `boot-cap-check.sh`, and fixed a stale "NAS-side daemon" reference for `weewx_monitor.py` found
  in passing. Residual size is a coverage-beats-cap case per OPS-DEC-0101 — commented on ops#306
  saying so. PR #381, merged.
- **Incidental finding while verifying the above, filed not fixed:** `marvinctl conf`'s
  server-side redaction catches `token` but not `server_url` — a real marvin LAN IP reached this
  session's transcript. Filed `eaglehunt-ops#308`; messaged heartofgold's live session directly
  (fix belongs there) and looped eaglehunt-ops, both per the standing cross-repo SOP. **No reply
  from either before this closeout — job 8 below.**
- **`docs/ROADMAP.md`'s reconciliation tripwire fired exactly on time.** Full pass, nothing stale:
  the P0 freeze-rate line deliberately still reads DEC-0088's 1.31/day (S131's 4.03/day reading
  stays unconfirmed/un-DEC'd pending job 1 below — carrying it here would be exactly the
  provisional-as-settled mistake this guardrail exists to catch); P0 DB-lock row unchanged; P3's
  INTERFACES.md line re-verified current through DEC-0093 via `git log`, nothing new since S126's
  own pass. This session's own DEC-0196 and the MANIFEST.md trim correctly touch no P0–P3 line,
  same call as DEC-0119/DEC-0143/DEC-0144. Next check: S146.
- **`docs/GOTCHAS.md` §3 gained two entries**: the `marvinctl conf` redaction gap above, and that
  the container's plain `python3` lacks `configobj` (weewx-venv's interpreter has it).
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.
- **Both cross-repo replies landed after the S136 closeout merge, folded into jobs 2 and 8
  below rather than restated here** — no mid-fix owed on `#308`; marvin's new pager on
  `weewx-monitor.service` (job 2); `#306`'s residual gaps, deferred (job 8).

### ▶▶ S137 JOB LIST

1. **Re-run `ops/freeze_baseline.py` after a quiet stretch** (no ops-driven restarts in the
   window) to check whether S131's AT-RECORD-MAX reading (4.03/day vs DEC-0083's ~1.49/day
   baseline) holds or was an artifact of incident/deploy activity. Still not re-read — now the
   subject of two full sessions' worth of carried watch (S135, S136) plus ROADMAP's own S136
   reconciliation explicitly declining to update the P0 line until this happens.
2. **`#373`** — decide whether `weewx_monitor.py` needs a distinct alert class for a
   full outage vs. partial degradation (filed S134/DEC-0154, not investigated further). **Now
   has adjacent context, not a fix:** `weewx-monitor.service` also got a box-wide crash pager
   this session (`weewx-rtldavis#380`) — a separate signal (unit died) from what #373 is about
   (the monitor's own RF/reception judgment), but worth reading together when designing #373.
3. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337).
4. **Whether reception at the dongle's new physical position (`5-1`) is actually better or worse
   than the old `7-1.2` cluster is unmeasured** — DEC-0154 fixed the crash loop, not this open
   question from #370's own original ask; needs a longer `rxCheckPercent` read once enough windows
   accumulate.
5. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`) exactly
   as S126 left them — none are due, none are blocked on anything weewx can do alone.
6. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
7. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S135/S136 both still inline, past the ~3-session guideline (pre-existing debt,
   carried again, two sessions closer).
8. **`eaglehunt-ops#306`, deferred (owner's call, S136):** another `MANIFEST.md` rule-9 pass
   (still 823 chars over cap per `boot-cap-check.sh`) and designing `BOOT.md`'s three missing
   "universal" sections (`## Current state`, `## Files needed at session start`, `## Style`) —
   both measured and logged on #306 by eaglehunt-ops S47, neither started here.

### Current state (S136 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unaffected this session — no restarts, no incidents. `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session |
| weewx-monitor | flock-based lock (PR #367) still live and stable; now also has marvin's box-wide crash pager (`weewx-rtldavis#380`, heartofgold, needed a `t-weewx`-specific fix to actually page); `#373`'s own alert-class question still open (job 2) |
| Reception | unchanged since DEC-0154's recovery; whether the new dongle position is better/worse than the old one is unmeasured (job 4) |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S136: PR #381 (MANIFEST.md trim) and PR #382 (backfill_container.py fix, DEC-0196) both merged to `dev`. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (marvin's file to fix) · #370 CLOSED-worthy but left to the owner/marvin to close (job 4) · #373 open (job 2) · #380 open (marvin's pager wiring, informational) · ops: #306 residual deferred (job 8) · #308 answered, no action owed · #265/#110 correctly gated/deferred |

## Blockers

1. **weewx process freezes — was 1.31/day median 240s (DEC-0088); S131's live read showed 4.03/day
   AT RECORD MAX, plausibly confounded by that session's own ops-driven restarts** — root cause
   unproven either way, re-read after a quiet window still not done (job 1). ROADMAP's own S136
   reconciliation explicitly declined to update the P0 line on this unconfirmed number.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. **`#373`** — monitor can't distinguish full outage from partial degradation (job 2).
5. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed at Sonnet, no action needed.** Session ran entirely on Sonnet, no `/model`
switch. Nothing to restore going into S137.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New this
session (§3):** `marvinctl conf`'s redaction misses `server_url`-shaped keys, and the container's
plain `python3` lacks `configobj` — use the weewx venv interpreter.

_Last updated: 2026-09-09 (S136). Session summary: fixed `ops/backfill_container.py` to actually
run self-service against marvin (DEC-0196) after finding it was broken as committed, not merely
stale — root-caused why three separate incidents had reimplemented the same backfill ad hoc, then
verified the fix live with `--dry-run` against the real running container. Trimmed `MANIFEST.md`
for `eaglehunt-ops#306`'s estate-wide tier-file sweep via genuine rule-9 collapsing. Filed
`eaglehunt-ops#308` for a `marvinctl conf` redaction gap found while verifying, and messaged
heartofgold's + eaglehunt-ops's live sessions directly for mutual updates. Ran `docs/ROADMAP.md`'s
own ~10-session reconciliation pass, due exactly this session — nothing stale found, tripwire
reset to S146. Both PRs (#381, #382) merged; green gate clean throughout (496 passed/17 skipped,
ruff/mypy clean). Two cross-repo replies landed after and are folded into jobs 2/8 above._
