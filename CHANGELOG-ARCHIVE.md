# Changelog Archive — weewx-rtldavis

**Append-only archive · read on demand (DEC-0030).** Older session entries moved here **verbatim**
from `CHANGELOG.md`, which keeps only the last ~3 sessions live (the Tier 1 session read). Same
format: most recent first, session-tagged (`[S16]`, `[S17]`, …), release tags called out inline.
Nothing here is rewritten — text moves, history stays greppable.

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

---
## [S62] — 2026-08-02 — A 105-minute receiver outage (ERR-0005), the follow-ups it earned, and campaign B moved up 4 days

Incident session. Prod went deaf at 00:05 and came back at 01:50; the rest of the day was spent on
what that exposed.

- **ERR-0005 — the outage.** Not one gap but **two**, separated by brief islands of reception:
  00:05:05→00:07:26, an ~56 s island at **71%**, then **00:08:22→01:23:56** (1 h 15 m), a ~36 s
  island, then 01:24:32→01:50:13. ~102 one-minute archive records missing. No correction applied —
  an honest gap, nothing to null. **WeatherLink Live backfill approved, not yet applied** (~7
  records at `interval = 15`, ERR-0003's path).
- **What actually fixed it: a full container recreate.** The LNA was already physically out and
  reception stayed at zero; `kill`→`rm`→`run` at 01:48 restored it. Nine USB resets and ~18 driver
  respawns had done nothing. **Root cause of the original fault remains unestablished** — 12 h of
  clean running since says the recreate cleared it, not what it was.
- **The watchdog made it worse, and now escalates instead (DEC-0065).** Measured: 9 resets, 0
  effective, 17 emails in 80 minutes, and not one distinguishing the 9th attempt from the 1st;
  reset #10 preceded a strictly worse failure mode by 46 s. **Detection was never the deficiency**
  — RECEPTION ALERT fired correctly 8 minutes in. Now: each reset is judged by whether reception
  recovered, 3 ineffective ones stop the loop and escalate **once** with a `docker inspect`-derived
  recreate command (secret env values redacted), and `rtldavis process is not running` never
  triggers a reset at all. Escalation lands ~18 min in — for ERR-0005, ~00:29 instead of 01:27.
  **Auto-recreate deliberately not built:** n=1 and unexplained, against the owner's own
  "proven fix" bar. 14 tests, including a replay of the incident's shape.
- **The driver threw away the evidence.** `logerr("err: %s" % self._mgr.get_stderr())` formatted a
  *generator's repr* — and iterating it would not have helped, since that generator is gated on
  `running()` and yields nothing once the process is dead. New `drain_stderr()`; 6 tests pin both
  layers. Driver → **`0.20+ws.4`**.
- **The DEC-0031 canary had silently stopped checking.** `ops/soak_check.sh` grepped a hardcoded
  `0.20+ws.1` and degraded to a soft `note` on mismatch, so from **v2.0.10 onward** it verified
  nothing and "wrong version" was indistinguishable from "banner not in window". Now reports the
  version actually announced, three distinct states, mismatch is a **FAIL**.
- **Abort near-miss investigated and cleared.** The campaign-A abort at 00:08:21 looked like a
  DEC-0061 repeat (loop data flowing at 71%) but was **correct**: `health_ok()` waits for an
  *archive* record, last was 00:04:20 and next 01:24:24. RapidFire publications are not archive
  records. Campaign B is not gated on it.
- **Campaign B prepared to launch 08-03, then HELD (DEC-0066).** Schedule shifted −4 days (pure
  constant offset; Latin square preserved by construction), v2.0.12 built and all four `BIAS_TEE`
  branches verified, apparatus green. Held after **two further outages the same day**: a 3-minute
  dropout at 13:47 (**unexplained** — no engine shutdown, no DB error, driver never faulted) and a
  10-minute outage at 19:45. The decisive argument is not abort risk but **instrument trust**: B
  measures reception, and a receiver intermittently losing 50–100% of packets for unexplained
  reasons yields noise shaped like a result. **Design unchanged; only timing.** ⚠️ The schedule
  literals now sit in the **past** — regenerate before any `install`, or `due_arm()` jumps straight
  into the middle of the square.
- **`database is locked` is a thread now, not a one-off.** It caused the 19:45 outage on its own,
  with no restart churn in front of it — this session first called those errors "downstream noise"
  and was **wrong**. The lock is momentary; what made it a 10-minute outage is that
  **OgoxeUploader, Influx and OWM all refused to shut down**, holding the teardown ~100 s with the
  driver killed. Any future DB hiccup does the same.
- **First honest no-LNA telemetry accruing:** n=1106 windows at gain 372, mean **72.0%**, **no
  hour-07 notch** (S58 measured ~2 pts LNA-in). Campaign A pooled 72.4% — but A pools the gain-207
  arms and is biased low, so this is **not** parity and **not** adoption evidence.
- **Versioning documented** after the owner asked what `ws` stands for — an expansion that appeared
  **nowhere in the repo**. New README §Versioning: image version vs driver version, `ws` =
  WeatheredScientist, per-file counters, and why we never renumber into upstream's space. Also
  fixed a README that still advertised **v2.0.9** as current, three releases stale.

---
## [S61] — 2026-08-01 — Campaign B designed end to end (DEC-0064): owner-gated swap night, overnight pilot, no-LNA square

Design session (owner-escalated). Nothing deployed; everything staged for the 08-06/08-07 window.

- **DEC-0064 — campaign B pre-registered end to end**, so the swap night is execution, not
  derivation. Swap sequence is **owner-gated**: nothing touches the container or bias tee until an
  in-chat GO with the owner physically at the dongle — the antenna-disconnected window is the
  20–40 s SMA swap. Checklist: **`docs/CAMPAIGN-B-RUNBOOK.md`** (new, + MANIFEST row).
- **`ops/rx_experiment.sh` rewritten for campaign B:** overnight pilot 08-07 00:35–04:20 (gain-only,
  45 min/arm, HIGH→LOW 496/449/402/372/328 — pre-registered as arm-selection input only; an abort
  = the cliff found with high arms already harvested), **H hold** (arm-A settings under their own
  harvest tag, Friday daylong baseline window), square 08-08→08-16 at gain **{372, 496}** × ex
  {0, 50} (372 = cross-campaign anchor; `-fc/-ppm 0` unchanged from A to keep the LNA contrast
  clean), abort floor 55→**50%**. Tests extended to 13 (pilot structure, hold placement, square
  balance); **full DRY_RUN pass** exercised every phase incl. guard trip/settle and sticky STOP.
- **v2.0.12 prepped:** `entrypoint.sh` gains a `BIAS_TEE` env (default 1 — published image
  unchanged for existing users; the off branch drives `rtl_biast -b 0` explicitly), Dockerfile +
  `soak_check.sh` bumped. Carries DEC-0062's deferred redaction; landing *between* campaigns means
  B runs uniformly on one image. Build+push Thu 08-06; deploy on the swap night with
  `-e BIAS_TEE=0`.
- **Archive forensics replaced the assumed no-LNA baseline.** A cold-backup copy of the archive
  shows two flat `rxCheckPercent` plateaus — Jun 2–18 **67.45** (sd 3.22, gain 207) and Jul 5–27
  **74.83** (sd 4.13, gain 372) — with the transition hidden in the metric-dark gap. Owner
  confirmed **the LNA was IN during June**: S29's "pre-LNA baseline" label was wrong, honest no-LNA
  telemetry does not exist, and Friday's pilot is the first real measurement. Bonus: both plateaus
  being LNA-in makes their contrast a same-hardware gain comparison — **207→372 = +7.4 pts**,
  retroactively corroborating DEC-0017 in 372's favor (uncontrolled, directional only).
- **Campaign A untouched and healthy** — block 12 (arm B) live at 18:07, 12 swaps clean, zero
  aborts; co-rejection watch still 0 hits. Partial results deliberately not read.
- [ops#126](https://github.com/WeatheredScientist/eaglehunt-ops/issues/126) closed — the citation
  fix had already landed in S59; only the tracker was stale.
- Overdue CHANGELOG roll executed: S54–S58 moved verbatim to `CHANGELOG-ARCHIVE.md` (the live file
  had grown to 7 sessions against the ~3 guideline).

---
## [S60] — 2026-08-01 — DEC-0063 executed: session-start context cut 72% (~25.5K → ~7.2K tokens)

- **Migrated to the ops session-context tiering standard.** `BOOT.md` + `CONSTANTS.md` +
  `MANIFEST.md` are now the entire session-start read; `ARCHIVE/` is never in the load path.
  Measured: always-load went **91,806 B (~25.5K tok) across six files → 25,819 B (~7.2K) across
  four** — a **72% cut**, at the optimistic end of DEC-0063's ~19K estimate. `BOOT.md` landed at
  **2,493 tokens against its ~2,500 cap**.
- **`docs/STATUS.md` is retired.** It did not fit in `BOOT.md` and forcing it would have blown the
  cap, so its content distributed by kind: live bench state → `BOOT.md`; open threads and
  housekeeping → `BACKLOG.md` verbatim; the four upstream threads → a new
  `docs/UPSTREAM-THREADS.md`. Resolved items collapsed to one-line pointers. Deleted rather than
  archived — git history preserves it, and a second copy is what rule 5 exists to prevent.
- **The hook was verified before the delete, not after.** STANDARD §5's hazard is that a `BOOT.md`
  matching no marker shape goes *silently* quiet — the DEC-0106 shape, not wrong output but no
  output. `resume_pointer_for()` was run while `docs/STATUS.md` still existed (returned source
  `BOOT.md`), and again afterward. Both passed.
- **The shared archiver matched a different set of files than ops#130 predicted.** It matches
  *date-stamped* names, so it found three unlisted pre-governance root artifacts and did **not**
  match the three `docs/handoffs/S3x-*.md` files ops#130 named — those are session-numbered. The
  root three were unreferenced and got archived; the handoffs are cited by path from two live docs
  and stayed put with `MANIFEST.md` rows. Moving them would have broken three live citations to
  satisfy a rule about a load path they were never in.
- **A third copy of the broken validation-gate list turned up in `AGENTS.md`**, still naming
  `ruff-format` — the command DEC-0027 exists to reject. S59b fixed `CLAUDE.md`'s copy; S43 fixed
  `.pre-commit-config.yaml`'s. Three copies, three independent drifts. All now point at the single
  list in `docs/CONVENTIONS.md`. `CLAUDE.md`'s duplicated infra table went the same way — it had
  already gone stale on the reception baseline and on the driver-vs-config layer table.
- **A second public-repo divergence: `ARCHIVE/` stays uncommitted.** STANDARD rule 3 has retired
  material live in the repo under `ARCHIVE/`. Here it can't: the directory was already gitignored,
  its three files had **never been tracked**, and a scan found **IP- and credential-shaped strings
  in two of them** — pre-governance conversation dumps written before this repo had any secret
  hygiene. Committing them would violate DEC-0012. `MANIFEST.md` now says this at the top of its
  `ARCHIVE/` section, because the alternative is a manifest pointing a fresh cloner at files their
  clone does not contain — the same dead-end-for-external-contributors problem DEC-0063 already
  called out once. **For a public repo, git history is the archive.** Nothing was lost; retired
  repo content is reachable with `git log --follow`.
- **Both divergences share one root cause**, worth stating for ops: the standard's two
  "preserve-or-share by pointing at a file" mechanisms — `ops/CONSTANTS.md` and `ARCHIVE/` — each
  assume every reader has access that the public member's readers do not.
- **`docs/ASSESSMENT.md` deliberately left alone.** It still describes STATUS.md as the source of
  truth, and it is a *dated audit artifact* — rewriting it to match today would destroy the record
  of what was true then. Flagged in its `MANIFEST.md` row instead.
- Gates: pytest **125 passed**, mypy clean on 33 files, secret gate positive-controlled. Hook
  resume-pointer verified live.

---
## [S59b] — 2026-08-01 — the documented validation gates now actually run

- **Three of the four commands under CONVENTIONS §"Python / validation" failed when followed
  literally, and one of them damaged the tree.** Found while running the S59 closeout green gate —
  the gate list had never been executed verbatim.
- **`ruff format` was listed as a required gate, and DEC-0027 exists specifically to reject it.**
  Running it as documented reformats **30 of 33 files**, against the deliberate column alignment
  that decision protects. The identical contradiction reached `.pre-commit-config.yaml` and was
  removed there at S43 — *this line was the surviving copy*, still instructing the reader to run it
  for two years of sessions. Now marked do-not-run with the reason attached.
- **The interpreter guidance pointed at two dead ends.** The doc said "on the macOS dev box the
  interpreter is `python3` — there is no bare `python`." Both halves are wrong: a bare `python`
  does exist (pyenv shim, 3.12.12), and **neither it nor `python3` (Homebrew 3.14) carries pytest,
  mypy or ruff at all**. `python3 -m pytest` returns `No module named pytest`. `.venv/bin/python`
  is the only interpreter on this box with the tooling; all three commands now spell it out.
- **mypy needed arguments the doc never supplied.** This repo has no mypy config of any kind (no
  `pyproject.toml`, no `mypy.ini`, no `setup.cfg` — only `ruff.toml`), so a bare `python -m mypy`
  exits `Missing target module, package, files, or command`. Documented with the flags
  `.pre-commit-config.yaml` actually passes plus an explicit file list, which reproduces CI locally.
- **Secret-gate note sharpened on the same parenthetical.** It said the gate "passes cleanly with no
  staged files rather than erroring" — true, and a trap: a clean pass (silent, exit 0) and
  `SECRET-SCAN: nothing to scan` (exit 0, scanned *nothing*) are indistinguishable by exit code.
  Now says to stage first and positive-control any clean result (DEC-0039/DEC-0045).
- Every command verified as written before committing: `ruff check` passes, pytest **125 passed**,
  mypy clean on 33 files with `.mypy_cache` cleared, and `ruff format --check` confirms the
  30-of-33 figure rather than it being inferred.
- **The lesson, which is the reusable part:** a documented command that nobody runs verbatim decays
  exactly like a doc's prose claims do (dash DEC-0104), except it fails *loudly* the first time
  someone follows it — or, in `ruff format`'s case, succeeds destructively. Worth running a doc's
  own gate list literally when touching it.

---
## [S59] — 2026-08-01 — #74 watch closed on evidence; ops#126 citation fixed; ops#130 answered ADOPT (DEC-0063)

- **Issue #74's calm-windDir watch is CLOSED.** The v2.0.9 fix is confirmed on air: **zero**
  `windDir expired` WARNINGs across five consecutive days (07-28 … 08-01) against a prior base rate
  of ~1/hr. Checked with a **positive control** — the same grep returns **21 hits** in the 07-27 log,
  so the pattern still matches and the zero is real, not a false zero from the `nasctl grep`
  multi-word gotcha. STATUS's standing-watch list and ROADMAP's P1 watch line both updated (DEC-0057
  step 5). **No DEC for this item specifically** — closing a watch against a criterion agreed when
  the watch was opened is not a new design call. (DEC-0063 below is this session's one DEC, and it
  is about ops#130.)
- **[ops#126](https://github.com/WeatheredScientist/eaglehunt-ops/issues/126) fixed** — after
  eaglehunt-ops suffixed three re-issued decision IDs, one citation here resolved to the wrong
  decision. `DECISIONS-FULL.md` (DEC-0052 body) now reads `locked OPS-DEC-0019b`, the
  CLOSEOUT-TEMPLATE lock. Independently re-verified that this repo's other three `OPS-DEC-0019`
  references (CHANGELOG-ARCHIVE, S45/S46) all mean the **first** use — the env-twin rollout — and
  correctly stay bare. No `OPS-DEC-0020`/`0021` citations exist here.
- **Campaign A untouched and healthy** — 10 of 32 blocks harvested, block 11 (arm A) live, 11/11
  swaps healthy, zero aborts, completes ~08-07 00:05. Partial results deliberately not read.
- **One unscheduled restart logged, not chased.** `weewxd CRITICAL Database OperationalError
  exception: database is locked` at 15:08:22 on 08-01; weewx waited its built-in 2 minutes,
  re-initialized cleanly at 15:10:22, and resumed publishing (verified 15:43). First of the live
  campaign. Recorded because the campaign's settle rule drops samples after a *swap*, not after an
  unscheduled restart, so block 11 carries a small unmasked transient.
- Also corrected in passing: STATUS.md's header still said "Current session: S57" two sessions on,
  and its handoff heading said "S57 done → S58". Both reconciled. Documented that
  `ops/rx_experiment.sh status` is **not** a `nasctl` verb, and that `rx_experiment.log` was never
  rotated — it still carries the aborted 07-29 run, which inflates a naive swap count by 2 blocks.
- **[ops#130](https://github.com/WeatheredScientist/eaglehunt-ops/issues/130) answered: ADOPT the
  session-context tiering standard (DEC-0063)** — against that issue's own recommendation to defer.
  ops filed it saying "the case here is genuinely weak," on the basis that this repo is the leanest
  in the forum at ~21K and migration buys "maybe 6–8K tokens." Checking the premise rather than the
  offer: the tree is at **~25.5K, not ~21K** (ops measured a tree two session-closes stale); the
  saving is **~19K, not 6–8K** (`CHANGELOG.md` + the `DECISIONS.md` index leaving always-load is
  ~12.2K by itself — more than ops's quoted total, an internal inconsistency in the issue); and
  decisively, Tier-1 measured at four consecutive merge points grows **~1.1K tokens per session
  close**, structurally, because DEC-0052's closeout steps 2 and 3 append to STATUS and CHANGELOG
  every time. "Leanest in the forum" is a statement about a moment, not a trajectory. Both siblings
  have already migrated; this repo was the last of the trio.
- **A spec gap found and NOT resolved unilaterally.** STANDARD.md §3 has the trio load
  `ops/CONSTANTS.md` at session start, and separately says this repo may point at ops but never
  quote it. Those clauses conflict here: **ops is private and this repo is public**, so a
  `CLAUDE.md` telling its reader to load `ops/CONSTANTS.md` is a dead end for every external
  contributor — the population this repo has and the other three do not. This repo's `CONSTANTS.md`
  will be self-sufficient for anyone who can clone it (closer to coffeeradar's DEC-0017 posture),
  with any ops reference marked an owner-only supplement. Filed back to ops rather than edited into
  their file — read-only across the boundary.
- **The migration itself is a work order for S60, not done here.** STANDARD §7 wants migration at a
  session end with full state in context, which this was; it was still wrong to start, because the
  session stood at **~157K absolute context** against AGENT-ECONOMY §7's ~200K ceiling and the
  mechanical work is ~40K more. A half-applied migration leaves two contradictory entrypoints and a
  hook choosing between them by fallback order. Decision taken where the state was; execution
  written down as seven numbered steps in STATUS.md.
- Gates: pytest **125 passed**, mypy clean on 33 files (`.mypy_cache` cleared first, per CONVENTIONS).

---

## [S58] — 2026-08-01 — campaign A tracking clean (9/32 blocks); a site RF notch characterized, DEC-0059's diurnal claim amended

- **Campaign A healthy, no intervention.** 9 of 32 blocks harvested, 9/9 swaps healthy, zero aborts;
  prod untouched apart from the arms cycling in the mounted `weewx.conf`. **Both main effects are
  flat**: gain 207 vs 372 = **−0.1 pts (±0.36 SE)**, ex 50 vs ex 0 = **−0.1 (±0.36)**, against
  DEC-0059's ≥2.0-point adoption bar. The apparent −1.2 pt gain effect visible on day 1 dissolved as
  blocks accumulated — which is precisely why the design pre-registers 8 blocks/arm instead of
  letting anyone read day 1.
- **Site RF notch characterized** (BACKLOG §Durable RF findings). Reception dips ~2 pts at **hour 07
  and hour 19**, reproducibly, and **predates the campaign** — so it belongs to the site, not to any
  arm. Corroborated by two independent metrics (the monitor's 26% sample and the archive's
  `rxCheckPercent` min of **4.9%** in the same minute). Three candidate explanations were tested
  against the station's own weather archive and **falsified**: dew (the dewiest hours have the
  *best* reception), solar noise (radiation peaks midday where reception is fine), and wind (the
  deepest notch fell on a zero-wind morning).
- **`freqError` thermal drift measured on our own hardware** — ~2400–2600 at 65–69 °F falling to
  ~900–1200 at 77–84 °F. Real and cleanly temperature-linked, but **not** the notch's mechanism:
  hour 06 pairs the highest freqError with excellent reception, so the AFC is absorbing it.
- **DEC-0059 amended**: its "no detectable diurnal cycle" holds at 6-hour resolution and fails at
  hourly. The notch is small enough to sit inside the quoted 70–75 band, which is how it was missed,
  but it repeats daily. No effect on campaign validity — the Latin square balances any time-of-day
  term across all four arms.

---
## [S57b] — 2026-07-29 — campaign A aborted after 80 min; two defects fixed (DEC-0061), schedule regenerated, re-armed

- **Campaign A aborted 12:13 EDT in its third block.** The safety model worked: baseline snapshot
  restored, sticky STOP sentinel set, prod left healthy on `gain 372` — verified. The one thing it
  failed to do was tell anyone.
- **Defect 1 — the health check was too small by construction.** `health_ok` allowed ~90s for a new
  archive record after a restart, but a restart needs boot (~25s) + up to a full 60s archive
  interval + ~30s write lag ≈ **115s worst case**. Measured on the failure: `weewxd` init 12:11:46,
  first record 12:13:30, abort fired 12:13:27 — **three seconds early**. Arm B had won the same coin
  flip 80 minutes before. Now `HEALTH_TRIES=36` (~180s), and the test asserts the *arithmetic*
  rather than the literal, so lowering it fails with the reason attached.
- **Defect 2 — every alert this script could send was inert.** `send_mail` sourced `monitor.env`
  without exporting, so its `python3` child saw nothing and died on `KeyError: 'ALERT_FROM'`. True
  since the file was written; never disproved because no alert had ever fired. Extracted
  `load_env()` (`set -a`/`set +a`), tested against a real child process, mutation-verified. Confirmed
  live against the real `monitor.env` after deploy (booleans only, never values) — all `True`.
- **Schedule regenerated for a 2026-07-30 start** (completes 08-07). The 07-29 run lost `A@00:05`,
  took a partial `B@06:05` and lost `C@12:05` — three damaged Latin-square cells, the exact
  time-of-day confound the design exists to remove. ~10h of delay bought a valid experiment.
- **Re-armed:** fixed script deployed (sha `88c1aeaf…`, byte-verified against the merged `dev` tip),
  stale state reset to `NONE` (otherwise the first tick would have harvested a baseline-config period
  and recorded it as arm-B data), STOP cleared, the aborted run's 88 samples rotated aside. Campaign
  starts itself at 00:05.
- Also corrected a comment promising a `schedule --generate <date>` mode that **has never existed**;
  the dev-side recipe that actually produces the table is recorded in its place.
- Gates: pytest **123 passed** (was 120), mypy clean. See DEC-0061.
- **Credential redacted from a startup log line (DEC-0062).** `pressure_service.py` logged
  `api_key[:8]` at INFO on every restart, into `weewx.log` and its 30 rotations. The point isn't the
  8 characters — it's that **DEC-0047's read-guard covers configs, not logs**, so the most routine
  operation in this repo (tail the log to confirm a restart was clean) walks past the guard into an
  agent transcript. It did, twice, on 2026-07-29. Now logs `present`/`MISSING` with the flags
  resolved into locals *before* the call, so no credential attribute appears in a log argument at
  all — guarded by an AST test with a positive control. **The file is BAKED (`Dockerfile:117`), not
  mounted as first assumed** — an `scp` would have been a silent no-op (DEC-0031), caught only by
  actually asking DEC-0046's "which layer wins in prod?". **Deploy deliberately deferred to the next
  image release:** rebuilding restarts prod, and swapping the image under a running 8-day factorial
  would confound its arms. pytest **125 passed**, mypy clean on 33 files.

---
## [S57] — 2026-07-29 — Phase 0 confirms FreqError telemetry (DEC-0060); RX campaign A deployed and running

- **Phase 0 answered:** `FreqError` telemetry exists in the deployed driver — confirmed within 13s
  of a restart (`Hop: {ChannelIdx:0 ChannelFreq:902419338 FreqError:0 Transmitter:0}`). Getting
  there took a real correction: the first attempt (`debug_rtld=2` alone, ~19:11 EDT 07-28) produced
  zero evidence for ~7h because the live `[Logging][[[user]]]` logger was at `INFO`, independent of
  `debug_rtld` — `dbg_rtld()` calls `log.debug()`, silently dropped regardless of verbosity. Fixed
  with a scoped `[[[user.rtldavis]]]` DEBUG logger entry (DEC-0060), not the broader `[[[user]]]`.
  Both changes fully reverted once confirmed (09:34 EDT 07-29). Honest tally: elevated-debug window
  ran ~14.5h against a planned 3h (a session gap), `weewx.log` grew to ~8.8 MB vs. a normal
  ~4 MB/day — non-critical, but a real DEC-0041 bloat instance. `ppm`/`fc` measurement-by-value
  deliberately deferred, not blocking the campaign.
- **`ops/rx_experiment.sh` deployed and running.** Scp'd to the NAS project root (sha-verified),
  `install` run (baseline snapshotted). Owner created the two DSM Task Scheduler entries (`tick`,
  `guard`, 5 min, root); first automatic tick swapped to arm B (gain 207, `-ex 0`) at 10:52:37 EDT.
  Campaign A runs unattended for 8 days, self-terminating to baseline (~2026-08-06 expected).
- **DEC-0059 status updated** (deployed/running, was design-only) and **DEC-0060 added** (the
  logger-level gotcha, so it isn't re-derived next time debug output is needed). ROADMAP.md P2
  section reconciled: Phase 0 checked off, campaign A marked running, the "rebuild for FreqError
  telemetry" item closed as moot (the current binary already has it).
- **Cross-repo:** [ops#112](https://github.com/WeatheredScientist/eaglehunt-ops/issues/112) closed
  with the full finding; [ops#114](https://github.com/WeatheredScientist/eaglehunt-ops/issues/114)
  tracks the running campaign; [ops#113](https://github.com/WeatheredScientist/eaglehunt-ops/issues/113)
  (the transient-state tracking proposal, filed this session) was independently built and closed by
  ops the same day — worth adopting `.claude/transient-state` here for future transient prod state.

---
## [S56d] — 2026-07-28 — S56 closeout

- Handoff rewritten so S57 opens on the three RX items in order (Phase 0 → deploy → regenerate the
  schedule if the start date slipped), with the standing watches demoted below them.
- Docs diet (DEC-0030): `[S53]` rolled verbatim to `CHANGELOG-ARCHIVE.md`; entries here now run
  S54–S56, and the S56 entries were **reordered newest-first** — they had landed S56, S56c, S56b,
  contradicting this file's own "most recent first" rule.

---

## [S56c] — 2026-07-28 — the RX experiment gets an apparatus (DEC-0059); 7 dead sweep scripts deleted

Design + tooling only — **nothing deployed, prod untouched** (still v2.0.11, gain 372).

- **`-ex N` ≡ `receiveWindow 300+N`** — upstream sums them and `receiveWindow` appears nowhere else,
  so the window axis is a mounted-config knob and **no arm of the experiment needs an image
  rebuild**. The `rw250/rw350/rw400` images were redundant, not just misnamed (DEC-0048). Read from
  upstream master; the deployed binary is older and unverified directly — caveat recorded.
- **Measured baseline replaces "~67–70%"**: 447 samples → **73.3%, sd 4.67**, autocorrelation ~0,
  no diurnal cycle. So 24 h/arm resolves 1.1 pts and DEC-0017's "1–2 weeks" was ~7× overkill.
- **`ops/rx_experiment.sh`** — Latin-square scheduler with literal-only arms, atomic verified writes,
  byte-exact whole-file revert, sticky STOP sentinel, self-termination to the production baseline,
  and a mailer independent of `weewx_monitor.py`. Verified end-to-end against fixtures.
- **`tests/test_rx_experiment.py`** (8 tests) — drives the real shell functions; includes a DEC-0045
  positive control proving the old global-regex approach corrupts the same fixture, and a machine
  check that the Latin square is balanced (mutation-tested: it goes red on a one-row typo).
- **Deleted all 7 pre-governance sweep scripts.** `gain_sweep.sh` and `fc_sweep.sh` counted
  `RAW_DATAPACKET_MATCH`, which prod no longer logs — they would have reported 0.0% for every arm
  and looked like they worked. `gain_sweep.sh` also used a 2.5 s denominator against our 2.8125 s
  ISS. The one durable finding living only in `fc_sweep.sh`'s header was moved to BACKLOG first.
- **DEC-0008's `set_gain.sh` exemplar superseded** — the kill/start codification moves to
  `restart_container()`; the rule itself is unchanged.
- Secret gate caught the test fixture's credential-shaped line; fixed the fixture, **not** the
  allow-list (DEC-0045).

---

## [S56b] — 2026-07-28 — ROADMAP.md split to P0–P3; long-term direction moves to BACKLOG.md (DEC-0058)

Same session, second act. Docs-only, nothing deployed.

- **STATION_NAME check:** before doing any work, live-verified the NAS `monitor.env` —
  `STATION_NAME="Eagle Hunt PWS"` was already set (since S31). BACKLOG.md's note was stale (dated
  "observed S27," pre-fix); corrected, no NAS mutation needed.
- **DEC-0058:** `docs/ROADMAP.md` trimmed to P0–P3 only (the actively-sequenced plan). P4 +
  "Longer horizon" (credential hygiene, multi-source adaptability, the template harvest, ops#110)
  moved to a new "Long-term direction" section in `BACKLOG.md` rather than a fourth document.
  `CLAUDE.md`'s doc-map annotated with the split.
- While editing `BACKLOG.md`, found and pruned a second stale copy of the already-resolved (S48)
  May rain-total item — same fact CHANGELOG `[S56]`'s ROADMAP pass had already corrected once, in
  the other file.
- **Self-caught bug:** the DEC-0057 append (`[S56]`, above) had matched an `old_string` that didn't
  include the file's true last line, stranding an orphaned original fragment (`*silently*.`) after
  everything inserted, and papering over it with an invented duplicate sentence. Fixed before
  appending DEC-0058: restored the original DEC-0056 closing line, removed the invented text.

---

## [S56] — 2026-07-28 — ROADMAP.md reconciled and restructured; DEC-0057 adds it to the closeout ritual

Docs-only, nothing deployed. Prompted by a routine status check that turned into an audit.

- Confirmed prod healthy on v2.0.11: co-rejecting grep 0 hits (positive-control-verified against a
  known-present pattern), ops#105 confirmed CLOSED. Found ops#110 newly opened (winter 2027
  sky-state instrumentation — IR sky sensor alongside the lightning detector; planning horizon
  only).
- **ROADMAP.md reconciliation pass:** found and fixed 5 items shown open that had already shipped —
  the `cleanup_backlog.md` fold-in (done S27), remote-URL-casing + stale-branch cleanup, P1.5's
  "deploy pending" (shipped v2.0.4, S34), the May rain-total reconciliation (done S48), and the
  README public-onboarding refresh.
- **Fuller restructure:** folded the old P1 ("false-rain fix") and P1.5 ("Sensor-QC hardening")
  sections into one continuous data-integrity arc that now actually covers what shipped since —
  v2.0.4 through v2.0.11 (sensor-QC filter, reception-metric fix, frame-level co-rejection, signed
  temp decode, cap-16 tuning) — previously unrepresented on the page entirely. Collapsed P0.5's
  mostly-done checklist to a pointer. Added the ops#110 item under Longer Horizon.
- **DEC-0057:** ROADMAP.md joins the closeout ritual as step 5 — same-session update whenever a DEC
  ships/closes/reprioritizes a line item — plus a "Keeping this current" tripwire inside
  ROADMAP.md itself (next full check due **by S66**). CLAUDE.md's closeout steps renumbered
  (5→6 model-tier restore, 6→7 commit+push).

---

## [S55c] — 2026-07-28 — v2.0.11 shipped: cap 16 live in prod; ops#105 audit closed from this side

Third act of the day, owner-approved after the ops relay flagged the gap: DEC-0056's cap was merged
but inert (the driver is baked, DEC-0031 — v2.0.10 was built before PR #93). Released same-day so
R2 actually protects the station.

- **Release:** `DRIVER_VERSION` → **0.20+ws.3**, Dockerfile header → v2.0.11 (one PR this time,
  #95); promoted via #96 (merge `a4628769`); NAS build from the md5-verified tree (the build
  script's tree gate caught my own stale ws.2 assertion from the v2.0.10 template and refused to
  build until corrected — the check working as designed, on its author); pushed `:v2.0.11` +
  `:latest` (digest `sha256:b8f35f36…`); prod recreated 11:00 EDT; live-verified banner
  `0.20+ws.3`, sensor_qc active, records publishing, soak 13/2/0 (restart-window WARNs). Tagged
  **`prod-baseline-20260728b`**;
  [GitHub release v2.0.11](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.11).
  **Rollback: `:v2.0.10`.** Fifth consecutive clean recreate; no stall.
- **Monitor tripwire live end-to-end:** owner killed the old monitor 10:28, scheduler respawned it
  on the reframed code (sha-verified), startup email received, `--test-alert` fired through the
  new wording and received.
- **Prod moved v2.0.9 → v2.0.10 → v2.0.11 in one day** (R1 then R2), each with its own baseline
  tag and retained rollback.
- **ops#105: both code items (R1 + R2) now released, deployed, live-verified** — audit umbrella
  closeable from this repo's side
  ([completion note](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5105845282)).
- Docs: CONVENTIONS/CLAUDE quick-ref → v2.0.11 / `prod-baseline-20260728b` / rollback `:v2.0.10`;
  soak `EXPECT_IMAGE` default → `:v2.0.11`.

---

## [S55b] — 2026-07-28 — R2 decided and coded: `MAX_PLAUSIBLE_TIPS` 60 → 16 (DEC-0056), rejection email reframed as the tripwire

Same session, second act: the owner opened the R2 design discussion, an **evidence pass over the
full 70-day archive** settled it, and the owner approved the package (PR #93).

- **The evidence** (pre-correction backup, 95,901 minutes, 490 wet): worst real minute **7 tips**;
  worst real 3-min window **exactly 16** (2026-06-14 storm — still passes, the check is
  `delta > max_tips`); reception during rain never below 50%; in-service gaps near rain: two
  1-minute events ever; rain-counter rejections at cap 60 in the 30-day logs: **zero** (all five
  "implausible" hits are SensorQC wind/humidity). Physics: at the bucket's ~4 s/tip ceiling a
  genuine delta can exceed 16 only across a >64 s gap — longer than any gap observed during rain.
  **Reframing:** weewx `[StdQC]` (0.3 in/min) already discarded anything over 30 tips, so
  "60 → 16" really exposes only the never-occupied 17–30 band.
- **The worry that shaped the package** (owner: don't lose an intense storm to an over-tight
  filter): the change ships with the failure mode converted from silent-permanent to
  loud-bounded-recoverable — `weewx_monitor.py`'s existing DEC-0021 glitch email is reframed as
  the **DEC-0056 tripwire** (prompts the WeatherLink cross-check; a rejection on a wet day is the
  predefined revisit trigger), a **recovery playbook** is written into DEC-0056 (console
  reconciliation via the ERR process), and a **driver↔monitor marker contract test** pins the
  alert to the driver's exact wording. Confirm-on-reject documented as the designed escalation if
  the tripwire ever fires on real rain.
- Tests 111 → **112**: boundary 16-passes/17-rejects, the 06-14 evidence vectors, cap-60-era
  cases retuned as documented rejects; cap and marker assertions both **mutation-tested red**.
- **Deployment split:** the monitor (mounted layer) deployed NAS-side same session — scp'd from
  the merged tip, sha-verified `383f5baa…`, restarted via the scheduler respawn. The driver cap
  (baked layer, DEC-0031) **rides `dev` until the next image cut (v2.0.11)** — prod's running
  driver keeps cap 60 until then; a hardening, not a live bug, so it forces no deploy.
- R2 closed out on [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105).

---

## [S55] — 2026-07-28 — v2.0.10 shipped: the signed temperature decode is live in prod; upstream PR #23 opened

**The R1 release (DEC-0055), executed end-to-end** — prod ran the unsigned decode until 09:28 EDT.

- **Version bump first** ([#88](https://github.com/WeatheredScientist/weewx-rtldavis/pull/88)):
  `DRIVER_VERSION` 0.20+ws.1 → **0.20+ws.2** — the banner is the live-verify marker (DEC-0046), so
  a driver release must be distinguishable in the running log — plus the missing 2026-07-28
  DEC-0055 entry in the driver's header change list, README, and the CHANGES-FROM-UPSTREAM version
  table (`influx.py` stays ws.1, untouched). Dockerfile header → v2.0.10
  ([#90](https://github.com/WeatheredScientist/weewx-rtldavis/pull/90); every release since v2.0.6
  bumps it). Promoted dev → main (PRs #89 + #91, merge `2d3bc09a`), CI green throughout.
- **Built on the NAS from the verified tree** (S52 pattern: staged tarball → fresh
  `build-v2.0.10/`, with `rtldavis.py` md5-checked against `git show` before the build could
  start); pushed `:v2.0.10` + `:latest`, digest `sha256:ee3027e1…`. weewx stays pinned 5.4.0
  (#78) — no silent drift this rebuild.
- **Prod recreated** from the re-captured live inspect config (kill→rm→3 s→run; no mounted-layer
  changes this release — `loop_json_writer.py`/`influx.py` untouched since v2.0.9).
  **Live-verified (DEC-0046):** banner `0.20+ws.2`, `sensor_qc True`, records arriving, outTemp
  74.1 °F sane, soak **13 PASS / 2 WARN / 0 FAIL** (both WARNs restart artifacts). No startup
  stall — 4th consecutive clean recreate. Tagged **`prod-baseline-20260728`**;
  [GitHub release v2.0.10](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.10).
  **Rollback: `:v2.0.9`** on the NAS and Docker Hub.
- **Upstream [lheijst#23](https://github.com/lheijst/weewx-rtldavis/pull/23) opened**
  (owner-reviewed verbatim), companion to #22. Found while drafting: **upstream #19 (LloydR) had
  already diagnosed the sign bug** — its 16-bit-signed ÷16 form carries the `pkt[4]` flag nibble
  into the value (a constant +0.05 °F on digital frames) and lacks `0xFF8`; #23 credits the
  diagnosis and offers the masked 12-bit form as an alternative, non-stepping per #22's precedent.
- **R1 closed out on [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5104787452)**;
  **R2 untouched** (owner holds it for design discussion).
- Housekeeping: two stale `.claude/worktrees/` (+ their `claude/*` snapshot branches, 0 unique
  commits) removed; four merged `s54-*` branches deleted local + origin — the repo is back to
  exactly `dev` + `main`. Session-start watches: co-rejection 0 hits (positive-control-verified),
  #74 calm-windDir silent 10.6 h post-v2.0.9 (last WARNING 21:59, 19 min before that deploy),
  humidity largest step 0.7 pts in 240 new samples, soak 10/5/0 pre-release.
  `ops/soak_check.sh` `EXPECT_IMAGE` default → `:v2.0.10` (STATUS's standing instruction). No new
  DEC — the session executed DEC-0031/0038/0046/0055 as designed.

---

## [S54] — 2026-07-28 — R1 landed: outside-temperature decode is now signed two's complement (DEC-0055); not yet released

Owner approved **R1** from the S53 ops#105 audit; **R2** (`MAX_PLAUSIBLE_TIPS` 60 → 16) held for
further discussion and is untouched.

- **`rtldavis.py`** — the 12-bit digital temperature field is decoded as **two's complement**
  (`(temp_raw - 0x1000) / 10.0` when bit 11 is set), and `0xFF8` joins `0xFFC` as a no-sensor
  sentinel. Unsigned, a −5 °F reading decoded to 404.6 °F (207 °C), tripped the −40…65 °C SensorQC
  bounds, and — since v2.0.9 — **co-rejected the entire frame** (DEC-0054), so an ordinary cold
  snap would have nulled wind + payload every ~30–60 s and saturated the corruption alarm we are
  currently watching. Analog/thermistor branch untouched.
- **Deliberate one-LSB deviation from weewx-meteostick** (DEC-0055): its
  `-(temp_raw ^ 0xFFF)` is *one's* complement — 0.1 °F warm on every negative, maps `0xFFF` and
  `0x000` both to 0.0 °F, and flips the truncation bias at zero. Its two real contributions (the
  field is signed; the `0xFF8` sentinel) are adopted.
- **`tests/test_temp_twos_complement.py`** — 10 new tests: −40 °F frame, the `0xFFF` case that
  distinguishes this from meteostick, both sentinels, a DEC-0054 **co-rejection non-fire** sweep
  (−0.1…−39.9 °F), plus two positive controls (frame-builder round-trip; proof the bounds gate
  really fires on the old unsigned decode). All three plausible regressions **mutation-tested red**.
  Also fixed a real cross-module test-isolation trap: these suites share `sys.modules` and replace
  `weewx.wxformulas` wholesale, so the stub is now additive and resolved through `rtldavis.weewx`
  (the object the driver actually dereferences) rather than `sys.modules['weewx']`.
- **`CHANGES-FROM-UPSTREAM.md`** — two DEC-0034 fork-inventory gaps closed. DEC-0054 (frame-level
  co-rejection, shipped in v2.0.9 at S52) had never been recorded there and is now behavior
  change **11**. The `rtldavis.py` delta was **recounted against the real upstream baseline** —
  fetched from the same `weewx-contrib` `src.tgz` the Dockerfile builds from, which this repo does
  not vendor: **+477 / −88** (1422 → 1811 lines), replacing S37's **+263 / −51**. That figure was
  one commit stale the day it was written (it is the exact count at `cd49214`, and the S37 commit
  recording it also added the fork-identity header). The reproduce recipe now ships next to the
  number, so the next recount is a paste rather than an archaeology session.
- **Upstreaming table** — gained the temp-sign candidate (the prose already claimed 10 was part of
  the intended contribution), and two **stale statuses corrected**: it still read *"draft comment …
  not posted"* and *"not yet offered"* for work that has been live upstream since S38 —
  [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22) and
  [david-lutz#1](https://github.com/david-lutz/weewx-influx2/pull/1) are both OPEN, and the issue #15
  comment was posted 2026-07-13. The table was written at S37 and never re-read after the PRs landed.
- **Stray `0` file removed** from the repo root ([#86](https://github.com/WeatheredScientist/weewx-rtldavis/pull/86)) —
  a zero-byte artifact committed by accident in `5e3c3dd` (S41) alongside `ops/soak_check.sh`, a
  script dense with redirects; a stray `2>0` for `2>&1` is the likely mechanism. It landed as
  `0 | 0` and was never referenced: nothing redirects to it, the `Dockerfile` `COPY`s only named
  files (no root glob, so it never entered the image), and there is no packaging manifest to sweep
  it up. Tracked files 82 → 81.
- Gates: pytest **111 passed**, `ruff check` clean (0.5.7, DEC-0027), `mypy --ignore-missing-imports
  --no-strict-optional .` clean on 33 files.
- **Not released.** The driver is baked (DEC-0031) → needs an image rebuild + deliberate release,
  deadline **before first frost**. A companion upstream PR belongs alongside lheijst#22.

---

## [S53] — 2026-07-27/28 — ops#105 cross-observable QC audit delivered; archive swept CLEAN; temp sign bug found (no code)

The owner-directed audit ([ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105),
carry-forward of ops#103's "where else could this slip through") delivered as an
[issue comment](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5099627052).
Every encoding verified against `rtldavis.py` source (ops#103's *inferred* entries confirmed; its
"rain closed since 07-12" claim corrected — counter deltas ≤ 30 tips = 0.30 in still clear both
`MAX_PLAUSIBLE_TIPS = 60` and the 0.3 in StdQC cap, and a phantom is never reversed).

- **Historical-signature sweep (full archive 2026-05-19 → 07-27, 95,901 rows, pre-correction
  backup): CLEAN.** 13 gust-spike candidates all adjudicated genuine (storm outflow / breeze
  context) except ERR-0004 itself; temp spike-and-return zero ever; humidity spikes all
  pre-SensorQC (known DEC-0029 class); night radiation/UV zero; isolated rain zero. All 5
  rejection events in 31 days of logs cross-checked — sibling fields clean in the archive. **No
  new ERR entries.** Corroboration: ~722 dup frames/day × 1/65536 CRC-pass ≈ 1 in-bounds escape
  per ~90 days — matches the 1 observed in ~4 months.
- **NEW finding (R1, needs-design, pre-winter):** the temp decode is **unsigned**; Davis is two's
  complement (verified vs weewx-meteostick, which also handles a second `0xFF8` sentinel both our
  fork and upstream lack). First sub-0 °F morning → every temp frame decodes ~+400 °F →
  bounds-trips → **DEC-0054 co-rejects the whole frame** (wind + payload nulled, ERROR-pair log
  spam) for the duration of real cold weather. Inherited upstream bug, never fired only because
  the station hasn't seen winter.
- **Recommendations R1–R5** (temp sign fix; `MAX_PLAUSIBLE_TIPS` 60 → 16; wind residual
  accepted driver-side / spike guard is dashboard's; radiation night-ceiling noted-not-built;
  extra-station zero-QC docs note) — all awaiting design agreement, no code this session.
- **v2.0.9 first-days watch:** co-rejection 0 hits (first post-deploy hour); #74 WARNINGs present
  up to the 22:18 recreate, silent after (needs a full-day re-check); soak 15/0/0, reception 81 %;
  no stalls; humidity watch through 07-27 23:14 still unfired; no Dependabot PRs yet.

---

## [S52] — 2026-07-27 — ERR-0004 phantom 39 mph gust: corrected in both stores, frame-level co-rejection shipped as v2.0.9 (DEC-0054)

**The incident (ERR-0004):** at 14:55:50 EDT, during an rxCheckPercent collapse to 13.2%, one
multi-bit-corrupt-but-CRC-valid frame (DEC-0033 class) carried humidity decoding to 144.9% — rejected
by SensorQC bounds — *and* a wind byte decoding to 39 mph from dead calm, which passed (in-spec, and
+16.5 m/s sat under the 20 m/s delta cap). It became the archive interval's gust max and went out to
all ten external sinks. Owner spotted it on the dashboard hours later; dashboard S149 and an
eaglehunt-ops session had already filed [#76](https://github.com/WeatheredScientist/weewx-rtldavis/issues/76)
+ ops#103 with the diagnosis — independently re-verified here (log + code) before acting; every
claim held. Coordinated in real time on #76 (3 comments: pickup → correction landed → release).

- **Correction applied live, both stores, same session (DEC-0025/0032/0037):** archive row
  1785178560 → windSpeed/windDir/windGust/windGustDir/ET/appTemp/windrun all NULL (wview-extended
  schema carries the derived fields in-row), guarded UPDATE + `rebuild-daily`; InfluxDB point
  rewritten minus 7 wind-affected fields with sparse `windGust_qc=1`/`windSpeed_qc=1` (DEC-0099
  contract). Verified via the public /query proxy: day-max gust now a genuine 12 mph. Dashboard's
  ops#104 verification unblocked the same hour. Backup: `weewx.sdb.bak-err0004-20260727`.
- **DEC-0054 — frame-level co-rejection (v2.0.9):** a bounds failure on ANY field now nulls every
  weather field of that frame and skips the rain counter *without* resyncing its baseline; delta
  trips never co-reject. Zero free parameters — explicitly not the parked DEC-0044 coupling filter.
  6 new tests incl. a verbatim replay of the corrupt frame; the old test asserting same-frame
  humidity *survives* a wind bounds failure was inverted (it encoded exactly this gap).
- **Issue #74 closed (bundled):** calm-windDir TTL expiry logs DEBUG when windSpeed is 0.0 (calm is
  Davis semantics, not a fault); WARNING kept for expiry with wind, and an expired windSpeed counts
  as a dropout. Recovery line downgraded symmetrically. 4 tests.
- **BACKLOG pruned:** DEC-0024 bullet (shipped v2.0.8) and RAW_* log bloat (resolved; live log has
  zero RAW_ lines) marked done.
- **v2.0.9 released:** PR #77 → dev (CI green), image built on the NAS from a fresh checkout, pushed
  to Docker Hub `:v2.0.9` + `:latest` (digest `sha256:5eb38850`), prod container recreated from the
  live inspect config (kill→rm→3s→run), `loop_json_writer.py` hot-swapped (`.bak-pre-v2.0.9`),
  live-verified: driver banner `0.20+ws.1`, `sensor_qc True`, records publishing, `current.json`
  writing (calm windDir correctly omitted), soak 14 PASS / 1 WARN (restart-empty reception window) /
  0 FAIL, no startup stall. Rollback: `:v2.0.8` remains on the NAS and Docker Hub.
- **Found in passing: the Dockerfile installed weewx UNPINNED** — this rebuild silently moved prod
  weewx 5.3.1 → 5.4.0 (came up clean, daily summaries fine; 5.4.0's changelog is reporting/tooling
  only — `weectl rest`, skin fixes — nothing touching the driver API, restx, schema, or QC paths).
  Same silent-drift class as S46's unpinned-ruff CI break. **Closed same session (#78):**
  `requirements.txt` pins `weewx==5.4.0` (matching what is verified-live), the Dockerfile installs
  from it, and `.github/dependabot.yml` turns future weewx releases into review PRs — notification
  and deliberate bump, never a blind update. No rebuild needed: the pin equals the running version.

---

## [S51] — 2026-07-26 — Watch items all run: DEC-0053 TTL watch resolved benign, humidity spike still unfired; issue #74 filed

No code changed. All four S50-handoff watch items executed against prod:

**DEC-0053 TTL-expiry watch — fired 10× in its first full day, both patterns benign, watch RESOLVED.**
(a) One real event: `dewpoint_F`/`outHumidity`/`heatindex_F` all expired at 20:09:44 after a genuine
~13-min humidity-packet reception dropout (19:59–20:12 EDT) — the bound doing exactly its job (the
~611 s of tolerated absence is the two caches stacking: DewpointCacher carries the value ≤300 s, then
the writer's own 300 s TTL runs). (b) Seven `windDir` expiries at ~301 s during calm stretches — the
driver *deliberately* sets `wind_dir = None` on calm readings (`rtldavis.py` ~1356), so any ≥5-min
calm expires the cache. Healthy sensor, semantically correct omission, misleading "sensor may be
failing" text. Filed [#74](https://github.com/WeatheredScientist/weewx-rtldavis/issues/74)
(tier:mid): proposed calm-aware downgrade to DEBUG, needs design agreement first (PRINCIPLES §8).
Explicitly NOT a bump-the-TTL case — a longer TTL would serve a stale direction during calm.

**Humidity-spike watch — still unfired.** 2,755 raw samples decoded covering 2026-07-24 00:04 →
2026-07-26 20:42; largest single step −8.7 RH pts, and that across a 4-min reception gap. Nothing
near the 16–37 pt DEC-0044 single-step signature. No SensorQC rejections in today's log at all.

**Soak check: 14 PASS / 1 WARN / 0 FAIL** (WARN = the known 67% reception baseline). Phantom-rainRate
prediction (DEC-0049): 0 qualifying rows in 1,214. No driver stalls in today's log — the S41
startup-race class is now clean across three consecutive restarts (S43, S47, S48).

---

## [S50] — 2026-07-26 — STATUS resume pointer fixed (micro-session)

One docs commit (PR #73): STATUS.md's `▶ Resume here` line still read "S48 → S49" after S49 had
shipped and closed. No other work.

---

## [S49] — 2026-07-26 — Issue #67 closed: mypy is now a real CI gate

Triaged and fixed the 19 pre-existing mypy errors S48 flagged (`--all-files` run while adding the
pytest hook) but didn't diagnose. Reproduced locally via `pre-commit run mypy --all-files`.

**Two genuine bugs, both in `ops/recover_sweep_results.py`:** the `results` list's `NO_DATA` row
appended an `int 0` for the pct column where every real-data row appends a `float`
(`round(mean_pct, 1)`) — now `0.0`. Separately, the summary loop reused the module-level names `ts`
(a `datetime` from the log-parsing loop) and `pct` (an `int` from the same) for unrelated `str`/
`float` values unpacked from `results` tuples — silent shadowing, not a crash, but genuinely
confusing and exactly the kind of thing mypy is right to flag. Renamed to `_ts` (unused) and
`row_pct`. `results` also gained an explicit type annotation
(`list[tuple[int, int, str, int, int, float, int | str]]`) documenting that its last column is
intentionally either a window count or the `"NO_DATA"` sentinel string — a deliberate design choice,
not something to unify.

**One missing stub, not a bug:** `pressure_service.py` needs `types-requests`. Added to
`.pre-commit-config.yaml`'s mypy hook `additional_dependencies` and to CI's `pip install` step.

**13 py2/py3-compat false positives (`influx.py` 9, `wcloud.py` 4), plus one real
shadowing bug in `influx.py` (3 cascading errors):** the `try: import X / except ImportError: import Y as X` compat shims
mypy statically flags on the branch that never executes under Python 3.14 — suppressed per-line with
`# type: ignore[no-redef]` / `[attr-defined]`, never a blanket per-file ignore, per the issue's own
suggested triage. Separately, `influx.py`'s manual test harness (`if __name__ == "__main__":`) had
`queue = queue.Queue()`, shadowing the `queue` module import with a same-named local — the two
`Module has no attribute "put"` errors were downstream of this one root cause, not independent bugs.
Renamed to `q: queue.Queue = queue.Queue()`.

Verified clean: `pre-commit run mypy --all-files` 19 → 0 errors, ruff clean, pytest 91/91. Removed
`.github/workflows/ci.yml:81`'s `|| true` — mypy failures now actually block CI, mirroring what
#55/DEC-0015 did for pytest via pre-commit at S48. No DEC entry — this closes an enforcement gap,
not a new design decision, same class as #55.

---

## [S48b] — 2026-07-25 — Provenance audit (DEC-0053): loop-JSON cache bounded; #48 and #45 closed

**Issue #48 — closed, DEC-0042 upheld.** A dashboard-side reconciliation found WeatherLink's
install-to-date total only balances if the console *excludes* the 2.56″ of phantom rain we corrected,
and asked whether that undercuts DEC-0042's ISS-side mechanism. It does not — the premise conflates
two classes this repo's data model already separates into independent flags: the 2.56″ is `rain_qc`
(3 points, the **counter**, owned by DEC-0021/0033/0035), while DEC-0042 governs `rainRate_qc`
(33 points, `rain = 0.0` in every one, contributing 0″ to any total). Both classes independently
*require* the console's absence — ERR-0001 was our own wraparound handler adding 128 to a logged
`rain_count=-64` and ERR-0002 a bit-7 flip passing CRC (both downstream of the shared broadcast), and
DEC-0042's mechanism predicts no tip at all. Per INTERFACES §4 the console is our ground truth for
"did the bucket actually tip," and it says no — confirmatory, not contradictory. The reconciliation is
real value as **independent validation that the correction was right** (residual 0.01″), now recorded
in `DATA_ERRATA.md`. DEC-0042 gained a "Challenged and upheld" note so it isn't re-derived.

**Issue #45 — closed as DEC-0053.** Audited every artifact a consumer reads for whether the
assumptions it was produced under travel with it. One real bug, two documented gaps:

- **Fixed:** `loop_json_writer.py`'s cache was **unbounded** — it updated only on non-None values,
  never expired them, and stamped every write with the *current* packet's `dateTime`. A dead or
  SensorQC-rejected sensor emitted its last value forever, indistinguishable from a live reading, on
  the surface the dashboard reads. Same failure `dewpoint_service.py` fixed for the archive path at
  S33/DEC-0022 — learned in one artifact, never propagated to its sibling. Now bounded per-field:
  300 s default (matching DewpointCacher), **2 × `[DavisPressure] fetch_interval`** for
  `barometer_inHg`, since a flat 300 s would have blanked the hourly-fetched barometer for 55 min of
  every hour and regressed Cold-load Fix B. Expired fields are omitted, not frozen, and logged at
  WARNING. 6 new tests + a mutation check confirming they go red against the old cache (91 total).
- **Documented, not fixed:** InfluxDB carries no station identity — and the "one-line" `tags =` fix is
  a trap, since it forks the series key (interface break, needs dashboard coordination). The SQLite
  archive carries no correction flag, so the system of record is less provenanced than the derived
  store. Both in BACKLOG with the reasoning.

`INTERFACES.md` §1 updated — the staleness bound is part of the contract, and a missing field now
explicitly means "no current value," never "value unchanged."

**Deployed and verified in prod** (PR #69 merged, then hot-swapped — `loop_json_writer.py` is MOUNTED
per DEC-0046, so the merge alone would have been inert). Pre-flight drift check confirmed the live
file was byte-identical to the repo's pre-change version; scp'd with md5 matched both ways, pyc
cleared, container restarted (`kill` → `start`, DEC-0008). Live log: `cache TTL 300 s,
barometer_inHg 7200 s` — the barometer TTL correctly derived from the live `fetch_interval = 3600`.
Watched 453 s, past the default TTL: zero expiry warnings, all fields still served, values updating.
Rollback is `loop_json_writer.py.bak-pre-ttl-S48` + restart. No image rebuild; `:v2.0.8` unaffected.

---

## [S48] — 2026-07-25 — pytest hard-gated at commit time; closes issue #55

Investigated [#55](https://github.com/WeatheredScientist/weewx-rtldavis/issues/55) ("closeout
doesn't hard-gate on a green test suite"), filed 2026-07-16 before this repo's closeout skeleton
existed. Found the practical exposure already narrow: `dev` is a protected branch requiring the
`tests`/`lint`/`secret-scan` CI checks before any merge (verified directly this session via PR #65),
so a broken-test commit has no path onto `dev` regardless of whether an agent remembers to run
pytest locally. The one real remaining gap: pytest wasn't part of `.pre-commit-config.yaml` — only
ruff/mypy/secret-scan ran at commit time, which is what DEC-0015 originally intended but never fully
wired up. Added a `local` pytest hook (isolated pre-commit env, `additional_dependencies: [pytest]`,
`always_run: true`) — the suite is all-stdlib so it needs nothing from this repo's `.venv`. Verified
it fires on every commit and passes in isolation. Commented on and closed #55, citing the branch-
protection/CI structure as the actual hard gate, with this as the immediate-local-signal bonus.

(Caught, not fixed, as out of scope: running `pre-commit run --all-files` surfaced 19 pre-existing
mypy errors and trailing-whitespace fixes across `influx.py`/`ogoxeUploader.py`/`weewx.conf.example`
that normal per-commit runs never touch, since pre-commit only checks each commit's own diff.
Reverted those incidental changes — not this session's task.)

---

## [S47] — 2026-07-25 — Backlog + branch cleanup: loopdata.py / reception_service.py removed, rw350/400-test images deleted, stale worktree removed

Cleared four long-parked, "not urgent" backlog items in one session.

**`loopdata.py` (DEC-0005, open since S16).** `user.loopdata.LoopData` was confirmed still absent
from every active `[Engine][Services]` list. Removed the `[LoopData]` config section from the live
`weewx.conf` (backed up first as `weewx.conf.bak-pre-loopdata-cleanup-S47`; a small Python script
found the section by its top-level header and asserted on expected content before writing, rather
than a line-count sed). Recreated `weewx-rtldavis-v2` (`kill` → `rm` → 3 s settle → `run`,
reconstructed from `docker inspect`) without the `loopdata.py` bind mount. Verified live: container
`running`, 6 mounts (down from 7), `weewx.log` publishing archive records and RESTful uploads within
seconds, no `CRITICAL`/stall. `loopdata.py` renamed aside on the NAS to `loopdata.py.removed-S47`
rather than deleted, for rollback.

**`ops/reception_service.py` (found S43).** Confirmed unimported anywhere in the test suite (one
stale comment reference in `tests/test_reception_layer_b.py`, fixed), never `COPY`'d into the
Dockerfile, and its `ReceptionMonitor` service never listed in `weewx.conf`. Deleted from the repo;
the NAS copy renamed aside to `reception_service.py.removed-S47`.

**`rw350-test` / `rw400-test` Docker images (DEC-0048's last piece).** `rw250-test` was retired at
DEC-0048 (S41); the other two ad-hoc `receiveWindow`-sweep tags were left. Confirmed neither backs
any running container (`docker ps -a` showed only `weewx-rtldavis-v2` on `:v2.0.8`) and deleted both
from the NAS. DEC-0048 is now fully closed.

**Stale worktree.** `.claude/worktrees/s46-closeout-amendment` (branch
`worktree-s46-closeout-amendment`, merged via PR #64) removed — same pattern as the 8 worktrees
cleaned up at S41.

No driver/source code changed, no image rebuild, `:v2.0.8` unchanged. Docs updated: BACKLOG.md,
ROADMAP.md, docs/ARCHITECTURE.md, docs/DECISIONS-FULL.md (DEC-0005), docs/STATUS.md.

## [S46] — 2026-07-24 — Humidity-spike watch checked directly (still unfired); OPS-DEC-0019 rollout closed cross-repo; dev housekeeping

Ran the DEC-0044 humidity-spike check directly against the live NAS logs rather than deferring it:
fetched every `log_humidity_raw` packet captured since the capture went live (2026-07-13 15:27, S41)
through the current log — 11 days, 8,852 raw packets, ~3x the largest prior sample (S43's 2,056).
Decoded per the driver's own formula (`rtldavis.py:1543-1550`) and searched for a single-step raw jump
of 16-37 %RH (the DEC-0044 signature). **Zero matches.** Largest swing: -9.86 %/min (2026-07-17
13:16→13:17, 60.5%→51.3%) — larger than S43/S44's reported 7.5 %/min purely from sample size, still
ordinary midday humidity movement, clustered in the predicted 11:00-16:00 window. Watch remains open,
unfired.

Closed [eaglehunt-ops#37](https://github.com/WeatheredScientist/eaglehunt-ops/issues/37) (OPS-DEC-0019
env-twin rollout): confirmed all three Eagle Hunt repos had merged their portion (weewx-rtldavis#59 in
S45, hyperlocal-forecast#135, eaglehunt-weather-dashboard#102+#112) — commented and closed.

Housekeeping: local `dev` was 2 commits behind `origin/dev` (PR #61, `ops-53-settings-consolidation`)
— pulled forward; removed the resulting stale merged worktree
(`.claude/worktrees/ops-53-settings-consolidation`) and its local branch. Checked eaglehunt-ops' open
issues and both sibling repos for anything owed here: nothing tagged `repo:weewx`, nothing outstanding.

Opening this closeout as PR #62 surfaced a real CI break: the lint job's unpinned `pip install ruff`
had drifted to 0.16.0, whose new default rules flagged 295 pre-existing hits (139 in `rtldavis.py`,
the driver protected from reformatting churn by DEC-0014/DEC-0027) — `lint` is a required check on
`dev`, so this was silently blocking every PR. Fixed via PR #63 (pinned `ruff==0.5.7`, matching the
`.pre-commit-config.yaml` pin DEC-0027 already settled on; no source files touched). Merge order:
#63 merged first, then #62's branch was updated onto it so its own lint check went green. Both
merged 2026-07-24. The CI workflow file changed; no source/driver code did.

---

## [S45] — 2026-07-20 — PR #59 merged: OPS-DEC-0019 env-twin permission rules (cross-repo)

`.claude/settings.json` gained two ask-rule entries: `Bash(env * git merge * main)` and
`Bash(env * git merge * dev)`. Env-wrapping (`env -u GH_TOKEN git merge …`) defeats ask-rule
pattern matching, since `env` isn't stripped before the match runs — the existing `git merge * main`/
`git merge * dev` rules never fired for an env-wrapped call, which fell through to the auto-mode
classifier instead of resolving by rule. `git push` already carried its env-wrapped twin; this fills
in the same gap for the two protected-branch merge rules. Mechanical, no code touched, part of the
cross-repo OPS-DEC-0019 rollout (`eaglehunt-ops#37`) landing the same fix in all three Eagle Hunt
repos. CI green (lint/secret-scan/tests). The branch and commit were already staged when this session
started; this session's contribution was flipping draft PR #59 to ready and merging it to `dev`.

Humidity-spike watch and the DEC-0049 rainRate prediction: unchanged, still unfired (see [S44]).

---

## [S44] — 2026-07-19 — Soak-check phantom-rain false positive fixed; shared closeout skeleton adopted (DEC-0052)

`ops/soak_check.sh` on the still-running v2.0.8 (up 98h) flagged 49 archive rows as a possible
DEC-0049-predicted phantom-rainRate event. Cross-checked against the full 2026-07-18 archive: it
wasn't one — 3 real bucket tips that day, a falling barometer (29.93→29.78 in) and rising gusts (to
8 mph) confirm a real storm, and every flagged row is the ISS's own rain-rate message decaying after
a real tip (one decay tail ran 38 minutes, past the light-rain formula's nominal ~1022s ceiling).
**Fixed:** the detector now excludes any row with a real tip in the preceding hour. Re-verified
live: 49 → 0 false positives, all other soak checks unchanged. The DEC-0049 prediction itself (a real
condensation event, tip counter not advancing) remains unfired.

**DEC-0052:** adopted eaglehunt-ops' locked closeout skeleton (OPS-DEC-0016), adapted. `CLAUDE.md`'s
closeout ritual — previously split across two paragraphs ("Session ritual — End" and a separate
"Docs-diet ritual at close") — is now one 6-step numbered list; the docs-diet ritual and this repo's
stricter local commit/push rule are kept as addenda, per the template's own pattern. The only
genuinely new content is step 5, a model-tier restore check — the third repo (after
hyperlocal-forecast, coffeeradar) to independently land on that same assessment. Closes
weewx-rtldavis#56; outcome reported to eaglehunt-ops#22.

Both changes landed via PR #57 (`s44-ops-closeout-and-rain-fix` → `dev`), checks green
(lint/secret-scan/tests).

Humidity-spike watch: still negative, 894 samples this container lifetime, largest jump ~7.5 %RH/min
— same magnitude as S43, no qualifying spike.

---

## [S43] — 2026-07-15 — v2.0.8 shipped, deployed and verified: Cold-load Fix B/DEC-0051, Reception Layer B/DEC-0024, duplicate-frame counter/DEC-0035

> **Soak check (v2.0.7, up 49h): green.** 11/15 pass, 4 expected startup-only warnings, 0 failures —
> archive current, stdout quiet, no tracebacks, no stalls, 100% reception, 45,190 records published, 0
> phantom-rain rows in 2,987 archive rows. **Humidity-spike check: no qualifying spike yet.** Decoded
> the full `humidity_raw=` series since the capture went live (2,056 samples, ~50h, including the
> rotated `weewx.log.2026-07-13`/`.2026-07-14` the live log had already rolled past) per the driver's
> real decode formula. Largest jump: 7.5 %RH/min, clustered in the predicted 11:00–16:00 window but
> well under the 16-37% DEC-0044 signature. Capture instrument confirmed working correctly.
>
> **Three backlog items shipped in code:**
>
> 1. **Cold-load Fix B + windchill (DEC-0051, closes issue #44).** `loop_json_writer.py` now writes an
>    identical snapshot to a second path (`current.json`, default `/opt/weewx-data/current.json`) on
>    every LOOP packet, atomic tmp+rename same as `loop-data.txt`; `windchill` added to `_FIELDS`
>    (`windchill_F`). `docs/INTERFACES.md` updated. **Deploy: mounted file — hot-swap (scp + clear-pyc
>    + restart), no image rebuild** (verified against `docs/ARCHITECTURE.md`'s mount table).
> 2. **Reception Layer B (DEC-0024 — now fully resolved).** The driver published channel-hop
>    (`freqError{n}`) packets as their own dataless loop packets, which every uploader (WU RapidFire
>    etc.) then published as if they were full weather updates — the ~1.6x overcount measured at S21.
>    Considered and rejected: dropping the packet outright (freqError is repurposed onto real archive
>    schema columns — `consBatteryVoltage`/`hail`/`hailRate`/`heatingTemp`/`heatingVoltage` — and
>    `ops/reception_service.py` logs non-zero freqErrors, so silently breaks both); tagging it dataless
>    and filtering in every consumer (broader blast radius for no benefit). **Chosen:** cache the
>    channel-hop packet's freqError fields and merge them onto the *next* real DATA packet instead of
>    ever yielding a standalone one (`_cache_pending_freq_fields` / `_merge_pending_freq_fields`, each
>    cached value rides exactly once). Side effect: also fixes `weewx_monitor.py`'s live `WINDOW:`
>    reception metric, which counted channel-hop packets as real readings via its epoch-dedup (S22)
>    never fully catching them (S31 confirmed it still pinned near 100%) — verified live post-deploy,
>    see below.
> 3. **Duplicate-frame counter (DEC-0035's own proposed instrument).** `genLoopPackets`'s stderr scan
>    now counts Go's `"duplicate packet:"` dedup line unconditionally (no `debug_rtld` gate) into
>    `self.stats['dup_count']`; `_update_summaries()` logs one INFO line per archive period (including
>    `N=0`, so a quiet period is distinguishable from the instrument not running); `_reset_stats()`
>    zeroes it for the next period — the same pattern already used for `pct_good_all`.
>
> Items 2+3 both touch the baked driver (`rtldavis.py`) — bundled for **one** image rebuild rather than
> two. +13 offline tests (`test_loop_json_writer.py`, `test_reception_layer_b.py`,
> `test_duplicate_frame_counter.py`); suite 72 → 85. **DEC-0051 added; DEC-0024 and DEC-0035 updated**
> with S43 sub-sections in `DECISIONS-FULL.md`.
>
> **Caught mid-commit: local pre-commit's `ruff-format` hook had silently contradicted DEC-0027 since
> S31.** CI dropped `ruff format` deliberately (it flattens `rtldavis.py`'s column alignment and
> reformats the baked driver — No-Rewrite); local `.pre-commit-config.yaml` still carried it. Never
> fired because pre-commit itself was never installed until S42 (DEC-0050) — its first real run
> attempted to mass-reformat `rtldavis.py` (3,213-line diff) on this session's commit. Caught (a second
> hook also blocked the same commit), reverted, `ruff-format` removed from the config. Checked both
> siblings for the same pattern: the dashboard already avoids it deliberately; `hyperlocal-forecast`
> carries it too but with no equivalent DEC and no known baked file, so no finding filed there.
>
> **Deployed and verified, same session.** PR #49 (the three items) and PR #50 (the `v2.0.8` version
> bump — Dockerfile header + README) merged to `dev`. Image built on the NAS in a fresh `build-v2.0.8/`
> checkout (`docker build`, zero errors in the build log), pushed to Docker Hub as `:v2.0.8` + `:latest`
> (digest `sha256:2c05493a...`). `loop_json_writer.py` hot-swapped into place (old copy preserved as
> `.bak-pre-v2.0.8`); production container recreated (`docker kill` → `rm` → `run`, DEC-0008 — replicated
> the *actual running container's* `docker inspect` config, not the NAS's own stale `docker-compose.yml`,
> which still said `:v2.0.4`). **Live-verified, not image-checked (DEC-0046 discipline):** driver banner
> `0.20+ws.1`; `current.json` writing real data including `windchill_F`; `duplicate frames this period: N`
> logging every archive period; **Wunderground-RF published-record count now matches unique record
> epochs exactly (53/53 over a 3-min window)** — the ~1.6x overcount DEC-0024 documented is gone;
> `soak_check.sh` 14/15 pass, 0 failures (1 warning: 71% reception, ordinary RF variance, not a
> regression). **`weewx_monitor.py`'s live `WINDOW:` metric confirmed fixed too:** post-deploy it reads
> `WINDOW: 14-17/21 (67-81%)`, `RECEPTION: 73-77% avg` — matching the driver's own trusted
> `rxCheckPercent` range (59-95%, median 75%, S31) for the first time, instead of the pre-fix pinned-
> near-100% pattern S31 documented. (Correction: `ops/reception_service.py` — a *different*,
> WeeWX-internal `ReceptionMonitor` service — turned out not to be wired into this station's
> `weewx.conf` at all, and per `git log` has sat untouched since S16; likely vestigial, like
> `loopdata.py`. It is not what generates the reception emails; `weewx_monitor.py` is.)
>
> **PR #51 promoted `dev` → `main`** (CI green on both source commits); tagged `prod-baseline-20260715`
> + `v2.0.8`; GitHub Release published. `docs/CONVENTIONS.md` and `CLAUDE.md` had stale `:v2.0.4`/`:v2.0.5`
> drift notes left over from S38 that were never corrected when S41 actually caught prod up — fixed now
> alongside this release. `ops/soak_check.sh`'s own `EXPECT_IMAGE` default bumped to `:v2.0.8`.

---

## [S42] — 2026-07-14 — the cross-repo round: DEC-0040's triggers fired, the identifiers were live on public dev, and pre-commit had never run (DEC-0050)

> **This was the scheduled `[Fable]` cross-repo coordination round** (dash S74 = this repo's S42),
> and this repo's share of it landed in one PR.
>
> **The identifier scrub was not hypothetical.** `ops/soak_check.sh` carried the real NAS
> user/IP/port as tracked shell defaults — **on `dev`, on a PUBLIC repo**, since S41. Our own
> `test_check_secrets.sh` tree check flags it (40/41 → the "1 FAILED" was this), but that check
> runs only where the gitignored `.identifiers` file exists — **CI is structurally identifier-blind
> by design**, so the only enforcement point was local pre-commit. And the hole under the hole:
> **pre-commit was configured but never installed** — `.git/hooks/pre-commit` did not exist, here
> or in either sibling repo. The load-bearing local gate for a public repo had never once executed.
> A configured control that nothing runs is prose (DEC-0040, one level down). Fixed: defaults are
> now placeholders that fail fast; real facts live in `~/.claude/nas.env` (also honored by the new
> eaglehunt-ops checks) / gitignored `docs/LOCAL_INFRA.md`; suite 41/41 with a clean tree; soak
> re-proven green end-to-end via `nas.env` and red on the placeholder path; pre-commit actually
> installed (owner-run). Per DEC-0028's precedent (identifiers, not credentials; LAN IP): fix
> forward, **no history rewrite**.
>
> **DEC-0050 — the station gets a master for its IDENTITY (and only that).** DEC-0040's own revisit
> triggers fired (five shared `~/.claude/` executables versioned nowhere; the same gate fix
> re-derived four times; the dashboard's DEC-0106 as the predicted casualty — 6.7 km of coordinate
> drift, a week of forecasts for the wrong town). The private **`eaglehunt-ops`** repo now holds:
> canonical `station-identity.env`, the drift check (**first run: 8/9 representations within 19 m —
> and the 9th finding was real**, see below), the NAS runtime contract, and the `~/.claude/` guards
> under version control with their tests (live copies = deployments via owner-run `install.sh`).
> Scope fenced by the S38 §Etiquette litmus test; deletion clause attached.
>
> **The identity check's first run caught a live outage in a sibling:** HLF's
> `/api/v1/forecast` hangs indefinitely for **every** coordinate pair (health/current fine,
> container "Up 8 hours" — *"Up" is not health*, our own DEC-0036 lesson, now on an API surface).
> Per §Etiquette: **filed in HLF's tracker with the evidence, not fixed from here.**
>
> **Also filed here (cross-repo asks from the dashboard's S73):** the loop writer emitting
> `cloudbase` (+`windchill`) — folds into the existing Cold-load Fix B thread; and a provenance
> audit (does the artifact a consumer READS carry the assumptions it was captured under — their
> DEC-0104/0106 twins of our DEC-0040/0045/0047 family). The dashboard's stale claim that our
> secret gate was "neutered" was **re-measured and retired** — 40/41 planted payloads pass; the
> one failure was the tree check doing its job on the identifiers above.
>
> **Read-guard field data (their `~/.claude/` DEC-0047 guard, now versioned in eaglehunt-ops):**
> S73/S74 logged five false positives — all token×verb string matches with no data flow (a commit
> MESSAGE containing "proxy.env" + the word "more"; the sanctioned `readconf` invoked by full path;
> a `.env` name inside an `echo` literal). Two mechanical fixes ride the eaglehunt-ops migration
> (readconf at a path boundary; a lone `git commit` exempted after heredoc-body stripping — chains
> and substitutions still block), proven 46/46 both directions. The wider class is documented as
> accepted: a false block costs a retype; a false allow costs a rotation.

---

## [S41] — 2026-07-13 — v2.0.7 shipped, and the config fix that would have missed prod entirely

> **v2.0.7 is on Docker Hub, prod runs it, and the raw-humidity capture is finally live.**
>
> The headline was meant to be routine: take S39's `[[root]]` logger fix (DEC-0043), which had been
> sitting merged-but-unreleased on `dev`, and ship it. That happened — `:v2.0.7` + `:latest`
> (digest `sha256:31cad4d2`), GitHub release, `main` == prod, `prod-baseline-20260713b` tagged.
>
> **The finding is what the deploy nearly missed.** The `[[root]]` fix lives in the image's *baked*
> config, protected by a Dockerfile build-time assertion so an image cannot be built without it. But prod
> bind-mounts `weewx-data/` over `/opt/weewx-data` — the mount covers the whole directory, so the live
> `weewx.conf` **shadows the baked config completely**. Deploying `:v2.0.7` and stopping there would have
> been, in prod, **a no-op with a green checkmark**: correct image, passing assertion, accurate release
> notes, and a station still emitting syslog tracebacks and still silently dropping every startup
> diagnostic. **DEC-0046.**

### Shipped — v2.0.7

- **Docker Hub:** `:v2.0.7` and `:latest`, both at digest `sha256:31cad4d2826b…`. Built on the NAS from
  `git archive v2.0.7` — the image is built from *exactly* the tagged tree (DEC-0038).
- **GitHub release** [v2.0.7](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.7);
  `dev` → `main` (PR #38, after PR #37's version bump); `main` and `dev` are identical trees.
- **Prod recreated on `:v2.0.7`** at 15:27 EDT. `docker kill`, never `stop` (DEC-0008); no `rtldavis.py`
  mount (DEC-0031). Rollback available: `:v2.0.6` (`e23cabd53591`) is still on the NAS.
- **`prod-baseline-20260713b`** tagged — the second baseline of the day (the first, `-20260713`, was
  v2.0.6). Not force-moved; the old tag still means what it meant. DEC-0011's *`main` = production truth*
  invariant holds.

### Found — DEC-0046: the baked config never reaches prod

- Caught by a **pre-flight `grep` of the live config**, which found **zero** `[[root]]` blocks while the
  image's baked config carried it and asserted it.
- **The exact mirror of DEC-0031.** There, the *driver* is baked and the bind-mount is the no-op, so an
  `scp` is silently ignored. Here, the *config* is mounted and the image is the no-op, so a rebuild is
  silently ignored. Inverses — which is precisely what makes the pair easy to get backwards. **Neither
  errors. Both accept the instruction and discard it.**
- Fixed in the same window: the live `weewx.conf` gained the `[[root]]` block (backed up first to
  `weewx.conf.bak-pre-v2.0.7`). Prod's version routes to `handlers = rotate,` — **file only, no console**,
  deliberately differing from the baked config, because prod declares no console handler and adding one
  would re-arm the DEC-0036 freeze hazard that DEC-0041 disarmed. **The fix must match; the text need not.**
- **The fifth member of the family**: an interface that accepts an instruction and silently discards it
  (DEC-0031's bind-mount, DEC-0036's `max-size`, DEC-0040's prose, DEC-0045's test that certified the
  hole). The build assertion was not wrong — **it was answering a question nobody was asking in prod.**

### Verified in prod — behaviorally, not by inspecting the artifact

- **`weewx.log` now contains `weewxd INFO Initializing weewxd version 5.4.0`**, plus the command line, the
  Python version, the platform and `WEEWX_ROOT` — **lines that had never once appeared in that file.** This
  is the S39 acceptance criterion, and it reads the running system. An image check would have said PASS.
- **Zero `--- Logging error ---` blocks** on stdout (was ~15 tracebacks / ~515 lines per start).
- `driver version is 0.20+ws.1 (patched by WeatheredScientist -- not stock upstream)`, `sensor_qc True`,
  **`log_humidity_raw True`**, 0 tracebacks, `RestartCount: 0`, and Wunderground (rapidfire + PWS), Influx
  and Windy all publishing.

### Armed — the raw-humidity capture is now live (DEC-0044)

`log_humidity_raw` had been sitting in the live config since S39 but weewx reads its config **only at
startup**, so it took this restart to activate. It is now running. **The next midday humidity spike logs
its raw `pkt[3]`/`pkt[4]`** and settles the nibble question deterministically — no averaging, no free
parameter. Spikes run ~2–3/week, clustered 11:00–16:00. The inversion method is in DEC-0044; do not
re-derive it.

### Security — DEC-0047: the secret gate guards commits, not reads

> **The transcript is an egress path, and nobody had modeled it as one.**

- **The gap.** Every secret control in this repo is a **commit-time** control — DEC-0012,
  `check_secrets.sh`, the CI secret-scan, the 41-payload proof suite. Four hardenings across S26 → S40, all
  of them guarding the **write** path to GitHub. **None says anything about reading.** Whatever a tool
  prints lands in `~/.claude/projects/*.jsonl` in plaintext and is transmitted to the model provider. The
  `.gitignore` entry feeds the blind spot: the live config is *deliberately* excluded from the repo, which
  makes it feel handled. **"Not in the repo" is not "not in the transcript."** DEC-0040 said *prose does not
  execute*; this is worse — **there was no prose.** No rule was broken because no rule existed.
- **What surfaced it:** a `sed -n "/^[Logging]/,+44p"` on the live config during this deploy. A fixed
  **line-count** window on a sectioned file: `[Logging]` is ~22 lines, so it ran off the end and printed the
  following sections into the transcript. **A line-count window on a sectioned config is a loaded gun —
  sections move, the window does not.**
- **Three mechanical controls, in `~/.claude/`** (global — DEC-0040's "no master repo"):
  `hooks/secret-read-guard.sh` (PreToolUse on Bash/Read/Grep; blocks *secret path* × *emitting verb*, sees
  through `ssh "…"`, **leaves editing alone** so the DEC-0046 release workflow still works — a guard that
  blocks the work gets switched off; matches **per-token**, so `cat weewx.conf.example && cat weewx.conf`
  cannot launder the live config through the `.example` carve-out);
  `bin/readconf` (**section-scoped — it structurally cannot take a line window**; values become stable
  `sha256` fingerprints while `handlers = rotate,` and `level = INFO` stay readable, because a DEC-0046
  deploy has to verify exactly those); and `bin/scan-transcripts` (the detection half).
- **Proven, not merely green.** The guard's suite asserts **both directions** (38/38 — the leaking command
  blocks; `cat weewx.conf.example`, `sed -i`, `cp`, `readconf` all still pass), and a **mutation test**
  turns it **red — 18 failures.** The scanner **self-tests before every run** and refuses to report "0" if
  the harvest returned nothing. **Verified live:** re-running the original command is now blocked by the
  hook.
- **A scanner that cries wolf is its own failure mode.** The first pass reported a real password sitting in
  `weewx.conf.example` on public `main` since S16 — which would have been a live exposure and a fifth gate
  hole. It was the example's own placeholder string. The evidence looked internally weird (the same
  "password" appeared as three different keys), and re-checking it is the only reason a five-alarm claim was
  not filed. DEC-0039: *a green exit code is not evidence.* DEC-0045: *a passing test is not evidence
  either.* **S41: a scan that finds nothing is not evidence unless you have proved the scanner can see.**
- **A full scan of all refs confirms no real credential has ever been committed to any of the three repos.**

### Housekeeping — the cleanup that found its own backlog item was stale

- **DEC-0049 — the ISS hardware is new and inspected, so the phantom rainRate is not a broken part.**
  DEC-0042 closed with *"next step is physical: inspect the bucket, the reed switch and its wiring."*
  **That action is now closed and it came back clean.** The owner reports the ISS hardware is **new**, was
  **recently inspected**, and has **no faults** — the one component that did fail, the **anemometer**, was
  **replaced ~16–17 June 2026**. A clean inspection does not falsify DEC-0042, it **sharpens** it: the two
  readings were always *defective part* or *working part reacting to the environment*, and **the first is
  now excluded.** Condensation bridging a **healthy** reed switch produces exactly the measured signature
  (94 % RH, 1.7 °F dewpoint spread, 0 mph wind, tip counter never advancing). **There is nothing to swap and
  no part to order** — anyone reading DEC-0042's "next step is physical" without DEC-0049 would order one
  for no reason. The anemometer date is also a **dating anchor**: wind data either side of mid-June comes
  from different physical hardware.

- **DEC-0048 — reception testing is a designed experiment, not a pile of image tags.** `rw250-test` is
  retired. It was a **misnomer within a day of being built** (`receiveWindow` ships at the upstream
  default), and it was **never published to Docker Hub** — verified against the live tag list, so the
  confusion was only ever ours. The deeper point: that sweep was never a controlled experiment, which is
  also **why DEC-0017 has sat open since S16** — gain is held at 372 pending an "averaged re-test" that
  never happened because no method was ever agreed. A proper RX test is **deferred, not abandoned**: when it
  runs it gets a hypothesis, a control arm, an averaged window, and a pre-registered metric — and it settles
  **gain 372-vs-207 and `receiveWindow` in the same run**, since they share the same apparatus and the same
  confound. Until then **neither parameter gets tuned by feel.**

- **Branch cleanup — and the backlog item was stale.** STATUS had been asking us to delete
  `feature/rain-spike-filter` and `s32-reconcile-main`; **neither still existed.** What *did* exist was **8
  merged `worktree-*` branches**, each verified at **0 unmerged commits** before deletion. The remote is now
  exactly **`dev` and `main`**. All three Eagle Hunt repos have **zero** open PRs, and the dashboard's
  long-flagged stranded draft PR is gone too.

## [S40] — 2026-07-13 — a comment is not an exemption: the gate's proof had certified the hole

> **The secret gate let commented-out credentials into a PUBLIC repo — and its own test said that was
> correct.**
>
> Carried over from the close of S39, where it was spotted and deliberately left as the owner's call.
> `scripts/check_secrets.sh` had an `ALLOW (1)`: *if the whole line is a comment, allow it.* So
> `# api_key = <a real credential>` shipped clean. `git push` does not strip comments, and neither does
> anyone reading the file on GitHub.
>
> **The part that made this a DEC and not a bug fix:** the rule was not a blind spot the test missed —
> **the test asserted it.** Two commented credentials sat in `test_check_secrets.sh` under *"must PASS"*,
> and they were part of DEC-0039's celebrated *"28/28 planted payloads, proven"*. DEC-0039's thesis is
> *"a green exit code is not evidence."* S40's correction: **a passing test is not evidence either, if
> the assertion is wrong.** The proof had certified the hole.

### Fixed — DEC-0045: comments are scanned exactly like code

- **`ALLOW (1)` deleted.** No comment rule at all. A comment earns no exemption; only its **value** can.
  `# api_key = YOUR_API_KEY_HERE`, `# token = "${INFLUX_TOKEN}"` and the `influx.py` docstring style still
  pass — via the placeholder / interpolation / prose rules, which test the value. Commenting a line out no
  longer changes the verdict **in either direction**.
- **No new exemptions.** The gate's own header had illustrated three past bugs with six real-looking
  credential literals, which the fix now flags. The tempting move — exempt `check_secrets.sh` by path, as
  the test file already is — was **rejected**: that is a 130-line blind spot in the one file that most
  needs scanning. The literals **moved into `test_check_secrets.sh`, where they execute as payloads**, and
  the header now points at them. DEC-0040 applied to the gate itself: *prose does not execute.* The gate
  scans 100 % of tracked files, including its own source.

### Evidence — because a green run proves nothing on its own (DEC-0039)

- **Blast radius measured before deciding:** deleting `ALLOW (1)` produced **6 hits across the entire
  tracked tree, all of them inside the gate's own header comments.** Every legitimate comment elsewhere
  (README's `YOUR_*` blocks, `influx.py`'s docstring, the handoff docs) already passed on its *value*. The
  exemption was doing **no legitimate work in this repo** — it was close to pure hole.
- **Planted-payload suite: 41 passed, 0 failed** (was 28). Seven new BAD payloads cover every comment
  marker form (`#`, `//`, `/* */`, ` *`, indented, no-spaces) plus a commented constructor line; six new
  GOOD payloads are the same placeholder/prose/empty values wearing a comment marker.
- **Mutation test:** re-adding `ALLOW (1)` turns the suite **red — 7 LEAKED**. The fix is load-bearing and
  the test can actually fail.
- **Full-history scan: 0.** Every blob that ever existed in this repo (**333 unique, all refs**) was
  scanned for a commented credential. None. **The hole was never exploited** — nothing needs revoking, and
  no history rewrite is warranted. Positive-controlled: the same scan with the gate's own files re-included
  finds the 11 known header examples, so the scanner demonstrably sees things. (The first version of that
  scan reported a false "0" because `git` was silently not running inside the loop and `2>/dev/null` ate
  the error — caught only *because* the positive control was run. Same lesson, third time in one session.)
- **The gate blocked this session's own ADR** on first draft (4 hits — it quoted the payloads verbatim).
  The literals were removed rather than exempted.

### Also

- **PR #34 merged** — S39's work (DEC-0043 root logger, DEC-0044 nibble theory) landed on `dev`. It had
  been sitting open and green since S39; the session-start hook flagged it.
- 72 pytest tests still green. **Prod untouched** — still `:v2.0.6`, `RestartCount: 0`. This session
  changed no runtime code, only the commit-time gate and its docs.

---

## [S39] — 2026-07-13 — the root logger nobody overrode, and a theory that did not survive its own test

> **Two findings, one shipped fix, and one filter deliberately NOT built.**
>
> A routine post-deploy health check on `:v2.0.6` found prod emitting **15 logging-error tracebacks
> (~515 lines) to stderr on every container start**. Root cause: weewx's own defaults point the **ROOT
> logger** at a syslog handler on `/dev/log` — a socket that does not exist in a container. Our
> `logging.additions` had always overridden the `weewx` and `user` loggers, but `weewxd` and
> `weeutil.*` are in **neither** namespace, so they fall through to root and blow up there.
>
> The louder half is cosmetic (bounded burst; steady state is still 0 lines/90 s, so DEC-0041 holds).
> **The quieter half is not:** `weewx.log` has *never* contained a single `weewxd` or `weeutil` line —
> no version banner, no config path, no group list. Those records were not noisy, they were **lost**,
> and the failure announced itself only on a stream nobody reads. Fixed with a `[[root]]` override plus
> a build-time assertion, and verified A/B inside the real container: with the fix, `weewxd INFO
> Starting up weewx version 5.4.0` lands in the file for the first time. **DEC-0043.** Ships in v2.0.7.

**The coupling filter was on the S39 plan. It is not being built, and that is the bigger result.**

The inherited task was a "cross-sensor consistency filter" from dashboard S69: *a humidity move
>6 %/min with temperature essentially flat is physically impossible*, reported 3-for-3 with 0 false
positives. Underneath it sat an unproven mechanism — the **nibble theory**: the ISS message-type nibble
(`pkt[0] >> 4`) takes a bit flip, so **another sensor's payload is decoded as humidity**. S69 proposed a
falsifiable arithmetic test and never finished it. S39 finished it. **DEC-0044.**

- **The theory's arithmetic contradicts its own story.** Humidity is `0xA` = `1010`. Its single-bit
  neighbours are `0x2` (supercap), `0x8` (temp), `0xB` (undefined), `0xE` (rain). **Solar is 2 bits
  away; UV is 3.** So "a misdecoded solar/UV payload — that's why it's always midday" is not reachable
  by a single bit flip, and midday was the theory's headline evidence.
- **Every testable variant fails.** UV: implied ≈ 2× actual on *every* spike. Temperature: implied
  200–400 °F. Supercap: fails where testable.
- **The solar "match" was fitted noise.** Recovering a raw reading from a 1-minute average needs
  `raw = n·spike − (n−1)·baseline` with `n` unknown; letting `n` float over {1,2,3} scored 12/28, but
  the winning `n` came out uniformly **{1:4, 2:4, 3:4}** — a meaningless parameter. Against **2000
  shuffled pairings**: true 43 % vs chance 35 %, **p = 0.248**.
- **This is structural.** The free parameter exists *because* the archive averages, and it is precisely
  what manufactures false matches. **No analysis of 1-minute data can settle this** — and InfluxDB
  stores the same 1-minute records (checked: bucket `weewx`, retention infinite).
- **The filter's own premise is weak too.** "Temperature essentially flat" describes **90 % of all
  minutes** (66,743 of 74,538 at |ΔT| ≤ 0.1 °F), so the flatness test discriminates almost nothing. And
  every spike visible in the archive implies a *raw* glitch of 16–37 %RH — **already rejected by
  DEC-0029's existing 10 %RH-per-reading cap**. The filter would have targeted a residual we never
  showed exists.
- **The cited false-positive test was not evidence.** The 2026-05-23 "gust front" shows a maximum
  humidity move of **1.0 %/min** in our archive (90 %RH, 50 °F, wind ≤ 2.5 mph — a calm, saturated
  day). Any threshold spares it.

**So: instrument, don't filter.** The decisive instrument was already in the code — **`log_humidity_raw`**,
an upstream option (Luc Heijst's) nobody had switched on. It logs `(pkt[4] << 8) + pkt[3]`: **both raw
payload bytes**. With a real `pkt[4]` there is no averaging and no free parameter, and the inversion
becomes deterministic. Armed in the live `weewx.conf` (INFO → file handler only; prod declares no
console handler, so it adds nothing to stdout and carries no DEC-0036 risk). It activates on the next
restart, and the next midday spike settles the question.

**Also:** `iss_channel = 5` with every other channel `0` — there is exactly **one** transmitter, so
"bleed from another *transmitter*" was never possible. A type-level misroute inside the ISS's own
packets is the only mechanism the hardware permits.

**Tests:** 67 → **72**. The five new ones assert the `[[root]]` override in both shipped configs and the
Dockerfile's build-time assertion; deleting the `[[root]]` block fails three of them (planted-payload
check, per DEC-0039).

---

## [S38] — 2026-07-13 — v2.0.5 → **v2.0.6** SHIPPED; the gates now execute instead of asking nicely

> **v2.0.5 was an incomplete fix, and v2.0.6 finishes it (DEC-0041).** v2.0.5 moved the console log
> handler to `WARNING` and I claimed that made weewx's stdout nearly silent. **It did not.**
> `report_services = weewx.engine.StdPrint` `print()`s **every LOOP packet straight to stdout**,
> bypassing the logging module entirely — no log level touches it. It was writing **~25 MB/day** into
> the very pipe that froze prod for 7h18m, and because it is a **weewx stock default** it was in the
> baked image *and* our `weewx.conf.example`, so **every downstream user had it too**.
>
> Found by finally checking the thing nobody had checked — the actual `log.db` sizes (needs root):
> `weewx-rtldavis-v2` had accrued **15 MB in 14 hours**. The mitigation had been *reasoned about from
> the architecture* instead of *measured at the source*. One `sudo du` would have caught it.
>
> **Fixed everywhere:** prod (`report_services =`, restarted — stdout growth now **0 lines/60 s**,
> was ~36); the baked image config, **with a build-time assertion that fails the build if the edit
> no-ops**; and `weewx.conf.example`. Shipped as **v2.0.6**. Also removed `/weewx`, a container **dead
> since 2026-05-04** still holding the **largest `log.db` on the box (47 MB)** — dead containers keep
> their log store forever.

**The headline: `v2.0.5` and `latest` are on Docker Hub.** Downstream users had been getting the
**stock driver** (DEC-0031) *and* the **console-handler freeze hazard** (DEC-0036) on every `docker
pull` since 2026-07-08. That stopped at 12:55 today. It is the only item in this session that had an
ongoing external cost, and it is closed.

**Why v2.0.5 and not v2.0.4 (DEC-0038).** The `v2.0.4` image on the NAS was built at **15:44 on
07-12 — eight hours before the freeze that produced DEC-0036**, so it never contained the fix the
release was being cut for. A rebuild was mandatory either way. Republishing different content under
`v2.0.4` would have made one tag name two different images, which is the *same* lie as DEC-0031 and
DEC-0034 — the artifact asserting one thing and being another. `v2.0.4` was never on Hub, so nothing
public breaks. Prod deliberately stayed on `:v2.0.4` **at that point in the session** — the delta was
behaviorally nil here (prod's `weewx.conf` has no console handler at all — the config drift that spared
us), and redeploying prod unattended, hours after a seven-hour outage, to fix something that did not
affect prod, was the wrong trade. *(Resolved later the same day: once v2.0.6 existed and the owner was
present, prod was deployed to `:v2.0.6` in an attended window and `prod-baseline-20260713` was tagged —
see below.)*

**S37 never landed, and that is its own lesson.** All of S37 — three ADRs, the fork-identity audit, the
duplicate-frame confirmation — was sitting in **draft PR #23** and had never merged to `dev`. CI green,
branch pushed, nothing shipped. Found and merged at the top of this session. It is the direct
motivation for the session-start hook below.

**The secret gate, hardened and PROVEN (DEC-0039).** The bug class, stated once: *an allow term that
can match anywhere on the line is not an allow-list, it is an escape hatch — the secret sits on the
left and the excuse on the right.* `token = REAL  # falls back to os.environ` passed the old gate
clean. Every allow term is now **anchored** or **positioned against the key the detector matched**, and
the `grep -n` prefix bug is fixed at the root (bash parameter expansion; the allow-list runs on raw
lines) rather than compensated for with `^[0-9]+:` anchors. Ships with
`scripts/test_check_secrets.sh`: **13 planted payloads that must be caught, 14 good lines that must
pass, plus a clean-tree check — 28/28.** It runs in CI *before* the scan. It earned its keep
immediately by catching a hole in **the fix being written to close the previous hole**, and then by
catching the ADR that described it. CI also now runs the **67 unit tests**, which it never did.

**The cross-repo question, answered (DEC-0040): the gap is an ENFORCEMENT gap, not a documentation
gap.** All three options on the table (shared ops repo / vendored fragment / status quo) distribute
*documentation* — and in the worst incident **the rule was already written down**. "`docker logs`
always with `--tail N`" was in `CLAUDE.md` *and* `CONVENTIONS.md` before the freeze; it was followed
for thirty-odd sessions and broken once, and once cost seven hours. **Prose does not execute.**
Decision: **no master repo.** Build a shared enforcement layer instead —
- `~/.claude/hooks/docker-guard.sh` (`PreToolUse`): blocks bare `docker logs` and `docker stop`.
  **19/19 tests**, including a `docker logs` hidden inside `ssh nas "..."` that beat the first draft.
  Verified live.
- `~/.claude/hooks/eaglehunt-status.sh` (`SessionStart`): reports draft PRs, stranded branches and
  uncommitted work **across all three repos**. **On its first run it found a live stranded draft PR in
  the dashboard (#22)** that nobody knew about.
- Branch protection: **`enforce_admins: true`** on `main` and `dev` (checks: `secret-scan`, `lint`,
  `tests`). The S36 bypass is now mechanically impossible, for everyone.

**The Synology `db` log driver cannot be capped — proven, not assumed.** A container run with
`--log-opt max-size=1m` emitted 200,000 lines and **kept all 200,000**. `db` is a proprietary Synology
driver with no published options; the cap is *unsupported*, not undocumented. The daemon accepts the
option and discards it — **the third time in one session** that "the configuration was accepted" did
not mean "the configuration does anything" (cf. the green secret gate, the silent compose clobber).
Also demonstrated, rather than inferred, the DEC-0036 mechanism: retrieving that log **hung for over
three minutes**, and that was a `--tail`-bounded read. Prod was never at risk.

**Provenance, outward half — SENT.** After three sessions of "the fork hasn't given anything back," it
has. Both upstreams forked separately (our distribution repo correctly stays a normal repo, not a GitHub
fork), both PRs **open**:
- **[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22)** — the rain-counter
  wraparound. Proven against LloydR's own numbers from issue #15: `115 → 49 → 115` now yields
  missing/missing instead of a phantom 1.28″, while genuine wraparounds still work (`127 → 0` = 1 tip).
- **[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1)** — five fixes, led
  by a **silent TLS-verification bypass** (`ssl._create_unverified_context()` applied unconditionally to
  every https endpoint, so every user posting to InfluxDB Cloud has certificate verification off and
  their token on an unauthenticated connection). That repo's first-ever PR.
- **[The issue-#15 comment is POSTED](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128)**
  (owner-approved, 2026-07-13) — **the first comment on that thread since 2022-11-14.** It explains the
  duplicate-frame mechanism, the wraparound bug, and that the phantom **rainRate is ISS-side, not a driver
  bug** (DEC-0042) — which the three people there had been hunting in software for four years.

**DEC-0042 — the phantom rainRate is ISS-side, and the rainRate thread is CLOSED.** Reconstructed from a
2026-05-29 DB backup that happened to predate our own S36 correction: no real rain that day at all; the
rate held **03:22–03:37 UTC, sharp on and sharp off** — exactly the ISS's ~15-min timeout; the implied tip
interval stayed in a tight **8.5–10.0 s** band; and **the tip counter never advanced** (`rain = 0.0000` in
all sixteen records). Decisive: reaching those raw values from the `0x3FF` "no rain" sentinel needs **~6
bit-flips in every packet for sixteen consecutive minutes** — RF corruption gives *one* bad packet, not a
coherent stream. **The ISS sent them.** Conditions both events: overnight, 94 % RH, 1.7 °F dewpoint
spread, 0 mph wind. **Condensation trips the reed switch enough to start the rate timer, never enough
water to tip the bucket.** So DEC-0033/0035 are now explicitly *bounded* — they explain the rain
**counter**, and no decode-layer filter will ever touch the rate. **The next step is physical, not
software.** Method lesson kept in the ADR: this was only answerable because a backup predated our own
correction — **snapshot the affected rows BEFORE a retrospective correction, not after.**

**Prod finished the session on `:v2.0.6`, and `main` == prod again.** Recreated 11:09 EDT; verified
`driver version is 0.20+ws.1 (fork of lheijst 0.20)`, `sensor_qc True`, `influx service version 0.20+ws.1`,
stdout **silent**, every uploader publishing, `RestartCount: 0`. `prod-baseline-20260713` tagged, which
restores DEC-0011's *`main` = production truth* invariant that S38 deliberately broke for a few hours.
Prod's bind-mounted `influx.py` also caught up with the repo (it had drifted — DEC-0031's class again:
the running copy still had `VERSION = "0.20"`, the unconditional `_create_unverified_context()`, and
per-record `loginf` spam; not a live exposure, since the endpoint is plain http).

---

## [S37] — 2026-07-12→13 — A 7-hour prod freeze, the CRC question answered, and the fork finally admits it is one

Three unrelated things collided. In order of how much they matter.

### The outage: weewx froze for 7h18m (DEC-0036, ERR-0003)

At 23:53:45 weewx stopped doing anything and stayed that way until 07:12. **It did not crash** — both
processes alive, container reporting `Up`, and **no error or traceback ever written, because the thing
that was stuck was the logging.** `weewx_monitor.py` emailed at 00:15 (22 min in — the monitor worked);
the owner was asleep.

- **Established:** weewx's main thread blocked in `pipe_wait`; the Docker daemon's path for *that one
  container* was wedged (`logs`/`exec`/`kill` all hung, other three containers healthy); a **bare
  `docker logs` with no `--tail`** had been hung since the previous day against Synology's SQLite
  `log.db`. Only `synopkg restart ContainerManager` cleared it.
- **NOT established, and the first answer was wrong.** The initial diagnosis — "the INFO console handler
  filled the stdout pipe" — is **false for this station**: the live `weewx.conf` has *no console handler
  at all*. `pipe_wait` covers a blocked pipe **read or write**, and it was read as a write without
  checking. **Mechanism recorded as OPEN.** No causal story was invented to close the ticket.
- **But the console-handler finding is real for the image we publish.** `logging.additions` (baked in by
  the Dockerfile) *does* set the console handler to INFO. Prod escaped only because **the live config has
  drifted from the repo**. Every downstream user has the hazard we did not — the same shape as DEC-0031.
  Fixed to `WARNING`; it reaches users only when v2.0.4 is pushed.
- **Recovery + backfill (ERR-0003):** ~438 one-minute records were **never captured** (nothing was
  cached; the restart discarded nothing). Backfilled 29 records from the co-located WeatherLink Live
  console via the WU history API — same ISS, **different receiver, 15-min cadence** — into both stores,
  flagged in-band `backfill = 1`. The window was dry and dead calm, so the loss is small.

### The CRC question is answered — and the test that answered it first was broken (DEC-0035)

The S36 Lloyd test reported **0 suspicious pairs** over 1,863 frames, with gaps perfectly quantized at
the 2.8 s ISS period. It looked like a decisive null. **It was an artifact — the instrument was blind to
the thing it was built to detect**, twice over: it parsed the driver's `data:` lines, which are emitted
*after* `main.go` has already dropped every duplicate; and its stated premise ("we see spurious frames
even when they fail CRC") is false, because `protocol.go` L218 bails on CRC failure *inside the Go
binary*.

Counting Go's own `duplicate packet:` lines instead: **61 frames arriving 1.4–10 ms (median 2.0 ms) after
a byte-identical frame — ~722/day.** A Davis ISS transmits every 2.8 s and cannot transmit twice 2 ms
apart. **The receiver manufactured them.** DEC-0033 is confirmed on our hardware (LloydR's gap was
262 µs; ours ~2 ms). The 712 duplicates at 2.8 s are just the transmitter repeating an unchanged payload.

This **meets the owner's precondition for the upstream post** (he wanted local confirmation first). The
post is still **not sent** — what remains is prose, in his voice, on his explicit go.

### The fork admits it is a fork (DEC-0034)

We shipped four GPLv3 files with our patches on top and said so **nowhere**, while `rtldavis.py` reported
`DRIVER_VERSION = '0.20'` — stock upstream — carrying +263/−51 lines. Every other link in the chain had
done this properly: Luc documents his merge in the header, and Vince Skahan added a dated
`# 20-12-2025 patched by...` block to the very same file. We inherited the convention and skipped it.

- **GPLv3 §5(a) modification notices** on `rtldavis.py`, `influx.py`, `ogoxeUploader.py`, and `wcloud.py`
  (whose only change is an SPDX line — recorded honestly).
- **Versioned honestly:** `0.20` → **`0.20+ws.1`** (PEP 440 local version) in the driver and the influx
  uploader. The driver now logs `(fork of lheijst 0.20 … not stock upstream)`, which also replaces the
  ad-hoc `RTLDAVIS_DRIVER_MARKER` canary — stock upstream cannot print that line.
- **`CHANGES-FROM-UPSTREAM.md`** — the full inventory, built by diffing against the real upstream
  sources, not from memory. It turned up **more than expected**: `influx.py` carries **five** patches, not
  the one we thought — including `e.read.decode()` (missing parens: the HTTP error handler raises
  `AttributeError` instead of reporting the error) and an unconditional `ssl._create_unverified_context()`
  on https. `rtldavis.py` holds **four** real upstream bugs beyond the rain filter, including a windDir
  branch that never populates wind data and a `NameError` crash path.
- **README rewritten** — it read as though we ship Luc's driver. We don't.

### Also

- **ERR-0001 amendment / DEC-0037** — the phantom-rain correction never propagated to the *derived*
  fields. The dashboard's S70 handoff caught `dayRain_in` still at **1.84″** against a corrected 0.56″;
  auditing found **`rain24_in` (1.84″) and `hourRain_in` (1.28″ — entirely phantom) were wrong too.** All
  three recomputed from the corrected SQLite series and rewritten in InfluxDB (5,394 points, in place,
  idempotent). New rule: *a retrospective correction must propagate to every field derived from it.*
- **Debug state reverted** (`debug_rtld` → 1, `user` logger → INFO). `qc-capture` on the NAS is gone.
- **Cross-project handoff** written for the dashboard + HLF (advisory; **no changes made in their
  repos**), carrying the owner's open architectural question about harmonizing shared NAS-level assets.

*Two confident, internally-consistent, wrong conclusions were reached and retracted in this session — the
"decisive null" and the console handler. Both collapsed the moment the actual artifact was inspected.
Recorded because the pattern matters more than either error.*

---

## [S36] — 2026-07-12 — v2.0.4 SHIPPED: SensorQC live; the driver-clobber found and killed; rain errata closed

The deploy that three sessions had staged and never shipped. Triggered by a handoff from dashboard
session S69, which had walked into this repo's territory, changed the live station, and found that the
bug it was chasing was already fixed here and never deployed. **Prod is v2.0.4; the bad data flowing to
WU/CWOP → NOAA MADIS (where it is immutable) has stopped.**

- **The handoff's recommended deploy path was wrong, and finding out why was the session.** It advised
  hot-fixing the driver by `scp`-ing to the bind-mounted `weewx-data/bin/user/rtldavis.py`. That path is
  **not what weewx imports** — `weewxd` loads `user.*` from the baked venv — and the running container
  had **no `rtldavis.py` mount at all**. The "fix" would have been a silent no-op.
- **The real find: `docker-compose.yml` was mounting the STOCK driver over the baked one.** Line 33 (and
  line 47 of the **public**, committed compose) bind-mounted `weewx-data/bin/user/rtldavis.py` — the
  stock driver `weectl extension install` lays down — straight over the patched one. Prod escaped it only
  because the live container was hand-run without the mount; **every downstream user of the published
  image was running the stock driver** (no rain filter, no SensorQC), regardless of image contents. This
  is the run-time twin of the S30 build-time `cp` clobber. Removed, with a "do NOT re-add" note at the
  exact line. → **DEC-0031** (driver is BAKED, never mounted; supersedes DEC-0004's driver half).
- **v2.0.4 built + deployed** (native amd64 on the NAS, `docker kill` per DEC-0008). Verified against the
  **running process**, not the version tag: `import user.rtldavis` → `SensorQC: True`, `sensor_qc True` in
  the log, `RestartCount: 0`, no driver mount. Reception came back **75–80%** (up from 63–70%). `:v2.0.3`
  retained for rollback. The live `docker-compose.yml` now genuinely describes production (it still said
  `:rw250-test`, an image two releases stale — a loaded gun for any future `compose up`).
- **Rain errata closed — all three phantoms, both stores.** A full-history sweep of InfluxDB and the
  SQLite archive finds **exactly three** implausible rain points ever. ERR-0002 (**new**, 2026-05-25
  23:22 EDT, +1.28" — a bit-7 flip; S69 spotted it, re-verified from scratch here) is now logged and
  corrected; ERR-0001's long-pending InfluxDB correction is finally applied. Both stores now agree
  exactly (2026-07-04 = 0.56", 2026-05-25 = 0.06"), which fixes the public water-balance charts.
  The "no `influx` CLI on the NAS" blocker in STATUS was **false** — there is one in the container.
- **DEC-0032 — retrospective correction: correct to the KNOWN value, flag it in-band.** DEC-0006's
  null-on-rejection rule governs the **runtime filter**, not retrospective correction. The phantoms are
  bracketed by zeros for ±20 min, so `0.0` is a *known fact* and `NULL` would have understated what we
  know. Corrected points carry a sparse **`rain_qc = 1`** flag (3 points in all of history; InfluxDB is
  schemaless, so it costs ~nothing and normal queries never see it) — WMO/MADIS practice, and it gives
  the dashboard its "corrected" marker without a parallel list. `DATA_ERRATA.md` stays narrative truth.
  → **INTERFACES.md** documents `*_qc` as an optional sparse field + pins the `record,binding=archive`
  series key.
- **`scripts/check_secrets.sh` never worked — fixed.** The allow-list ran with `grep -viE`; the `-i`
  erased the `[A-Z]` terms that carry the whole constant-vs-literal distinction, so the ALL_CAPS rule
  (meant to allow `= FOO_KEY`) also swallowed any unquoted lowercase literal — i.e. essentially every
  real secret written without quotes. **The gate was green because it caught nothing.** Now
  case-sensitive (the secret pattern keeps `-i`), plus two further holes closed that were live here *and*
  upstream: `# ` matched a comment anywhere on the line, and the docstring rule passed a capitalized
  single token. Verified 6/6 planted forms blocked, whole tracked tree clean. (Ports the dashboard's
  DEC-0063.)
- **The CRC question answered — DEC-0033 (and a retraction).** Chasing the owner-wanted community bug
  report, we first concluded the corruption *must* be transmitter-side, reasoning that CRC-16 cannot
  miss a single-bit error (verified: 0 of 64 single-bit flips of a valid 8-byte message pass).
  **That inference was invalid** — "catches all single-bit errors" does not imply "catches all errors".
  Raw packets posted by user *LloydR* in upstream issue `lheijst/weewx-rtldavis#15` settle it: two frames
  **262 µs apart** (a Davis ISS transmits every ~2.5 s), differing in **4 bits**, **both passing CRC** —
  the error pattern is a valid codeword. So one transmission is being decoded twice: the *receiver*
  makes the second frame. Model: the rtldavis Go demodulator emits spurious near-duplicate frames; most
  fail CRC and are dropped silently, ~1 in 65,536 passes and delivers garbage. The driver's dedup
  (`data != self._last_pkt`) is **exact-equality**, so a *corrupted* near-duplicate is by construction
  not a duplicate and sails past it. DEC-0029's original stated cause was right; DEC-0033 **confirms**
  it. Both rtldavis.py comments that had propagated the retracted claim are fixed.
- **The upstream contribution is drafted but NOT posted, and held out of git** (public repo). Research
  found issue #15 open since **Oct 2022** with three users reporting this exact symptom class and no
  root cause — so this is a **comment on their thread, not a new issue**. Our analysis explains *their*
  data: LloydR's counter values (115→49→115) run through the upstream handler give 0.62" + 0.66" =
  **1.28"**, matching the "1.3 inches" he reported in 2022. (The handler is wrong twice: once on the
  corrupt jump, once when the sensor returns to the truth.) Maintainer is responsive (commented
  2026-07-09); LloydR's PR #19 covers wind/temps, not rain, so we complement it.
- **`ops/find_duplicate_frames.py` — the "Lloyd test"**, to confirm the mechanism on our own hardware.
  Key property: the driver logs the raw `data:` line **before** the CRC check, so spurious frames are
  visible **even when they fail CRC** — this answers in hours, not weeks. Prod temporarily runs
  `debug_rtld = 2` + `user` logger at DEBUG to feed it (**revert steps in STATUS**).
- **Cross-repo handoff written** — `docs/handoffs/S36-to-eaglehunt-dashboard.md`: answers all three of
  dashboard S69's open questions, documents the new `rain_qc` contract, and returns a reciprocal finding
  (their secret gate still has two live holes we closed here).
- **Doc staleness swept:** ARCHITECTURE §6 claimed the running image was `rw250-test` and the Dockerfile
  "an rw350 experiment" (both stale since S30); CLAUDE.md + CONVENTIONS named the same dead tag. All now
  state the real image and the baked-driver rule. `weewx.conf.example` reconciled with the live station
  (S69's service reorder + tightened StdQC bounds); the stale DEC-0029 comment in `rtldavis.py` fixed.

## [S35] — 2026-07-09 — Docs diet (DEC-0030): tiered session read, DEC index+full split, CHANGELOG roll

Docs-only; no code, no prod change. Ports the family docs-diet pattern — born on the dashboard
(dash S57, its DEC-0081; recipe at `eaglehunt-weather-dashboard:docs/reference/docs-diet-playbook.md`),
proven on hyperlocal (its S143, DEC-0095) — to this repo, closing the three-repo alignment loop.
Session boot drops from ~130 KB ≈ 32K tokens to ~33 KB ≈ 8K tokens. **Invariant honored: text moved
verbatim, nothing rewritten or deleted; all rehomed files passed `scripts/check_secrets.sh` (public repo).**

- **DECISIONS split:** `docs/DECISIONS.md` is now a one-row-per-DEC **index** (+ open/deferred
  list); full append-only bodies moved verbatim to `docs/DECISIONS-FULL.md`. New DEC = full body
  there + index row. Noted explicitly: DEC-0018–0020 were never assigned (numbering gap).
- **CHANGELOG roll:** this file keeps ~3 live sessions; `[S31]` and earlier (back to `[Pre-S16]`)
  moved verbatim to `CHANGELOG-ARCHIVE.md` (append-only, same format).
- **CLAUDE.md doc map → two tiers** (Tier 1 always ≈ 33 KB; Tier 2 on demand, anti-loophole rule:
  *"working near it" means read it*), plus the stale-checkout guard the S35 pickup itself tripped
  over: **current docs live on `dev`** — read from `dev`'s tip if the local checkout lags.
- **Session-close ritual extended:** STATUS prune (shipped → CHANGELOG pointer, settled → DEC
  pointer), CHANGELOG roll, and a secret scan over anything a doc move rehomes.
- **ROADMAP reconciled + collapsed:** P0/P0.6/P1 → DONE pointer summaries (v2.0.3 shipped S32;
  code-quality fixes landed S24–S28); P1.5 → resolved by DEC-0029, deploy rides v2.0.4.

## [S34] — 2026-07-08 — S33 sensor-QC merged to `dev` (PR #17); health check clean; parked stable on v2.0.3

Short close-out session; owner goal: end in a place that holds for days/weeks. No production change.

- **Health check (read-only): clean.** Container on `:v2.0.3`, up 16 h, `RestartCount=0`;
  `rxCheckPercent` 68–80% live (6 h mean 74.6%, min 50, **360/360** minute rows — no archive gaps);
  **0 rain rejections ever**; monitor polling normally.
- **PR #17 merged → `dev`** (merge `db763c8`, checks green: secret-scan + lint): `SensorQC`
  decode-layer filter (DEC-0029) + DewpointCacher timeout-null (closes DEC-0022). **Staged, not
  deployed** — the driver is baked; ships with the owner-run v2.0.4 rebuild.
- **Rebuild pre-verified:** the `dev` Dockerfile COPYs the patched `rtldavis.py` into the venv
  (L99) with the S30 clobber trap explicitly guarded (L101 note) — the v2.0.4 image will genuinely
  contain `SensorQC`.
- **Reception Layer B (DEC-0024) decided: waits for v2.0.5.** v2.0.4 stays single-purpose so its
  live-verification and rollback stay unambiguous; Layer B is cosmetic + log-bloat relief, still
  undesigned (No-Rewrite), and the S31 monitor fix already made the reception emails honest.
- **Backlog: tuning infrastructure idea captured** (owner, S34) — live-tuning control panel and/or
  a statistically sufficient sweep plan (ties into DEC-0017); framing deferred to a future session.



## [S33] — 2026-07-08 — Bad-packet root cause + decode-layer sensor plausibility filter (DEC-0029, on `feature/s33-sensor-qc`, off `dev`)

The owner-priority bad-packet session. Evidence-first (owner: "pull the raw packet logs first;
let's be methodical"), then design approval, then code. **Not yet merged or deployed** — the driver
is baked, so this ships with the next image rebuild (v2.0.4).

- **Post-release health check (read-only): clean.** Container on `:v2.0.3`, `RestartCount=0`
  (expected post-reboot start 07:02 EDT), 0 rain rejections ever, monitor WINDOW 21/21 (100%).
- **Evidence dead end that matters:** the `RAW_CHANNEL_PAYLOAD` log lines never contained packet
  payloads — only frequency-hop metadata — and the v2.0.3 upstream-default binary silenced even
  those (weewx.log 16.6 → 7.5 MB/day). **No bit-level packet capture exists**; the archive DB
  (68,877 records, 2026-05-19→07-08) became the evidence base.
- **Root cause CONFIRMED from the archive** (details in DEC-0029): 18 one-minute **outHumidity**
  glitch spikes under flat radiation + flat temp, deviations clustering at 25.6/3 and 12.8/2 —
  the bit-7/bit-8 flip signature of the raw %×10 field; a physically impossible **UV 16.29** under
  overcast; midday-only pattern shown to be a **selection effect** (night glitches land >100% RH →
  StdQC nulls → carry-forward masks). **outTemp/wind archives clean** — dashboard temp + 201 mph
  wind spikes ride the unfiltered loop-JSON path (`LoopJsonWriter` runs before all QC). S30's
  suspected `MAX_WIND_DELTA` unit bug **disproven** (post-StdConvert = mph, correct).
- **Fix (DEC-0029): `SensorQC` decode-layer filter in `rtldavis.py`**, applied in `_data_to_packet`
  (rain's choke point): Davis-spec bounds (temp −40..65 °C, hum 0..100%, wind 0..89.4 m/s, UV 0..16,
  rad 0..1800 W/m²) + per-reading delta with baseline-resync (temp 4 °C, hum 10%, wind 20 m/s, UV 8;
  **no delta for radiation** — cloud edges are genuine). Honest null on rejection (DEC-0006), logs
  `"rejecting implausible value"`, rejected wind also nulls same-packet `wind_dir`. Config:
  `sensor_qc` master switch + `qc_<field>_max_delta` overrides (documented in `weewx.conf.example`).
- **DEC-0022 closed: `dewpoint_service.py` carry-forward → timeout-null.** The temp/hum/rad/UV cache
  still bridges the message-type rotation but expires after 300 s of sensor silence; dewpoint/
  heatindex computed only from fresh values. Failed sensors now read null, not frozen.
- **Tests:** `test_sensor_qc.py` (16, recorded signatures: +25.6% humidity flip, UV 16.29, 201 mph)
  + `test_dewpoint_timeout_null.py` (6). **Suite 85/85**; `ruff check` clean; secret scan green.

## [S32] — 2026-07-08 — v2.0.3 RELEASED (`v2.0.3` + `prod-baseline-20260705`); S31 monitor live; Gmail app-password rotation

**v2.0.3 released end-to-end.** Soak day 4 = clean, so the S30 hold cleared: 24 h `rxCheckPercent`
avg **75.4%** (1427/1429 records populated, min 50 / max 105 — the known floor-division cosmetic),
**0** rain-glitch rejections since the Jul-5 deploy, `RestartCount=0`, and the container rode out an
*unplanned NAS reboot* (~06:57) with a clean dongle handoff — the strongest soak evidence we could
have asked for. Only third-party upload blips (Windy/WOW 429s, a transient OWM outage). Steps:

- **PR #15** — `main`'s independent S26 secret-gate commits (PR #7) conflicted with `dev`'s (PR #6) on
  `ci.yml`, making the promotion PR un-mergeable; merged `main` into `dev` once, keeping `dev`'s
  DEC-0027 `ci.yml` (no `ruff format` gate). *(First attempt took the wrong side of the conflict —
  caught by CI's lint job doing exactly what DEC-0027 built it for, fixed before merge.)*
- **PR #11 merged** — `dev` → `main` (`f64f8d8`); `main` = production truth again.
- **Tagged `v2.0.3` + `prod-baseline-20260705`**; **GitHub release** published with the S30-drafted
  notes; **Docker Hub push `:v2.0.3` + `:latest`** (same digest `9dfd9b57…`, 281 MB) — the first
  public image that actually contains the driver fixes (rain filter, `rxCheckPercent` H2, honest-null
  wind, clobber fix).

**S31 monitor deployed + verified live — after diagnosing a reboot-broken boot task.** The morning's
NAS reboot restarted the `weewx_monitor` esynoscheduler task as a **non-root user**: its
`/etc/sudoers` append got Permission-denied and `sudo -u weewx-monitor` failed every 5 min ("a
terminal is required"), so the monitor was **down 06:56→17:28** with sudo-spam filling its log. Owner
reset the task user to root. Since the monitor was down, the S31 deploy needed no kill: scp'd `dev`'s
`weewx_monitor.py` (sha `23dfa03d…` verified; backup `weewx_monitor.py.bak-20260708-105410`), owner
ran the task, and the new code came up clean — pidfile written, incremental byte-offset polling,
startup email delivered ("Eagle Hunt PWS": `STATION_NAME` is now set, closing that housekeeping
item). First 6 h dropped-packets summary due at the next 00/06/12/18 boundary.

**Security — Gmail app password exposed in public history; rotated same-day (DEC-0028).** Found the
monitor's Gmail app password hardcoded in the legacy NAS `weewx_monitor.sh` *and* in two public-repo
history commits of `weewx_monitor.py` (`d2fb080` May 22, `eff3f56` May 24 — reachable from `main`+
`dev`, exposed ~6 weeks; the DEC-0012 gate scans trees/diffs, not history, so it never fired). Owner
revoked the credential, issued a replacement into the NAS `monitor.env` (via a clipboard-pipe
one-liner after interactive-prompt approaches failed through the `!` runner), and the monitor's
startup email verified SMTP auth on the new value. Legacy script's copy neutered to a placeholder.
**No history rewrite** — rotation kills the credential's value; force-pushing a public repo's history
doesn't un-leak it (DEC-0028).


---

*Older entries (S31 and earlier, back to [Pre-S16]) live in `CHANGELOG-ARCHIVE.md` — moved
verbatim, append-only (DEC-0030). Roll the oldest live entry there at session close once this file
exceeds ~3 sessions.*
## [S31] — 2026-07-08 — RF reception metric audited; daily email re-sourced from rxCheckPercent

**Audit finding:** the daily RF-reception email measured publish *liveness*, not reception. It counted
`Wunderground-RF: Published` log lines ÷ expected/min — a count padded by the freqError freq-hop
publishes (DEC-0024) so it reads ~100% even during real ~25% packet loss. Live proof: 14 straight
minutes pinned at "100%" while the driver's own `rxCheckPercent` ran 59–95% (median 75%); the metric's
only movement off 100% is a crash to 0% during a total stall. That bimodal 100↔0 behaviour, plus the
denominator churn (24→dedup→21) and the old ~150% reading, is why the numbers had been "all over the
place." The honest metric — the driver's `rxCheckPercent` (good CRC-decoded packets / theoretical max
per archive period) — was already in the archive DB; the email just wasn't using it.

**Layer A (monitor-only, no image rebuild):** re-source the daily summary from the archive's
`rxCheckPercent`. The email now reports packets **transmitted / received / dropped** plus hourly mean +
min — not "windows above a threshold." Verified against the live DB: 2026-07-06 = mean **75%**, 30,720
transmitted, **~7,701 dropped**. Read-only DB access with a safe fallback to the legacy scrape summary
on any hiccup; real-time `WINDOW` logging + outage alerting left unchanged (No-Rewrite, DEC-0014).
`tests/test_reception_db_summary.py` (+7); **suite 61/61**. Refines DEC-0024 (its epoch-dedup fixed the
*count*; this fixes the *source*). **Deploy = monitor restart (owner-run scp + `sudo kill`), not yet
done.** Driver-side follow-up (persist raw packet counts; fix the ~1–2 pt floor-division optimism)
folds into a later driver build.

**Reception summary cadence: daily → every 6 h (env-tunable).** A once-a-day midnight report was being
read the next morning — too late to act. The summary email now fires every `RF_REPORT_INTERVAL_HOURS`
(default **6** = 00/06/12/18 local; set 12 for twice-daily or 24 for the old daily cadence), aligned to
local-midnight blocks and reporting the window that just closed. Generalized `db_reception_summary` to
explicit epoch bounds + added `period_floor`/`period_label`; the formatter now labels the window and
lists only its hours. Verified live (mean 75%, ~1,900 dropped per 6 h window). `+2` tests, **suite
63/63**. Ships with the same monitor deploy as Layer A above.

**Also this session — CI lint made honestly green (DEC-0027).** The `lint` job had been red on every
branch (incl. `dev`) — a broken check erodes the "`main` = production truth" signal. Audited the debt:
27 `ruff check` findings (17 in vendored code, 10 ours) + `ruff format --check` wanting to reformat 25
files incl. the baked driver. Decision: lint what we maintain, don't police style or vendored code —
(1) dropped the `ruff format --check` CI gate (the codebase uses deliberate column alignment; the
driver is baked → reformatting it is No-Rewrite churn), (2) excluded vendored uploaders (`influx.py`,
`wcloud.py`, `ogoxeUploader.py`) via new `ruff.toml`, (3) fixed the 10 findings in our code
(`rtldavis.py` unused imports + bare `except`; `weewx_monitor.py` import split; test ambiguous `l`→`ln`;
`ops/*` unused imports). `ruff check .` now passes; driver logic + formatting untouched. Merged via PR #13.

---

## [S30] — 2026-07-05 — v2.0.3: driver fixes finally go live (clobber fix + build)

**Built (native amd64 on the NAS) and deployed to prod.** After deploy, `rxCheckPercent` went
NULL→real (**70–82%**) within two archive cycles — the driver's honest reception metric alive for the
first time since 2026-06-18, proving the clobber fix baked the patched driver. Packets flowing, clean
dongle handoff (no USB reset), old `rw250-test` image kept for rollback. *Still owner-gated: promote
`dev`→`main` + tag `v2.0.3`, GitHub release, Docker Hub push.*

The image folds in H1/H2/M3 (already on `dev`) plus:

- **Dewpoint service — wind honest-null (ported from the reviewed Jun-16 draft).** `_filter_wind` no
  longer substitutes the last cached `windSpeed` into a packet whose `windSpeed` is `None`. The Davis
  ISS transmits wind in **every** anemometer packet (`rtldavis.py:1122`), unlike temp/humidity/rain/UV
  which rotate across message types — so `windSpeed` is `None` only when the reading is genuinely absent
  (a "no sensor" raw `0,0` packet) or was just delta-rejected as a corrupt spike. In both cases an honest
  null is correct; a stale carried-forward value looks like live wind when there is none (e.g. a failed
  vane) and is harder to diagnose. Calm air still writes an explicit `0.0`, so charts stay continuous.
  Archive records aggregate many LOOP packets, so an occasional null packet does not blank the record;
  uploads omit nulls rather than sending bad data. **Temp/humidity/radiation/UV keep the carry-forward**
  for now — those rotating sensors legitimately miss most packets (DEC-0022 sensor-QC hardening, later).
  New `tests/test_dewpoint_wind_honest_null.py` (5 tests); **suite 54/54**.
- **receiveWindow reconciled (ARCHITECTURE §6).** Dropped the `Dockerfile` `sed 300→350` patch so the
  build ships the **upstream-default receiveWindow** — v2.0.3 carries only the proven software fixes, not
  the unproven rw350 experiment (its 24 h sweep stays backlogged). `main.go` is left unpatched.
- **Dockerfile clobber fixed — the driver fixes actually ship now (major).** `Dockerfile:101` did
  `cp /opt/weewx-data/bin/user/rtldavis.py …/site-packages/user/rtldavis.py`, overwriting the patched
  driver `COPY`'d one step earlier with the **stock** driver that `weectl extension install` lays down
  from upstream `src.tgz`. Since weewx imports `user.*` from the venv `site-packages/user/` (confirmed on
  the running container three ways: the weewx path resolver, `.pyc` presence only in that dir, and a
  content grep showing the live driver has **no** `rain_delta_tips` and the deadlocked H2), **every built
  image has shipped the stock driver** — no rain filter, no H1/H2/M3. This explains both open mysteries at
  once: `rxCheckPercent` NULL (stock's `pct_good_all` deadlock) *and* the July-4 phantom rain entering the
  archive (no live rain filter). Driver hot-swaps were landing in `data/bin/user/` — a path weewx does not
  import. Removed the clobbering `cp` (kept the `__init__`/`extensions` touches). With this, the v2.0.3
  rebuild bakes the patched driver → weewx imports it → the **rain filter, H1/H2/M3, and dewpoint
  honest-null go live for the first time**, and the public Docker Hub image finally contains them. *(The
  reception-metric fix and ERR-0001 were the NAS monitor + a DB edit, not the driver — those were already
  live.)*
- Bumped the `Dockerfile` header `v2.0.2 → v2.0.3` and refreshed the stale rtldavis `COPY` comment.
- **Committed `logging.additions` — the build was not reproducible from a clean clone.** `Dockerfile:80`
  `COPY logging.additions` referenced a file that was **untracked** (present only in the owner's checkout,
  never committed, not gitignored), so `docker build` from a fresh `git clone` failed at that step. Found
  when the v2.0.3 image was built on the NAS from the `dev` tarball. Also de-duplicated its contents (the
  `[Logging]` block had been accidentally appended twice). Now tracked → the image builds from a clean
  checkout on any host.

## [S29] — 2026-07-05 — RF-metric honesty, rxCheckPercent root cause, ERR-0001 correction

Turned the "how is reception really doing?" question into trustworthy answers, and reconciled the
July-4 rain glitch. Two owner-run prod steps deployed live (agent-guided, read-only-verified).

- **Reception "91%" was a denominator artifact — fixed + deployed.** The monitor divided the WU-publish
  count by a hardcoded **24**, but this ISS (Transmitter 4) transmits every ~2.8125 s → only ~**21.3**
  records/min are physically sent. Live measurement: **21.75/min**, ~2.78 s mean spacing, no multi-second
  gaps → **~100% reception**, not 91%. Set `WU_RF_EXPECTED` → **21** (env-overridable per station) and
  added `wu_pct()` (single source of truth, capped at 100). New `tests/test_reception_pct.py` (9 tests);
  **suite 49/49**. Merged **PR #10 → `dev`** (also carries the S28 M-A/L-B incremental read) and
  **deployed** (monitor restart); live log flipped `WINDOW: 22/24 (92%)` → **`WINDOW: 23/21 (100%)`**.
- **`rxCheckPercent` root-caused (dead since 2026-06-18).** The driver's own honest reception metric
  populated the archive 2026-05-26 → 2026-06-18 18:42 UTC (avg **67.5%**, the pre-LNA baseline), then
  went NULL. Traced to a **weewx engine reload at 2026-06-18 14:44 EDT** whose code carries the S24 "H2"
  `pct_good_all` deadlock (`rtldavis.py:1006` guards the assignment with `… and pct_good_all is not None`,
  but it's reset to `None` every period → can never pass). **Fix already on `dev`** (`:1011`,
  regression-tested); ships with the v2.0.3 image rebuild. (Reception genuinely improved ~70% → ~100% via
  the LNA between June and July — right when both honest metrics were dark.)
- **DEC-0025 — known-bad data: preserve-and-flag, never delete.** New public append-only
  **`docs/DATA_ERRATA.md`** + the reconciliation model (as-transmitted / errata / corrected best-estimate).
- **ERR-0001 applied — July-4 phantom honest-nulled.** The +1.28" 3 AM glitch (old driver, `rain_count=-64`
  → +128) was confirmed baked into the archive **and** the Weather Underground record (day total **1.84"**;
  MADIS almost certainly too — precip is barely QC'd downstream). Owner nulled the two 3 AM records
  (`dateTime IN (1783148640, 1783148700)`) + `weectl database rebuild-daily --date=2026-07-04`; July-4 rain
  **1.84" → 0.56"** — surgical (the day's genuine 0.56" evening rain preserved). InfluxDB copy still carries
  it (cross-repo follow-up); external WU/MADIS immutable, reconciled by the errata.
- **DEC-0026 — v2.0.3 confidence gate waived.** Cut the release with the rain fix baked in rather than wait
  weeks for a live glitch; the fix is already protecting prod, is tested, and the pipeline was validated
  end-to-end this session.
- **Housekeeping:** merged PR #10 (branch deleted). `dev` now carries rain + reception (metric + denominator)
  + governance + S24/S25 code-quality. **Next session ships v2.0.3** (image rebuild on Mac Docker Desktop →
  redeploy → promote `dev`→`main` + tag → GitHub/Docker Hub → live-confirm `rxCheckPercent` repopulates).

## [S28] — 2026-07-05 — Monitor incremental read (M-A/L-B) + branch cleanup

Release still calendar-gated (no real rain glitch yet); this session cleared the unblocked follow-ups.

- **P1 verified (read-only, live).** Rain wild-watch: **0** `rejecting implausible counter delta`
  events across the full log range (2026-06-05 → now) — the first real glitch still hasn't fired, so
  v2.0.3 stays parked. Reception Layer A confirmed live: WINDOW **88–100%**, 5-window avg **91–92%
  [OK]**, 0 bad windows; monitor healthy (PID alive under the esynoscheduler wrapper). Layer B
  signature still present live (driver emits `RAW_CHANNEL_PAYLOAD`/`FreqError` + double-publishes the
  same record epoch — exactly what Layer A dedups; weewx.log ~10 MB/day).
- **M-A + L-B: monitor incremental byte-offset read (PR #10 → `dev`, draft).** Replaced
  `get_linecount()` + `get_new_lines()` — which each re-read the whole (~10 MB/day, growing)
  `weewx.log` on every 30 s poll — with a single byte-offset read: `get_log_size()` +
  `get_new_lines(offset)` → `(lines, new_offset)` via one `seek()`. Fixes the O(n)-per-poll re-scan
  (**M-A**) and the double-open size/read race that double-counted appended lines (**L-B**, resolved
  for free by the `seek()`). Rotation (`get_log_size() < offset` → reset) + partial-line (hold back a
  line with no trailing newline) guards. New `tests/test_monitor_incremental_read.py` (6 tests);
  **suite 40/40**; secret-scan green; `lint` red (known pre-S24 ruff baseline, non-blocking).
  **Not yet deployed** — owner-gated (scp + `sudo kill`, same as Layer A).
- **Branch housekeeping.** Deleted merged remote branches `s20-governance-hardening` and
  `feature/influxdb-grafana` (moved off Grafana to Influx; its only driver-relevant bit — the
  wind-warmup one-liner `3f5470f` — was already in `dev`). `s27-p3-deployed` was already
  auto-deleted on PR #9's merge (stale local ref pruned). Remote-URL casing was already correct
  (both no-ops). Remote now: `dev`, `main`, `feature/rain-spike-filter` (kept for v2.0.3),
  `feature/s28-monitor-incremental-read`.
- **Still owner/calendar (→ S29):** review + merge + deploy PR #10; watch for the first real rain
  glitch → then cut v2.0.3; rotate the exposed WU key; set `STATION_NAME` in the NAS `monitor.env`
  (emails currently fall back to "My PWS").

## [S27] — 2026-07-05 — Land the secret gate + collapse the review stack onto `dev`

Tied up the S23–S26 PR backlog (five open, nothing merged). No prod/driver code touched; all the
review work landed on `dev`, and `main` got only the secret gate.

- **Secret gate now blocking (P1).** Merged **PR #6 → `dev`** (`90ef51b`) and **PR #7 → `main`**
  (`490e776`) — `main` previously had zero secret scanning. CI on both merge commits: `secret-scan` =
  pass, `lint` = fail (expected pre-S24 ruff, non-blocking to the gate). Then set **`secret-scan` as a
  required status check** in branch protection on `dev` + `main` (via the keyring token — the PAT's 403
  was a scope problem; `enforce_admins: false`, no required reviews). The DEC-0012 gate is no longer
  advisory.
- **Governance/review stack collapsed onto `dev` (P2).** The whole stack merges clean — the predicted
  `ci.yml`/`check_secrets.sh` conflict never materialized because the stack's S20 gate fix (`2a6327c`)
  is byte-identical to dev's #6 fix. Retargeted **PR #5** (`feature/s24-code-quality-review`, whose tip
  already carried reception-dedup + s23-governance + s24/s25) to base `dev` and merged it (`2c75c5e`),
  bringing all S18–S26 work — the rain fix, reception Layer A, the S23 governance docs (LICENSE/AGENTS/
  ASSESSMENT), and the S24/S25 code-quality fixes — onto `dev` in one gated merge (secret-scan green,
  34/34 tests). Closed **#3** and **#4** as merged-via-#5.
- **S23 tail closed.** Folded the 8 still-open items from the retired root `cleanup_backlog.md` into
  `BACKLOG.md` (dedup'd against what it already carried) and deleted `cleanup_backlog.md` + the
  duplicated `logging.additions` fragment (`7025afa`).
- **`main` untouched beyond the gate.** The `dev`→`main` v2.0.3 promotion stays parked pending the rain
  fix's first wild glitch + the dewpoint rebuild.
- **Reception Layer A DEPLOYED live (DEC-0024).** scp'd the dev `weewx_monitor.py` to the NAS (backup
  `weewx_monitor.py.bak-20260705-141508`), `sudo kill`ed the monitor; the esynoscheduler `sleep 300`
  wrapper respawned it on the new code. **Confirmed**: the RF WINDOW metric dropped from a steady
  ~150–162% to **92%** (`22/24`) on the first post-restart window — same packet volume, correct
  epoch-dedup. Reversible via the backup.
- **Still owner/calendar actions (→ S28):** watch for the first real rain glitch; rotate the exposed WU
  key; the influxdb-grafana cherry-pick + stale-branch cleanup; remote-URL casing; set `STATION_NAME`
  in `monitor.env` (emails currently fall back to "My PWS").

## [S26] — 2026-07-05 — Fix the secret gate's mainline coverage (draft PRs #6 → dev, #7 → main)

A dashboard (dash) cross-repo note flagged the ported DEC-0012 secret gate as neutered and warned this
repo's gate "almost certainly has the same hole." Verified empirically — the concern is real, but not
where the note assumed. **No prod/driver code touched; two draft PRs, nothing merged.**

- **Diagnosis (empirical).** The neuter bug — the `grep -n` `<lineno>:` prefix matched the docstring
  allow-rule's bare `:` and silently whitelisted real `ident = secret` lines — was **already fixed** on
  the governance feature-stack in S20 (`2a6327c`, `:` → `[A-Za-z]:`); the current gate catches a planted
  secret assignment (a real-looking `api_key` value) that the old gate passed clean. But the fix
  never reached the mainline:
  - **`main`/`origin/main`** — **no `check_secrets.sh` and no `ci.yml` at all.** A fresh clone of the
    public default branch had zero secret scanning.
  - **`dev`/`origin/dev`** — the **neutered S17 gate**, *and* its secret-scan was the last step of a
    single CI job behind `ruff check`, which fails on the pre-S24 tree (32 errors) — so the whole job
    went red at ruff and the scan never ran. Doubly dead.
- **PR #6 → `dev`** (`s26-secret-gate-dev`) — replaced `check_secrets.sh` with the fixed version; split
  `.github/workflows/ci.yml` into an independent **`secret-scan`** job + a `lint` job so a lint failure
  can never skip the gate.
- **PR #7 → `main`** (`s26-secret-gate-main`) — added `check_secrets.sh` (fixed) + the two-job `ci.yml`
  + `.pre-commit-config.yaml` (main had none of the apparatus).
- **Verified.** On both PRs, CI **`secret-scan` = pass** (clean tree) and **`lint` = fail** (expected,
  pre-S24 ruff; non-blocking to the gate). Locally: planted secret caught (exit 1); the fixed gate scans
  each whole tracked tree clean (exit 0, no false positives).
- **Open (→ S27):** (1) mark **`secret-scan`** a **required** status check in branch protection on `dev`
  + `main` (needs repo admin; PAT 403'd) — until then CI is advisory, not blocking. (2) Reconcile the
  s20→s24 governance stack's old single-job `ci.yml` to this two-job structure when it merges. (3) Review
  + merge #6 then #7. Cross-repo finding recorded; the corrected takeaway for dash: verify against the
  branch that actually carries the fix, and confirm its own gate uses the `[A-Za-z]:` guard.

## [S25] — 2026-07-05 — Finish the S24 review fixes (on `feature/s24-code-quality-review`)

Completed the S24 review's deferred tail. **Branch-only, not deployed;** the driver changes still ride
the next rebuild + hot-swap. No-Rewrite honored — every change is surgical. Full offline suite green
(34/34: the prior 29 + 5 new `owm` tests).

- **U1/U2 (`owm.py` rebase)** — the uploader overrode `RESTThread.run_loop` with a hand-rolled
  `queue.get`/`urlopen` loop, silently discarding every resilience knob it was constructed with
  (`post_interval`/`max_backlog`/`stale`/`max_tries`/`retry_wait`/`skip_upload`) — a transient network
  failure dropped the record with no retry. Re-based on the standard hooks: kept `format_url`, moved the
  JSON body to `get_post_body(record) → (body, 'application/json')` (the same contract `influx.py`
  uses), deleted `run_loop`/broken `post_request`/`import time`/unused `urllib.request`. RESTThread now
  owns retry/backoff. New `tests/test_owm_post_body.py` (5 tests: kwargs forwarded, hooks not
  overridden, body shape + km/h→m/s conversion, None-field omission, appid URL).
- **U4 (`influx.py` TLS)** — `post_request` unconditionally used `ssl._create_unverified_context()` for
  any `https://` endpoint (silent MITM exposure). Added a `verify_ssl` option (**default `True`** =
  verifying context; explicit opt-out restores unverified for self-signed/internal endpoints), wired
  through the service `__init__` + `InfluxThread`, documented in the docstring. Moot for the current
  local `http://` Influx; drop-in.
- **M4 (dead code)** — deleted `_fmt` (py2-only `ord()`) and `parse_readings` from `rtldavis.py`; both
  had zero callers repo-wide.
- **L6 (driver nits)** — fixed the per-transmitter debug guard to test the list *element*
  (`stats['pct_good'][i] is not None`) instead of the always-truthy list; hoisted `_stderr_sample_count`
  init out of the hot read loop into `__init__`; annotated the unreachable `elif lines:` branch. **L5:**
  documented the `@staticmethod`-that-takes-`self` convention at `parse_raw` rather than restructuring.
- **Nit sweep** — `weewx_monitor.py`: narrowed three bare `except:` → `except OSError:`, and made the
  three hardcoded `/volume1/...` paths env-overridable (`WEEWX_RTLDAVIS_DIR`/`MONITOR_LOG`/
  `MONITOR_PIDFILE`/`WEEWX_LOG`) for parity with the env-sourced credentials. `windy.py`: replaced the
  `__import__('queue')` wart with a normal `import queue`. `influx.py __main__`: `os.environ[...]` →
  `.get(...)` so `--version`/`--help` no longer `KeyError`, and fixed the `InluxDfB` typos.
  `ogoxeUploader.py`: reconciled the contradictory `server_url` comments and logged the real
  hardcoded URL instead of `None`.
- **SPDX** — added per-file `SPDX-License-Identifier: GPL-3.0-or-later` headers to the driver + all
  reviewed satellites (`rtldavis`, `weewx_monitor`, `owm`, `windy`, `influx`, `ogoxeUploader`, `wcloud`,
  `loop_json_writer`).
- **Deferred (still, → S26):** **M-A** (monitor incremental read) and its coupled **L-B** (double-read
  race) — both wait for the DEC-0024 Layer A monitor deploy so they don't step on the queued
  `weewx_monitor.py`. The S24 driver fixes (H1/H2/M3) + these still need the rebuild/hot-swap.
- Verified: `py_compile` clean on all 8 touched modules; offline suite **34/34 green**; secret-scan
  passes on every changed file.

## [S24] — 2026-07-05 — Code-quality review + first fixes (on `feature/s24-code-quality-review`, stacked on S23)

Reviewed the driver and its satellites, then fixed the two real bugs plus the log-bloat source. **Fixes
are branch-only; the driver ones need a rebuild + hot-swap and are NOT deployed.** No-Rewrite honored —
every change is surgical.

- **`docs/CODE_REVIEW_S24.md` (new)** — deliverable-of-record: ranked findings across `rtldavis.py`
  (1506 ll), `weewx_monitor.py`, and all uploaders (`owm`/`windy`/`ogoxe`/`wcloud`/`influx`) +
  `loop_json_writer.py`. Draft **PR #5**, based on the S23 branch. Records a verification note: a
  candidate `setDaemon`/`setName` finding was **dropped** after testing against the live Python 3.14.5.
- **H1 (`0929952`)** — `parse_raw` unknown-channel branch referenced an undefined `raw` (param is
  `pkt`) → `NameError` inside `genLoopPackets` instead of the intended log line. One-line fix +
  `tests/test_parse_raw_channel.py` (proven to fail with the exact NameError pre-fix).
- **H2 (`970c47e`)** — `pct_good_all` bootstrap deadlock: `_update_summaries` only set it under a guard
  that also required it to be non-`None`, but `_init_stats`/`_reset_stats` null it every period, so the
  driver's own `rxCheckPercent` was **never populated** (likely why the log-scraping monitor exists).
  Dropped the self-defeating clause + `tests/test_reception_stats.py` (drives two archive periods +
  `new_archive_record`; fails pre-fix). Live-confirm `rxCheckPercent` on deploy.
- **M3 + U3 (`8872947`)** — the `weewx.log` bloat (DEC-0024 Layer B family): gated the driver's
  per-packet `RAW_CHANNEL_PAYLOAD`/`RAW_RTL_HOP`/`RAW_RTL_STDERR_SAMPLE` INFO logging behind
  `debug_rtld`, and dropped `influx.py`'s per-record `loginf` → `logdbg` (also fixed the "Bindding"
  typo). Pure log-level changes, no behavior change.
- **Deferred (in STATUS handoff → S25):** M-A (monitor incremental read — waits for the Layer A deploy
  to avoid stepping on it), U1/U2 (`owm.py` RESTThread rebase for retry/backoff), U4 (`influx.py` TLS
  verification), and the M4 dead-code + minor-nits + SPDX-header sweep.
- Verified: full offline suite **29/29 green** (H1 2, H2 2, plus the existing 25); secret-scan passes
  on every changed file; both edited modules `py_compile` clean.

## [S23] — 2026-07-05 — Cross-project governance alignment (on `feature/s23-governance-alignment`)

Docs-only, **no driver or prod code touched, not deployed.** Piloting a shared governance standard
across the three-repo Eagle Hunt family (this repo is the pilot; ASSESSMENT.md §2/§5).

- **`docs/ASSESSMENT.md` (new)** — cross-repo governance audit (weewx vs `eaglehunt-weather-dashboard`
  vs `hyperlocal-forecast`), the "isolate content / harmonize form" alignment model, a draft
  **Governance Standard v1** (shared core + per-repo profiles), ranked recommendations, and the
  pilot→harvest→propagate roadmap toward a generic project template.
- **`LICENSE` (new)** — GPLv3, verbatim canonical text (reused from `hyperlocal-forecast` for
  guaranteed-correct text + cross-repo consistency). Fills the gap of a public, published tool with no
  license; ecosystem-standard for a WeeWX-derived work. Per-file SPDX headers deferred to the S24 review.
- **`AGENTS.md` (new)** — cross-agent entrypoint (the `AGENTS.md` convention) pointing at CLAUDE.md +
  STATUS.md, so a non-Claude agent or human can pick the repo up from GitHub alone.
- **ROADMAP restructured** — shared `P0–P4` vocabulary mapped to short/medium/long horizons; folded to
  post-S22 reality with ✅ done-markers and a "vision" preamble; added the P0.5 governance-alignment
  workstream. P0 governance bootstrap marked done.
- **STATUS.md made the single source of truth** for the session number (DEC-0023) and the
  **next-session handoff moved into the repo** (out of Claude-private memory, now a pointer) — the
  north-star fix so handoff state is visible on GitHub. Doc-map reordered to put STATUS at slot #2.
- Verified: secret-scan gate (DEC-0012) passes on all changed files; docs-only diff.

## [S22] — 2026-07-05 — Merge PR #2 + reception metric Layer A fix (on `feature/reception-dedup`, off `feature/rain-spike-filter`)

Picked up the S21 handoff. No driver or prod code touched; not yet deployed.

- **Merged PR #2** (`s20-governance-hardening` → `feature/rain-spike-filter`): the S20 governance work
  (independent numbering DEC-0023 + two `check_secrets.sh` gate fixes) now rides with the rain fix
  toward v2.0.3. Resolved three append-conflicts keeping both S20 and S21 content (CHANGELOG S21→S20,
  DECISIONS DEC-0023 above DEC-0024, STATUS last-updated). Merge commit `1a265e7`.
- **Reception-metric Layer A fix (DEC-0024, `20bf7c0`):** `weewx_monitor.py` counted raw
  `Wunderground-RF … Published` log lines, but the driver publishes freqError freq-hop packets as
  duplicate publishes of the **same record epoch** — over-reading reception to ~150%. A live read-only
  sample (2026-07-05) showed a clean 2× (same `(epoch)` posted twice). Fix: a pure `wu_record_key()`
  helper dedups on the trailing `(<unix_epoch>)`; the window now counts **unique epochs**.
  `close_reception_window` + the driver are untouched. 6 offline tests
  (`tests/test_reception_dedup.py`). **Deploy = monitor restart only** (respawn loop reloads on-disk
  code); reversible. **Layer B stays deferred.**
- **Live read-only check (SSH):** confirmed no rain glitch has fired in the wild yet (v2.0.3 promotion
  still calendar-bound); verified the live `weewx_monitor.py` was byte-identical to the repo copy
  (md5 match) before patching.

## [S21] — 2026-07-04 — Reception metric ~150% root cause (DEC-0024) + numbering made independent (on `feature/rain-spike-filter`)

Investigation + governance, **no driver or prod code touched**. (The S20 governance-hardening
CHANGELOG entry rides in separately via draft PR #2 — see below.)

- **Reception-metric ~150% — root cause confirmed (DEC-0024, OPEN).** Live read-only diagnosis: the
  daily RF-Reception emails over-count because `weewx_monitor.py` counts `Wunderground-RF: Published`
  *log lines* ÷ `WU_RF_EXPECTED`(=24), but the driver publishes freqError freq-hop `CHANNELPacket`s as
  extra **dataless loop packets** (~1.66×; live sample 1605 publishes / 968 unique record epochs,
  single Transmitter:4). True reception was ~90%. Cosmetic — real weather data + the rain fix are
  unaffected. Documented Layer A (monitor counts unique epochs — safe, monitor-restart-only) vs
  Layer B (driver stops publishing dataless freqError packets + disable `RAW_*` debug logging; also
  fixes the 15 MB / 122 k-line `weewx.log` bloat). Fix **deferred** (diagnosis + docs only).
- **Doc-vs-reality flag:** BACKLOG claimed the Go binary emits no `ChannelIdx`/`FreqError`; the running
  binary emits **both** — the likely trigger. BACKLOG finding corrected.
- **Session numbering made independent per-repo (DEC-0023, supersedes DEC-0013).** A forensic audit
  showed the "shared lineage with the dashboard" premise never held (the dashboard runs its own
  continuous S1→S40 counter and never referenced a shared one). Each repo now counts its **own**
  sessions; number from *this repo's* CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S21` vs
  `dash S40`); this repo's line is contiguous S16→…→**S20**→**S21**. The prior draft PR that tried to
  *reunify* into a shared counter (mislabeled "S40") was reworked into the **S20** governance-hardening
  session and now rides as **draft PR #2** (`s20-governance-hardening`; PR #1 auto-closed by the branch
  rename). That branch also carries two real `check_secrets.sh` fixes.

## [S20] — 2026-07-04 — Governance hardening: independent session numbering + fix secret-scan gate (on `s40-governance-hardening`, off `feature/rain-spike-filter`)

Governance audit ("does our governance make sense, is it robust, is it aligned with the sibling
repos") + the fixes it surfaced. No driver/prod code touched.

- **Session numbering made independent (DEC-0023, supersedes DEC-0013):** a forensic audit showed the
  "shared lineage with the dashboard" premise never held — the dashboard runs its own continuous
  S1→S40 counter and never referenced a shared one; this repo's DEC-0013 invented a parallel counter
  that re-used numbers (S16–S19) the dashboard had long passed. Resolution: **each repo counts its own
  sessions**; number from *this repo's* own CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S20`
  vs `dash S40`). This repo's line stays contiguous **S16→S17→S18→S19→S20**. (An earlier draft of this
  session tried to *reunify* into the shared counter and relabel this session "S40"; reversed before
  merge so `main` never sees the detour.) Updated `CLAUDE.md`, `docs/STATUS.md`.
- **Secret-scan gate hardened (`scripts/check_secrets.sh`)** — the load-bearing DEC-0012 gate, two bugs:
  1. **False-negative (serious, latent since S17):** the generic assignment-style detector (branch b)
     was effectively **dead**. Its allow-list runs against `grep -n` output, and the docstring-param
     rule `:[[:space:]]*[A-Z][a-z]` matched the `<lineno>:` prefix (e.g. `1:api_key = "…"` → the `:a`),
     silently whitelisting virtually every real `ident = "secret"` line. Tightened to `[A-Za-z]:…`
     (require an alpha char before the colon) so the numeric prefix no longer matches. Verified: a
     planted fake credential (an `sk_live_…`-style token assignment) is now caught; the whole tracked
     tree still scans clean (no new false positives); genuine docstring params still allowed. (This
     very reword was itself flagged by the fixed gate — dogfooding. The S16 leaks were caught by the
     *identifier* branch, which skips this filter — so the hole went unnoticed.)
  2. **Empty-array crash:** threw `files[@]: unbound variable` under `set -u` when run by hand with no
     staged files (bash-3.2 empty-array expansion). Added a clean-pass guard so the manual whole-tree
     audit path fails safe. CI (`git ls-files | xargs`) and pre-commit were already unaffected by both.
- **Doc note (`docs/CONVENTIONS.md`):** the macOS dev box has only `python3` (no bare `python`); the
  prescribed `python -m …` validation commands don't run verbatim locally — noted, plus how to run
  the secret gate standalone.
- **Audit verdict:** governance is coherent and well-aligned with the dashboard's nine-file model
  (intentional, documented divergences: `INTERFACES.md` ← `DATA-MODEL.md`, added `BACKLOG.md`); the
  one real drift was STATUS.md going stale after the S18 deploy — already reconciled in `689b12c`.

## [S18] — 2026-07-04 — False-rain fix (on `feature/rain-spike-filter`, off `dev`)

Confirm-first diagnosis then fix for the phantom-rain bug. Not yet deployed (pending a dry-window
live hot-swap) or merged. Target release v2.0.3.

- **Diagnosis (read-only):** root cause confirmed from code + archive DB + driver logs — the driver
  treated *any* negative rain-counter delta as a 127→0 wraparound and added 128, converting an
  RF-decode glitch into phantom rain. Two events found in 63k archive records: 2026-05-25 (1.28",
  exceeds the world 1-min rainfall record) and 2026-07-04 (0.64"×2, `rain_count=-64` in the log),
  both flat-zero-bracketed and false vs the WeatherLink Live console. Corrected two prior
  assumptions: the counter is 7-bit (not 8-bit), and the recent event was −64→+64 (not a single +128).
- **Fix (`rtldavis.py`):** extracted the pure `rain_delta_tips()` helper (DEC-0021) — only near-−128
  deltas are wraparounds; small-negative and >60-tip (0.60") deltas → `None` (null-on-rejection,
  DEC-0006). Self-documenting docstring explains the bug for future readers.
- **Tests (`tests/test_rain_filter.py`):** 13 offline cases against the exact recorded signatures
  (both glitches reject; real −127 wraparounds and normal rain pass); stubs weewx so it runs with no
  install, wired for CI.
- **Backstop (`weewx.conf.example [StdQC]`):** `rain 0,10 → 0,1.0`; added `rainRate 0,16` — the
  live-config edit happens at deploy time.
- **Audit found (deferred to S19, DEC-0022):** `dewpoint_service.py` still substitutes stale
  temp/humidity/radiation/UV (DEC-0006 violation); minor windGust/radiation/UV StdQC gaps.
- **Email alert (`weewx_monitor.py`):** watch the weewx log for the driver's rejection line and
  email on each caught glitch (reusing the monitor's existing Gmail + log-tail; the driver stays
  pure I/O-free). Reports the counter values and the false rainfall the old code would have
  recorded. `--test-alert` sends a sample email for verification. Detection unit-tested
  (`tests/test_rain_glitch_alert.py`, 6 cases — no false positives on real wraparounds/uploads).
  DEPLOYED (rain driver + StdQC) to the live container 2026-07-04 via reversible hot-swap with an
  in-container import pre-flight; verified healthy. Monitor file staged; alert activates on the next
  monitor restart.

## [S17] — 2026-07-04 — Documentation governance bootstrap (on `dev`)

- Authored the nine-file governance package modeled on `eaglehunt-weather-dashboard` (DEC-0010):
  `CLAUDE.md` + `docs/{PRINCIPLES, CONVENTIONS, DECISIONS, ARCHITECTURE, INTERFACES, ROADMAP,
  STATUS}` + `CHANGELOG.md` + `BACKLOG.md`.
- `DECISIONS.md`: backfilled genesis ADRs DEC-0001…0009 (reconstructed, approximate dates) and
  recorded the governance-era decisions DEC-0010…0017 (governance model, branch model, secret
  hygiene, session numbering at S16, No-Rewrite, hyperlocal tooling graft, Opus 4.8 driver, and the
  interim gain-372 amendment).
- `INTERFACES.md`: documented the two consumer contracts — the loop-JSON real-time surface (field
  table + units + sparse-field caching) and the InfluxDB 2.x line-protocol schema — so the driver
  stays re-pointable toward non-Davis / CumulusMX producers (PRINCIPLES §1).
- Added Python tooling grafted from the hyperlocal-forecast repo (DEC-0015): `.pre-commit-config.yaml`
  (ruff, ruff-format, secret-scan) and `.github/workflows/ci.yml`.
- All authored on `dev`; `main` untouched.

## [S16] — 2026-07-04 — Reconcile repo with production reality → `prod-baseline-20260704`

The published repo had drifted badly from the live NAS system; the drift ran in *both* directions
(GitHub missing runtime files, but also GitHub *ahead* with corrupted uploaders). Captured what is
actually running as the truth on `main`. Commit `7e79d15`, tagged `prod-baseline-20260704`.

- **Added** runtime/driver files missing from the repo: `rtldavis.py` (the driver), `influx.py`,
  `loop_json_writer.py`, `ogoxeUploader.py`.
- **Fixed corrupted uploaders**: GitHub's `owm.py`/`windy.py` had stale duplicate class definitions
  appended that shadowed the clean RESTThread classes (Python uses the last definition) — a latent
  regression for anyone deploying from the public repo. Reconciled to the running versions.
- **Synced infra** stale v2.0.1 → live v2.0.2: `Dockerfile` (rtl-sdr pkg, `receiveWindow` patch,
  influx2 install, COPY steps) and `entrypoint.sh` (dropped syslogd, added `rtl_biast -b 1` bias-tee).
- **Regenerated `weewx.conf.example`** from the live config with maximum scrub (all credentials,
  station IDs, `station_url`, coordinates, and the InfluxDB org name → `YOUR_*` placeholders).
- **Curated `docker-compose.yml`** to driver-only; documented the hot-swappable extension mounts and
  treated downstream consumers (InfluxDB, dashboards) as external (DEC-0010, INTERFACES).
- **Expanded `.gitignore`** (secrets, backups, logs, data, dashboard artifacts, vendored deps).
- **Versioned `ops/`** RF/operational tooling under clean canonical names (dropped version-numbered
  sweep iterations); `wxcheck.sh` scrubbed of a hardcoded WU API key + PWS id.
- **Secret hygiene:** three real leaks caught and scrubbed pre-commit (a hardcoded WU API key + the
  PWS id in `wxcheck.sh`; a station-location chart title in `gain_sweep_analyze.py`; the InfluxDB
  org name). Verified the tracked tree carries zero personal identifiers.
- Resolved the four verify-at-start items: gain is live at **372** (not 207); the v2.0.3 dewpoint fix
  never shipped; the `rw250-test` Dockerfile exists (no reconstruction needed) but diverges toward
  rw350; live `weewx_monitor.py` matches GitHub.
- Discovered `v2.0.2` was never git-tagged (DEC-0003 gap); the vestigial `loopdata.py` mount.

---

## [Pre-S16] — pre-governance history (reconstructed, approximate)

- **v2.0.2** (~2026-05-31, built, never git-tagged): baked-in `rtldavis.py` windDir patch,
  `rtl_biast -b 1` bias-tee in `entrypoint.sh`, `rtl-sdr` package added.
- **v2.0.1** (~2026-05-29): RF reception monitoring in `weewx_monitor.py`, wind-filter iterations,
  elevation fix, StdCalibrate wind offset, STATION_NAME de-personalization.
- **v2.0-ubuntu26** (~2026-05-26): Ubuntu 26.04 / Python 3.14 multistage build (979 MB → 278 MB).
- **v1.0-ubuntu22** (~2026-05): original working image, Ubuntu 22 base.
- Extensive RF tuning (gain/fc/ppm/receiveWindow sweeps), the custom `loop_json_writer.py`, and the
  11-service upload chain were built across these sessions. See BACKLOG.md for the durable RF findings.
