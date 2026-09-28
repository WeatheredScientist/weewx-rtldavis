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

**S143 moved the loop feed into `weewx-data/feed/` (DEC-0202, `eaglehunt-ops#348` step 1).** It has
been live on marvin since 2026-09-27 22:58 ET.
- `[LoopJsonWriter]` `path`/`current_path` point at `feed/` in the live conf **and** the tenant-root
  `weewx.conf.rx-baseline`. Both are 0600, and the pre-edit copies are in `conf-archive/`.
- The top-level `loop-data.txt` and `current.json` are now relative symlinks into `feed/`, so
  `eh-proxy`'s current whole-dir mount still reads live data. They are temporary; job 1 deletes
  them.
- Rules for `feed/` (from marvin S54) are in `CONSTANTS.md`'s deviations table. Never delete or
  recreate it while eh-proxy runs, and only rename files into it.
- Verified: eh-proxy served `/loopdata` 200 at 1.4 s old right after the swap. `weewx.log` showed
  0 errors against 101 INFO lines since the restart.

**S142's DEC-0201 is merged** (PR #396, squash `0d79daf`): conf backups live in `conf-archive/`, and
the live conf stays 0600. **DEC-0200 is confirmed on the InfluxDB side** (HLF S349). Only its
archive-side overnight check is left (job 2).

### ▶▶ S144 JOB LIST

1. **`eaglehunt-ops#348` step 4: delete the two symlinks.** Do it only after marvin's flip (step 2)
   and the dashboard's check (step 3) are posted on #348.
   - Confirm the flip yourself first: `marvinctl --tenant weewx inspect eh-proxy` must show the
     source `…/weewx-data/feed` at `/weewx-data` (it read the whole `weewx-data` at S143 close).
   - Then, in one `marvinctl exec … -- sh`, `test -L` each name and `rm` only those two. Never
     touch `feed/` itself.
   - Re-read `/loopdata` through eh-proxy, post on #348, and ring marvin and the dashboard. If the
     flip hasn't happened, do nothing: the symlinks are harmless.
2. **DEC-0200 full-overnight archive verification.** Query archive rows with `radiation = 0` after
   2026-09-27 17:41 ET for any `0 < UV < 0.05`; expect none.
   - **A twilight fraction such as 18:28's 0.0141 is expected.** It's a transition minute that
     averages zeroed readings with readings ≥ 0.06.
   - **Expect a NULL or partial row around 22:57.** S143's restart caused it, the same as 17:41.
     It is not a DEC-0200 failure.
   - A dark fraction, or any exact 0.02/0.04, needs its minute examined. Find the code before
     touching the window; never widen it.
3. **`#394` (surface the ISS low-battery flag `bat_iss`).** Owner-filed 2026-09-20, `tier:mid`,
   untriaged. Start with the issue's own question: is `bat_iss` archived or surfaced anywhere yet?
4. **Reception at the dongle's new position (`5-1`) vs the old `7-1.2` cluster is unmeasured.**
   DEC-0154 fixed the crash loop, not this. It needs a longer `rxCheckPercent` read.
5. Carry forward job 8's remaining items (EnvironmentFile, `marvin-release.sh`) exactly as S126 left
   them. None are due.
6. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7)** for a maintainer reply
   (repo dormant since 2023-12-22). Don't chase it.
7. `eaglehunt-ops#306`'s residual `MANIFEST.md` cap overage: coverage beats the cap, so no action
   unless a real instance-collapse turns up.
8. **`CONSTANTS.md` infra re-verify, the remainder.** The marvin rows (e.g. host tool availability)
   are still S105-era. The NAS rows were re-verified at S142. `CONVENTIONS.md`'s stale infra copy is
   gone as of S143, replaced by a pointer.
9. Optional, owner route only: one tenant-root tidy that isn't reachable by any other tenant (see
   the local-infra doc). Do it only if a root-route window opens anyway.

## Current state (S143 close)

| Thing | State |
|---|---|
| Prod | marvin, `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986). `weewx.service` restarted 2026-09-27 22:56:50 ET for DEC-0202. `weewx-data` has `feed/` (0755, the loop feed), two temporary top-level symlinks into it, and `conf-archive/` (0700) |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged. Dark UV arrives as 0 (confirmed by HLF) |
| weewx-monitor | unchanged, running since 2026-09-18 23:13 ET; carries the `REMEDY_SYSTEMCTL` fix + DEC-0199 |
| Reception | unchanged since DEC-0154's recovery; new-position comparison unmeasured (job 4) |
| `main`/`dev` | S143: DEC-0202 docs PR to `dev`, on top of #396. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged |
| Trackers | repo: #394 open (job 3) · #380 open (marvin's pager, informational) · ops: #348 step 1 done, waiting on marvin's flip (job 1) · #347 answered, #396 merged so heartofgold can tick weewx's row · #265/#110 deferred-trigger, unfired · #306 residual (job 7) · #344 macOS LAN (worked around; this desktop session reached marvin) |

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
**Desktop app:** the model persists into later sessions. Jobs 1 and 2 are execution, so the next
session should switch back to Sonnet by hand.

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

_Last updated: 2026-09-27 (S143). #396 merged. `eaglehunt-ops#348` step 1 is live: the loop feed is
in `weewx-data/feed/` behind temporary symlinks (DEC-0202). marvin's flip is next, then weewx deletes
the symlinks (job 1). The DEC-0200 overnight archive check is job 2._
