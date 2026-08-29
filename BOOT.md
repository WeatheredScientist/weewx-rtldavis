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

## ▶ Resume here (S105 → S106)

*Numbering note: BOOT.md's pointer still read "S103 → S104" at this session's start despite S104
having already merged (PR #279) — that session's own closeout apparently skipped the BOOT.md
rewrite step. Corrected here; tonight is S105.*

### What's settled (do not re-derive)

**Production migrated from the NAS to marvin overnight 2026-08-28/29 (DEC-0118).** Cutover
succeeded; consumers (dashboard, HLF) repointed transparently via an NFS overlay mount at the same
NAS path they always used — no compose edits on their side. A live ~90-min incident mid-cutover was
the host's **USB controller** (every port on the B850 chipset's own xHCI breaks RTL-SDR hop-tracking
under sustained streaming; the CPU-attached controller is clean) — not RF, not gain, not fc/ppm, not
a process freeze. Full narrative, what was ruled out and why, in DEC-0118 — don't re-walk it.

**v2.0.14 is unchanged as the running image** — the exact same build (`335a6cf4a6c6`) crossed via
`docker save`/`load`, no rebuild. Driver banner still `0.20+ws.5`, weewx still 5.5.0.

**Gain is 372 right now, not 496 — provisional, not a re-adoption.** DEC-0115's 496 never got a
clean test against marvin's RF position (the controller was the actual incident cause). A proper
re-sweep is job 4 below, not urgent — 372 works.

**`debug_rtld=3`** (per-packet) is left on for marvin's initial soak — revert to the driver's own
default `2` once proven stable for a few days (job 5).

**Foundation (the NAS container) is stopped, not decommissioned.** Rollback net stays through a
week-plus soak, matching this repo's own image-rollback conservatism (job 6).

**`t-weewx`'s marvinctl key is not minted yet** — self-service deploys to marvin from this repo
aren't live. `eaglehunt-ops`'s own follow-up (§9 step 4, same process CoffeeRadar got); tonight's
deploy was driven directly from marvin's own session, so this didn't block anything.

**S103's gain/receive-window hot swap (DEC-0117) is unchanged by tonight** — built, merged to `dev`,
off by default, still not in prod (`rtldavis.py` is BAKED; needs an image rebuild). S104's job list
carries forward unstarted, see below.

**Standing SOP (S101) carried the entire cutover: message the other repo's live session directly
first, always loop `eaglehunt-ops` too.** Real-time coordination across weewx/marvin/ops/dashboard
tonight — passive polling would not have worked at incident speed.

### ▶▶ S106 JOB LIST

**Carried forward from S104, untouched by tonight:**
1. **`main` promotion for v2.0.14** — still deliberately deferred (DEC-0114). Unchanged by the host
   move; promote per the usual release mechanics once proven out on marvin too.
2. **Convert `ops/rx_experiment.sh` to the DEC-0117 control file** — still gated on the hot swap
   reaching prod first (job 3).
3. **DEC-0117 hot swap still needs an image rebuild to reach prod** — no urgency (off by default).
   **Note: the next image cut needs to reach marvin, not the NAS.** `docker save`/`load` is the
   proven path from tonight, but check whether marvin can build natively first — it's a Ryzen 9700X
   (amd64), unlike the arm64 Mac that forced NAS-native builds per DEC-0078. Untested; worth checking
   before repeating the save/load dance out of habit.

**New from tonight:**
4. **Gain re-sweep at marvin's RF position** — 372 vs 496 vs possibly something new, done properly
   (Campaign-style measurement), not decided under an incident clock.
5. **Revert `debug_rtld` 3→2** once marvin's weewx has a few clean days behind it.
6. **Foundation decommission timing** — after a week-plus of clean marvin operation. Owner's call
   when the soak looks done, not a unilateral session decision.
7. **NAS-LEASE cross-host wiring** — marvin's `/nas-lease` mount is a deliberate empty no-op
   (`MARVIN-DEC-0063`). Low priority (courtesy-yield only, fails safe), worth closing once marvin
   hosts another heavy-I/O tenant that would actually benefit.
8. **`CONSTANTS.md`'s infra section needs a careful second pass.** This session updated the headline
   facts (container host, project root, release mechanics) but the file was written assuming a
   single NAS-only deploy target for years — re-verify every row against `nasctl`/marvin's own
   inspect output rather than trust this session's first pass alone.

### Current state (S105 close)

| Thing | State |
|---|---|
| Prod host | **marvin** (was the NAS/"Foundation" through S104) — DEC-0118, 2026-08-28/29 |
| Prod | **v2.0.14** unchanged, driver **ws.5**, weewx **5.5.0**, gain **372** (provisional, see above) |
| Foundation (NAS container) | Stopped, intact, rollback net through a soak period |
| Consumers | Dashboard + HLF repointed transparently (NFS overlay at the old NAS path), both restarted and verified live |
| InfluxDB | Still NAS-hosted; only the config URL pointing at it moved |
| `debug_rtld` | **3** (soak) — revert to default **2** later (job 5) |
| Hot swap (DEC-0117) | Unchanged — built, merged to `dev`, off by default, not in prod |
| `dev` vs prod | Unchanged from S104's audit — see that session's findings, not re-walked here |
| Trackers | [ops#216](https://github.com/WeatheredScientist/eaglehunt-ops/issues/216) is the cutover's full coordination record and incident narrative |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven on
   the NAS specifically. **Tonight adds a data point, not a close**: DEC-0067/0081's predicted
   watchdog cycle got independent confirmation on different hardware, firing only under a bad USB
   controller — supports "environmental," doesn't identify the NAS's own trigger.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). Untouched this session —
   marvin's hardware, not the NAS's RF environment.
3. **ERR-0005** — unchanged.
4. `ppm`/`fc` — still unmeasured, now for a second confirmed reason: deliberately unchanged for
   Campaign B, and tonight confirmed no sweep data exists to fall back on either.

## Model tier

No `/model` switch this session. Nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-29 (S105 close). Green gate: ruff clean, 428 passed / 8 skipped (unchanged —
no code touched), mypy clean (65 files), secret gate clean. Shipped: production
migrated to marvin (DEC-0118), a live USB-controller incident root-caused and fixed mid-cutover, a
live SQLite backup gap closed the same night — full narrative in `CHANGELOG.md`._
