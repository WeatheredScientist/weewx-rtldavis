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

## ▶ Resume here (S89 → S90)

### ⏰ FIRST THING NEXT SESSION: harvest the probe before anything else

`proc_probe_nas.sh` (pid **28699**) stops at **08-19 05:00** and its output is **not** backed up
anywhere. Harvest it read-only, then clean the NAS. Full context in job 2 below — do this before
the daily watch, because nothing else in the session is time-sensitive and this is.

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged.** Square runs
**08-15 → 08-23T00:05** — **~4.5 days left as of S89 close (08-18 midday)**, block 15 of 32
starting (the 12:05|B swap was due at close), every swap on time, none deferred. Live state in the
table below.

**The v2.0.14 queue (post-campaign, ~08-23) is fully staged on `dev`, and the window has a
MANDATORY OPENING MOVE:**

0. **FIRST PR of the window: empty the SCHEDULE block** (stand-down, DEC-0096 — support landed
   S88, PR #209). The square's terminator `08-23T00:05` is the window's own opening moment, and
   `tests` is a required check on both branches: until this trivial, self-green deletion lands,
   **every other PR sits red** on the staleness guard.
1. Image cut: weewx **5.5.0** (merged, PR #208 — the deliberate bump behind dependabot #158, now
   closed; upstream adds retry-on-database-locked, the DEC-0070 class) + #183's pressure package
   (merged, closes #172/#144) + monitor trio (DEC-0090/0091). NAS-native build (DEC-0078); the
   recreate re-verifies CONSTANTS' three live-config deviations **and** the LNA-out
   hardware-timeline line.
2. Move `:latest` to v2.0.13 once the square proves it.
3. **Copy the new `loop_json_writer.py` (with `current_interval`) to the NAS *project root* — NOT
   the image, NOT `weewx-data/bin/user/`** (mounted not baked, DEC-0093 — that second path is a
   decoy). Verify with `nasctl inspect` before; confirm the startup line reads `every 60 s` after —
   a file check proves the FILE, never the PROCESS (DEC-0074). Deploy note lands on [weewx#204]
   (the cadence ping's home; dash#430 is closed as superseded by it).
4. NAS-side, same window (from ops#169/DEC-0092): `noatime` on `/volume1`, `chattr +C` on the
   archive DB, move our logrotate off 00:05.
5. **NAS-LEASE first adoption (DEC-0099, S90):** mount `LEASE_DIR` read-only at the recreate;
   `influx.py` checks it at its own poll, raises `post_interval` while a foreign lease is held; the
   NAS image build (DEC-0078) wraps `docker build` with acquire→flock→release as weewx's first
   HOLDER. Renewal in-place only (seek+write+truncate) — **never** `tmp`+`os.replace`, DEC-0051's
   idiom would silently strand the flock.

**The cut is execution-only, Sonnet-fit.** #144's offset itself is settled (station-side,
WeatherLink console elevation; ops#168 owner-side, no repo work).

**Resume machinery (DEC-0087/0089) is proven, not theoretical: 12+ pause/resume cycles across four
nights, all auto-recovered, zero STOPs** (08-18 added two on arm D). Still unexercised: the 120-min
ceiling escalation, the swap-deferral path, rotated-log reads across a `.1` boundary.
*(`rx_experiment.STOP.campaignA` at the project root is campaign **A**'s — not a live sentinel.
Raised with the owner at S89 close and deliberately left in place; delete it only on an explicit
say-so, since it is a STOP-named file sitting beside a live campaign.)*

**The nightly-heavy-window confound (ops#169, DEC-0092) is absorbed by design** — each arm takes
the midnight slot exactly twice. Nothing owed by weewx on that thread; its queue items are line 4
above.

**Hardware history is documented (CONSTANTS.md, S86): LNA in ~01Jun→02Aug, out since.** The
elevated stall rate's onset (08-10 23:56) is 8 days after removal, not coincident — attribution
stays open (DEC-0083), post-campaign characterization question.

### ▶▶ S90 JOB LIST

**Job 2 is the session's real work and is judgment-tier — flag the model call when starting it.
Everything else is watch- or execution-tier.**

1. Daily square watch (~5 min): `ops/soak_check.sh`; STOP absent, state matches schedule.
   **Verified good through block 14 (08-18 ~10:00 EDT)** — soak 16 pass / 2 expected-WARN (chatty
   stdout + ineffective USB hedge are both expected). `remote probe took Ns` ≥20 s is a NAS-load
   signal, not noise.
2. ⚠️ **HARVEST + INTERPRET the mechanism probe — the open judgment item (DEC-0098).**
   `proc_probe_nas.sh` pid **28699**, started 08-18 10:49, **ended/ends 08-19 05:00** →
   `/volume1/docker/weewx-rtldavis/logs/proc_probe_nas.log` (~400 KB by S89 close, growing).
   One run covers **both** target windows with control flanks: evening (freezes, DEC-0094) and
   **00:00–04:00** (DEC-0097's RF-dead cluster, overlapping DEC-0092's tenant maintenance).
   Harvest read-only into a file (never onto the terminal), then:
   `ops/proc_probe.py --ingest <pulled> && ops/proc_probe.py --analyze logs/proc_probe.csv`
   — ingest is idempotent, `--analyze` de-dupes, and gap-spanning deltas are dropped, so a partial
   or overlapping harvest is safe. **How to read it:** the probe measures **cumulative** per-thread
   counters, not instantaneous state — DEC-0068's "all `S`, never `D`" was sampling coverage, and
   `block_max` showed a **4041 ms** block in a 4 h span with no evening in it, so blocking happens
   at baseline. **The claim under test is that the window is WORSE than its flanks.** Load with a
   **flat** iowait ratio answers DEC-0068 **NEGATIVE — a real result, not a failed probe.**
   Then **clean up the NAS**: `proc_probe_nas.sh`, `proc_probe_nas.pid`, and
   `logs/proc_probe_nas.{log,err}`. Class C, so it needs the in-chat path.
3. Resume machinery — keep counting cycles; watch for the three untested paths above.
4. **[ops#173] BOOT.md over cap — TRACKED, do not re-derive or open a second issue.** Diet at the
   square's close (~08-23), both sides already agreed. **S89 grew it further; the diet is overdue,
   not optional** — this job list and the gotchas section are the obvious candidates.
5. **v2.0.14 prep is DONE** — everything staged on dev; nothing to decide before ~08-23. The
   window opens with the DEC-0096 emptying PR (queue item 0 above).
6. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Owner's framing: revisit once the square closes **and** the gated queue clears. Do
   not start it mid-square (protocol change breaks comparability, DEC-0064).

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#169]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/169
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[ops#175]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/175
[weewx#204]: https://github.com/WeatheredScientist/weewx-rtldavis/issues/204

### Current state (S88 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b, sha+process verified |
| Campaign B | **Live and on schedule — block 14 of 32 in progress (arm A since 08-18T06:05:02), 13 complete, every swap on time, none deferred.** 08-18: `B→D` 00:05:02 · `D→A` 06:05:02 (both healthy). Next swap `08-18T12:05|B`. Square through `08-23T00:05` (~4.7 d left as of 08-18 ~08:00 EDT). STOP/lock absent; PAUSEs are RF-dead episodes behaving as DEC-0087 designed, not a reception dip (DEC-0097). Verified 08-18 ~10:00 EDT, soak 16 pass / 2 expected-WARN |
| Swap settle time | n=9: 82/139/198/137/197/79/136/196/144 s — **not a trend, do not re-flag**. Budget ~383 s, wide margin — but an unhealthy swap is `trip_abort()`, a sticky STOP DEC-0087 does **not** soften |
| Retention | **SETTLED (DEC-0095)** — accept-and-monitor, no prune; tripwire executes in `soak_check.sh`, reopen at 10% of MemTotal (~2.6 yr out). InfluxDB horizon is the **dashboard's** call |
| `dev` beyond prod | **Everything for v2.0.14 — two deploy layers, don't conflate.** Baked (ride the image cut): weewx 5.5.0 pin, #183 pressure package, DEC-0096 stand-down support. Mounted (needs the project-root file copy): `loop_json_writer.py` incl. `current_interval`. Plus S84–S88 docs |
| Freeze rate | DEC-0088-corrected (1.31/day), untouched. Hour-of-day split done (DEC-0094): nightly refuted, evening 18:00–21:00 carries the signal — job 6 is its mechanism probe |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md`, hardware timeline alongside |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | **Steady state: exactly `dev` + `main`.** PR #208 (5.5.0 bump) + PR #209 (DEC-0096) merged 08-18, branches deleted. Dependabot #158 **closed with a pointer** — its red `tests` check was an artifact of its only CI run predating the S73 test correction on `main`, not a 5.5.0 problem |
| Trackers | #158 closed (superseded by #208, commented) · #172/#144 open until v2.0.14 (code done, deploy pending) · **#204 open as the current.json-cadence deploy home** (body is a broken literal file path — `--body @path` misfire, cosmetic) · ops#163/#176 closed |
| Cross-repo (S90) | **Two threads resolved, both replies drafted not yet posted.** ops#169/NAS-LEASE: OPS-DEC-0107 landed + HLF adopted while BOOT sat stale on it — weewx's own adoption deferred to v2.0.14, concrete plan in queue item 5 (DEC-0099). ops#175: InfluxDB rollup strawman answered — dashboard's to build, weewx declines with reasons (DEC-0100). ops#173/#179/#110 unchanged from S89 |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (S80 measurement via
   `ops/freeze_baseline.py`, DEC-0088-corrected), separate phenomenon** from DEC-0081's episodes.
   **Still hard-aborts — DEC-0087 deliberately does not cover freezes** ("RF re-established" isn't
   a meaningful resume condition for a process-wedge event). Root cause still unproven (thread
   blocking on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068).
   **The S83 hour-of-day lead is ANSWERED and NEGATIVE (S84d, DEC-0094) — do not re-run it.** The
   nightly window holds **9 of 40 freezes vs 7.2 expected, P=0.29**; durations inside match outside.
   **The evening carries the signal instead: 18:00–21:00 = 12 vs 5.0 (P=0.0027)**, coffee-radar's
   ~19:00 window 7 vs 2.5 (P=0.011), over 10 distinct dates — DEC-0068's n=1 is now a base rate
   (30% of freezes in 12.5% of the day). **Mechanism still unproven** — DEC-0068 measured the main
   thread `S`, never `D`, so neither coffee-radar's load nor our own write volume is established as
   *blocking* us (DEC-0093 declines the write-volume link). Next real step is job 6's mechanism
   probe, not more timestamp counting.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open): interference vs no-LNA
   front-end margin vs site vs condensation. **DEC-0083 adds a dated onset (08-10 23:56) the
   characterization should start from** — it coincides with the campaign-B pilot night and the
   v2.0.12 promotion, neither of which is established as cause. **DEC-0097 adds a timing
   signature: episodes cluster 00:00–04:00** (stall-bearing 7/9 vs 1.50, P=0.00009), on every
   ledger night, across all four arms — start the characterization there. Caveat carried: the
   ledger is 6.5 d, left-censored at ws.5, and DEC-0092's tenant window overlaps.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains
   the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **Campaign clocks are LOCAL (EDT); most tool output is UTC — convert before comparing.** The
  `SCHEDULE` rows (`2026-08-15T00:05|A`), the swap slots, the log timestamps and DSM's crontab are
  all **local**; `git`/`gh` output (`mergedAt: …Z`), and most API responses are **UTC**. S83 read a
  `Z` timestamp as local and put the swap four hours nearer than it was. DEC-0068 hit the identical
  trap from the other side. Two hits, so treat any bare timestamp as UTC until proven local.
- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` trips every NAS `scp` deploy** (S81/S82/S82b — likely the `. nas.env`
  sourcing; the `command`-prefix escape does NOT clear it). The settled fallback: hand the owner
  the single command, **saying explicitly it runs on the Mac**. Ran cleanly that way three times.
- **A guard block can be a MISFIRE — check before you go near the mint path (S85, ops#176).**
  `push-nas-guard.sh` hard-blocked a `python3` heredoc that only edited a **local** `.md` file,
  because the *prose being written* quoted the transfer verb. **Do not ask for a mint on a
  misfire** — rung 0: re-spell it (`Write`/`Edit` for file content instead of a shell heredoc). A
  genuine NAS write just blocks again, so the check costs nothing.
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("requirements not met", state stays OPEN — and `gh pr merge`'s quiet refusal is another face
  of its never-trustworthy output). Fix server-side: `gh api -X PUT repos/<r>/pulls/<n>/update-branch`,
  wait for the CI rerun, then merge. Found S82b on #183. (S88 avoided it by merging sequentially.)
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is
  correct; a holder older than 1800s is broken automatically and loudly. Don't read a missing lock
  as "the cron is dead".
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations need the Class C mint path (confirm in chat, mint,
  re-run identical — mint and re-run as TWO separate calls). The scp shape falls through to the
  read-guard fallback above instead.
- **`due_arm()` never returns `NONE` once the pilot block has run** — its last pilot row (`H`)
  is the implicit hold value until the square's first row, so `tick`'s silent no-op
  (`want == have`) can run for hours with zero log output. Check `current_arm()`/state +
  STOP/PAUSE directly, not log silence. *(Post-campaign note: an EMPTY schedule does return
  `NONE` — that's the DEC-0096 stand-down state, and `install` refuses it before it can matter.)*
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root** — but its LOG output does
  not: `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the project root next to the script; `.log` and
  `_data.log` under `logs/`, alongside `weewx.log`/`weewx_monitor.log`/`monitor_episode.state`.
  `nasctl ls` the actual directory before assuming either layout.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** — reversed
  arguments are rejected confusingly (S80); multi-word patterns silently return a FALSE ZERO
  through the ssh quoting layer (S53). Positive-control any zero count. `nasctl cat`/`tail` need
  **absolute** paths.
- **Merging several same-session PRs in sequence: re-`git fetch` before every merge-into, not just
  the first** (S79 silently dropped a merged PR's doc changes off a stale ref). And **never
  `git checkout -- <file>` to unplant a staged positive-control payload** — it restores the
  planted version from the index (S55's gotcha, re-bitten S82b); edit the lines out instead.
- **GitHub's API can degrade on WRITES while READS stay fine (S86)** — verify with a GET before
  assuming a mutation failed either way; don't hammer the write path in a foreground retry loop.
  `docker logs` also accumulates across a container's own restarts — swap-day boot chatter in
  `soak_check.sh`'s stdout count is history, not a live crash loop; confirm with `inspect`'s
  unchanged `StartedAt`/`Pid` before alarming (S88).

_Last updated: 2026-08-18 (S89 close — Opus). Landed **PR #211** (DEC-0097 + DEC-0098) and
**PR #212** (BACKLOG), both merged, branches deleted, steady state restored. **DEC-0097 closed the
reception-dip watch**: never a reception measurement but RF-dead episodes truncating records, and
BOOT's own 08-18 row was wrong (02:55/5 cycles, not 03:30/2), retiring the "drifting later"
premise. What survives is a timing signature for blocker 2 — episodes cluster 00:00–04:00
(P=0.00009 on stall-bearing rows), **zero** in the evening freeze window, so the two blockers keep
different clocks. **DEC-0098 moved the mechanism probe onto the NAS** after the laptop-side design
proved infeasible (12+ h awake, and DEC-0097's overnight window unreachable that way); it runs
unattended to 08-19 05:00 — **job 2 next session is harvesting it.** Gain hot-swap filed
(BACKLOG + ops#179), deliberately not started. Green gate at close: ruff clean, **299 passed**,
mypy clean/51 files. ROADMAP: targeted DEC-0057 update to the freeze P0 item; full pass still
S96. **Model note (closeout step 6): S89 ran on Opus for the judgment work; the switch was
SESSION-ONLY and NOTHING NEEDS RESTORING** — verified at close across all four scopes,
`~/.claude/settings.json` = `sonnet`, no `model` key in `~/.claude/settings.local.json` (absent),
`.claude/settings.json`, or `.claude/settings.local.json`. *Earlier in the session this was
asserted the other way, from OPS-DEC-0010's rule rather than from a check — in THIS client a
`/model <m>` did not touch the floor. Verify the scopes before claiming a restore is owed.*_
