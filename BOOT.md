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

## ▶ Resume here (S82b → S83)

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged.** Square runs
**08-15 → 08-23T00:05** (third shift, DEC-0089). Holding on **H**; arm **A** due
`2026-08-15T00:05` — the first block runs on ALL of S82/S82b's fixes.

**S82 (DEC-0090): the state-machine audit shipped five `rx_experiment.sh` fixes** — floor-aligned
resume, rotated-log reads, swap deferral while paused (BASELINE exempt), guard stand-down at
BASELINE, tick/guard/abort lock — PR #179, deployed sha `4438a2a3…`. Plus the dead
`soak_check.sh` reset counter ('RESET: running' now).

**S82b (DEC-0091): the owner's reframe ("square hasn't started") used the pre-block-1 window.**
PR #182 (the #180 monitor trio) merged AND deployed same day — episode state mirrored to
`logs/monitor_episode.state` + restored at startup, rotation voids pending reset verdicts,
reset-exception path emails; live as **pid 7625** since 12:25:21, verified per DEC-0074; #180
closed. PR #183 (#172 + #144) merged to `dev`: **`barometer_fetch_epoch`** (no-TTL staleness
stamp) and **honest-null `pressure`/`altimeter`** (archive columns go NULL at deploy — hlf#302
heads-up posted). INTERFACES §1 updated; #172/#144 stay open until the v2.0.14 deploy.

**The v2.0.14 queue (post-campaign, ~08-23):** weewx 5.5.0 (PR #158, deliberately deferred) +
#172's field + #144's honest nulls + move `:latest` to v2.0.13 once the square proves it.
NAS-native build (DEC-0078), recreate re-verifies the three CONSTANTS live-config deviations.

### ▶▶ S83 JOB LIST

1. **Verify arm-A's block 1 swapped in at `2026-08-15T00:05`** — tick log `swapping H -> A` +
   `arm A live and healthy`. First live working tick of the S82 code: if the swap did NOT
   happen, check for a PAUSE first (a deferred swap is now legitimate behavior), then STOP.
2. Daily square watch (~5 min): `ops/soak_check.sh`; STOP **and PAUSE** both absent; state
   matches schedule.
3. **Watch the revised resume machinery on a real pause** — floor-resume + rotated reads +
   deferral have no live exercise yet (n=0 on the S82 mechanism; BACKLOG watch re-baselined).
4. Optional, campaign-safe: **#144's offset quantification** — archive `barometer` vs METAR
   MSLP over a multi-day window; method in the issue comment; keep the METAR station id out of
   committed text.

### Current state (S82b close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` (S82) + `weewx_monitor.py` (S82b, pid 7625) both redeployed today, sha+process verified |
| Campaign B | Holding on **H**; arm **A** due `2026-08-15T00:05`, square through `08-23T00:05`. STOP and PAUSE both absent |
| `dev` beyond prod | #183's pressure package (baked files) — rides until the v2.0.14 image cut |
| Freeze rate | DEC-0088-corrected (1.31/day), untouched |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` = `origin/dev` (`ba09e80`; PRs #179/#181/#182/#183 all merged). Only `dependabot/pip/weewx-5.5.0` (#158) beyond, queued for v2.0.14 |
| Trackers | #180 closed · #172/#144 commented, open until v2.0.14 · ops#163 closed / ops#165 filed |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (S80 measurement via
   `ops/freeze_baseline.py`, DEC-0088-corrected), separate phenomenon** from DEC-0081's episodes.
   **Still hard-aborts — DEC-0087 deliberately does not cover freezes** ("RF re-established" isn't
   a meaningful resume condition for a process-wedge event). Root cause still unproven (thread
   blocking on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068).
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open): interference vs no-LNA
   front-end margin vs site vs condensation. **DEC-0083 adds a dated onset (08-10 23:56) the
   characterization should start from** — it coincides with the campaign-B pilot night and the
   v2.0.12 promotion, neither of which is established as cause.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains
   the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` trips every NAS `scp` deploy** (S81 rx_experiment, S82 again, S82b
  monitor — likely the `. nas.env` sourcing; the `command`-prefix escape does NOT clear it). The
  settled fallback: hand the owner the single command, **saying explicitly it runs on the Mac**.
  Ran cleanly that way three times now.
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("requirements not met", state stays OPEN — and `gh pr merge`'s quiet refusal is another face
  of its never-trustworthy output). Fix server-side: `gh api -X PUT repos/<r>/pulls/<n>/update-branch`,
  wait for the CI rerun, then merge. Found S82b on #183.
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is
  correct; a holder older than 1800s is broken automatically and loudly ("breaking stale lock").
  Don't read a missing lock as "the cron is dead".
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations need the Class C mint path (confirm in chat, mint,
  re-run identical — mint and re-run as TWO separate calls). The scp shape falls through to the
  read-guard fallback above instead.
- **`due_arm()` never returns `NONE` once the pilot block has run** — its last pilot row (`H`)
  is the implicit hold value until the square's first row, so `tick`'s silent no-op
  (`want == have`) can run for hours with zero log output. Check `current_arm()`/state +
  STOP/PAUSE directly, not log silence.
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root** — but its LOG output does
  not: `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the project root next to the script; `.log` and
  `_data.log` under `logs/`, alongside `weewx.log`/`weewx_monitor.log`/`monitor_episode.state`.
  `nasctl ls` the actual directory before assuming either layout.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** — reversed
  arguments are rejected with a confusing "not metacharacter-free" error (S80); multi-word
  patterns silently return a FALSE ZERO through the ssh quoting layer (S53). Positive-control any
  zero count.
- **Merging several same-session PRs in sequence: re-`git fetch` before every merge-into, not just
  the first** (S79 silently dropped a merged PR's doc changes off a stale ref). And **never
  `git checkout -- <file>` to unplant a staged positive-control payload** — it restores the
  planted version from the index (S55's gotcha, re-bitten S82b); edit the lines out instead.

_Last updated: 2026-08-14 (S82b close) — the owner's "square hasn't started" reframe knocked out
#180 (deployed, verified, closed), #172 and #144 (merged for v2.0.14) the same day, on top of
S82's audit fixes. DEC-0091 logged. Arm A due 2026-08-15T00:05 — the square starts on one
consistent, fully-patched instrument stack._
