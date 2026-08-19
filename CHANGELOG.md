# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S93] — 2026-08-19 — Channel-gating fixed (#222), #227's sequence now 4 of 8 shipped; #223 scoped

- **#227's sequenced plan: #222 (channel-gating consistency, mid) fixed, tested, merged.** Three
  instances of the same root cause — channel routing not consistently enforced across sibling
  decode/config paths. (1) Wind bytes decoded unconditionally from any of 4 configured channel
  roles instead of gating on the already-computed `wind_channel` — fixed by wrapping the decode
  block in the missing gate, sibling to the message_type dispatch that follows it. (2) `rain_count`
  (message_type 0xE) had no channel check, unlike its sibling `rain_rate` a few lines earlier —
  fixed by copying that existing gate. (3) `ch_to_xmit()` accumulated transmitter bits with no
  check the 5 configured channel numbers are pairwise distinct, so a duplicate silently corrupted
  the `-tr` bitmask into a different channel than either role was configured for — fixed with an
  explicit `ValueError` in `__init__`, matching the sibling frequency-validation two lines above it.
  9 new tests (`tests/test_channel_gating.py`), all 4 bug-repro cases confirmed to fail pre-fix via
  `git stash`. Wiring `wind_channel` into `parse_raw()` broke 13 pre-existing tests across 4 files
  whose minimal fake-driver fixtures predated the change and had no `wind_channel` key — fixed by
  adding it to each, not a behavior change. **PR #238, merged** (`f31438d`). 329/329 full suite
  (320 baseline + 9 new), ruff/mypy clean (56 files), secret scan positive-controlled clean.
- **#219/#220/#221 closed on GitHub** — merged in S92 but never explicitly closed (this repo's
  `Closes #N` doesn't auto-fire since `dev`, not `main`, is where PRs land). Each closed with a
  comment cross-referencing its PR and merge commit, per `CONVENTIONS.md`'s explicit rule. #227's
  sequence now correctly reads 4 of 8 shipped on GitHub, not just in `BOOT.md`'s own tally.
- **#223 (`dewpoint_service.py` wind-filter redesign, frontier) scoped, not implemented** — read
  and grounded all 4 sub-bugs against current code (deadlock from missing resync-on-reject with no
  TTL; `windDir` surviving a rejected `windSpeed`/`windGust`, confirmed by the two existing tests
  that seed a `windDir` value and assert nothing about it; the unfiltered warmup buffer that seeds
  bug 1; `windGust` unguarded when `windSpeed` is `None`, confirmed unreachable by this repo's own
  driver today). Identified the fix pattern to port (`SensorQC.check()`'s always-resync-the-baseline
  + TTL-gated reseed) and flagged one open design call for the actual session: porting the pattern
  locally vs. importing `SensorQC` from `rtldavis.py`, which would break `dewpoint_service.py`'s
  current zero-coupling to the driver. Deliberately held for its own dedicated session per #227's
  own note and the frontier tag — no code written.
- **Session survived a mid-session crash cleanly** — verified on resume that nothing drifted (git
  state, PR #238's CI/mergeability all exactly as left) before continuing, rather than assuming the
  transcript was still ground truth.
- Daily square watch (once, session start): 16 pass / 2 expected-WARN (chatty stdout + ineffective
  USB hedge, both already-known), reception 75% 5-window avg / 62% last window, arm B unchanged
  since 08-19T06:06:26, no STOP/PAUSE/lock. Model tier confirmed Sonnet at session start (fresh
  session, nothing elevated to restore from S92's #219 escalation).
- **None of #222 deploys yet** — `rtldavis.py` is baked into the image, holds for the v2.0.14 cut
  (~08-23) same as the rest of #227's plan.
- ROADMAP checked: nothing this session ships/closes/reprioritizes a P0–P3 line — no DEC logged
  (routine audit-remediation fixes don't generate their own DEC, same as #219/#220/#221 in S92).
  Tripwire unchanged, still due by S96.

---
## [S92] — 2026-08-19 — Overnight-probe finding shipped (DEC-0102); 3 of 8 code-audit fixes merged (#219/#220/#221)

- **Job 2 closes: DEC-0098's probe ran, and DEC-0102 records what it found.** Resolved the
  probe's unrecorded-timezone question by process evidence, not computation — `proc_probe_nas.sh`
  stopped cleanly on schedule at 05:00 EDT. Ingesting its data exposed and fixed a real bug in
  `proc_probe.py --analyze`: a second named window's data was silently absorbed into "control" the
  first time both existed in the same CSV, inverting the evening-window ratio. Headline result:
  overnight (00:00–05:00) iowait is **11.80x** a clean daytime baseline — the first hard number on
  the confound DEC-0092/DEC-0097 already flagged — but confounded itself by a concurrent ops#169
  coffee-radar event, and a minute-level cross-check against that night's actual stall timestamps
  came back mixed, not confirmatory. **Root cause of blocker 2 stays open**; a single clean re-run
  won't settle it, since DEC-0092's confound recurs every night. ROADMAP's P0 freeze line updated;
  ops#169 notified. **PR #231, merged.**
- **Job 7 (S91 audit remediation, #227's sequenced plan): 3 of 8 items fixed, tested, and merged.**
  **#219** (ProcManager subprocess-lifecycle, frontier — Opus, explicit user-approved escalation):
  `shutdown()`'s unguarded `get_pid()` call skipped the S73/DEC-0081 zombie-reap fix on exactly the
  case it's most needed; `AsyncReader`'s EOF-sentinel bug (`''` vs binary `b''`) busy-spun a reader
  thread on every child exit and — worse than filed — left abandoned `ProcManager` instances' reader
  threads with no termination path at all; `get_stderr()` could block ~2x its documented 10s cap.
  Design validated with a Plan-agent pass before implementation; 4 new tests, each confirmed to fail
  against git-stashed pre-fix code. **PR #232, merged.** **#220** (`DATAPacket.IDENTIFIER` silently
  dropped every battery-low frame — not just battery status, but wind/temp/humidity/rain too, mid):
  one-line regex fix, dispatch-ambiguity rigorously verified against the only other packet type
  first; 3 new tests. **PR #234, merged.** **#221** (4 unguarded divide-by-zero/negative-shift
  crashes — thermistor, both rain-rate branches, `iss_channel=0`, an unhandled CRC `ValueError`
  confirmed to exit the daemon entirely, mid): guard-and-degrade, matching the pattern already
  established elsewhere in the file; 8 new tests. **PR #235, merged.** Follow-up issue **#233**
  filed (`shutdown()` has no direct kill/terminate, tier:mid, not urgent) — found pressure-testing
  #219, kept out of its scope.
- **All 5 PRs merged same session** (the four above plus this session's own closeout, #236), each
  verified via `gh pr view --json state,mergedAt` rather than `gh pr merge`'s own untrustworthy
  output; four hit the expected branch-behind-base gotcha once an earlier one landed, fixed with
  `update-branch` + wait-for-CI each time. Re-verified on the real merged `dev`: **320/320 tests**,
  ruff/mypy clean. All 5 feature branches deleted, steady state restored to exactly `dev` + `main`.
- NAS cleanup: `proc_probe_nas.sh` + its two logs removed from the NAS on owner instruction,
  verified gone via read-only `nasctl ls`.
- **None of this deploys yet** — `rtldavis.py`/`proc_probe.py` changes hold for the v2.0.14 image
  cut (~08-23) per DEC-0064; merging to `dev` doesn't touch the live station. Campaign B checked
  twice this session (start and close), healthy both times, untouched throughout.

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
---
*(S73–S90 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
