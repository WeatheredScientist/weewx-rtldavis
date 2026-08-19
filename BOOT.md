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

## ▶ Resume here (S93 → S94)

### What's settled (do not re-derive)

**#227's sequence: #222 fixed, tested, merged — 4 of 8 now shipped.** Three channel-gating bugs,
one root cause (channel routing not consistently enforced across sibling decode/config paths): wind
bytes decoded from any configured channel instead of gating on `wind_channel`; `rain_count` had no
channel check unlike its sibling `rain_rate`; duplicate configured channel numbers silently
corrupted the `-tr` bitmask instead of raising. Fixed all three, matching each one's own sibling
pattern already established elsewhere in the file. 9 new tests, all 4 bug-repro cases confirmed to
fail pre-fix via `git stash`. Wiring `wind_channel` into `parse_raw()` broke 13 pre-existing tests
across 4 files whose fake-driver fixtures predated the change — fixed by adding the key to each,
not a behavior change. **PR #238, merged (`f31438d`).** 329/329 suite, ruff/mypy clean (56 files),
secret scan positive-controlled clean. Steady state restored: exactly `dev` + `main`.

**#219/#220/#221 closed on GitHub** — merged in S92 but never explicitly closed (`Closes #N`
doesn't auto-fire here since PRs land on `dev`, not `main`, the default branch). Each closed with a
comment cross-referencing its PR and merge commit. Found while closing #222 — worth a habitual
check after any merge on this repo, not just this once.

**#223 (`dewpoint_service.py` wind-filter redesign, frontier) scoped, not implemented.** All 4
sub-bugs grounded against current code: no resync-on-reject + no TTL in `_filter_wind` (a genuine
permanent deadlock until process restart, not just "tens of seconds"); `windDir` survives a
rejected `windSpeed`/`windGust` in both reject branches (confirmed by the two existing tests that
seed a `windDir` value and assert nothing about it); the unfiltered warmup buffer that can seed the
deadlock; `windGust` unguarded when `windSpeed` is `None` (confirmed unreachable by this repo's own
driver today — lower priority). Fix pattern identified: port `SensorQC.check()`'s
always-resync-the-baseline + TTL-gated reseed (`rtldavis.py:412-433`). **One open design call for
whoever starts this**: port the pattern locally into `dewpoint_service.py`, or import `SensorQC`
from `rtldavis.py` — the latter breaks this file's current zero-coupling to the driver, which this
repo's own driver-agnostic goal (`docs/INTERFACES.md`) argues against. Not decided; flag and decide
at the start of the real session, not implied by carrying it forward.

**Model tier: resolved.** S92's ambiguity (unconfirmed whether a de-escalation from #219's Opus
run actually landed) doesn't carry forward — session-only switches don't persist to a new session
by design, and S93 started and stayed on Sonnet throughout, confirmed directly. Nothing to restore.

**Session survived a mid-session crash.** Verified on resume that nothing drifted (git state,
PR #238's CI/mergeability all exactly as left) before continuing rather than trusting the
transcript as ground truth. The "live peer" the SessionStart hook flagged post-crash didn't
appear in `ListAgents` at all — see gotcha below.

**Daily square watch, checked twice (start and close).** Start: arm B, 16 pass / 2 expected-WARN,
reception 75%/62%. Close: **arm C as of 08-19T12:07:28** (a scheduled swap happened mid-session —
expected, not a problem; the lower record/sample counts in the close soak are just the fresh
post-swap container, matching the documented settle-time pattern), 16 pass / 2 expected-WARN,
reception 73%/71%. No STOP/PAUSE/lock either time.

### ▶▶ S94 JOB LIST

1. Daily square watch (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
2. Continue #227's sequence: **#223 next** (frontier — already scoped at S93, see above; flag the
   model-tier escalation before writing code, and decide the port-vs-import call first). #224 (mid,
   pairs naturally — same file) is a reasonable same-session follow-on once #223 lands. #225/#226
   (lower priority, confirmed dormant / cheap-tier) — can ride v2.0.15+, don't compete for v2.0.14
   scope.
3. **v2.0.14 prep is DONE**, now also carrying #222's merged fix (unchanged shape from S91/S92,
   one more item in the pile). Nothing to decide before ~08-23.
4. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
5. **[ops#173] BOOT.md over cap — TRACKED, do not re-derive or open a second issue.** Diet at the
   square's close (~08-23), still deferred on purpose.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[weewx#227]: https://github.com/WeatheredScientist/weewx-rtldavis/issues/227

### Current state (S93 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b, sha+process verified |
| Campaign B | **Live and on schedule — arm C since 08-19T12:07:28.** Square through `08-23T00:05` (~3.5 d left at close). STOP/PAUSE/lock absent. Soak (close): 16 pass / 2 expected-WARN, reception 73%/71% |
| Swap settle time | n=10 (unchanged since S90): 82/139/198/137/197/79/136/196/144/84 s — not a trend |
| Retention | **BOTH halves SETTLED** (DEC-0095/DEC-0100), unchanged since S90 |
| `dev` beyond prod | Everything for v2.0.14 (unchanged) **plus** DEC-0102 + #219/#220/#221/#222's fixes — **all merged to `dev`**, verified together: 329/329 tests, ruff/mypy clean |
| Freeze rate | DEC-0088-corrected (1.31/day); DEC-0102 adds the overnight-window confound number, does not change the rate |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | **Steady state: exactly `dev` + `main`.** S93's feature branch merged and deleted, remote + local, same session |
| Trackers | **#227's plan: 4/8 done, merged, and closed on GitHub (#219/#220/#221/#222).** #233 open (follow-up from #219, tier:mid, not urgent) · #158 closed · #172/#144 open until v2.0.14 · #204 open (current.json cadence heads-up) · ops#163/#176 closed · ops#180/ops#169-thread/ops#175/ops#110/ops#179 informational or already tracked, no action expected |
| Cross-repo (S93) | Swept at session start (`repo:weewx` label), nothing new actionable beyond what's already tracked above. No posts made this session |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected), separate phenomenon**
   from DEC-0081's RF-dead episodes. Still hard-aborts. Root cause still unproven (thread blocking
   on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068). Evening 18:00–21:00
   carries the signal (DEC-0094). Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds a timing
   signature (clusters 00:00–04:00). DEC-0102 (S92) adds the first hard kernel-level number on the
   leading confound (11.80x iowait) but does NOT close this — a concurrent one-off ops#169 event
   and a mixed stall-timestamp cross-check keep it open. Next real step is multi-night minute-level
   correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains the
   largest on record. Unchanged.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B. Unchanged.

## Gotchas that survive here because they are NOT in the canonical docs

- **A post-crash SessionStart concurrency FYI can name a session that no longer exists.** After a
  crash-and-resume, the hook flagged a "live peer... active 20m ago" that `ListAgents` didn't list
  at all — most likely that session ID was this same logical session's own dead predecessor, not a
  second agent. Don't skip the check (git status + `ListAgents`), but don't assume the FYI's session
  is real either — cross-check before treating it as something to coordinate with.
- **Adding a new `self.channels[...]` (or similar driver-state) read to `parse_raw` breaks every
  test fixture that predates it, silently, until you run the FULL suite.** #222's wind-gate fix
  wired `wind_channel` into `parse_raw()` for the first time; 4 other test files' minimal
  `_FakeDriver.channels` dicts had no such key and KeyError'd, only visible once `pytest` ran
  everything, not from the new test file alone. Generalizable: any change that makes shared decode
  code read one more field from a driver-shaped object needs a full-suite run before trusting a
  single new test file's own green result.
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
  alias that actually triggers the Class C hook.
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("3 of 3 required status checks are expected" from `gh pr merge`, or `mergeStateStatus: BEHIND`
  — both faces of the same thing). Fix: `gh api -X PUT repos/<r>/pulls/<n>/update-branch`, wait for
  the CI rerun, then merge. Didn't recur this session (only one PR), but re-confirmed S91/S92.
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
  **So does `weewx.log`** — `logs/weewx.log`, not `weewx-data/weewx.log`; a filtered `ls` that
  greps for one filename pattern can hide siblings in the same directory.
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
  `gh pr view --json state,mergedAt` is trustworthy, every time. Re-confirmed S93: #238 merged with
  zero stdout from `gh pr merge`.
- **A freshly-opened PR reads `mergeStateStatus: BLOCKED` / `UNKNOWN` before CI has reported —
  that's a timing state, not a problem.** `land` itself says "no checks reported (yet)"; a
  `gh pr view --json statusCheckRollup` GET a few seconds later shows them QUEUED/IN_PROGRESS.
  Don't chase this as an error.
- **zsh reserves `$status` as an alias for `$?`** — a shell loop variable literally named `status`
  fails to assign with `read-only variable: status`. Minor, but costs a retry if you reach for that
  name in a polling loop.

_Last updated: 2026-08-19 (S93 close — Sonnet throughout, confirmed at session start and unchanged.
Green gate re-verified on the actual merged `dev`: ruff clean, mypy clean (56 files), **329/329
tests**. #222 shipped end-to-end (design discussed and agreed before coding, implemented, tested
against pre-fix code via git stash, landed via PR #238, merged, closed on GitHub with an explicit
comment) — plus the retroactive #219/#220/#221 GitHub closes found along the way. #223 scoped in
full but deliberately not started, matching its frontier tag and #227's own note that it deserves
a dedicated session. Session survived a mid-session crash; verified state on resume rather than
trusting the prior transcript. Campaign B checked twice (start: arm B; close: arm C after a
mid-session scheduled swap), healthy both times, untouched by any of this session's own work.
ROADMAP.md checked: nothing this session ships/closes/reprioritizes a P0–P3 line, no DEC logged
(routine audit-remediation fixes don't generate their own DEC, matching S92's #219/#220/#221
precedent) — nothing to reconcile, tripwire unchanged at S96. CHANGELOG.md entry written; S90
rolled to `CHANGELOG-ARCHIVE.md` verbatim in the same pass, keeping the ~3-session window
(S91/S92/S93)._
