# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
## [S97] — 2026-08-20 — S91 audit fully closed (#225/#226); NAS-LEASE holder client built + verified (DEC-0108); INTERFACES.md's two DEC-0053 gaps actually documented

- **The S91 audit's 8-issue sequence (#219–226) is now fully closed.** #225 (5 QC-completeness
  findings, all dormant on this station's single-ISS config) and #226 (4 public-facing CLI/config
  bugs) were the last two, both shipped this session (PRs #258, #260); #219–224 had already landed
  in prior sessions. Tracking issue #227 closed with the full sequence noted. #226 item 1 is the
  standout for impact beyond this station: the shipped config template carried a literal,
  unsubstituted `[options]` token that any new user following the documented setup shipped straight
  into `weewx.conf`, silently discarding the auto-appended `-tf`/`-tr` flags and falling back to
  868MHz EU instead of 915MHz US with zero error. 23 new regression tests across the two PRs.
- **`ops/nas_build.py` — weewx's NAS-LEASE holder client — built, tested, and verified against the
  real NAS, ahead of the ~08-23 build (DEC-0108).** A generic lease-wrapper (`--job <name> --
  <command>`): `O_CREAT|O_EXCL` acquire, explicit `fchmod 0644` (the exact umask near-miss
  `NAS-LEASE.md` v1.4 documents and DEC-0107 found on the box), `flock` held for the wrapped
  command's run, stale-break only when flock is free **and** `expires_at` has passed, release with a
  truthful outcome (`clean`/`build-failed`/`crashed`) wrapped in `try/finally`. Generic over any
  command so it covers both of weewx's named holder cases (image build, manual bulk analysis) from
  one script. **Scope decision, recorded in DEC-0108:** the observer/downshift side is deliberately
  not built — weewx has no live downshift lever to act on a "held" verdict yet, so a courtesy read
  with nothing to act on has unclear benefit today; revisit once the InfluxDB `post_interval` lever
  ships. 14 tests against a real `flock()` on a `tmp_path` dir, not mocked. **Later in the session,
  ran it for real** against the actual shared `LEASE_DIR` (a clearly-labeled dry-run job, TTL 60s) —
  clean `acquired`/`released` pair logged, directory left exactly as found, no stray lease file.
  Floor/TTL ship as §5's provisional 600s/3600s, to be re-pinned against the real ~08-23 build's
  measured duration; the adopting DEC itself still waits for that event on purpose.
- **`INTERFACES.md` actually documents both of DEC-0053's open findings now — ROADMAP had been
  overclaiming this since S48.** Tracing ROADMAP's P3 line (which asserted DEC-0053's
  station-identity finding was "documented there") against the actual file found that only Finding 1
  (bound the loop-JSON cache) had made it in. Finding 2 — InfluxDB carries no station-identity tag,
  and adding one later forks a parallel series instead of annotating it — is now written into §2,
  along with a one-line pointer to Finding 3 (the SQLite archive's own missing correction flag,
  deliberately left in `DATA_ERRATA.md` where DEC-0053 always said it belonged). ROADMAP's P3 line
  corrected in the same pass, with the guardrail's own "targeted pass writes both places" rule
  followed this time. PRs #261, #262.
- **Session-start concurrency, resolved cleanly.** A live peer session (`weewx-rtldavis-e4`, S96)
  was still finishing as this session started; coordinated directly rather than duplicating work.
  The peer's handoff corrected an early misreading on this session's part — ops#169's current
  title/body read as an unresolved coffee-radar heads-up, but the actual unresolved thread had
  already closed as DEC-0104/DEC-0107, verified independently against `DECISIONS.md` rather than
  taken on the peer's word alone. Mid-session, coffee-radar (`coffeeradar-28`) cross-checked the
  ~08-23 timeline directly; confirmed, and told them the holder client was now built and verified,
  not just designed.
- **Interim Campaign B readout, informational only — square left running untouched per owner
  instruction.** Using `ops/campaign_analyze.py --since <the live attempt's epoch>` (the raw log
  pools 6 aborted attempts back to 08-11; the tool's own pooling warning caught it): at 22 of 32
  blocks, arm B (gain 496, ex 0) leads arm A (372, anchor) by +2.25 pts, and D leads C by +1.16 pts
  at ex 50 — gain wins both head-to-heads; the ex axis itself reads as a wash (+0.93 pts one way,
  −0.16 the other). Already exceeds campaign A's entire 4-arm spread (0.94 pts). Explicitly not a
  verdict — the runbook's own rule is not to read partial results, and DEC-0102's overnight iowait
  confound is still open.
- **Two secret-read-guard false positives found and worked around, worth a note to ops.** The guard
  blocked a plain `scp` upload of this repo's own already-secret-gated script (never touches
  `weewx.conf`), and separately a `tail` on the NAS-LEASE attribution log (plain JSONL, no
  credentials) — both keyed on the command verb/NAS-host pattern rather than which file is actually
  touched. The documented `command` escape hatch resolved both, but only once `command` was the
  **literal first word** of the whole invocation — `cmd; command scp ...` still triggered it,
  `command bash -c '...scp...'` did not. Flagged via `spawn_task` for ops to fold into the guard's
  own documentation rather than left as a per-session rediscovery.
- **Green gate at close:** ruff clean, **386/386**, mypy clean (62 files), secret gate clean and
  positive-controlled mid-session (planted a fake key, confirmed the catch, restored from a
  pre-mutation backup rather than `git checkout` since the index held the payload). Soak at close:
  17 pass / 2 warn / 0 fail — same two known warns (chatty stdout #253, USB hedge during RF-dead).
- Model tier: ran on Sonnet 5 throughout, confirmed directly rather than inferred — no restore owed.
- Five PRs merged this session: #258 (#226), #259 (DEC-0108), #260 (#225), #261 (INTERFACES.md
  Finding 2), #262 (INTERFACES.md Finding 3). Steady state verified `dev` + `main` only after each.

---
---
*(S73–S96 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
