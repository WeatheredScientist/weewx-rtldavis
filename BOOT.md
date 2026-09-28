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

## ▶ Resume here (S143 → S144)

### What's settled (do not re-derive)

**S143 moved the loop feed into `weewx-data/feed/`, and `eh-proxy` now mounts only that
(DEC-0202).** `eaglehunt-ops#348` finished in one night, with all four steps done and no
synchronized window.
- `[LoopJsonWriter]` `path`/`current_path` point at `feed/` in the live conf **and** the tenant-root
  `weewx.conf.rx-baseline`. Both are 0600, and the pre-edit copies are in `conf-archive/`.
- marvin flipped `eh-proxy`'s bind to `weewx-data/feed` at 23:20:56 ET (MARVIN-DEC-0183), and the
  dashboard's check passed. weewx removed the temporary top-level symlinks at 23:26:57, so neither
  feed name remains in `weewx-data`'s top level.
- Rules for `feed/` (from marvin S54) are in `CONSTANTS.md`'s deviations table. Never delete or
  recreate it while eh-proxy runs, and only rename files into it. A rollback now needs marvin's
  mount reverted in the same window.
- Verified after the last step: eh-proxy served `/loopdata` 200 at 0.2 s old. `weewx.log` showed
  0 errors against 27 INFO lines.

**S142's DEC-0201 is merged** (PR #396, squash `0d79daf`): conf backups live in `conf-archive/`, and
the live conf stays 0600. **DEC-0200 is confirmed on the InfluxDB side** (HLF S349). Only its
archive-side overnight check is left (job 1).

### ▶▶ S144 JOB LIST

1. **DEC-0200 full-overnight archive verification.** Query archive rows with `radiation = 0` after
   2026-09-27 17:41 ET for any `0 < UV < 0.05`; expect none.
   - **A twilight fraction such as 18:28's 0.0141 is expected.** It's a transition minute that
     averages zeroed readings with readings ≥ 0.06.
   - **Expect a NULL or partial row around 22:57.** S143's restart caused it, the same as 17:41.
     It is not a DEC-0200 failure.
   - A dark fraction, or any exact 0.02/0.04, needs its minute examined. Find the code before
     touching the window; never widen it.
2. **`#394` (surface the ISS low-battery flag `bat_iss`).** Owner-filed 2026-09-20, `tier:mid`,
   untriaged. Start with the issue's own question: is `bat_iss` archived or surfaced anywhere yet?
3. **Reception at the dongle's new position (`5-1`) vs the old `7-1.2` cluster is unmeasured.**
   DEC-0154 fixed the crash loop, not this. It needs a longer `rxCheckPercent` read.
4. Carry forward job 8's remaining items (EnvironmentFile, `marvin-release.sh`) exactly as S126 left
   them. None are due.
5. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7)** for a maintainer reply
   (repo dormant since 2023-12-22). Don't chase it.
6. `eaglehunt-ops#306`'s residual `MANIFEST.md` cap overage: coverage beats the cap, so no action
   unless a real instance-collapse turns up.
7. **`CONSTANTS.md` infra re-verify, the remainder.** The marvin rows (e.g. host tool availability)
   are still S105-era. The NAS rows were re-verified at S142. `CONVENTIONS.md`'s stale infra copy is
   gone as of S143, replaced by a pointer.
8. Optional, owner route only: one tenant-root tidy that isn't reachable by any other tenant (see
   the local-infra doc). Do it only if a root-route window opens anyway.

## Current state (S143 close)

| Thing | State |
|---|---|
| Prod | marvin, `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986). `weewx.service` restarted 2026-09-27 22:56:50 ET for DEC-0202. `weewx-data` has `feed/` (0755, the loop feed, the only part `eh-proxy` mounts) and `conf-archive/` (0700) |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged. Dark UV arrives as 0 (confirmed by HLF) |
| weewx-monitor | unchanged, running since 2026-09-18 23:13 ET; carries the `REMEDY_SYSTEMCTL` fix + DEC-0199 |
| Reception | unchanged since DEC-0154's recovery; new-position comparison unmeasured (job 3) |
| `main`/`dev` | S143: #396, #397 (DEC-0202 plus closeout) and #348's completion follow-up, all to `dev`. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged |
| Trackers | repo: #394 open (job 2) · #380 open (marvin's pager, informational) · ops: #348 complete, all four steps (ops can close) · #347 answered, #396 merged so heartofgold can tick weewx's row · #265/#110 deferred-trigger, unfired · #306 residual (job 6) · #344 macOS LAN (worked around; this desktop session reached marvin) |

## Blockers

1. **weewx process freezes — rate confirmed 1.31/day median 240s (DEC-0088, reconfirmed DEC-0198
   S138); root cause/mechanism still unproven** (DEC-0068/DEC-0094). No active watch on the rate;
   re-derive only if a fresh elevated reading appears.
2. **RF-dead episode root cause unknown** (DEC-0081). First clean post-fix baseline read was taken
   at S126 (100% mean, no episodes yet); the watch continues.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**The whole session ran on Opus 5.5, flagged at the start as fitting #348's attended prod change**
(a live-conf edit, a restart, and a cross-repo contract). No `/model` switch was made in-session.
**Desktop app:** the model persists into later sessions. Job 1 is execution, so the next session
should switch back to Sonnet by hand. The exception is #394's triage (job 2), which is design work.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after:** S143 re-hit its configobj entry by skipping it. **New this
session:**
- §1: `weewx.log` timestamps are ISO, so a syslog-shaped window filter is a false zero.
- §3: `ssh -G` trips the marvin guard, and ConfigObj needs `interpolation=False`.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-27 (S143). #396 merged. `eaglehunt-ops#348` is complete: the loop feed lives
in `weewx-data/feed/`, the only part `eh-proxy` mounts (DEC-0202). The DEC-0200 overnight archive
check is job 1._
