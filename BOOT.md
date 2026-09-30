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

## ▶ Resume here (S147 → S148)

### What's settled (do not re-derive)

**v2.0.18 has run in prod since 2026-09-29 16:37:37 ET (DEC-0206).** It carries DEC-0205's baked
halves: #402's slot-count seed fix (driver banner `0.20+ws.6`) and #405's OWM and Windy rain in
millimeters. Tagged `v2.0.18` on `4fd9039` with a GitHub release; not on Docker Hub
(`eaglehunt-ops#265`). The monitor's #413 has run since 09:31:16 ET (sha `5cd09917…` = `dev`).
Verified: exactly four baked files differ from v2.0.17, clean boot, soak 19/0/0, first real record
100%. #402–#405 are closed with that evidence, and heartofgold's CHANGELOG row is in.

**The S145 audit's ten high items are all fixed and shipped.** The 29 medium/low ones stay in
`docs/CODE_REVIEW_S145.md`; the secret gate's four detector holes are #421. The ROADMAP full pass is
done (a P0.7 opened; next check S156). #408 is recorded as deliberate, and ERR-0010 logs the
OWM/Windy rain history.

**INTERFACES.md was wrong and is corrected.** The archive's `pressure` and `altimeter` are derived
by weewx (`StdWXCalculate`, `PressureCooker`) and populated in 99.5% of rows, not NULL. Found while
answering `eaglehunt-ops#357`.

### ▶▶ S148 JOB LIST

1. **Confirm the S147 PR (#423's `rx_experiment.sh` non-root fix) merged into `dev`**
   (`gh pr list` finds it; the merge is the owner's). Then **the first campaign is the end-to-end
   test** of an arm swap as `t-weewx` through `marvin-own`; run it attended, and note the result on
   #423. The monitor's credential file is now `/etc/marvin/env.d/weewx/`, and the tenant-root
   `monitor.env` is a root-owned symlink that must stay one.
2. **`eaglehunt-ops#357`, `bar_absolute`: the design needs the owner's call and a Fable 5.1
   session** (a cross-repo contract change). The tracker reply gives (A) feed `bar_absolute` in as
   weewx's own `pressure`, or (B) a new field. The dashboard answered that it reads neither
   `pressure_inHg` nor `altimeter_inHg`, so (A) costs it nothing. **HLF has not answered** (which of
   the two does it read?). First step of any build: one WeatherLink fetch to confirm this station's
   response carries `bar_absolute`, credentials never printed. Fix `pressure_service.py`'s stale
   "archive columns go NULL" comment in the same change; it is baked, so it rides a release.
3. **`eaglehunt-ops#360`** (marvin's docker-tenant hardening): weewx answered, marvin decides. If it
   schedules `--cap-drop ALL --security-opt no-new-privileges` on `weewx.service` or
   `weewx-influxdb.service`, ring weewx first and keep the restart out of any image cutover. Two
   measurements stay open because the classifier denied them: the running weewx container's own
   `/proc` caps and the influxdb image's setuid list (GOTCHAS §3).
4. **weewx 5.5.0 → 5.5.2 (v2.0.19, the S147 branch `s147-weewx-5.5.2`; PR #420 is superseded by
   it, close #420 with a pointer once it lands).** Read and tested: `ops/weewx_bump_check.sh` passes
   on 5.5.2 and fails on 5.5.0 (the control). The one prod-visible change: with `rapidfire` and
   `archive_post` both on (our live `[[Wunderground]]`), 5.5.0 posted the rapidfire thread to the
   archive URL and 5.5.2 posts it to `rtupdate.wunderground.com`. **Release steps left, all the
   owner's gestures at each prod step:** the release commit (Dockerfile stamp v2.0.19, soak canaries,
   README base-image line, ARCHITECTURE line 26, CONSTANTS release rows), `marvinctl build`, cutover,
   then watch the log for `Wunderground-RF` lines and confirm WU still shows the station. The Docker
   Hub push stays `eaglehunt-ops#265`.
5. **`dev` → `main` promotion**, the owner's timing. `main` is v2.0.13; v2.0.14 to v2.0.18 have run
   unpromoted.
6. **Watches, no action:** OWM and Windy rain in millimeters (needs rain; a dry day proves nothing,
   ERR-0010) · the first `frame failed message-type proof` line (needs a glitch) · freeze lead
   (blocker 1), measure when the next working freeze lands.
7. **Owner-only:** `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the shell profile, never CI; the
   remainder of `eaglehunt-ops#358` (were the two replaced planted addresses live hosts, and the
   history question).
8. Carry forward, none due: S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry.

## Current state (S147 close; prod unchanged since S146)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.18`** as `:marvin-live` (image `7feeda50…`) since 2026-09-29 16:37:37 ET, weewx 5.5.0, gain 372, `t-weewx` (996:986). `:v2.0.17`/`:v2.0.16` verified local for rollback (retag + restart) |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged |
| weewx-monitor | restarted 2026-09-29 09:31:16 ET onto #413; sha `5cd09917…` = `dev`@`4fd9039`; `REMEDY_MODE=none`; four `ISS battery: OK` reports so far |
| Reception | 99.9% mean at USB port `5-1` (archive metric) |
| `main`/`dev` | `dev` = `4fd9039` plus the S146 records PR. `main` is still v2.0.13, unpromoted (job 5) |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · v2.0.17 and v2.0.18 not pushed (`eaglehunt-ops#265`) |
| Trackers | repo: #421 (gate holes), **PR #424 (#423's fix) and PR #425 (weewx 5.5.2, stacked on #424) open, green, owner merges #424 first**, #423 answered and waiting on #424, #420 closed (superseded by #425), #380 informational · ops: #357 answered, awaiting the owner and HLF (job 2) · #360 answered, marvin decides (job 3) · #358 owner remainder · #265/#110 deferred-trigger · #306 residual · #344 macOS LAN (this desktop session reached marvin) |

## Blockers

Unchanged from S145: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

**S147 ran on Sonnet 5.5 throughout** (the floor): #423's script fix and the weewx 5.5.2 staging were
bounded execution, not judgment work. No `/model` switch was made, so there is nothing to restore.
The `#357` design still waits for a Fable 5.1 session (job 2). **Desktop app:** the model persists, so
start S148 on Sonnet unless job 2 is the session's work.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** **New this session:**
- §1: a green check on a dependency bump is about the stubs, not the dependency (CI installs only
  pytest); run `ops/weewx_bump_check.sh`. A script whose user changes needs every privileged call
  listed, not just the one the ticket names.
- §1: `secret-read-guard.sh` matches the config filename in the command text; `cp` a scratch file to a
  neutral name, or run a script file.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-30 (S147). #423 non-root campaign fix on a PR. v2.0.18 in prod (DEC-0206); ROADMAP
pass done. Job 2 (`#357`) is the next real design work._
