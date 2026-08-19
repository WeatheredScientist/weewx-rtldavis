# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S90] — 2026-08-18 — NAS-LEASE adoption deferred to v2.0.14 (DEC-0099); the InfluxDB rollup answered as dashboard's build (DEC-0100)

- **Off-cycle start, by design.** BOOT's resume pointer had no date-gate reached yet (probe harvest
  waits on the 08-19 05:00 stop; the daily watch is cheap and unblocking). Session instead swept
  ops + dashboard + HLF for cross-repo messages — the routine `repo:weewx` check, run further than
  usual because the sweep surfaced a live thread nobody had caught yet.
- **DEC-0099 — OPS-DEC-0107 (NAS-LEASE) landed 2026-08-15 and HLF adopted (their DEC-0177, live
  since 08-16) while `BOOT.md` sat completely stale on both.** weewx has zero live levers today —
  the one committed-unbuilt lever (InfluxDB `post_interval` deferral, safe to ~30 min per DEC-0092)
  needs `influx.py` inside the container to see `LEASE_DIR`, which isn't mounted and can't be
  without a release-class recreate. **Deferred, not declined: v2.0.14 already recreates the
  container**, so that's the no-extra-cost moment to add the mount — bundled plan now in BOOT's
  v2.0.14 queue (mount `LEASE_DIR`; `influx.py` checks it and raises `post_interval` while held; the
  NAS image build becomes weewx's first HOLDER via acquire→flock→release; renewal in-place only,
  **never** `loop_json_writer.py`'s tmp+`os.replace` idiom, which the spec names as the exact way to
  strand a flock on an unlinked inode). Posted to ops#169, left open against weewx until the window
  lands the client.
- **Free correlation, no adoption needed:** read the live world-readable `heavy-io.log` this
  session — one real lease-held window exists so far (HLF's `daily-maintenance`, 2026-08-18
  00:10–06:10 EDT), containing both one RF-dead episode (02:41, 26.3 min) and one freeze
  (03:15–03:22, 420 s). n=1, far too small to test anything — logged as a lead in BACKLOG's standing
  watches, explicitly **not** revising DEC-0094's P=0.29 or the RF-stall P=0.32.
- **DEC-0100 — ops#175's mutual wait (weewx: "dashboard's call"; dashboard: "waiting on weewx to
  propose a shape") broke on an ops strawman; weewx answered.** Accept-and-monitor for InfluxDB
  agreed. On who builds the permanent daily rollup dashboard's all-time-record queries need: weewx
  declines, recommends dashboard build it as a native InfluxDB 2.x Task — `docs/INTERFACES.md`
  already draws the boundary ("our responsibility ends at writing the documented schema"), dashboard
  already runs Flux against this bucket and `influx.py` never has, and a Task changes neither write
  path. Posted to ops#175.
- **PR #215 merged (`b5c1be5`)** — both DECs, BACKLOG/BOOT synced to current reality, steady state
  restored. Green gate at close: ruff clean, 299 passed, mypy clean/51 files.
- **Campaign B watch, at close: block 16 of 32, arm C** (swapped 18:05:02, settled 84s — confirmed
  directly via `rx_experiment.state` + log, not derived). Soak run earlier the same session: 16
  pass / 2 expected-WARN (chatty stdout + ineffective USB hedge, both already-known), reception 75%
  5-window avg / 71% last window, 0 stalls, no STOP/lock. This was the session's only contact with
  the running square — the originally-planned S90 job list (probe harvest, closer campaign
  tracking) is untouched and carries to S91.
- ROADMAP checked: neither DEC touches a P0–P3 line item (both live in BACKLOG, not ROADMAP) —
  nothing to reconcile. Tripwire unchanged, still due by S96.

---
## [S89] — 2026-08-18 — The overnight "reception dip" was never reception (DEC-0097); the mechanism probe moves to the NAS (DEC-0098)

- **DEC-0097 — the reception-floor dip is RF-dead episodes, and BOOT's own record of it was
  wrong.** A watch carried four sessions ("n=4, window drifting later, needs the proper
  statistical test") fails on three premises. **The record:** PAUSE/RESUME lines pair one-to-one,
  so 08-18 was onset **02:55, five cycles**, not the logged "03:30, two" — corrected onsets
  02:15/02:15/03:25/**02:55** are not monotonic, and the drift was the stated reason for rejecting
  a fixed-clock artifact. The four nights are arms **A, B, C, D** — every gain × receive-window
  cell, so not an arm effect. **The measurement:** on per-minute `rxCheckPercent` (DEC-0069/S31 —
  *not* the monitor's 30-min mean; different instruments, the 50% floor does not transfer), tested
  on **31 pre-campaign nights the hypothesis was not derived from**, contrasting the window
  against its flanks *within one arm block* so gain/window/arm are constant: mean d = **−0.01 pts**
  (Wilcoxon p=0.60, permutation p=0.47). Deepest 30-min mean on campaign nights **68.4%** against
  DEC-0059's 73.3% baseline; **0 of 35 nights** under 50% while the monitor reported 20–45%.
  **The mechanism:** every episode reads one pathological value (3–22%), then minutes **absent**,
  then NULL, then normal 65–90% — `campaign_analyze.py`'s documented truncated-accumulation
  artifact, which cannot self-identify because `interval` stays 1. Those artifacts feed the laggy
  30-min mean and trip the floor. The null held-out result *is* the mechanism's confirmation:
  `partition()` already excludes them. **And night 1 was already classified** — DEC-0094 recorded
  08-15 02:00–02:22 as RF-dead three sessions before the watch was flagged untested.
  **What survives, on the right unit** (ledger rows re-clustered per DEC-0083's unit lesson):
  RF-dead episodes concentrate **00:00–04:00 — 8/19 vs 3.17 expected, P=0.0079**, stable at
  30/45/60-min clustering; stall-bearing rows only **7/9 vs 1.50, P=0.00009**, and **0/9** in
  DEC-0094's evening freeze window — different clocks, independent support for the two being
  separate phenomena. **7 of 7 ledger dates**, including three that **predate the square**.
  Stated against itself: ledger is 6.5 d, left-censored at ws.5; omnibus does **not** reject
  uniformity (X²=27.7, df=23, crit 35.2); DEC-0092's tenant maintenance (00:10→~03:00–05:10)
  overlaps and is not discriminated against. **No code changes** — DEC-0087 scoped the PAUSE to
  RF-dead episodes and that is exactly what fires it. Job 2 closes; blocker 2 gains a timing
  signature.
- **DEC-0098 — the mechanism probe runs on the NAS, because a laptop-side overnight probe is not a
  limitation but an infeasible design.** `ops/proc_probe.py` was built to BOOT job 6's "read-only
  from the laptop, no NAS write" scope and hardened inside it (per-batch ssh, a supervisor that
  relaunches on process death — verified by SIGKILL, rc=137 → auto-resume — idempotent `--resume`,
  gap-guarded deltas). None of that addresses the real failure mode: it required the owner's laptop
  awake **12+ hours**, and DEC-0097's second window (00:00–04:00) a laptop-side probe can never
  sample at all. `ops/proc_probe_nas.sh` now runs under `nohup` on the NAS (pid 28699, ends
  08-19 05:00) emitting the **same pipe-delimited stream** `proc_probe.py` parses; `--ingest`
  reuses `parse_line()`, and merging is idempotent. Footprint went **down** — ~2,700 ssh
  round-trips replaced by `/proc` reads plus an append. Costs recorded: a Class C write approved in
  chat, a bounded resident process on prod, and **cleanup owed**.
- **The probe measures cumulative counters, not instantaneous state** — the reason two prior
  attempts could not settle DEC-0068. `block_max` already showed a **4041 ms** uninterruptible
  block in a 4 h span containing no evening, so "main thread `S`, never `D`" was sampling coverage,
  not evidence. Measured before building, not assumed: no PSI (kernel 4.4.302+), `wchan` reads `0`,
  `/proc/<pid>/io` denied as non-root. A smoke test caught three real bugs pre-flight (a
  two-column row shift, both md2 fields collapsing to one value, `/wait_sum/` also matching
  `iowait_sum`).
- **New trap:** `nasctl cat /proc/<pid>/cmdline` returns **empty for a live process** — caught only
  by positive-controlling the method against weewxd's own known-live pid. Third instance of *a zero
  from a look-alike tool is a claim, not a result*.
- **Gain / receive-window hot-swap filed, not started (PR #212, [ops#179]).** Owner asked what
  prevents hot-swapping a gain instead of restarting the container every arm swap. **Only the
  feature.** Gain is a CLI flag on the Go binary carried in the `cmd` string, and `rtldavis.py` has
  **no concept of it at all** — `grep -i gain` returns five hits, four of which are the word
  "a*gain*st". The swap path already exists: `ProcManager.startup(cmd, …)` takes the command as a
  parameter, `shutdown()` kills and reaps, and the 150 s watchdog exercises that respawn cycle
  routinely (DEC-0081). The gap is only the trigger — config is read once in `__init__`. `-ex`
  rides the same string, so both axes of the square could swap with no container touch, retiring
  the 600 s settle window (~2.8% of campaign data) and the abort-on-unhealthy-swap failure class
  (DEC-0082, DEC-0087). Filed with its constraints attached: **not during campaign B**, the binary
  sets gain only at startup, it widens the vendored fork, and device re-open time after a
  deliberate SIGKILL is unmeasured.
- Campaign B watch: block 14 verified healthy at ~10:00 EDT (soak 16 pass / 2 expected-WARN);
  block 15 starting at close. Square through `08-23T00:05`, ~4.5 d left, no swap deferred.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179

---
## [S88] — 2026-08-18 — weewx 5.5.0 staged for v2.0.14; the schedule gains a stand-down state (DEC-0096)

- **weewx 5.4.0 → 5.5.0 merged to dev (PR #208)** — the deliberate bump behind dependabot #158,
  per the issue-#78 flow (the dependabot PR is the notification; #158 closed with a pointer).
  Rides the v2.0.14 image cut. Upstream 5.5.0 notably adds retry-on-database-locked — the
  DEC-0070 failure class. Corrected en route: #158's red `tests` check was an artifact of its
  only CI run predating the S73 test correction on `main` (the pre-S73 first-row assertion
  against a schedule that had legitimately launched), not a 5.5.0 problem — current `main` would
  pass it today.
- **DEC-0096 (PR #209): an empty SCHEDULE block is now the explicit between-campaigns stand-down
  state.** Campaign B's terminator (08-23T00:05) is the v2.0.14 window's opening moment, and
  `tests` is a required check on both branches — without this, every PR of the cut would have
  queued behind a red staleness guard, with nothing honest to regenerate the table to. `install`
  refuses the empty block loudly; six structural tests skip on emptiness; the staleness guard's
  classification moved to `_schedule_state()` with its stale branch positively controlled
  (DEC-0045) so a fully-elapsed real schedule still fails exactly as before. The live schedule is
  untouched; the post-square emptying PR must land FIRST in the window. 299/299.
- Watches: 08-18 swaps `B→D` 00:05:02 (settle ~196 s) and `D→A` 06:05:02 (~144 s) both healthy,
  block 14 of 32 in progress; reception-floor dip recurred 03:30–03:45 ×2 on arm D — watch n=4,
  window still drifting later (02:15 → 03:25 → 03:30). Soak 16 pass / 2 expected-WARN.
- Docs: CONSTANTS' release row corrected — `prod-baseline-20260811` (`main` = `1cc9605`) landed
  at S73, the "promotion pending" note was stale. ROADMAP checked: no v2.0.14 line to reconcile,
  scheduled pass S96.

## [S87] — 2026-08-17 — The soak was lying about a healthy station; retention settled as accept-and-monitor (DEC-0095)

- **`ops/soak_check.sh` measured every age against a clock captured before its own remote body —
  PR #206.** `now` was taken at the top of the ssh block, then ages were computed against it at the
  bottom, after `docker logs`, a full `weewx.log` window read and a `docker exec` sqlite loop. Every
  age was understated by exactly the block's runtime. That runtime was ~2 s historically (every
  recorded value 1–29 s, all inside the monitor's 30 s poll) and 15–100 s under load by 08-17, so
  the monitor's log mtime always landed *after* `now`, the age went negative, and the `-ge 0` guard
  reported a perfectly healthy watchdog as **`MONITOR LOG STALE … wedged`** — for ten days, on every
  run. The watchdog was in fact polling on the dot: 19:10:17 → :47 → 19:11:18 → :48 → 19:12:18, no
  gaps. **The quieter half mattered more:** the same stale clock fed `record_age_s`, the DEC-0036
  freeze detector, whose 180 s threshold silently became 180+runtime (measured 195–280 s) — least
  sensitive exactly when the box is loaded, which is when freezes happen (DEC-0088: median 240 s).
  Both ages now read the clock at the point of measurement, the runtime is reported rather than
  hidden, and the monitor verdict splits into its four real outcomes (dead / no log / clock skew /
  wedged). Also retires the reception check's hardcoded 80% floor, which read **one** 60 s window of
  21 packets — sd ~9.7 pts at this station's measured 73.3% baseline (DEC-0059) — and so warned on
  most healthy runs, 20 pts tighter than the monitor's own `WU_RF_MIN_PCT=60`; the soak now reports
  the monitor's five-window average and its `[OK]/[LOW]` verdict instead of keeping a second
  threshold beside it. New `tests/test_soak_check.py` drives the real script with `ssh` stubbed;
  every "no longer cries wolf" assertion is paired with a positive control that the check still
  fires, verified by running the suite against the pre-fix script (7 fail, all three teeth-controls
  pass).
- **DEC-0095 — retention is accept-and-monitor, not archive-then-prune, and the monitor executes.**
  Answers the weewx half of ops#175. Measured read-only 08-17: archive **33.61 MB = 0.89% of
  MemTotal 3.69 GiB**, 5.1 TB free disk, **1,392 rows/day at 275 B = 0.37 MB/day, ~7.3 yr to 1 GB**,
  InfluxDB engine 14 MB; `dbstat` puts 32.94 of 33.61 MB in the single `archive` table. HLF's
  DEC-0156/0174 **method** transfers and its **conclusion** does not — DEC-0174 justified retention
  on the working set at ~8.0 M hot rows against *this same 3.69 GiB box*, and we have 66× fewer
  rows. Three further grounds: the `archive` table is the deliverable rather than a regenerable
  diagnostic (a passively intercepted station cannot backfill); upstream already bounds long reads
  by aggregation (114 `archive_day_*` tables, ~0.1 MB); and the one cost this DB's history documents
  is CoW fragmentation, for which retention is the wrong lever (`chattr +C` queued, DEC-0092,
  confirmed unapplied). Because accept-and-monitor is worthless as prose (DEC-0040), the reversal
  condition ships as code: the soak reports the archive against **10% of MemTotal** (~386 MB, ~2.6 yr
  out) and crossing it reopens the DEC. The **InfluxDB half is deliberately left open against the
  dashboard** (DEC-0010) — weewx proposes no horizon for a shared bucket.
- **Campaign B watch: block 12 of 32**, `A→B` swap on time at 18:05:02, settle 136 s (n=7, still not
  a trend). STOP/lock absent, arm `B` live, square through `08-23T00:05`.
- **Recorded as a lead, not a finding:** at 19:16 EDT — inside DEC-0094's significant 18:00–21:00
  band — NAS loadavg was **9.05/11.39/8.75** on 4 cores, driven by ~220% CPU of `chrome-headless`
  (coffee-radar) plus ~14 MB/s sustained writes on `md2`. No process was in `D` state and weewxd's
  threads were all `S`, so tenant load is established but *blocking* is not — which is precisely
  blocker 1's open question. One instant is not a probe; sampling across a window is the next step.

---
*(S73–S86 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
