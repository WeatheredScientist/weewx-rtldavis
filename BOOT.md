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

## ▶ Resume here (S100 → S101)

### What's settled (do not re-derive)

**Phantom 37 mph gust (ERR-0006, DEC-0110) and the NAS-LEASE `influx.py` yield (DEC-0111) are
coded, tested, and queued — unchanged since S98/S99, not re-touched.** Both ship baked into the
~08-23 v2.0.14 image; see job 1 for the full deploy-night list. Don't re-derive either
measurement — DEC-0110/DEC-0111 have the full reasoning if the thresholds or mechanism ever need
revisiting.

**The S91 code audit is now FULLY closed — all 8 remediation issues (#219–226) done, nothing
left.** `eaglehunt-ops#180`'s heads-up closed to match, and reconfirmed still closed/accurate at
S100 (owner asked directly). If a similar full-repo audit is ever proposed again, it does not need
to re-scope `rtldavis.py`/`dewpoint_service.py`.

**#144 (barometer offset) is fully resolved (DEC-0113) — nothing left to decide.** Item 2 was
already fixed pre-S99. Item 3: `fetch_interval` 3600→300, queued as a live `weewx.conf` edit (see
job 1). Item 1: owner confirmed the console's elevation correction is working as designed for the
surveyed 550 ft — closed with no change, don't re-open without new measurement.

**#233 and #252 are fixed, merged (PR #271, `071f684`), and closed.** #233 (`ProcManager` direct
kill) is baked, ships with v2.0.14. #252 (`soak_check.sh` midnight-rotation fix) needed no deploy
step — already live for anyone running the script from an updated checkout.

**`ops/rx_experiment.sh status` gives a false-empty read from a local checkout — always verify
against the NAS.** Ran it locally at S100 pickup and got `arm: NONE`/`installed: no`, which reads
exactly like "campaign self-terminated." It isn't real — the script has no `ssh` calls and needs
to run ON the NAS. Full trap + the `nasctl cat` workaround: `docs/GOTCHAS.md` §3.

### ▶▶ S101 JOB LIST

1. **★ The ~08-23 v2.0.14 build is now a SEVEN-purpose event.** Carries **#224**, **DEC-0110**,
   **DEC-0111** (NAS-LEASE `influx.py` yield), and **#233** (ProcManager belt-and-braces kill) into
   prod — all four on `dev`, baked in. **Also apply the queued live-config edit from DEC-0113:
   `weewx.conf`'s `[DavisPressure]` → `fetch_interval` 3600 → 300** — a MOUNTED-layer change, not
   baked, but held to this same restart per campaign-comparability discipline; verify after with
   `nasctl conf ... DavisPressure`. (**#252** needs no deploy step at all — already live.)
   **`LEASE_DIR` mount is no longer optional — owner confirmed at S99: include it this event.**
   Mount path decided: `-v /volume1/docker/nas-lease:/nas-lease:ro` + `weewx.conf`'s `[[Influx]]`
   gains `lease_dir = /nas-lease`. **Precondition: verify Campaign B has actually self-terminated**
   — read `rx_experiment.state` via `nasctl cat <project root>/rx_experiment.state` (or ssh onto
   the NAS itself); **do not** trust a local `ops/rx_experiment.sh status` run, see `docs/GOTCHAS.md`
   §3 — before touching the container. As of S100 close it was still **arm D, live**, last swap
   **2026-08-22 00:07:25**, on track for its **08-23T00:05** self-termination — don't start off a
   clock guess, re-verify fresh. Build command + `BUILD-EXIT` verification: `ops/nas_build.py`'s own
   docstring. Floor/TTL re-pin formula + the live-config deviations any recreate silently reverts
   (SQLite `timeout`, `pragmas` subsection, radiation calibration, now also `fetch_interval`):
   `CONSTANTS.md`. Full NAS-LEASE mechanism: `DEC-0111`. **Verification this event:** driver banner
   must stay **unchanged** at `0.20+ws.5` (a *changed* banner means the wrong image shipped),
   `weewx.log` should show `influx.py 0.20+ws.2`. Adopting DEC: recompute the next free number that
   day, don't reuse DEC-0111 or DEC-0113 — locks `NAS-LEASE.md` §5's constants for every tenant
   (DEC-0104), a governance act, not just paperwork. **`main` promotion is separate and later**,
   once v2.0.14 proves out — not part of this event.
2. **Daily square watch** (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read via
   `nasctl cat` — **run at S100, all green, resume only if Campaign B is somehow still live when
   S101 starts.** If it has already self-terminated by then (likely — owner expects to resume
   ~Sunday morning, after the 08-23T00:05 end), skip straight to job 1's precondition check instead
   of re-running this. Interim readout still the one from S97 (22/32 blocks): gain 496 leads 372
   past DEC-0059's 2.0-pt adoption bar at both ex levels; ex axis is a wash. **Not a verdict** —
   square isn't done as of S100, DEC-0102's overnight-iowait confound is still open. `stdout is
   chatty` is #253, permanent until the next container recreate (i.e. job 1).
3. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
4. **[ops#173]** — left open on purpose for the automated sweep to close. Nothing to do unless it
   re-flags.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173

### Current state (S100 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; unchanged this session |
| Campaign B | **Live, arm D** (verified via `nasctl cat` on the real state file — a local `rx_experiment.sh status` run falsely showed `NONE`/not-installed, see `docs/GOTCHAS.md` §3). Last swap **2026-08-22 00:07:25**. Square through **08-23T00:05**. Interim readout still S97's (22/32 blocks) — job 2 doesn't call for a refresh |
| Soak | **17 pass / 2 warn / 0 fail, confirmed directly at S100** — same two known warns (chatty stdout #253, USB hedge), matches S98 exactly, no regressions |
| Restart rate | DEC-0106 baseline unchanged: 4/day during a campaign, 0/day between |
| `dev` beyond prod | Unchanged from S99 — everything for v2.0.14 **plus DEC-0110, DEC-0111, #233** (baked) **and DEC-0113's queued `fetch_interval` edit** (mounted). S100 shipped only this closeout + a new `docs/GOTCHAS.md` entry, no code |
| Data integrity | ERR-0006 correction unchanged from S98 (archive + InfluxDB); external copies still permanently carry the bad value |
| NAS-LEASE | Unchanged from S97/S98 — holder client built + verified (DEC-0108); adopting DEC still waits for ~08-23. ops#169: HLF delivered its floor re-measure this round (nightly grew to 7h34m, shipped a heartbeat-renewal model instead of a fixed floor) — no weewx action pending |
| Trackers | #172/#144 open until v2.0.14 (item 3 now queued, DEC-0113) · #204 open until v2.0.14 · #253 permanent until next recreate · ops#179 open on purpose · ops#169 active, nothing owed from us |
| Cross-repo (S100) | Owner asked if `ops#180` needed an update — verified live, still closed and accurate since S99, nothing new to post. No other cross-repo action this session |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven
   (thread blocking on the bind-mounted log volume leads, DEC-0067/0068); evening 18:00–21:00 carries
   the signal (DEC-0094). Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds 00:00–04:00
   clustering; DEC-0102 the 11.80x iowait confound, which does **not** close it. Next real step is
   multi-night minute-level correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; its 21-stall episode remains the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Model tier

Ran on Sonnet 5 throughout S100, confirmed directly (not inferred) — nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-22 (S100 close). Green gate: ruff clean, **410/410** (unchanged, no code
touched), mypy clean (64 files, `.mypy_cache` cleared first), secret gate clean. Shipped: no
code — a verification-only pickup. Confirmed no regressions (soak 17/2/0, matches S98) and
Campaign B genuinely still on track (arm D, live) after a local `rx_experiment.sh status` run gave
a false-empty read; documented that trap in `docs/GOTCHAS.md` §3. Reconfirmed `ops#180` still
closed/accurate on direct ask. Full narrative in `CHANGELOG.md`._
