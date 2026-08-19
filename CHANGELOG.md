# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S91] — 2026-08-19 — Full code audit (BOOT job 7): security fixes shipped (DEC-0101), 26 correctness findings filed as a sequenced plan (#219–227)

- **The owner's planned focus for the session, decided at S90 close.** Two independent halves, run
  as separate multi-agent passes rather than one combined effort.
- **Security pass**: 4 DEC-primed finder agents (one per file: `rtldavis.py`,
  `pressure_service.py`/`dewpoint_service.py`, `weewx_monitor.py`, `ops/rx_experiment.sh`) + an
  Opus-tier adversarial verification pass over everything they surfaced. **DEC-0101**: SMTP
  connections skipped TLS certificate verification at both alert-mail call sites
  (`weewx_monitor.py`'s continuously-running production monitor, `ops/rx_experiment.sh`'s campaign
  abort-notification path) — `smtplib`'s default with no `context=` is unverified, exposing
  `GMAIL_PASS` to an on-path attacker; `influx.py` already does this correctly elsewhere in the
  repo, this was a regression against an established in-house pattern, not a novel ask. Second
  finding: the WeatherLink API key could leak into `weewx.log` via exception text on any connection
  failure (reproduced empirically) — a new gap, not a DEC-0062 regression, since the credential
  only exists at runtime inside the exception's `__str__()`, invisible to DEC-0062's AST-based
  regression test. Both fixed, both guarded by new/extended tests with positive controls. **PR
  #229, merged.**
- **Bundled into the same PR**: a `docs/DECISIONS.md` structural fix — DEC-0093 through DEC-0101
  had been sitting under `## Open / deferred` despite every one being `Accepted` (found by the
  ultrareview cloud pass, which also caught the S91 session's own DEC-0101 addition landing in the
  same wrong spot). Fixed via a scripted, assertion-guarded reorder rather than a hand-retyped edit
  — the block was too large to safely retype by hand.
- **Also merged this session, unrelated to security but surfaced by the same ultrareview pass**: a
  pre-3.12 Python `SyntaxError` in `ops/proc_probe.py` (a conditional inside an f-string's `{}`
  spanning two lines needs PEP 701) — would have broken every entrypoint of the tool BOOT job 2
  depends on, on any pre-3.12 interpreter. All locally-available interpreters here are 3.12+, so
  this session's own probe harvest was never at risk, but it's a real bug in a public repo. **PR
  #228, merged.**
- **Correctness pass**: 10 independent finder angles (5 correctness + 3 cleanup + altitude +
  conventions, per the local `/code-review` skill's own methodology, adapted for a path-target
  full-file audit rather than a diff) against `rtldavis.py` + `dewpoint_service.py`, followed by
  Opus-tier adversarial verification of all 21 surviving candidates (batched by theme into 4
  verification passes) and a sweep pass that found 6 more. **26 distinct findings survived** (20
  confirmed, 6 plausible); 2 further candidates were independently **REFUTED** — a suspected
  packet-duplicate-detector aliasing bug turned out inert, because the Go binary already dedups
  byte-identical frames upstream and every packet carries monotonic counters that make the
  equality-based dedup check always-true regardless. **Filed as GitHub issues, not fixed this
  session** — the volume made same-session fixes impractical, and several (the ProcManager
  subprocess-lifecycle bugs, the dewpoint wind-filter redesign) are explicitly judgment-tier design
  work better done as their own deliberate sessions. Grouped into 8 issues (#219–226) by shared root
  cause rather than filed 1:1; sequenced with model tiers and deploy gating in tracking issue
  **#227**, the map for the next several sessions of this work.
- **Standout findings** (full detail in #219–226, not re-narrated here): an uncaught exception on
  CRC mismatch that can crash the whole weewxd daemon (found independently by 5 of the 5
  correctness-angle finders); `ProcManager.shutdown()`'s zombie-reap skip on an unguarded
  `pidof` call (also 5x-corroborated — the repo's own existing test monkeypatches around it with a
  comment admitting the gap); a regex bug that silently drops an entire transmitter's data whenever
  its battery goes low, leaving 5 status fields permanently dead; the shipped config-generator
  template shipping a literal unreplaced `[options]` token that would break any new user's first
  install; and wind data leaking in from the wrong sensor channel on any station with a separate
  Anemometer Transport Kit.
- **Cross-repo heads-up posted**: eaglehunt-ops#180 (informational — the audit methodology may be
  worth reusing on HLF/dashboard, not a request, no reply expected).
- **Deploy gate, applies to all of #219–226**: `rtldavis.py` (and likely `dewpoint_service.py`) are
  baked into the Docker image, so none of it can deploy before Campaign B closes (~08-23) — design
  and merge to `dev` freely, hold the image cut for v2.0.14 (or v2.0.15+ for the two lowest-priority
  issues).
- Green gate at close, on merged `dev`: ruff clean, **305 passed**, mypy clean/52 files.
- Campaign B checked twice (session start and close), both times healthy and completely off this
  session's critical path — block 16→17 of 32, a scheduled 00:05 swap into arm A landed clean
  between the two checks. No code from this session touches the running station.
- ROADMAP checked: nothing here ships/closes/reprioritizes an existing P0–P3 line (the audit's
  findings are new work, not a resolution of a tracked item) — nothing to reconcile, tripwire still
  S96.

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
*(S73–S88 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
