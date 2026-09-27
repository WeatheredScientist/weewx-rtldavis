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

## ▶ Resume here (S142 → S143)

### What's settled (do not re-derive)

**S142 moved every `weewx.conf` backup out of the `weewx-data` top level (DEC-0201).** They now sit
in `weewx-data/conf-archive/` (dir 0700, files 0600), live on marvin since 2026-09-27 19:13:58 ET.
- **Why:** `weewx-data` is bind-mounted whole into the dashboard's `eh-proxy` (994:984), which reads
  it as *other*. File mode is the only boundary there.
- **How:** owner-approved, one `marvinctl exec` as t-weewx. The live conf was untouched and there
  was no restart.
- **Standing rule:** after any `weectl` run that rewrites the conf, `chmod 0600` it and archive the
  timestamped copy. `weecfg.save()` loosens it (`GOTCHAS.md` §3).
- **NAS side re-verified clean.** The export was retired 2026-09-05 (MARVIN-DEC-0134), and
  `CONSTANTS.md`'s stale overlay/Docker/rollback-host rows are corrected.
- Specifics are in the gitignored local-infra doc. Rotation is the owner's end-of-run call.

**DEC-0200 (S141) is confirmed on the InfluxDB side.** HLF S349 read the `weewx` bucket at UV
exactly 0 from 18:30 ET (0.065 at 18:20 was the last daylight bin). `eaglehunt-ops#343` is closed
with a comment. Only the archive-side overnight check is left (job 1).

### ▶▶ S143 JOB LIST

1. **DEC-0200 full-overnight archive verification.** Query archive rows with `radiation = 0` after
   2026-09-27 17:41 ET for any `0 < UV < 0.05`; expect none.
   - **A twilight fraction such as 18:28's 0.0141 is expected.** It's a transition minute that
     averages zeroed readings with readings ≥ 0.06.
   - A dark fraction, or any exact 0.02/0.04, needs its minute examined. Find the code before
     touching the window; never widen it.
2. **`eaglehunt-ops#348` — narrowing `eh-proxy`'s mount (dashboard + marvin own it).** weewx's
   part comes only when they're ready: point `[LoopJsonWriter]` `path`/`current_path` at
   `weewx-data/feed/`. That's a live-conf edit plus a restart, cut over in one window with marvin's
   mount change. Never do it alone; `eh-proxy` would read a dead file.
3. **`#394` (surface the ISS low-battery flag `bat_iss`).** Owner-filed 2026-09-20, `tier:mid`,
   untriaged. Starts with the issue's own question: is `bat_iss` archived or surfaced anywhere yet?
4. **Reception at the dongle's new position (`5-1`) vs the old `7-1.2` cluster is unmeasured.**
   DEC-0154 fixed the crash loop, not this. Needs a longer `rxCheckPercent` read.
5. Carry forward job 8's remaining items (EnvironmentFile, `marvin-release.sh`) exactly as S126 left
   them. None are due.
6. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7)** for a maintainer reply
   (repo dormant since 2023-12-22). Don't chase it.
7. `eaglehunt-ops#306`'s residual `MANIFEST.md` cap overage: coverage beats the cap, so no action
   unless a real instance-collapse turns up.
8. **`CONSTANTS.md` infra re-verify, the remainder.** S142 re-verified the NAS rows. The marvin rows
   (e.g. host tool availability) are still S105-era. `docs/CONVENTIONS.md`'s "Project root (NAS)"
   row names the retired path.
9. Optional, owner route only: one tenant-root tidy that isn't reachable by any other tenant (see
   the local-infra doc). Do it only if a root-route window opens anyway.

## Current state (S142 close)

| Thing | State |
|---|---|
| Prod | marvin, `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986). `weewx.service` untouched this session (up since 2026-09-27 17:40:18 ET, DEC-0200). `weewx-data` now has `conf-archive/` (0700) and no loose conf backups |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged. Dark UV arrives as 0 (confirmed by HLF) |
| weewx-monitor | sha = `dev` tip, running since 2026-09-18 23:13 ET; carries the `REMEDY_SYSTEMCTL` fix + DEC-0199 |
| Reception | unchanged since DEC-0154's recovery; new-position comparison unmeasured (job 4) |
| `main`/`dev` | S142: DEC-0201 PR to `dev`. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged |
| Trackers | repo: #394 open (job 3) · #380 open (marvin's pager, informational) · ops: #348 filed (job 2) · #343 closed · #265/#110 deferred-trigger, unfired · #306 residual (job 7) · #344 macOS LAN heads-up (worked around, MARVIN-DEC-0179) |

## Blockers

1. **weewx process freezes — rate confirmed 1.31/day median 240s (DEC-0088, reconfirmed DEC-0198
   S138); root cause/mechanism still unproven** (DEC-0068/DEC-0094). No active watch on the rate;
   re-derive only if a fresh elevated reading appears.
2. **RF-dead episode root cause unknown** (DEC-0081). First clean post-fix baseline read was taken
   at S126 (100% mean, no episodes yet); the watch continues.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**The whole session ran on Opus 5.5, flagged at the start as fitting.** The work was a security
investigation, a design call (DEC-0201) and an attended prod change. No `/model` switch was made
in-session. **Desktop app:** the model persists for later sessions, so the next *execution* session
(e.g. job 1's query) should switch back to Sonnet by hand.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **Two new this
session:** §1, in a worktree `check_secrets.sh` silently skips its identifier check; §3, a `weectl`
conf rewrite silently loosens `weewx.conf`.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-27 (S142). Conf backups archived out of the shared `weewx-data` top level
(DEC-0201), exposure verified read-only first. `CONSTANTS.md` NAS rows corrected. `eh-proxy` mount
narrowing filed to ops. DEC-0200 confirmed on the InfluxDB side by HLF, and `ops#343` closed. The
overnight archive check is job 1._
