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

## ▶ Resume here (S98 → S99)

### What's settled (do not re-derive)

**Phantom 37 mph gust (11:12 EDT) diagnosed, corrected, and guarded against going forward
(ERR-0006, DEC-0110).** Same recurring class as `ERR-0004`: an RF-dead reception collapse
(`rxCheckPercent` 9.2% vs. 60–90%+ baseline) let one corrupted-but-CRC-valid frame's wind byte
through, with nothing else in the frame corrupt enough to trip DEC-0054's co-rejection. Archive +
InfluxDB corrected (day-max now 19 mph, genuine). **Going forward, `dewpoint_service.py` nulls
this pattern automatically** (`rxCheckPercent<20%` AND `windGust>10mph` at archive-record time,
before any uploader sees it) — measured first (93 days of history) that genuine high wind and
severe reception collapse have never co-occurred here, so this can't false-null a real gust.
Ships with the ~08-23 v2.0.14 build (baked into the image), not before. Do not re-derive the
measurement — it's in DEC-0110 if the thresholds ever need revisiting.

**ROADMAP.md's P0.5 is fully closed (DEC-0109) — its last follow-on is retired, not done.**
Keep-a-Changelog/DECISIONS-skeleton convergence (proposed S25) had no recoverable rationale and no
family-wide adoption to converge toward. Don't re-propose without new reason; DEC-0109 has the
full reasoning if this comes up again.

**The S91 audit and NAS-LEASE holder client (DEC-0108) are exactly as S97 left them** — nothing
touched either this session. See S97's own entry in `CHANGELOG.md` if context is needed; not
re-narrated here.

### ▶▶ S99 JOB LIST

1. Confirm steady state is exactly `dev` + `main`, no stray branch (checked clean at S98 close —
   `s98-p05-retire-and-err0006-guard` deleted post-merge). PR #265 merged; nothing else outstanding
   from S98.
2. **Daily square watch** (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
   **Campaign B ENDS 08-23T00:05 — ~2.5 days out.** Interim readout still the one from S97 (22/32
   blocks): gain 496 leads 372 past DEC-0059's 2.0-pt adoption bar at both ex levels; ex axis is a
   wash. **Not a verdict** — square isn't done, DEC-0102's overnight-iowait confound is still open.
   Rotation-artifact WARNs after midnight are #252; `stdout is chatty` is #253, permanent until the
   next container recreate.
3. **★ The ~08-23 v2.0.14 build is now a SEVEN-purpose event.** Carries **#224**, **DEC-0110**,
   **DEC-0111** (NAS-LEASE `influx.py` yield, built S99), and **#233** (ProcManager belt-and-braces
   kill, PR #271, S99) into prod — all four on `dev`, baked in. **Also apply the queued live-config
   edit from DEC-0113 (S99): `weewx.conf`'s `[DavisPressure]` → `fetch_interval` 3600 → 300** — a
   MOUNTED-layer change, not baked, but held to this same restart per campaign-comparability
   discipline; verify after with `nasctl conf ... DavisPressure`. (**#252**, the `soak_check.sh`
   midnight-rotation fix also in PR #271, needs no deploy step at all — it's a repo script, live the
   moment it's on `dev`.)
   **`LEASE_DIR` mount is no longer optional — owner confirmed at S99: include it this event**
   (supersedes S97–S98's "skip costs adoption nothing"). Mount path decided: `-v
   /volume1/docker/nas-lease:/nas-lease:ro` + `weewx.conf`'s `[[Influx]]` gains `lease_dir =
   /nas-lease` (S99's own naming, not spec-mandated — rename freely). **Precondition: verify
   Campaign B has actually self-terminated** (`ops/rx_experiment.sh status` = `BASELINE`) before
   touching the container — don't start off a clock guess. Build command + `BUILD-EXIT`
   verification: `ops/nas_build.py`'s own docstring. Floor/TTL re-pin formula + the three
   live-config deviations any recreate silently reverts (SQLite `timeout`, `pragmas` subsection,
   radiation calibration): `CONSTANTS.md`. Full mechanism + why the fail-safe direction matters:
   `DEC-0111`. **New verification this event:** driver banner must stay **unchanged** at
   `0.20+ws.5` (a *changed* banner means the wrong image shipped) and `weewx.log` should show
   `influx.py 0.20+ws.2`. Adopting DEC: recompute the next free number that day, don't reuse
   DEC-0111 — locks `NAS-LEASE.md` §5's constants for every tenant (DEC-0104), a governance act,
   not just paperwork. **`main` promotion is separate and later**, once v2.0.14 proves out — not
   part of this event. Full phase-by-phase walkthrough: S99 session transcript (2026-08-21).
4. **Watch for HLF's ~08-23 floor re-measure.** Their blend-refresh ran 88 min → 155m31s → 275m33s
   (ratios 1.767, 1.772 — compounding, not settling). **Their 8h TTL goes out of spec the moment
   they declare an honest floor** (3×275min = 13.8h) — unresolved, their thread to close.
5. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
6. **[ops#173]** — left open on purpose for the automated sweep to close. Nothing to do unless it
   re-flags.
7. **weewx-rtldavis must NEVER host a self-hosted CI runner** (OPS-DEC-0117) — public repo, so a
   self-hosted runner lets any PR execute arbitrary code on the host. If `ops#171`'s shared
   compute-node project ever discusses centralizing runners there, weewx is excluded by design.
   Separately: this repo's CI is cost-exempt (free public-repo runners, $0 despite being the
   forum's heaviest user) — don't trim it for budget reasons if that ever comes up.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173

### Current state (S98 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; unchanged this session |
| Campaign B | **Live.** Square through **08-23T00:05**. Interim readout: see job 2. Soak at S98: **17 pass / 2 warn / 0 fail** — both warns known (#253 chatty stdout; USB hedge, expected during RF-dead per S73) |
| Restart rate | DEC-0106 baseline unchanged: 4/day during a campaign, 0/day between |
| `dev` beyond prod | Everything for v2.0.14 **plus DEC-0110** (reception-quality wind guard) — PR #265 merged |
| Data integrity | **ERR-0006 corrected** (archive + InfluxDB); external copies (WU/CWOP/PWSWeather/OWM) permanently carry the bad value, same as ERR-0004 |
| NAS-LEASE | Unchanged from S97 — holder client built + verified (DEC-0108); adopting DEC still waits for ~08-23 |
| Trackers | #233 open · #172/#144 open until v2.0.14 · #204 open · ops#184 open on purpose (HLF redirect) · ops#192 closed (ERR-0006 thread) |
| Cross-repo (S98) | Diagnosed the ERR-0006 gust jointly with an eaglehunt-weather-dashboard session (independent InfluxDB cross-check, matched exactly) and an eaglehunt-ops session (raised #225 item 2 + a restart confound as candidates, both checked and ruled out for this incident). Separately fixed a `secret-read-guard.sh` false-positive in eaglehunt-ops (OPS-DEC-0115, command-prefix anchoring + nas.env co-occurrence) |

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

Ran on Sonnet 5 throughout S98, confirmed directly (not inferred) — nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-20 (S98 close). Green gate: ruff clean, **397/397** (was 386, +11 new,
0 regressions), mypy clean (63 files, `.mypy_cache` cleared first), secret gate clean. Shipped:
**ERR-0006 diagnosed and corrected** (archive + InfluxDB) · **DEC-0110** reception-quality wind
guard, closing the ERR-0004/ERR-0006 blind spot (measured first: genuine high wind and severe
reception collapse have never co-occurred at this station) · **DEC-0109** retires ROADMAP's P0.5
· a ROADMAP overclaim on DEC-0054 caught and corrected in the same pass · a cross-repo
`secret-read-guard.sh` fix landed in eaglehunt-ops (OPS-DEC-0115). **PR #265 merged**, steady state
verified after. Full narrative in `CHANGELOG.md`._
