# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S66] — 2026-08-05 — Both campaign-B gates handled: metric goes freeze-aware (DEC-0069), DB lock bounded (DEC-0070)

- **New `ops/campaign_analyze.py` + 14 tests** — reads per-minute `rxCheckPercent` from the archive
  DB, excludes freeze artifacts structurally, reports per-arm means with the *uncleaned* figure
  alongside so the size of the correction is visible rather than asserted. `ops/rx_experiment.sh`
  is deliberately untouched: the unattended, prod-config-writing apparatus was not modified to close
  a reporting gate.
- **The gate was mostly a resolution problem, not a freeze problem.** `harvest()` scraped the
  monitor's *5-minute* `RECEPTION:` aggregate, where one frozen minute drags the whole bucket
  (measured 16 % and 27 % against a ~72 % neighbourhood) and destroys four good minutes — that is
  where BOOT's ~0.8-point estimate came from, and it was correct *for that metric*. The same
  measurement is stored **per minute** in the archive. Net effect on a pooled arm mean: **±0.03
  points** against a 2.0-point adoption bar.
- **Measured the freeze signature** over 10 988 records / 33 gaps: three non-overlapping classes
  (freeze / arm swap / lock-outage). **The contaminated record is the one adjacent to the gap; the
  freeze minutes are simply absent rows** — BOOT had assumed they scored as zeros, which is what
  made the estimate ~60× too large. Retro-found one freeze nobody had logged (07-29 22:12).
- **Corrects DEC-0067 in both directions.** Its predicted post-freeze "up" is real — 2026-07-29
  03:10 reads `rxCheckPercent = 200.0` — but conditional, ~1 in 8 days. An initial two-freeze
  reading here concluded there was no "up" at all; the 8-day scan overturned that.
- **Campaign A recomputed:** A 74.81 / C 74.37 / D 74.17 / B 73.87, spread **0.94 pts**, no arm near
  adoption. The ~1.9-pt offset from the previously-recorded 72.4 % matches `weewx_monitor.py`'s own
  "~1–2 pts optimistic" note — the two metrics validate each other, and A-vs-B must be read on the
  same one. *This unsealed A's arm winner ahead of B; see DEC-0069's sealing note.*
- **Two build-time defects caught, both of which would have printed confident wrong numbers:** a bare
  run pooled campaign A's aborted 07-29 attempt with the campaign proper (unbalanced square, tidy
  table, no indication) — now detected mechanically; and deriving the query bound locally dragged the
  entire archive over ssh — now bounded NAS-side.
- **ROADMAP:** metric gate closed; the `database is locked` defect restated as campaign B's **sole**
  remaining gate. The by-S66 *full* reconciliation tripwire fired and is flagged as still owed.
- **DB lock bounded (DEC-0070) — it was two defaults, not a bug.** `journal_mode=delete` (a reader's
  SHARED lock blocks the writer) plus weedb's **5 s** SQLite timeout (`weedb/sqlite.py:136`, and the
  live config set none). Six seconds of reader therefore cost a CRITICAL + weewx's hardcoded 120 s
  wait + restart ≈ **5–10 min outage**. Shipped **`timeout = 30`** to the live `weewx.conf`; verified
  in the running system (resolved `database_dict` carries it) and restart healthy at **106 s**.
  Outages now capped at ~30 s. New behaviour to expect: weewx *blocks* rather than erroring, and such
  a stall is indistinguishable from a DEC-0067 freeze to `freeze_watch.sh` — excluded correctly by
  `campaign_analyze.py`, not a bug to chase.
- **WAL is the real fix and is blocked cross-repo — filed ops#141.** `hyperlocal-forecast-api` binds
  the archive DB as a single *file*, so WAL's `-wal`/`-shm` siblings can never appear beside it. An
  initial reading that the mount would also need to become *writable* was **tested and disproved** on
  the container's own SQLite 3.46.1: read-only directory mounts work with `-shm` present or absent;
  only the single-file case fails, and it fails as `no such table`, not as stale data. So `RW=false`
  stays and no HLF code changes.
- **`CONSTANTS.md` gains a live-config deviations table.** `weewx.conf` is the mounted layer and is
  never committed, so `timeout = 30` exists only on the NAS with no CI and no diff — a stock
  container recreate would silently revert it.
- **Guard finding (belongs to ops):** the NAS mutation that wrote live prod config **did not trip the
  Class C guard** — `ssh <nas> "python3 -" < script` hides the mutation in stdin while the guard
  matches the command string, and that is the batching shape CONVENTIONS recommends. Meanwhile the
  *read* guard fired three times on `grep`/`tail` against files carrying no secrets. Owner-authorized
  in chat, so nothing improper — but the mechanism didn't enforce it.
- **Corrects DEC-0067's reader list:** it named "the dashboard" as an archive-DB reader. Scanning
  every container that mounts a weewx path finds only `hyperlocal-forecast-api`, `eh-proxy` (parent
  dir, read-only), and weewx itself.
- **WAL tried and ROLLED BACK (DEC-0071) — with a self-inflicted ~6 min prod outage.** HLF shipped
  the directory mount (ops#141), WAL went live 06:56 EDT, and hyperlocal-forecast **froze on a stale
  snapshot within minutes**. Two blockers, both missed: a Docker `:ro` bind makes the **files**
  read-only, and DEC-0070's own test only chmod'd the *directory*, so it never reproduced that —
  structurally blind, DEC-0035's lesson recurring; and SQLite creates `weewx.sdb-wal` mode **0555**,
  so even a read-write mount leaves a non-root reader unable to write it.
- **Rolling back was the hard part.** `PRAGMA journal_mode=DELETE` needs an exclusive lock that
  weewx's persistent connection denies, and with the container stopped there's no `docker exec`
  either. Resolved by letting weewx apply it: `[[[pragmas]]] journal_mode = DELETE`, kept in place so
  the mode is re-pinned on every start. **That pragma was first written as a scalar** — weedb wants a
  mapping, so it raised `TypeError: string indices must be integers` and crash-looped weewxd
  (CRITICALs 07:18:58, 07:20:22) until the subsection form landed at 07:24.
- **Process failures worth naming:** the first rollback attempt opened with a `SELECT COUNT(*)` that
  had *already* timed out earlier the same session, and the config shape was assumed from the field
  name rather than checked against the consumer whose source had been read an hour before. Two of
  three failures repeated lessons already written down in this repo.
- **Net:** WAL is not viable as scoped; `timeout = 30` is the fix, not an interim, and delivers most
  of WAL's practical benefit. weewx healthy and current. **hyperlocal-forecast is still stale and
  needs a container restart by an HLF session** — reported on ops#141, relabelled `repo:hlf`.
- **Branch hygiene:** nine merged S62–S66 feature branches deleted (local + remote), restoring the
  `dev` + `main` steady state CONSTANTS.md specifies. Every one verified contained in `dev` first;
  `main` deliberately untouched. BOOT.md's "stale branch still exists, harmless" row retired with it.

---
## [S65] — 2026-08-04 — Freeze-watcher fixed (parallel reads, dedup bug, local notification); two freezes caught, one tied to coffee-radar's scheduled run

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
- **Freeze #1 (17:48:59–17:52:37 EDT, ~4 min):** every thread read `S` throughout except three
  isolated moments where a single `rtldavis` worker thread went `R`; `weewxd`'s main thread and all
  four REST-uploader threads stayed `S` the entire time. Still no `D`. **Coffee-radar was not
  running and loadavg was normal (0.3–0.7)** — no shared-NAS signature on this one.
- **Freeze #2 (19:13:43–19:15:41 EDT, ~2 min): loadavg spiked to 12.39, and coffee-radar was
  confirmed running the entire time** — checked at the owner's request, since this NAS also runs
  hyperlocal-forecast and coffee-radar. `nasctl inspect` showed image `coffee-radar` on a
  Docker-auto-named container (`dreamy_merkle` — its scheduled command never passes `--name`, which
  is why every earlier `docker ps` name-string check missed it), started **19:00:16 EDT**, 13m27s
  before detection. That start time lines up almost exactly with coffee-radar's documented 19:00
  daily run — its schedule is **local time (EDT), not UTC**, a unit mismatch in this session's own
  earlier comparison. `pid=30506 (rtldavis)` read `R` in *both* 20s-apart samples this time
  (continuously runnable, not a single blip) — more consistent with CPU contention than the brief
  ticks seen elsewhere. `weewxd`'s main thread still read `S` throughout, never `D`.
- **Net read: coffee-radar likely contributes to some freezes, not all.** Freeze #1, the same
  night, shows the identical symptom with neither coffee-radar running nor elevated load — so it
  isn't the sole cause. A general NAS-wide stall stays ruled out (S63/DEC-0067); this is narrower.
  Re-checking the 4 historical freeze timestamps against coffee-radar's now-corrected local-time
  schedule still shows no clean match, but that comparison is weaker evidence than tonight's direct
  `docker ps`/`inspect` observation, and DSM's own coffee-radar run history (if it logs one) hasn't
  been checked yet. `nasctl ps` is captured on every future catch, at no extra cost.
- **The overnight run finished at its 15h deadline with exactly one catch** — the coffee-radar one
  above; no third freeze materialized. `docs/ROADMAP.md`'s P0 freeze item updated to match.
- **DEC-0068 accepted**, capturing this finding as the settled (if partial) record: coffee-radar is
  a confirmed contributor to some freezes, not a full explanation. n=1 correlated of 3 total
  detailed captures — not a base rate. Full body: `docs/DECISIONS-FULL.md`.
- **`ops/freeze_watch.sh` committed** — third time this watcher was rebuilt from session-transcript
  archaeology (S63, S64, S65); no reason for a fourth. Also fixed a real bug found while writing
  this up: its coffee-radar-presence check grepped container *names* via `nasctl ps`, but a one-shot
  container run without `--name` (coffee-radar's own scheduled command) never gets one, so the check
  could never have matched — now greps the whole `nasctl ps` line, catching the `IMAGE` column too.
  `MANIFEST.md` gains a row.
- **Priority shifts off freeze-chasing.** Root cause isn't fully explained, but campaign B doesn't
  need it to be — its two real remaining gates (make the metric freeze-aware, fix the DB lock) are
  unchanged by this finding and are next.

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
