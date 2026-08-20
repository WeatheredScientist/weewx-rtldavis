# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S95] — 2026-08-20 — The reported crash-loop was scheduled swaps (DEC-0106); `soak_check.sh` gains a restart-loop detector

- **#245 / ops#184 (tier:frontier) refuted on measurement, and closed.** The report — `RestartCount: 0`
  while stdout showed RTL-SDR re-detection cycling inside a 30-line tail — was read as a crash loop.
  It was not. **Aug 15–19: exactly 4 weewxd startups a day, every one at HH:05 ±30 s**, which is
  precisely Campaign B's four scheduled arm swaps, 6 h apart, with **zero off-schedule restarts in
  five days**. The contrast case is in our own history: 2026-08-06's `journal_mode` crash-loop ran
  **7 starts in 7 minutes** (43–90 s apart). The healthy and pathological signatures differ by three
  orders of magnitude — the evidence was never ambiguous, nothing had ever put the two side by side.
- **Why it looked exactly like a loop — three things compounding, none of them careless.** Container
  stdout carries no timestamps; **`docker restart` never increments `RestartCount`**, so the reported
  zero was truthful *and* uninformative about the process; and the container object was 8 days old and
  *restarted* rather than recreated, so its stdout accumulated every restart into one stream. ~32
  routine restarts stack consecutively, and a 30-line tail catches ~4 of them that are in fact six
  hours apart. Corroborated by count: all three restart markers read **exactly 27** in a `--tail 200`
  window — itself truncation at ~7 lines/start, so the true figure is ~32 = 8 days × 4/day.
- **The owner's "a lot more crashes lately, it used to be super stable" is correct, and the cause is
  benign.** Measured across a month of rotated daily logs: **0/day between campaigns** (Jul 20–24,
  Aug 3–14), **4/day during them** (Aug 15–19). Every elevated non-campaign day has a known cause —
  Aug 6 = 7 (the WAL loop), Aug 11 = 10 (the v2.0.13 deploy), Aug 10 = 3 (v2.0.12). The zeros were
  **positive-controlled** (DEC-0045), not assumed: Aug 3's log runs full of data through 23:59 with
  zero `weewxd` events. So the rate genuinely rose; every one of the new restarts is deliberate.
- **HLF's staleness is not ours — redirected, not absorbed.** Through their reported window
  (19:45–20:07Z) weewx was adding archive records **and** publishing to InfluxDB every minute,
  successfully, no errors. The day's four driver stalls sat at 02:55–05:29 EDT (DEC-0097's overnight
  cluster), hours away. ops#184 deliberately **left open** — its HLF redirect is still an open action
  item for another repo, and closing it would bury that.
- **The monitoring gap this exposed, fixed (DEC-0106).** `soak_check.sh` counted startup banners with
  `grep -c` then tested only non-zero — 1 and 50 read identically green, which is what the S94 soaks
  ran through twice while #245 was live. **Raising it to a count would not have worked:**
  `entrypoint.sh` `exec`s weewxd, so weewxd is pid 1, its death takes the container with it, and
  every container lifetime holds **exactly one** banner. A loop is structurally invisible inside a
  per-container window. The detector therefore reads a **fixed 6 h window** and fails when consecutive
  starts are **<1800 s apart** — swaps are 21,600 s, loops are 43–90 s, so the threshold sits in a gap
  two orders of magnitude wide. **Positive-controlled over 7 cases** against the real Aug-6
  timestamps, including both sides of the boundary (1799 s fires, 1800 s does not) and a loop hidden
  beside a legitimate swap.
- **A rotation trap, caught in verification and proven in production.** The first draft grepped only
  the current `weewx.log` — which **rotates daily**, so a 6 h window run after midnight spans two
  files. The first live run (00:0x EDT) found the window's only start in the **rotated** file, so the
  unfixed version would have returned **0 — a false green**, at exactly the hour DEC-0097's stalls
  cluster. Now reads yesterday's rotated file first. Same trap the `mon_resets` check already
  documented for `weewx_monitor.log`; `docs/GOTCHAS.md` §1 gains both.
- **Found, filed, deliberately not fixed here** (DEC-0014, keep the change small): the soak's
  *pre-existing* window computation has the same rotation blindness — after midnight it collapses to
  the new day's log, which is why four window-scoped checks currently WARN as artifacts rather than
  findings. And the long-standing `stdout is chatty — 162 lines` WARN is now **explained**: accumulated
  restart output on a long-lived container, permanent until the next recreate, not "freeze fuel" —
  it has been read as expected noise for weeks.
- **Nothing deployed.** `ops/soak_check.sh` is a laptop-side diagnostic; prod remains **v2.0.13** /
  driver ws.5, untouched. Campaign B checked during the session, healthy. Gates: ruff clean,
  **339/339**, mypy clean (57 files), secret gate clean **and positive-controlled** (all three planted
  payload shapes caught, exit 1).

---
## [S94] — 2026-08-19 — #223 shipped (DEC-0103); ops#169 unblocked by correcting our own DEC-0099 (DEC-0104); BOOT.md diet, under cap (DEC-0105)

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
- **`BOOT.md` diet done on owner instruction — 4,866 → 2,406 tok, under the 2,500 cap for the first
  time since before S83 (DEC-0105, ops#173).** Done days ahead of the ~08-23 plan. The starting point
  was worse than ops#173 last recorded (4,427 at S86) because this session added ~1,000 of its own.
  **Four prior rule-1 trimming passes at S84 had moved the file ~50 tok net** — deleting resolved
  items cannot keep pace with a file that absorbs a session's state every close, so the remaining
  bulk was diagnosed as *misfiled rather than stale*: the gotchas block was **41% of the file** and
  nothing in it expires at a session close. Moved to **`docs/GOTCHAS.md`**, four sections deep, with
  a `MANIFEST.md` row whose "load when" names a trigger rather than a topic — an index entry saying
  "read this sometimes" is unread, not lazily loaded. Then What's-settled and job 2 compressed to
  conclusions now that DEC-0103/DEC-0104 hold the detail (the ops#169 briefing alone was ~700 tok
  restating DEC-0104). **Rejected:** distributing the entries into `CONVENTIONS.md`/`ARCHITECTURE.md`
  by topic — each would land in a defensible home but the class would stop existing, and the class is
  the point. **A rule-5 trap caught mid-task:** the first draft of the new file also copied in the
  gate commands, the baked-vs-mounted deploy table and the pyc cache from the canonical docs; it read
  as completeness and is precisely STANDARD rule 5's defect (a second copy is what drifts). Eight
  entries removed, exclusion stated inline. **Cost taken deliberately:** `MANIFEST.md` 1,096 → 1,226,
  including correcting its own stale "~1.1K" self-figure — 130 tok there bought ~1,700 out of the
  always-load tier. **ops#173 left open on purpose**, result posted to the thread: `MANIFEST.md` is
  still over its own cap, and the automated sweep — not this repo — should be what calls it green.
- **A second follow-up PR (#249) fixed two stale references the diet itself created** — job 6 still
  read "diet at the square's close, still deferred on purpose", and the gotchas pointer cited a §5
  that no longer existed after the rule-5 removals merged it into §4. Same shape as #242: a doc
  describing a state that changed while it was being written. Caught by re-reading the finished file
  rather than trusting the edits.

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
---
*(S73–S92 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
