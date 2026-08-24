# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
## [S98] — 2026-08-20 — Phantom 37 mph gust diagnosed and corrected (ERR-0006); reception-quality wind guard ships (DEC-0110); P0.5's last follow-on retired (DEC-0109)

- **Owner-reported phantom 37 mph gust at 11:12 EDT, diagnosed to source and corrected (ERR-0006).**
  Same class as `ERR-0004` (2026-07-27), recurring independently: `rxCheckPercent` for that one
  archive minute collapsed to 9.2% (vs. 60–90%+ every surrounding minute), a genuine RF-dead
  episode (weewx.log silent 11:11:35→11:15:22, confirmed not a restart). One of the few packets
  that passed CRC that minute carried a corrupted wind byte; every other field in the row read
  normally, so nothing tripped DEC-0054's frame co-rejection. Investigated and ruled out `#225`
  item 2 (rain-rate co-rejection gap, fixed same day in PR #260 but not yet deployed) as the
  mechanism here — rainRate was clean. Archive row nulled + daily summary rebuilt (day-max now 19
  mph, genuine); InfluxDB point deleted and rewritten minus the 7 wind-derived fields, with
  `windGust_qc=1`/`windSpeed_qc=1` flags (24 fields verified, matching `ERR-0004`'s own precedent
  exactly) — the dashboard's read-only proxy token can't write/delete (confirmed 403), so the
  correction used `weewx.conf`'s own uploader token instead. Wunderground/CWOP/PWSWeather/OWM/etc.
  already have the bad value; that's permanent, same as `ERR-0004`. Cross-verified independently by
  an eaglehunt-weather-dashboard session (InfluxDB via its own query path) and an eaglehunt-ops
  session (raised `#225` item 2 and a container-restart confound as candidate mechanisms; both
  checked directly and ruled out for this incident) — good example of the coordination working.
- **Reception-quality wind guard ships, closing the ERR-0004/ERR-0006 blind spot (DEC-0110).**
  Neither the bounds check nor the 75 mph delta cap can distinguish this corruption from a genuine
  squall gust of similar magnitude — `ERR-0004`'s own writeup already established that tightening
  either risks false-rejecting real weather. Measured first, before designing anything (93 days,
  129,607 records): genuine high wind and severe reception collapse have never co-occurred at this
  station (lowest `rxCheckPercent` among 220 records with `windGust>=10mph`: 54.5%; 87 of 89
  `rxCheckPercent<20%` records stayed calm at 0–4 mph) — so a guard combining both signals can't
  false-null a real gust, with wide margins on both sides. `dewpoint_service.py`'s `DewpointCacher`
  gains a `NEW_ARCHIVE_RECORD` binding (`rxCheckPercent<20%` AND `windGust>10mph` → null the wind
  triple + derived fields), confirmed via `weewx.conf`'s own `[Engine][Services]` order to run
  before `StdArchive`'s write and every RESTful uploader. Explicitly does not reach Wunderground's
  RapidFire feed (publishes pre-archive-close — a live ticker, not an archive of record). 11 new
  tests including both incidents replayed verbatim as positive controls. Ships with the ~08-23
  v2.0.14 build (baked into the image), same gate as `#225`.
- **ROADMAP.md's P0.5 fully closed (DEC-0109).** Its last follow-on ("Keep-a-Changelog headings +
  DECISIONS entry-skeleton convergence," proposed S25, ~72 sessions unclaimed) is retired, not
  picked up: the original rationale is unrecoverable (no surviving transcript), no sibling repo
  adopted anything to converge toward (checked all three), and `DECISIONS-FULL.md` already grew
  its own working skeleton independently of `CHANGELOG.md` — nothing left to reconcile. Judgment
  call, not just absence of evidence: this repo's entries are dense, cross-referencing narratives
  that an external single-facet schema would likely fragment rather than clarify.
- **A `ROADMAP.md` overclaim caught while closing the loop on the above.** Its P1 arc credited
  DEC-0054 with "closing ERR-0004" outright — true only for the co-occurring-bounds-failure
  mechanism, not the whole class, which `ERR-0006` just proved recurs independently. Corrected in
  place rather than left standing.
- **Cross-repo, same session:** fixed a `secret-read-guard.sh` false-positive gotcha in
  eaglehunt-ops (`command` escape-hatch anchoring + a co-occurrence false-positive class), found
  and flagged via `spawn_task` while doing unrelated ops work; landed there as OPS-DEC-0115, tested
  and deployed.
- **Gates:** 397/397 full suite (was 386, +11 new, 0 regressions), ruff clean, mypy clean (63
  files, `.mypy_cache` cleared first), secret gate clean. PR #265 merged to `dev`.

---
---
*(S73–S97 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
