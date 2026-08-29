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

## ▶ Resume here (S106 → S107)

### What's settled (do not re-derive)

**ops#183's InfluxDB write outage (00:14→12:08:27 ET, ~11h54m) is fully remediated, backfilled, and
closed (DEC-0119).** Root cause was external to this repo — `eaglehunt-ops` deleted a token it didn't
know `influx.py` also wrote with (`OPS-DEC-0162`); weewx's own config was never at fault, confirmed
unchanged since 08-23. Fixed with a new dedicated write token, installed by a marvin-side session
(this repo's own `marvinctl` access has no arbitrary file write). Entire outage window backfilled
clean — 712 records, 0 errors — via `ops/backfill_influx.py`, which had two real bugs found running it
live for the first time (committed `INFLUX_ORG` placeholder, read-write `sqlite3.connect()` against a
read-only export) — both fixed on PR #282, still open, green gate passed, live-tested in production
before merge. Full narrative: DEC-0119, don't re-walk it.

**`weewx_monitor.py` (this repo's own artifact) sent ~14h of false "STILL DOWN" alerts during the
outage — found and disabled, not yet replaced.** It watches a hardcoded Foundation log path the
marvin NFS overlay doesn't cover (`weewx-data/` is live-mirrored, `logs/` is not); the file froze at
cutover and every alert since was reporting a dead file's age, not station health. Disabled on
Foundation (owner action); no marvin-side equivalent exists yet — job 10 below. A second stale
watcher, `usb_watchdog.sh`, found in the same sweep, filed on `eaglehunt-ops`#233 — same "points at
where weewx used to be" shape.

**All twelve publish legs confirmed independently healthy** (WU-RF/PWS, PWSWeather, CWOP, AWEKAS,
WOW/WOW-BE, WeatherCloud, OWM, Windy, Influx, Ogoxe) via the newly-live `marvin-weewx` `marvinctl`
alias — this repo's own session's first real use of it. Tier-1 reads worked cleanly, no guard
friction. Tier 2 (start/stop/restart own units) is available but untested this session; no arbitrary
file write either tier, by design — the config fix still had to run from a marvin-side session.

**S105's migration items are otherwise untouched this session** — see job list below, all carried
forward.

### ▶▶ S107 JOB LIST

**Carried forward from S105, untouched this session:**
1. **`main` promotion for v2.0.14** — still deliberately deferred (DEC-0114).
2. **Convert `ops/rx_experiment.sh` to the DEC-0117 control file** — gated on job 3.
3. **DEC-0117 hot swap still needs an image rebuild to reach prod** (off by default, no urgency).
   Still unverified whether marvin (Ryzen 9700X, amd64) can build natively, vs. repeating the
   `docker save`/`load` dance.
4. **Gain re-sweep at marvin's RF position** — 372 vs 496, done properly, not under an incident clock.
5. **Revert `debug_rtld` 3→2** once marvin's weewx has a few clean days behind it.
6. **Foundation decommission timing** — owner's call, after a week-plus soak.
7. **NAS-LEASE cross-host wiring** — low priority, marvin's `/nas-lease` mount is a deliberate no-op.
8. **`CONSTANTS.md`'s infra section second pass** — still not independently re-verified row by row.

**New from today:**
9. **Merge PR #282** (`s106-backfill-influx-org-secret-fixes`) — green gate passed; unusually, the fix
   was already proven live in production before the branch merged, because the incident couldn't wait
   for the normal order.
10. **Decide a marvin-side alerter (or an explicit retirement) for `weewx_monitor.py` /
    `usb_watchdog.sh`.** Both are now simply OFF — marvin currently has zero automated health
    alerting from this repo's side. Not urgent (consumer-side/ops monitoring exists independently),
    but a real, named gap rather than a silent one.
11. **Sanity-check `eaglehunt-ops`'s `CONSTANTS.md` §5 register row for weewx's new token**
    (fingerprint `ef8e9af8`) — this repo doesn't own that file, but it names `influx.py`/`weewx.conf`
    as a consumer and is worth a quick correctness check next time either file changes.

### Current state (S106 close)

| Thing | State |
|---|---|
| Prod host | marvin (unchanged from S105) |
| Prod | v2.0.14 unchanged, driver ws.5, weewx 5.5.0, gain 372 (still provisional) |
| InfluxDB write token | New dedicated token, fingerprint `sha256-ef8e9af8` (was `56d69d93`, shared/deleted — DEC-0119) |
| Backfill | Complete — 712 records + small follow-up slices, 0 errors, verified from the consumer side |
| Alerting (Foundation) | `weewx_monitor.py` + `usb_watchdog.sh` both OFF; no marvin equivalent yet (job 10) |
| `marvin-weewx` alias | Live; tier-1 read proven working this session |
| PR | [#282](https://github.com/WeatheredScientist/weewx-rtldavis/pull/282) open, green gate passed, awaiting merge (job 9) |
| Trackers | `eaglehunt-ops`#183 closed · #216 open (non-weewx items only: dashboard gate re-derivation, ops closeout report) · #229/#233/#227 filed as follow-ups, not weewx's to close |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven on
   the NAS specifically. S105 added a data point (independent confirmation on different hardware,
   firing only under a bad USB controller); untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). Untouched this session.
3. **ERR-0005** — unchanged.
4. `ppm`/`fc` — still unmeasured; deliberately unchanged for Campaign B, no sweep data to fall back on.

## Model tier

No `/model` switch this session. Nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-29 (S106 close). Green gate: ruff clean, 428 passed / 8 skipped, mypy clean
(65 files), secret gate clean. Shipped: ops#183's Influx outage fully remediated and backfilled
(DEC-0119), `ops/backfill_influx.py` hardened (PR #282), `weewx_monitor.py`'s stale-watch-path blind
spot found and disabled — full narrative in `CHANGELOG.md`._
