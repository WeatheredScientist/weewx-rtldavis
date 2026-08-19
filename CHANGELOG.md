# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
---
*(S73–S89 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
