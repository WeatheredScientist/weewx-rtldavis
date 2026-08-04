# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S65] — 2026-08-04 — Freeze-watcher fixed (parallel reads, dedup bug, local notification); a richer live capture; shared-NAS hypothesis checked

- **The watcher's second-sample bug is fixed.** S64's second `S`-vs-`D` sample landed ~7 min late
  because it read all 12 thread states sequentially, one `nasctl` round-trip at a time (no SSH
  connection multiplexing on this box). Now fanned out in parallel (background + `wait`, single
  retry for stragglers): a full 12-thread sample takes ~1-2 s.
- **Found and fixed a second bug the same night: the watcher didn't dedup an ongoing freeze.**
  Tonight's run "caught" three stalls in a row, all reporting the identical frozen `weewx.log` size
  — it was one continuous ~4 min freeze (longer than the usual ~3.5 min), captured three times,
  which burned `MAX_CATCH=3` on a single event and exited the watcher 8+ hours early. It now waits
  for the log to actually regrow before re-arming detection.
- **Native macOS notification wired in** (`osascript`, confirmed deliverable live) on each genuine
  catch and on exit. The watcher is a detached `nohup`+`caffeinate` process; it now needs no open
  Claude session or cloud connectivity to reach the owner.
- **The richer capture (21:48:59–21:52:37 UTC):** every thread read `S` throughout except three
  isolated moments where a single `rtldavis` worker thread went `R`; `weewxd`'s main thread and all
  four REST-uploader threads stayed `S` the entire time. **Still no `D`** — leans further against
  the I/O-blocking hypothesis and points more specifically at something stuck in `weewxd`'s own loop
  while the RF-capture side keeps intermittently ticking.
- **Checked whether shared-NAS contention (coffee-radar / hyperlocal-forecast) explains it, at the
  owner's request.** A *general* NAS-wide stall was already ruled out at S63 (InfluxDB's own timer
  fired sub-ms, on schedule, mid-freeze). A *narrower* hypothesis — page-cache eviction from
  coffee-radar's scheduled batch runs or HLF's own heavy jobs, the documented mechanism behind HLF's
  own DEC-0162 incident class on this same box — hadn't been checked and isn't the same claim.
  Tonight's snapshot: coffee-radar's container was **not** running during the freeze. Not proven,
  not ruled out; a `nasctl ps` snapshot is now captured on every future catch at no extra cost. The
  four known freeze timestamps don't cleanly match coffee-radar's advertised schedule.
- Watcher relaunched (v4) for the rest of the night, deadline 2026-08-05 13:33 UTC, up to 3 more
  distinct catches. Script still lives only in scratchpad, not the repo — third time it's been
  rebuilt from session-transcript archaeology; worth committing to `ops/` if this keeps recurring.
  Detail: [docs/ROADMAP.md](docs/ROADMAP.md) P0 freeze item.

---
## [S64] — 2026-08-04 — First live D-vs-S capture of a freeze, plus two closed trackers

- **CI: bumped pinned GitHub Actions off Node 20** (#121, closes weewx-rtldavis#117).
  `actions/checkout` v4→v7, `actions/setup-python` v5→v7, `peter-evans/dockerhub-description`
  v4→v5 — Node 20 runners are removed this Fall and every CI run already warned. Breaking-changes
  for each action were checked against how these specific workflows use them; none apply.
- **ops#114 closed.** It tracked campaign A toward an expected 08-06 self-close, but campaign A
  actually ended 4 days early via its own abort tripwire (2026-08-02, confirmed correct in S62) —
  there was never going to be a completion email to wait for.
- **First live thread-state capture of a process freeze (DEC-0067's open question).** An overnight
  read-only watcher (poll `weewx.log` size, `nasctl cat /proc/<tid>/stat` on the container's thread
  IDs) ran 15 h (17:32→08:32) and caught the 08-03 23:23:03→23:27:25 freeze (262 s, zero driver
  stall exceptions that day — the process-freeze signature, not RF loss). All 12 named threads read
  `S` (sleeping), none `D` (uninterruptible I/O), about 2 min into the freeze — independently
  confirmed against the raw log (exactly one gap ≥60 s all night, matching the watcher's count).
  **Leans away from the leading I/O-blocking hypothesis but isn't conclusive**: the design's second
  sample, meant to confirm the state persists, took ~7 min instead of the intended 20 s (12
  sequential `nasctl` round-trips) and landed after the freeze had already recovered. One clean
  sample, not two. Detail: [docs/ROADMAP.md](docs/ROADMAP.md) P0 freeze item.

---
## [S63] — 2026-08-03 — The recurring "reception dropouts" are process freezes, and the driver already knew

Diagnostic session, no production change. Nothing was deployed; campaign B stays held.

- **DEC-0067 — they are not reception dropouts.** `get_stderr()` is bounded at 10 s, so a *running*
  main thread that hears no RF raises `rtldavis process stalled` at 150 s. Across the silent
  208–218 s gaps it **never fired** — the main thread was not executing. **The receiver was fine;
  the weewx process freezes**, ~3.5 min, roughly once a day. The discriminator was already deployed
  and already correct; what was missing was reading its *silence* as data.
- **Measured, not asserted:** genuine RF loss is confined **entirely to ERR-0005** — 21 driver
  detections on 08-02, **0** on 07-30, 07-31, 08-01 and 08-03. So ERR-0005 is a single incident, not
  the head of a pattern. Its own root cause is still unestablished.
- **The standing watch is answered and closed.** A freeze on **07-30 with the LNA still installed**
  proves the dropouts are **not** new to the no-LNA regime. Removing the LNA did not cause them.
- **The instrument was the problem, not the weather.** The monitor counts *published output*, so a
  frozen process and a deaf receiver both read `WINDOW: 0/21 (0%)`. Every "unexplained dropout" was
  scored by a metric that cannot make the distinction the watch existed to make.
- **A freeze also misdates what it recovers.** Packets are stamped at *parse* time, so a backlog
  collapses onto the resume instant: the frozen minutes have no records at all and the next record
  absorbs ~3.5 min of packets — distorting the very counters campaign B measures, down then up.
- **Campaign B's gate is reframed, not lifted.** The recurring class is explained in kind and
  bounded (~0.4 % of wall-clock); the launch condition becomes mechanical — detect and exclude
  freeze windows — instead of "wait until the instrument is trusted".
- **`database is locked` is recurrent and pre-dates the LNA** (08-01 15:08, 08-02 19:45). The 10-min
  outage decomposes as ~106 s hung threads + **120 s of weewx's own hardcoded wait** + ~5 min
  restart; the identical lock on 08-01 cost 4 min because threads exited in 0.26 s. **The archive DB
  is not in WAL mode** — the first thing to try.
- **Ruled out with evidence:** NAS-wide stall (influxdb's timer fired mid-freeze, sub-ms on
  schedule), the S37 stdout wedge (live config has **no console handler**), CPU-quota throttling
  (DSM 4.4 exposes no `cfs_quota_us`), `pressure_service` (82 fetches, worst 8.99 s), the monitor's
  6-hourly read, and the HH:04 gap cluster (campaign-A swaps).
- **Still open: why it freezes.** All threads stop together and nothing is logged — consistent with
  a thread blocking on the bind-mounted log volume while holding the logging lock (box runs at
  **18.6 % cumulative iowait**). Unproven; the `D`-vs-`S` capture did not land before session end.
- Also corrected S62's stale handoff: the branch had merged and the watchdog had been deployed
  between sessions, so BOOT.md was telling S63 to redo both.
