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

## ▶ Resume here (S101 → S102)

### What's settled (do not re-derive)

**v2.0.14 shipped (S101) — DEC-0110, DEC-0111, #233, #224, weewx 5.5.0, NAS-LEASE `LEASE_DIR`
mount, all live and verified.** Driver banner unchanged `0.20+ws.5`, `influx.py` confirmed
`0.20+ws.2` post-fix, no new errors since restart. Three real bugs found and fixed live during the
deploy (not glossed over) — full account in `docs/DECISIONS.md` DEC-0114: `docker` off the
non-interactive SSH PATH, a genuine 70+min build hang (killed, not waited out), and `influx.py`'s
mounted-not-baked deploy-layer miss (caught via live version banner, fixed with a separate `scp`).
**NAS-LEASE adoption is locked** — `RENEWAL_FLOOR_S`/`TTL_S` re-pinned in `ops/nas_build.py`
against the real measured build duration (DEC-0114). Don't re-derive any of this.

**Campaign B is CLOSED — gain 496 adopted as the new RF baseline (DEC-0115).** Clean 32/32-block
final square: gain 496 beats 372 by +2.00 points, exactly at DEC-0059's adoption bar (not
comfortably above it — read the margin honestly if this ever needs re-litigating). Deployed to
both live `weewx.conf` and `weewx.conf.rx-baseline`. `ops/rx_experiment.sh`'s `SCHEDULE=` block is
now EMPTY (stand-down state, DEC-0096) — regenerate it fresh if a new campaign is ever proposed,
don't assume the old dates are reusable. A narrower gain sweep near 496 was considered and
declined — see DEC-0115 if that ever comes back up.

**#144, #233, #252 remain fully resolved** (unchanged since S99/S100 — #144 via DEC-0113, now
live; #233/#252 via PR #271). **The S91 code audit remains fully closed** (#219–226).

**New standing SOP (S101): for live inter-repo coordination, message the other repo's live Claude
session directly first (`ListAgents`/`SendMessage`), always loop `eaglehunt-ops` too.** Exercised
for real this session against HLF over the shared `heavy-io.lease` — see the parallel session's own
memory for the full account; not repeated here since it's process, not repo state.

### ▶▶ S102 JOB LIST

1. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. The gated queue that was blocking it (Campaign B + the v2.0.14 event) has now
   cleared — revisit whether this is next.
2. **[ops#173]** — left open on purpose for the automated sweep to close. Nothing to do unless it
   re-flags.
3. **`main` promotion for v2.0.14** — deliberately not part of S101's event (DEC-0114). Once
   v2.0.14 has proven out in prod for a reasonable stretch, promote per the usual release mechanics
   (`CONSTANTS.md`).
4. **Docker Hub push for v2.0.14** — also deferred until prod proof, per DEC-0078's standing rule.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173

### Current state (S101 close)

| Thing | State |
|---|---|
| Prod | **v2.0.14**, driver **ws.5** unchanged, `influx.py` **ws.2**, weewx **5.5.0**, gain **496** |
| Campaign B | **CLOSED.** Gain 496 adopted (DEC-0115). Nothing further scheduled |
| Soak | Not re-run post-deploy this session — next session should confirm green on the new image/gain before trusting anything downstream |
| Restart rate | DEC-0106 baseline (4/day during a campaign, 0/day between) — now stale since there's no active campaign; watch for the new steady-state rate |
| `dev` vs prod | **In sync as of S101** — `main` promotion is the only thing still pending (job 3) |
| Data integrity | ERR-0006 correction unchanged; external copies still permanently carry the bad value |
| NAS-LEASE | **Adopted and locked (DEC-0114)** — `RENEWAL_FLOOR_S=420`, `TTL_S=3600`. ops#169 round fully closed |
| Trackers | #172 open (item still pending, unrelated to this session) · #204 open until v2.0.14 proves in prod · #253 permanent until next recreate (i.e. already true again post-S101) · ops#179 ready to revisit (job 1) |
| Cross-repo (S101) | HLF cross-repo notes on weewx#274 + ops#202, both replied to. `OPS-DEC-0136`/`0138` (HLF deprioritization) noted, not acted on — no weewx action implied |

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

Ran on Sonnet 5 throughout S101, confirmed directly (not inferred) — nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap. **New this session:** §4
gained the mounted-file-survives-a-rebuild trap that bit `influx.py` tonight.

_Last updated: 2026-08-23 (S101 close). Green gate: ruff clean, **402 passed / 8 skipped**
(2 tests gained a stand-down skip guard for the now-empty `SCHEDULE=` block, matching the existing
convention — not a regression), mypy clean (64 files), secret gate clean. Shipped: v2.0.14 to prod
(DEC-0114) + Campaign B's gain-496 adoption (DEC-0115) — full narrative in `CHANGELOG.md`._
