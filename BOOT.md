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

**v2.0.17 has run in prod since 2026-09-28 13:32:39 ET (DEC-0204).**
- It carries DEC-0203's driver half, so a co-rejected frame drops its battery flags and message
  types 0x0/0x1/0xB/0xD/0xF condemn a frame. It also carries S126's GPLv3 notice (#327).
- It was the first build from the tenant root itself, behind the new `.dockerignore` allowlist, and
  was verified against v2.0.16 by baked-file sha before the cutover.
- It is tagged `v2.0.17` on `f255efb`, with a GitHub release. It is not on Docker Hub
  (`eaglehunt-ops#265`).

**The monitor has run DEC-0203's battery gate since 13:21:52 ET.** Each 6-hourly RF email carries
an `ISS battery:` line, and a one-shot low-battery email fires at 5 or more flagged minutes with
healthy reception in a block. `REMEDY_MODE=none` is unchanged.

**Also settled in S144:** DEC-0200 is verified end to end. Reception at USB port `5-1` equals
`7-1.2`. `CONSTANTS.md`'s marvin rows are re-verified; a release is pull → build → `exec-ro` verify
→ tag `:marvin-live` → restart.

### ▶▶ S145 JOB LIST

1. **Confirm the monitor's first `ISS battery:` line**, due in the 18:00 ET RF report. It is logged
   as well as emailed: `marvinctl --tenant weewx grep ISS.battery
   /srv/docker/weewx/logs/weewx_monitor.log`. Expect `OK -- flag clear in all N healthy-reception
   minutes`. A `frame failed message-type proof` line in `weewx.log` confirms the driver half live
   whenever a glitch arrives (8 in 31 days).
2. **Regenerate the dupgate patch against upstream `main.go`.** v2.0.17's build log shows #327's
   notice hunk applying "with fuzz 2". A comment is harmless, but a drifting patch is not; the next
   build should apply it cleanly.
3. **Freeze lead (Blocker 1), measure only when next working freezes.** Every corrupt-frame battery
   flip was the last thing logged before a ~4-minute silence (e.g. 21:09:35 → 21:13:50). The reverse
   rate (how many freezes a corrupt frame precedes) is unmeasured.
4. **`dev` → `main` promotion, the owner's call on timing.** `main` is still v2.0.13
   (`prod-baseline-20260811`); v2.0.14 through v2.0.17 have run unpromoted (DEC-0114's "once it
   proves out").
5. Carry forward S126's job-8 items (EnvironmentFile, `marvin-release.sh`), none due. Watch
   [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) without chasing it.
   `eaglehunt-ops#306`'s residual needs no action. The local-infra doc's marvin entry is unverified,
   since the read guard blocks the check. The owner-route tenant-root tidy is optional, only if a
   root window opens anyway.

## Current state (S144 close)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.17`** as `:marvin-live` (image `621710f7…`) since 2026-09-28 13:32:39 ET, weewx 5.5.0, gain 372, `t-weewx` (996:986). `:v2.0.16`/`:v2.0.15`/`:v2.0.14` local for rollback (retag + restart) |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged |
| weewx-monitor | restarted 2026-09-28 13:21:52 ET onto DEC-0203's battery gate (sha `8a07efd7…` = `dev`); `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB port `5-1` |
| `main`/`dev` | `dev` = `f255efb` plus S144's records PR. `main` is still v2.0.13, unpromoted (job 4) |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · v2.0.17 not pushed (`eaglehunt-ops#265`) |
| Trackers | repo: #394 closed S144 with the deploy evidence · #380 marvin's pager, informational · ops: #343/#347/#348 closed · #265/#110 deferred-trigger · #306 residual · #344 macOS LAN (this desktop session reached marvin) |

## Blockers

1. **weewx process freezes — rate confirmed 1.31/day median 240s (DEC-0088, reconfirmed DEC-0198
   S138); root cause/mechanism still unproven** (DEC-0068/DEC-0094). S144 lead: corrupt CRC-valid
   frames sit at outage onsets (job 3).
2. **RF-dead episode root cause unknown** (DEC-0081). First clean post-fix baseline read was taken
   at S126 (100% mean, no episodes yet); the watch continues.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**S144 ran on Opus 5.5 throughout**, persisted from S143 and flagged in the first reply. #394's
design and the attended v2.0.17 cutover were frontier work. No `/model` switch was made.
**Desktop app:** the model persists. S145's jobs 1 and 2 are execution (Sonnet).

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** **New this session:**
- §1: an archive record's timestamp is the *end* of its interval, so its log evidence sits in the
  minute before.
- §1: `boot-cap-check.sh` with no argument checks eaglehunt-ops' BOOT; pass `"$PWD/BOOT.md"`.
- §3: `marvinctl grep` and `exec-ro` refuse `[…]` and `|` with a misleading "whitespace" error.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-28 (S144). v2.0.17 in prod (DEC-0204). The monitor runs DEC-0203's battery
gate. #394 closed. Job 1 confirms the first `ISS battery:` line at 18:00 ET._
