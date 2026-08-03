# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
