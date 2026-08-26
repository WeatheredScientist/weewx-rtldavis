# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S103] — 2026-08-26 — Gain / receive-window hot swap built (DEC-0117): a validated control file, plus the post-swap watchdog grace that keeps it from tearing the driver down

- **Picked up the last open `BACKLOG.md` idea / [ops#179], filed at S89 and deliberately unstarted
  until Campaign B closed.** S89's analysis held up on re-inspection: nothing prevented a hot swap
  but the trigger. `gain` and `-ex` are startup-only CLI flags on the Go binary, `rtldavis.py` never
  inspects them, `ProcManager.startup(cmd, …)` already takes the command as a parameter, and the
  150 s watchdog exercises that kill→respawn cycle routinely.
- **Built as a watched control file carrying bounds-checked integers only — never a command string.**
  `hotswap_control_file` (unset = feature off, stock behavior). The driver polls it about every 10 s
  at the top of `genLoopPackets` — no thread, no signal handler, since `get_stderr()` already budgets
  10 s per pass — and on an mtime change validates, splices into the running command, and respawns.
  Only `gain` (0–496) and `ex` (0–1000) are accepted: `cmd` reaches `shlex.split()` → `Popen`, so a
  raw-command channel would be arbitrary code execution inside the container for anything able to
  write that NAS path. Tests pin that rejection explicitly.
- **The hazard S89's note missed, and the reason this needed design work:** `time_last_received` is a
  **local** in `genLoopPackets` and is *not* reset by a child respawn, while a fresh child is
  legitimately silent for the US 133 s radio init period. A naive `shutdown()`→`startup()` inherits a
  stale timer, trips the 150 s stall watchdog mid-init and tears the driver down — reintroducing the
  abort-on-unhealthy-swap failure class the feature exists to retire, on *every* swap. Every swap now
  resets the four watchdog counters and widens the threshold to `HOTSWAP_GRACE_S = 240` until the
  first packet (a flat 150 s left only 17 s of margin over that init period), reverting as soon as
  anything is received.
- **Also: rollback** to the last known-good command if the new one fails to start (a bad gain must
  not cost us the receiver), **an atomic ack file** recording status and the measured respawn gap —
  which self-measures ops#179's constraint 4, the never-measured RTL-SDR re-open time — and the
  control file **honored at init before the first spawn**, so a container restart cannot silently
  revert a swapped gain while the ack still advertises it (DEC-0116's exact shape).
- **Green gate: 428 passed / 8 skipped** (26 new), ruff clean, mypy clean (65 files), secret gate
  clean. The three loop-level tests are **mutation-verified** — removing the grace, the reset, or the
  rollback each turns the suite red — with a positive control proving the same silence *without* a
  swap still stalls at 150 s. One secret-scanner false positive fixed at source by renaming a local
  (`key = …`) rather than widening the allow-list.
- **Not in prod.** `rtldavis.py` is a **BAKED** file, so this ships only with an image rebuild, and
  the feature is off until the config key is set. `ops/rx_experiment.sh` still swaps arms by
  rewriting the mounted config and restarting — converting it is a separate change, and the one that
  must not land mid-campaign.

---
## [S102] — 2026-08-25 — Ops-tracker verification sweep: #144/#172/#204 checked live (not memory), two didn't hold up; `loop_json_writer.py`'s stale mount found and fixed (DEC-0116)

- **An `eaglehunt-ops` session asked to confirm four post-v2.0.14 items were live and close whichever
  were done: ops#179, #144, #172, #204.** Checked each against the running container directly instead
  of trusting the ship announcement. ops#179 matched ops's own description (still unstarted,
  untouched). #144 held up and closed clean: `fetch_interval=300` confirmed live via `readconf --nas`,
  the triple-field null fix baked into the running image, owner's item-1 decision already final.
- **#172 and #204 did NOT hold up — DEC-0116.** Both features live in `loop_json_writer.py`, a
  **mounted** file per `CONSTANTS.md`'s deploy-layers table. The deployed copy was still the
  2026-07-27 version: hash mismatched `dev`, missing both `current_interval` and
  `barometer_fetch_epoch` entirely, confirmed by a live `current.json` read with the field absent and
  `current.json`/`loop-data.txt` sharing an identical mtime (per-packet writes, not throttled). Same
  deploy-layer trap DEC-0114 caught for `influx.py` three days earlier, just outside that event's own
  verification scope — `dev` and prod were **not** actually in sync as `BOOT.md`'s S101 close claimed,
  for this one file.
- **Fixed live, with the owner's explicit go-ahead:** deployed current `dev`'s `loop_json_writer.py`
  to its NAS mount source, hash-verified the match, `docker kill` + `docker start` (DEC-0008). Confirmed
  post-restart: `barometer_fetch_epoch` appeared on the first WeatherLink poll, and `current.json`'s
  60s throttle is now measurably active (mtimes diverge from `loop-data.txt`'s per-packet writes).
  #172/#204 closed with the live evidence in the closing comments. Ops looped throughout via direct
  session-to-session messages, including the correction on the two claims that didn't hold up.
- **Lesson for next time (DEC-0116):** an image bump proves the baked layer moved; it says nothing
  about any mounted file not specifically re-verified that session. The deploy-layers table's other
  mounted files (`ogoxeUploader.py`, `sortedcontainers`, `weewx.conf`) remain independently unverified.
- **Gates:** 402/402 (8 skipped, unchanged — no code touched this session), ruff clean, mypy clean
  (64 files, `.mypy_cache` cleared first), secret gate clean.

---
## [S101] — 2026-08-23 — v2.0.14 ships (weewx 5.5, NAS-LEASE adoption); Campaign B closes, gain 496 adopted

- **Merged S100's closeout PR (#273), then ran the ~08-23 v2.0.14 build event.** Campaign B
  self-terminated on schedule (`BASELINE`, 2026-08-23T00:05); built natively on the NAS from
  `origin/dev`@`efeeebd` under `ops/nas_build.py`'s NAS-LEASE holder wrapper. Ships DEC-0110
  (reception-quality wind guard), DEC-0111 (`influx.py` NAS-LEASE courtesy yield), #233, #224, and
  weewx 5.4.0 → 5.5.0 (pinned since S88, `ca3c024` — this is the first release to actually carry
  it, since `dev` has been running ahead of prod).
- **Three real problems found and fixed live during the deploy, not glossed over:**
  1. `docker` wasn't on the non-interactive SSH PATH — first build attempt crashed instantly
     (`FileNotFoundError: docker`); fixed by passing the full `/usr/local/bin/docker` path.
  2. A retried build genuinely hung 70+ minutes at 0:00 accumulated CPU on a `weectl`
     syslog-handler crash mid-Step 7/30 (verified via `ps aux`, not inferred from log silence) —
     killed on owner instruction, stale lease cleared, log rotated, retried clean in ~360s.
  3. `influx.py`'s DEC-0111 code never reached the running container despite a fresh image —
     it's a MOUNTED file, so the image rebuild didn't touch the NAS-side mount source, which still
     held the old `ws.1` code. Caught by checking the live version banner post-deploy (not assumed
     from a clean-looking recreate); fixed via a separate `scp` + restart, checksum-verified.
- **DEC-0114: NAS-LEASE adoption locks** (the §5 event DEC-0104/DEC-0107 deferred).
  `RENEWAL_FLOOR_S` re-pinned 600 → 420 against tonight's real measured build duration; `TTL_S`
  held deliberately generous at 3600 given the hour-plus hang above was a real, non-capacity
  failure mode. Also added `LEASE_DIR` mount (`-v /volume1/docker/nas-lease:/nas-lease:ro`) and
  `weewx.conf`'s `[[Influx]] lease_dir = /nas-lease`.
- **Live NAS-LEASE contention with `hyperlocal-forecast` resolved via direct session-to-session
  coordination** — a new standing SOP this session (message the other repo's live Claude session
  directly for time-sensitive shared-resource questions, always loop `eaglehunt-ops` too, not just
  on decisions needing sign-off). HLF found and killed a concurrent lease-unaware manual job of
  their own, then their own stuck `daily-maintenance` run, after an owner priority call
  (`OPS-DEC-0136`). Verified independently at each step, not taken on report.
- **DEC-0113 applied live**: `[DavisPressure] fetch_interval` 3600 → 300, verified.
- **DEC-0115: Campaign B closes, gain 496 (arm B) adopted as the new RF baseline.** Clean 32/32-block
  final square (2026-08-15 → 08-23, after excluding 6 pooled aborted/restarted attempts the
  analysis tool's own default run would otherwise have mixed in): **A (372/ex0, incumbent) 72.83% ·
  B (496/ex0) 74.83% (+2.00) · C (372/ex50) 73.28% (+0.45) · D (496/ex50) 74.77% (+1.94)**. Gain
  axis clearly favors 496; extraction axis a wash. The margin is exactly at DEC-0059's 2.0-point
  adoption bar, not comfortably above it — adopted anyway given the consistent direction across
  both the interim and final readouts. A narrower follow-up sweep near 496 considered and declined
  for now (pilot data suggests a flat curve there). Deployed to both live `weewx.conf` and
  `weewx.conf.rx-baseline` (a live-only edit would be silently wiped by the next campaign's own
  restore path). `ops/rx_experiment.sh`'s `SCHEDULE=` block emptied per its own stand-down
  convention (DEC-0096) now that the campaign is complete.
- Post-deploy verification: driver banner unchanged at `0.20+ws.5`, `influx.py` now `0.20+ws.2`,
  no new CRITICAL/ERROR since restart, `weewxd` on 5.5.0.
- **`CONSTANTS.md`, `docs/DECISIONS.md`/`DECISIONS-FULL.md`, `docs/ROADMAP.md` updated same
  session** — release/rollback table, live-config-deviations table (3 new/updated rows), hardware
  timeline, reception baseline figure (73.3%/gain-372 → 74.83%/gain-496), Campaign B roadmap item
  closed.

---
## [S100] — 2026-08-22 — Verification-only session: clean pickup confirmed, Campaign B on track, new GOTCHAS entry for `rx_experiment.sh`'s local-run trap

- **No code shipped this session** — a status-check pickup, not a coding session. Clean-pickup gate
  ran clean: `dev` up to date with origin, working tree clean, 410/410 (unchanged from S99, no
  regressions).
- **Daily square watch (BOOT job 2, deferred at S99) run for real.** `ops/soak_check.sh`: 17 pass /
  2 warn / 0 fail, same two known warns (chatty stdout #253, USB hedge during RF-dead) — matches
  S98's last-known figure exactly, no drift.
- **Caught `ops/rx_experiment.sh status` giving a false-empty read when run from a local checkout**
  (`arm: NONE` since epoch, `installed: no`, `samples: 0` — looks exactly like "campaign
  self-terminated," which would have wrongly cleared job 1's precondition). The script has no `ssh`
  calls of its own and only resolves real state when it's actually running on the NAS. Verified the
  real state directly with `nasctl cat` on `rx_experiment.state`: Campaign B is genuinely still
  live, **arm D**, last swap **2026-08-22 00:07:25** — on schedule for its **08-23T00:05**
  self-termination. Documented the trap in `docs/GOTCHAS.md` §3 so the next session (or anyone else
  running this script) doesn't have to rediscover it.
- **Owner asked whether `eaglehunt-ops#180` needed an update.** Verified live via `gh issue view`:
  already closed at S99 with an accurate closing comment (remediation code-complete, only the
  v2.0.14 deploy gate remains, already tracked here) — nothing had changed since, so no new comment
  was needed.
- **Gates:** ruff clean, **410/410** (unchanged — no code touched), mypy clean (64 files,
  `.mypy_cache` cleared first), secret gate clean.
- Model tier: ran on Sonnet 5 throughout, confirmed directly rather than inferred — no restore owed.

---
## [S99] — 2026-08-22 — Ops-tracker close-out sweep: 5 issues closed, #233/#252 fixed and shipped, #144 resolved (DEC-0113)

- **Opened on a stale handoff and closed it first.** `BOOT.md`'s resume header still read "S98 →
  S99" and its footer "S98 close" despite two PRs (#269, #270) already merged under S99 branch
  names — an earlier S99 instance had deliberately held off on its own closeout after
  `eaglehunt-ops#195` flagged a possibly-concurrent session. Confirmed no other weewx session was
  active (this session's own `ListAgents`) and both loose ends that issue named — a stray remote
  branch, a stale detached-HEAD worktree — were already gone. Closed `eaglehunt-ops#195` with that
  confirmation.
- **`eaglehunt-ops#180` (the S91 audit heads-up) closed: all 8 remediation issues (#219–226) are
  confirmed closed**, `#227`'s sequencing plan fully executed. Only the deploy gate (the ~08-23
  v2.0.14 image) remains, already tracked here.
- **`#233` fixed: `ProcManager.shutdown()` now kills its own Popen handle directly**, belt-and-braces
  alongside the existing `pidof` name-match sweep, which had no fallback if it ever missed a
  still-live child. Regression test reproduces the exact gap (pidof matches nothing, child genuinely
  still alive) with a positive control. Baked file — ships to prod with the v2.0.14 image.
- **`#252` fixed: `ops/soak_check.sh`'s window computation and restart-loop detector now share one
  `$LY+$L` read** (yesterday's rotated log + today's), replacing the window cut's silent
  `ln=1`-widens-to-the-whole-file fallback when a container start predates midnight — the exact
  false-WARN shape the issue reported (driver-identity canary silently unverified, among others).
  Two new tests extract and run the real deployed bash block against synthetic logs, since the
  existing suite stubs `ssh` entirely and never exercised this layer. Not baked — a repo script, live
  the moment it's on `dev`. Both landed together in PR #271 (merged, `071f684`).
- **`#144` fully resolved (DEC-0113).** Item 2 (triple-field bug) was already fixed pre-session
  (S82b). Item 3 (hourly `fetch_interval`): checked WeatherLink v2's actual documented ceiling
  (1,000 calls/hour + 10/s) rather than the original guess ("what I thought the free tier allowed");
  300s uses ~1.2% of it and cuts the archived barometer from a 60-min staircase to a 5-min one.
  Queued as a live `weewx.conf` edit (confirmed via `nasctl conf` as the winning MOUNTED layer),
  held to the same v2.0.14 restart as everything else behind Campaign B's comparability discipline —
  new rows in `CONSTANTS.md`'s deviations table and this file's job list. Item 1 (the ~0.03 inHg
  console-vs-METAR offset): put to the owner directly, who confirmed the console's elevation-based
  correction is working as designed for the surveyed 550 ft (the DEC-0086 mechanism, not in
  question); closed with no change, the residual already absorbed downstream by HLF's per-source
  correction. Issue stays open pending the v2.0.14 deploy, same pattern as `#172`/`#204`/`#253`.
- **The ~08-23 v2.0.14 build is now a seven-purpose event**: `#224`, DEC-0110, DEC-0111, `#233`
  (all baked), plus DEC-0113's live `fetch_interval` edit — `#252` needs no deploy step at all.
- **Also closed: `#239`**, a stale, fully-contained InfluxDB-gap courtesy notice with nothing
  pending.
- **Gates:** 410/410 full suite (was 397, +13, 0 regressions), ruff clean, mypy clean (64 files,
  `.mypy_cache` cleared first), secret gate clean, positive-controlled throughout. PR #271 merged;
  branch cleaned up (local + remote), steady state verified after.

---
---
*(S73–S98 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
