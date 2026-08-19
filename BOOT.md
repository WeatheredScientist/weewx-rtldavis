# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3 — the "escape the WeatherLink lock" tool. A public, published
WeeWX extension (Docker Hub + GitHub releases), GPLv3. Its real contract is the **data it emits**
(loop-JSON + InfluxDB line-protocol schema), not any one consumer. The dashboard that consumes it
is a **separate repo** — don't make dashboard changes here.

---

## ▶ Resume here (S92 → S93)

### What's settled (do not re-derive)

**All five S92 PRs merged same session — steady state restored.** #231 (DEC-0102 +
`proc_probe.py` fix), #232 (#219), #234 (#220), #235 (#221), #236 (this closeout) all merged to
`dev` in that order, each verified via `gh pr view --json state,mergedAt` (never trusted `gh pr
merge`'s own output, which was silent on every one). Four of the five hit the expected
"branch behind base" gotcha once an earlier one landed — fixed each with
`gh api -X PUT .../update-branch` + wait-for-CI, no real textual conflicts despite #220 and #221
both touching the `DATAPacket` class. **Re-verified on the actual merged `dev`, not just per-PR:**
ruff clean, mypy clean (55 files), **320/320 tests** (305 baseline + 4 + 3 + 8) — confirms all four
fixes work correctly together. All five feature branches deleted, remote and local (git's own safe
`-d` refused anything not actually merged — an independent confirmation). **None of this deploys
yet** — still holds for the v2.0.14 image cut (~08-23) per DEC-0064; merging to `dev` doesn't touch
the live station.

**Job 2 (overnight probe) is CLOSED.** `proc_probe_nas.sh` stopped cleanly on schedule at 05:00
EDT — resolved DEC-0098's unrecorded-timezone gap (confirmed by process evidence: pidfile gone,
`/proc/<pid>` gone, its own "done" line, not computed). Harvested, ingested, analyzed — the ingest
exposed and fixed a real bug in `proc_probe.py --analyze` (a second named window's data was
silently absorbed into "control" once both existed in the same CSV, inverting the evening-window
ratio; both windows now excluded from each other's control, a `D hits/sample` ratio added). Headline
result: overnight (00:00–05:00) iowait is **11.80x** a clean daytime baseline — the first hard
number on the confound DEC-0092/DEC-0097 already flagged, but confounded itself by a concurrent
ops#169 coffee-radar event and a mixed, not-confirmatory, minute-level stall-timestamp cross-check.
**DEC-0102** has the full record; **ops#169 notified** (informational); **ROADMAP's P0 freeze line
updated** (targeted, not the full pass — tripwire still S96). **Root cause of blocker 2 stays
open** — a single clean re-run will NOT settle it, since DEC-0092's confound recurs every night;
the real next step is multi-night minute-level stall-vs-iowait correlation, not a retry.
**NAS cleanup done** — `proc_probe_nas.sh` + `logs/proc_probe_nas.{log,err}` deleted from the NAS
same session (mint refused twice, then succeeded on a third attempt — matches the documented
~even-odds pattern, not a signal anything was wrong), verified gone via read-only `nasctl ls`.

**Job 7 (S91 audit remediation, #227's sequenced plan): 3 of 8 done.** #219 (ProcManager
lifecycle, frontier — Opus, explicit user-approved escalation): validated the design with a
Plan-agent pass before writing code, fixed all 4 findings, 4 new tests each confirmed to fail
pre-fix via `git stash`. Surfaced that one fix (the `AsyncReader` EOF sentinel) closes a worse
failure mode than the issue text described — abandoned `ProcManager` instances had no path to
terminate their reader threads at all, not just a delayed one — and corrected a citation error in
the issue itself (the deploy-gate rule is DEC-0064, not DEC-0092). #220 (battery-low dispatch,
mid): one-line regex fix (`DATAPacket.IDENTIFIER`), rigorously verified against dispatch ambiguity
with the only other packet type (`CHANNELPacket`) before touching it — 3 new tests. #221 (4 crash
guards, mid): thermistor + both rain-rate branches' `ZeroDivisionError`, `iss_channel=0`'s
negative-shift `ValueError`, unguarded CRC `ValueError` (verified against the actual installed
`weewxd.py` that it genuinely exits the daemon) — 8 new tests. **Follow-up issue #233 filed**
(`shutdown()` has no direct kill/terminate, relies entirely on `pidof` matching, tier:mid, not
urgent) — found pressure-testing #219's interaction with DEC-0081, deliberately kept out of that
issue's scope. **#222 (channel-gating consistency, mid) is next** in #227's own stated order.

**Model tier: ambiguous, verify/restore before continuing judgment work.** Escalated to Opus for
#219 (frontier, explicit user go-ahead in chat). Flagged a de-escalation suggestion for #220 (mid)
proactively but never got explicit confirmation of a switch back before #220/#221's work happened
— #220/#221's commits are attributed to Sonnet on the assumption the system-prompt identity is
authoritative absent a confirmed switch, but this is a genuine guess, not a verified fact. Check
the actual running tier next session before assuming either way.

**Daily square watch: healthy, checked twice (start and close), unchanged.** 16 pass / 2
expected-WARN both times; arm B since 08-19T06:06:26, no swap during the session; reception
57–69% across both checks. Campaign untouched by any of this session's work — everything above
was off its critical path.

### ▶▶ S93 JOB LIST

1. Model-tier restore check — verify the actual running tier before starting judgment work;
   restore to Sonnet if still elevated from S92's #219 escalation.
2. Daily square watch (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
3. Continue #227's sequence: **#222 next** (channel-gating consistency, mid), then #223 (frontier
   — `dewpoint_service.py` wind-filter redesign, deserves its own unhurried session per #227's own
   note), #224 (mid, pairs naturally with #223 — same file), #225/#226 (lower priority, confirmed
   dormant / cheap-tier — can ride v2.0.15+, don't compete for v2.0.14 scope).
4. **v2.0.14 prep is DONE**, now also carrying #219/#220/#221's merged fixes (queue item 6,
   unchanged from S91/S90). Nothing to decide before ~08-23.
5. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
6. **[ops#173] BOOT.md over cap — TRACKED, do not re-derive or open a second issue.** Diet at the
   square's close (~08-23), still deferred on purpose. This rewrite trimmed the now-resolved S91
   narrative (audit methodology, security-pass detail — durable in DEC-0101/#219-227 already) in
   exchange for S92's own outcomes; net effect not measured.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[weewx#227]: https://github.com/WeatheredScientist/weewx-rtldavis/issues/227

### Current state (S92 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b, sha+process verified |
| Campaign B | **Live and on schedule — arm B since 08-19T06:06:26.** Square through `08-23T00:05` (~3.2 d left at close). STOP/PAUSE/lock absent. Soak (re-run S92 close): 16 pass / 2 expected-WARN, reception 57–69% |
| Swap settle time | n=10 (unchanged since S90): 82/139/198/137/197/79/136/196/144/84 s — not a trend |
| Retention | **BOTH halves SETTLED** (DEC-0095/DEC-0100), unchanged since S90 |
| `dev` beyond prod | Everything for v2.0.14 (unchanged) **plus** DEC-0102 + #219/#220/#221's fixes — **all merged to `dev`** same session (PRs #231/#232/#234/#235), verified together: 320/320 tests, ruff/mypy clean |
| Freeze rate | DEC-0088-corrected (1.31/day); DEC-0102 adds the overnight-window confound number, does not change the rate |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | **Steady state restored: exactly `dev` + `main`.** All 5 S92 feature branches (probe/#219/#220/#221/close) merged and deleted, remote + local, same session |
| Trackers | **#227's plan: 3/8 done and merged (#219/#220/#221).** New: **#233** (follow-up from #219, open, tier:mid). #158 closed · #172/#144 open until v2.0.14 · #204 open (current.json cadence heads-up) · ops#163/#176 closed · ops#180/ops#169-thread informational, no action expected |
| Cross-repo (S92) | One comment posted: ops#169 heads-up with DEC-0102's finding, linking PR #231 — informational, no action requested |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected), separate phenomenon**
   from DEC-0081's RF-dead episodes. Still hard-aborts. Root cause still unproven (thread blocking
   on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068). Evening 18:00–21:00
   carries the signal (DEC-0094). Unchanged this session — DEC-0102 is about blocker 2, not this one.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds a timing
   signature (clusters 00:00–04:00). **DEC-0102 (S92) adds the first hard kernel-level number on
   the leading confound — DEC-0092's sibling-tenant maintenance window, 11.80x iowait vs. clean
   daytime — but does NOT close this**: a concurrent one-off ops#169 event and a mixed (not
   confirmatory) stall-timestamp cross-check keep it open. Next real step is multi-night
   minute-level correlation, not a re-run (a single re-run hits the same recurring DEC-0092
   confound every night regardless).
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains the
   largest on record. Unchanged.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B. Unchanged.

## Gotchas that survive here because they are NOT in the canonical docs

- **A tool's "control" set silently absorbs a second named window's data unless BOTH are excluded
  from each other, not just each from its own.** `ops/proc_probe.py`'s `--analyze` defined control
  as "every hour outside the evening window" — correct until job 6 grew a second window (00:00–04h),
  whose data got pooled into "control" the first time it existed in the same CSV, inverting the
  evening ratio (S92, fixed). Generalizable: adding a second measurement target to an existing
  analysis tool needs the window/control partition re-examined explicitly, not assumed to still be
  right.
- **`/code-review ultra`'s cloud launcher wants a base branch, not a path target — the local
  `/code-review <target> <level>` command is the one that honors a path/PR/branch argument.**
  Passing file paths to `ultra` gets silently read as a free-text note and it falls back to a
  `dev`→`main` diff instead. Found S91, burned one of three free ultrareview slots learning it.
- **Campaign clocks are LOCAL (EDT); most tool output is UTC — convert before comparing.** Three
  prior sessions hit this from opposite sides (S83, S91/DEC-0068); S92 resolved DEC-0098's
  unrecorded-timezone gap the same way — check the actual process/log evidence, don't compute.
- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` trips every NAS `scp` deploy** (S81/S82/S82b) — the settled fallback:
  hand the owner the single command, saying explicitly it runs on the Mac.
- **A guard block can be a MISFIRE — check before you go near the mint path** (S85, ops#176).
  Rung 0: re-spell it (`Write`/`Edit` for file content instead of a shell heredoc) before asking
  for a mint. **The `ssh nas` alias is genuinely read-only at the KEY level** (authorized_keys
  forced command, ops#82) — a mutation attempt through it is a server-side refusal, not a Claude
  guard, and is not the signal to start the mint dance; `ssh nas-admin` is the mutation-capable
  alias that actually triggers the Class C hook (S92, re-confirmed).
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("3 of 3 required status checks are expected" from `gh pr merge`, or `mergeStateStatus: BEHIND`
  — both faces of the same thing). Fix: `gh api -X PUT repos/<r>/pulls/<n>/update-branch`, wait for
  the CI rerun, then merge. Re-confirmed S91 on PR #229; S92 shipped **four** same-session PRs
  (#231/#232/#234/#235) all branched from `dev` before any merged — expect this on most of them.
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is
  correct; a holder older than 1800s is broken automatically and loudly.
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations need the Class C mint path (confirm in chat, mint,
  re-run identical — mint and re-run as TWO separate calls).
- **`due_arm()` never returns `NONE` once the pilot block has run** — check `current_arm()`/state +
  STOP/PAUSE directly, not log silence. *(An EMPTY schedule does return `NONE` — the DEC-0096
  stand-down state; `install` refuses it before it can matter.)*
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root, but its LOG output does
  not**: `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the root; `.log`/`_data.log` under `logs/`.
  **So does `weewx.log`** (S92) — `logs/weewx.log`, not `weewx-data/weewx.log`; a filtered `ls`
  that greps for one filename pattern can hide siblings in the same directory.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** —
  multi-word patterns silently return a FALSE ZERO through the ssh quoting layer. Positive-control
  any zero count. `nasctl cat`/`tail` need **absolute** paths.
- **Merging several same-session PRs in sequence: re-`git fetch`/`git pull` before every
  merge-into, not just the first.** And **never `git checkout -- <file>` to unplant a staged
  positive-control payload** — it restores the planted version from the index; edit the lines out
  instead.
- **GitHub's API can degrade on WRITES while READS stay fine** — verify with a GET before assuming
  a mutation failed either way.
- **`gh pr merge`'s output is never trustworthy either way** — a totally silent/empty stdout can
  mean success just as easily as an explicit error can mean a transient, retryable state. Only
  `gh pr view --json state,mergedAt` is trustworthy, every time.
- **A freshly-opened PR reads `mergeStateStatus: BLOCKED` / `UNKNOWN` before CI has reported —
  that's a timing state, not a problem.** `land` itself says "no checks reported (yet)"; a
  `gh pr view --json statusCheckRollup` GET a few seconds later shows them QUEUED/IN_PROGRESS.
  Don't chase this as an error (S92, all four PRs showed it briefly).
- **zsh reserves `$status` as an alias for `$?`** — a shell loop variable literally named `status`
  fails to assign with `read-only variable: status`. Minor, but costs a retry if you reach for that
  name in a polling loop.

_Last updated: 2026-08-19 (S92 close — Sonnet for job 2 and initial job 7 setup; Opus for #219's
design/implementation on explicit user escalation; tier uncertain for #220/#221 and everything
after, see the model-tier note above — verify/restore next session).
Green gate re-verified twice: independently on each branch before merging, then again on the
actual merged `dev` after all five PRs landed — ruff clean, mypy clean (55 files), **320/320
tests** (305 baseline + 4 + 3 + 8), confirming the four fixes compose correctly, not just pass in
isolation. This session's planned focus (from S91 close): resolve DEC-0098's probe-timing question,
then job 7. Both done and then some — job 2 fully closed with a real, honestly-hedged finding
(DEC-0102), job 7 advanced 3 of 8 items with pre-fix-verified regression tests, and — beyond the
original plan — all five PRs merged same session plus the NAS probe-artifact cleanup, on explicit
owner instruction after review. Campaign B checked twice this session (start and close), both times
healthy, untouched by any of this session's work. ROADMAP.md reconciled: DEC-0102 updated the P0
freeze line (targeted update, not the full pass — tripwire still S96); #219/#220/#221 don't touch a
ROADMAP line (tracked via #227 instead, which needed no edit — its own sequenced table stays
accurate as written). CHANGELOG.md entry written after the merges landed (deliberately held until
then — its own convention marks entries "merged," and nothing was until this point); S89 rolled to
`CHANGELOG-ARCHIVE.md` verbatim in the same pass, keeping the ~3-session window (S92/S91/S90)._
