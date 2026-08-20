# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S94] — 2026-08-19 — Wind-filter redesign shipped (#223, DEC-0103); ops#169 unblocked by correcting our own DEC-0099 (DEC-0104)

- **#223 (`dewpoint_service.py` wind-plausibility filter, frontier) fixed, tested, PR #241.** Its
  four defects were one design gap, exactly as the issue argued: `_filter_wind` never adopted the
  resync-on-reject and co-null behavior `rtldavis.py`'s `SensorQC` already established in this repo.
  **The fix is one distinction, applied consistently** (DEC-0103): a **bounds** reject — an
  impossible reading, or a gust below its own speed — is positive proof of corruption, so the
  baseline is left untouched; a **delta** reject may be a genuine gust front, so the baseline
  **always resyncs, even when rejecting**. (1) That resync closes the deadlock: previously a
  rejected step froze `last_wind_speed` permanently and every later reading was nulled against a
  baseline the weather had left behind, until the weewx process restarted — a 300 s TTL
  (= `QC_RESEED_SECONDS`) adds a second, independent escape. (2) `windDir` is now co-nulled in every
  reject branch; a bare heading with no speed previously reached loop-JSON, InfluxDB and every
  uploader, and this matches the driver's own two precedents while staying narrower than DEC-0054's
  frame-level co-rejection, which delta correctly still never triggers. (3) Cold-start warmup samples
  are bounds-checked before they can seed a wrong baseline and trigger (1). (4) `windGust` is
  bounds-checked independently of `windSpeed`'s presence — unreachable with today's driver, included
  because the driver-agnostic goal is the same one that decided (below) not to import from the driver.
  10 new tests (`tests/test_dewpoint_wind_filter_223.py`). 339/339 full suite (329 baseline + 10 new),
  ruff/mypy clean (57 files), secret scan positive-controlled clean.
- **The port-vs-import call, decided and recorded (DEC-0103).** Importing `SensorQC` from
  `rtldavis.py` is the cheaper move and was rejected: `dewpoint_service.py` has zero driver imports
  today, and `docs/INTERFACES.md` commits it to being re-pointable at non-Davis WeeWX. Coupling a
  driver-agnostic LOOP-packet service to a vendored fork carrying USB and subprocess concerns, to
  reuse ~20 lines of pure logic for a single field, costs more than the duplication. Recorded
  because the reasoning is invisible from the code — a later reader should know the second filter is
  a considered port, not drift.
- **The first pre-fix proof was worthless and looked convincing.** All 10 new tests "failed" against
  the stashed pre-fix file — every one with `TypeError: unexpected keyword argument 'now'`, i.e. the
  signature change, not the defects. Re-run through a shim giving the old `_filter_wind` the new
  signature so only behavior was under test: **6 of 8 behavioral checks fail pre-fix with the exact
  predicted symptom, 0 after**, and the 2 convention locks pass on both sides by design. The
  generalizable form of DEC-0045's rule, from the other side: *a failing test is no more evidence
  than a passing one if it fails for the wrong reason.*
- **`dewpoint_service.py` confirmed BAKED, not mounted** — established with `nasctl inspect` and
  positive-controlled against a known-mounted file, not assumed from its sibling `pressure_service.py`.
  `CONSTANTS.md`'s deploy-layer table did not list the file at all (the same omission S85 found for
  `loop_json_writer.py`, which would let a change "ship" with an image cut and silently do nothing —
  DEC-0046's exact failure); it gains the row. **Nothing deployed this session**: the fix ships on an
  image rebuild, gated behind v2.0.14.
- **[ops#169] promoted to job 2 on owner instruction — and researching it overturned our own
  DEC-0099, logged as DEC-0104.** The owner raised its priority ("next few sessions for sure") and
  then corrected the approach: *"ask the repo… you have coded all of this, so you should be able to
  find answers."* Re-reading `eaglehunt-ops/NAS-LEASE.md` against our own record found three things.
  (1) **DEC-0099's gating premise was wrong.** It deferred adoption to the v2.0.14 container recreate
  because `influx.py` cannot see `LEASE_DIR` from inside the container — true for that one lever,
  over-generalized into a gate on the whole client (and an earlier commit this session amplified it
  into `BOOT.md` as a hard deadline). §9 had already settled it the other way: weewx's client's
  *"natural home is host-side"*, chosen precisely to avoid a release-class recreate. **Holder** (wrap
  the NAS image build) runs on the host; **observer** (read lease, append `heavy-io.log`) is
  `weewx_monitor.py`, already resident with a 30 s poll — neither needs a container change. Only the
  InfluxDB `post_interval` **yield** lever does. (2) **The "two strands" are one:** coffee-radar's
  disk-contention handshake IS this lease — their DEC-0181 Stage 2 landed *as* OPS-DEC-0107. The
  question we nearly posted to ops#169 was already answered in coffee-radar's own `BACKLOG.md`, one
  grep away. (3) **★ weewx's adoption LOCKS §5's constants for every tenant** (unlocked "until the
  second adopting DEC"; HLF's DEC-0177 was first) — a governance act arriving disguised as merge
  order, flagged to ops so other tenants can amend first. Pre-flight verified rather than assumed
  (DEC-0074): `LEASE_DIR` exists at `/volume1/docker/nas-lease/` mode 1777 (owner step already done),
  `heavy-io.log` live with HLF renewing in production (~8.7 h held 08-19, released
  `outcome: step-failures`). **DEC-0099's index row gains a correction pointer rather than being
  edited** — a decision is superseded, never rewritten in place. Position posted to ops#169.
- **Three of this session's six PRs were corrections of its own errors, each caught by re-reading
  rather than by getting it right first.** #242: `BOOT.md` was written before the merge landed, so it
  shipped telling S95 to delete a branch already gone and close an issue already closed. #243: the
  model-tier line asserted "a restore is owed" from OPS-DEC-0010's rule while a read already showed
  `sonnet` — **the identical mistake S89 made and was corrected on by ops**; all five scopes verified
  intact, nothing owed. #246: the DEC-0099 correction above. The generalizable lesson, now in
  `BOOT.md`: for anything whose truth depends on a merge landing, the handoff is written *after* it,
  even though the closeout ritual lists BOOT at step 2 and push at step 7.
- Daily square watch, checked twice. Start: **arm C**, 16 pass / 2 expected-WARN, reception 71%/62%.
  Close: **arm D as of 08-19T18:08:23 EDT** — a scheduled swap mid-session, confirmed against the
  state file *and* container uptime (19 min) rather than inferred from the fresh counters; 16 pass /
  2 expected-WARN, reception 72%/86%. No STOP/PAUSE/lock either time. Untouched by this session's work.
- ROADMAP checked: neither DEC-0103 nor DEC-0104 ships/closes/reprioritizes a P0–P3 line (#227's
  remediation is tracked on the issue tracker, and ops#169 appears on ROADMAP only inside DEC-0102's
  narrative record, not as a line item) — nothing to reconcile, tripwire unchanged, still due by S96.
- Model tier: escalated to Opus for #223's frontier design work. **Floor verified intact across all
  five scopes at close — nothing to restore** (see #243 above for why that is checked, not inferred).

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
---
*(S73–S91 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
