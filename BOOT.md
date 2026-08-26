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

## ▶ Resume here (S102 → S103)

### What's settled (do not re-derive)

**v2.0.14 remains prod, unchanged since S101** — DEC-0110/DEC-0111/#233/#224, weewx 5.5.0,
NAS-LEASE adoption locked (DEC-0114). Campaign B is CLOSED, gain 496 adopted (DEC-0115). Full
detail in `docs/DECISIONS.md` DEC-0114/DEC-0115 if this ever needs re-litigating — not repeated
here.

**S102: an ops verification sweep found `dev`/prod were NOT actually fully in sync, despite S101's
claim — DEC-0116.** ops asked to confirm #144/#172/#204/ops#179 were live. Checked each against the
running container rather than trusting the ship announcement. #144 held up, closed clean. **#172
and #204 did not**: both features live in `loop_json_writer.py`, a MOUNTED file — the deployed copy
was still dated 2026-07-27, missing both entirely (same trap DEC-0114 caught for `influx.py`, just
outside that event's verification scope). Fixed live this session: current `dev`'s
`loop_json_writer.py` deployed, hash-verified, container restarted, both features confirmed live
post-restart. #144/#172/#204 all closed. **`ogoxeUploader.py`, `sortedcontainers`, and `weewx.conf`
— the deploy-layers table's other mounted files — remain independently unverified**; don't assume
current without checking.

**#233, #252 remain fully resolved** (via PR #271). **The S91 code audit remains fully closed**
(#219–226).

**Standing SOP (S101): for live inter-repo coordination, message the other repo's live Claude
session directly first (`ListAgents`/`SendMessage`), always loop `eaglehunt-ops` too.** Used again
this session (ops verification exchange) — process, not repo state, not repeated here.

**Marvin (new Debian hypervisor build) is targeting a Saturday 2026-08-29 host migration for
weewx + eaglehunt-weather-dashboard + hyperlocal-forecast, conditional on Marvin's network-link
soak surviving concurrent Win11-VM bring-up and coffeeradar's own move through the weekend.** Not
this repo's decision to track in detail — `~/Projects/marvin/STATE.md` is the source of truth — but
relevant context for anything infra-adjacent proposed before then.

### ▶▶ S103 JOB LIST

1. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Still unblocked, still not picked up.
2. **`main` promotion for v2.0.14** — deliberately deferred (DEC-0114). Once v2.0.14 has proven out
   in prod for a reasonable stretch, promote per the usual release mechanics (`CONSTANTS.md`).
3. **Docker Hub push for v2.0.14** — also deferred until prod proof, per DEC-0078's standing rule.
4. **Optional: spot-check the other mounted files' live-vs-`dev` state** (`ogoxeUploader.py`,
   `sortedcontainers`, `weewx.conf`) — not urgent, but DEC-0116 established that an image bump says
   nothing about a mounted file unless it was specifically checked, and none of these three have
   been since well before S101.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179

### Current state (S102 close)

| Thing | State |
|---|---|
| Prod | **v2.0.14**, driver **ws.5** unchanged, `influx.py` **ws.2**, weewx **5.5.0**, gain **496** |
| Campaign B | **CLOSED.** Gain 496 adopted (DEC-0115). Nothing further scheduled |
| Soak | Not re-run since S101 — next session should confirm green before trusting anything downstream |
| Restart rate | DEC-0106 baseline (4/day during a campaign, 0/day between) — stale since there's no active campaign; watch for the new steady-state rate |
| `dev` vs prod | **Genuinely in sync as of S102** for `loop_json_writer.py` (fixed this session, DEC-0116); `main` promotion still the only baked-layer item pending (job 2). Other mounted files unverified (job 4) |
| Data integrity | ERR-0006 correction unchanged; external copies still permanently carry the bad value |
| NAS-LEASE | Adopted and locked (DEC-0114) — `RENEWAL_FLOOR_S=420`, `TTL_S=3600` |
| Trackers | #172, #204, #144 all closed this session. #253 permanent until next recreate. ops#179 ready to revisit (job 1) |
| Marvin migration | Target **Saturday 2026-08-29** for this repo's host move, conditional on the soak — see above |

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

Ran on Sonnet 5 throughout S102, confirmed directly (not inferred) — nothing to restore.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap. **New this session:** §4
gained the cross-session variant of the mounted-file trap — a stale mount can persist silently for
weeks across many "clean" sessions, not just survive one deploy event (DEC-0116).

_Last updated: 2026-08-25 (S102 close). Green gate: ruff clean, **402 passed / 8 skipped**
(unchanged — no code touched this session), mypy clean (64 files), secret gate clean. Shipped: a
live deploy fix for `loop_json_writer.py`'s stale mount (DEC-0116), #144/#172/#204 closed — full
narrative in `CHANGELOG.md`._
