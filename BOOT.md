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

## ▶ Resume here (S144 → S145)

### What's settled (do not re-derive)

**#394 is designed, built and tested as DEC-0203, in S144's PR to `dev` (branch
`s144-dec0200-394-battery`), not deployed.** Every one of `txBatteryStatus`'s 10 archived flips was
a corrupt frame at an outage onset, not the battery.
- **Monitor half:** each 6-hourly RF email gains an `ISS battery:` line. A one-shot low-battery
  email fires at 5 or more flagged minutes with healthy reception (≥ 50%) in one block.
- **Driver half:** a co-rejected frame drops its battery flags, and message types
  0x0/0x1/0xB/0xD/0xF condemn a frame like a bounds failure (9 of 10 flips drop at the source).

**DEC-0200 is verified end to end:** all 733 non-NULL dark archive rows since the apply read UV 0,
and HLF confirmed the InfluxDB side. **Reception at USB port `5-1` equals `7-1.2`** (99.9% at both);
that watch is closed. **`CONSTANTS.md`'s marvin rows are re-verified.** A release is `build` →
`tag …:marvin-live` → `restart`, not `set-image`. S143's DEC-0202 feed move stands.

### ▶▶ S145 JOB LIST

1. **Once the owner merges S144's PR, deploy DEC-0203's monitor half (self-service).** Run
   `marvinctl --tenant weewx pull`, then `restart weewx-monitor.service`.
   - Verify the on-disk sha matches `dev`'s tip, the start time follows the file's mtime, and the
     `Remedy armed:` line appears.
   - The next 6-hourly RF email (00/06/12/18 ET) should carry `ISS battery: OK …`.
   - Then comment on #394 and close it with that evidence (never a bare close). The driver half
     rides job 2.
2. **v2.0.17, DEC-0203's driver half: an attended prod cutover, so it needs the owner's go.**
   - First bump the Dockerfile's version comment (it still says v2.0.14) in a PR.
   - Then `pull`, `marvinctl build /srv/docker/weewx -t weatheredscientist/weewx-rtldavis:v2.0.17`,
     `tag … :marvin-live`, and `restart weewx.service`. Expect a short outage plus hop re-acquisition,
     about 2 min at S143.
   - Verify: the banner, a clean boot, and later a `frame failed message-type proof` line if one
     turns up.
   - The `vX.Y.Z` tag, GitHub release, `prod-baseline` promotion and README "From v2.0.17" note ride
     it (`CONVENTIONS.md`). The Hub push stays `eaglehunt-ops#265`'s question.
3. **Freeze lead (Blocker 1), measure only when next working freezes.** Every corrupt-frame flip was
   the last thing logged before a ~4-minute silence (e.g. 21:09:35 → 21:13:50). The reverse rate
   (how many freezes a corrupt frame precedes) is unmeasured.
4. Carry forward S126's job-8 items (EnvironmentFile, `marvin-release.sh`), none due. Watch
   [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) without chasing it (no reply as
   of S144). `eaglehunt-ops#306`'s residual needs no action. The local-infra doc's marvin entry is
   unverified (the read guard blocks the check).
5. Optional, owner route only: one tenant-root tidy that isn't reachable by any other tenant (see
   the local-infra doc). Do it only if a root-route window opens anyway.

## Current state (S144 close)

| Thing | State |
|---|---|
| Prod | marvin, `v2.0.16` as `:marvin-live` (the unit's floating tag, `--pull=never`), weewx 5.5.0, gain 372, runs as `t-weewx` (996:986). Up since 2026-09-27 22:56:50 ET. `:v2.0.15`/`:v2.0.14` present locally for rollback |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged. Dark UV arrives as 0 (HLF) |
| weewx-monitor | unchanged, running since 2026-09-18 23:13 ET; DEC-0203's battery line not deployed yet (job 1) |
| Reception | 99.9% mean at USB port `5-1` (unchanged from `7-1.2`) |
| `main`/`dev` | S144's PR to `dev`: DEC-0200 verified, DEC-0203 code and tests, `CONSTANTS.md` corrections. `main` is still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged |
| Trackers | repo: #394 addressed in S144's PR (close after job 1) · #380 marvin's pager, informational · ops: #343, #347, #348 closed · #265/#110 deferred-trigger, unfired · #306 residual · #344 macOS LAN (worked around; this desktop session reached marvin again) |

## Blockers

1. **weewx process freezes — rate confirmed 1.31/day median 240s (DEC-0088, reconfirmed DEC-0198
   S138); root cause/mechanism still unproven** (DEC-0068/DEC-0094). S144 lead: corrupt CRC-valid
   frames sit at outage onsets (job 3).
2. **RF-dead episode root cause unknown** (DEC-0081). First clean post-fix baseline read was taken
   at S126 (100% mean, no episodes yet); the watch continues.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**S144 ran on Opus 5.5**, persisted from S143 and flagged in the first reply. Job 1 was execution;
#394's triage and design, the bulk of the session, was frontier work. No `/model` switch was made.
**Desktop app:** the model persists. Job 1 next session is execution (Sonnet). Job 2 is an attended
prod cutover, which calls for Opus 5.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** **New this session:**
- §1: an archive record's timestamp is the *end* of its interval, so its log evidence sits in the
  minute before. Missing that produced a wrong tally mid-decision.
- §3: `marvinctl grep` refuses bracket expressions, with a misleading "whitespace" error.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-28 (S144). DEC-0200 verified overnight. #394 built as DEC-0203, in S144's PR
to `dev` and not deployed: the monitor half is job 1, the driver half (v2.0.17) job 2._
