# GOTCHAS — traps that cost this project real time

**Read on demand (DEC-0063 tiering).** Moved out of `BOOT.md` at S94 under STANDARD rule 1: BOOT is
rewritten every session and holds *current* state, while everything below is **durable** — none of it
expires at a session close, and carrying ~1,700 tokens of it in the always-load tier is what put
`BOOT.md` at 195% of its cap (ops#173).

Every entry was earned by something going wrong. They live here rather than in the canonical docs
because each is a *trap in using a tool or reading a signal*, not a fact about how the system is
built — `ARCHITECTURE.md`, `CONVENTIONS.md`, `CONSTANTS.md` and `CAMPAIGN-B-RUNBOOK.md` describe what
things are; this file describes how they mislead.

**Nothing here is a second copy.** Anything already stated in a canonical doc — the gate commands and
the only interpreter that has them (`CONVENTIONS.md`), the baked-vs-mounted deploy table
(`CONSTANTS.md`), the pyc cache (`ARCHITECTURE.md`) — was deliberately left there, per STANDARD rule
5: a second copy is a defect, not redundancy, because it is what drifts.

**When to read which section:** §1 before trusting any tool's zero, empty, or green result · §2
before any PR/merge sequence or handoff write · §3 before any NAS or campaign task · §4 before
concluding a component is dead, live, or shipped.

---

## §1 False signals — a zero, an empty, or a green is a claim, not a result

The single most repeated failure class in this repo's history. The canonical version of the rule is
DEC-0045's positive control; the entries below are the spellings it has taken that a positive control
alone did not catch.

- **A failing test proves nothing if it fails for the wrong reason** — the mirror of DEC-0045's
  positive-control rule, and it looks *identical* to real evidence. S94's first pre-fix proof had all
  10 new tests failing against the stashed old file; every one died on
  `TypeError: unexpected keyword argument 'now'` — the signature change, not the defects. **When a
  fix changes a signature AND behavior, shim the signature so only behavior is under test**, then
  re-run. Post-shim: 6 of 8 failed for the right reason, 0 after the fix.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** — multi-word
  patterns silently return a FALSE ZERO through the ssh quoting layer. **Positive-control any zero
  count** (used again S94 to prove the mount grep). `nasctl cat`/`tail` need **absolute** paths.
- **A `grep -o 'DEC-0[0-9]*' | tail` to find the next DEC number returns OTHER REPOS' numbers** —
  cross-repo references (HLF DEC-0177, ops DEC-0107) are quoted verbatim inside this repo's own DEC
  bodies and sort highest. Read the index table's last row instead.
- **A tool's "control" set silently absorbs a second named window's data unless BOTH are excluded
  from each other** (`ops/proc_probe.py --analyze`, S92, fixed). Adding a second measurement target
  to an existing analysis tool needs the window/control partition re-examined explicitly.
- **A SessionStart concurrency FYI can name a session that does not exist.** Seen twice (S93
  post-crash, S94 clean start): the hook flagged a "live peer" that `ListAgents` did not list at all.
  Do the check — `git status` + `ListAgents` — but treat the FYI as a claim, not a fact.
- **An undated log tail reads accumulated HISTORY as current activity** (S95, DEC-0106). Container
  stdout has no timestamps, **`docker restart` never increments `RestartCount`** (so a truthful
  `RestartCount: 0` says nothing about the process), and a container that was *restarted* rather than
  recreated accumulates every restart into one stream. ~32 routine 6-hourly restarts stacked
  consecutively read as a tight crash-loop in a 30-line tail and reached the owner as a tier:frontier
  alarm. **Get timestamps before judging any rate:** `weewx.log`'s `Initializing weewxd version` lines
  are timestamped and daily-rotated, so restart history is countable per day — container stdout is not.
  Healthy vs pathological here differ by three orders of magnitude (6 h apart vs 43–90 s), but only
  once you can see the clock.
- **`weewx.log` rotates daily, so ANY window longer than "since midnight" spans two files.** S95's
  restart detector returned the right answer only because it also reads the rotated
  `weewx.log.YYYY-MM-DD`; the single-file draft would have returned a **false zero on its first live
  run** — at exactly DEC-0097's 00:00–04:00 hour, where the real trouble clusters. `soak_check.sh`'s
  `mon_resets` check already documents this trap for `weewx_monitor.log`; the same applies to
  `weewx.log`, and the soak's own window computation still has it (filed, not fixed).

## §2 Git, PRs, and the handoff

- **`gh pr merge`'s output is never trustworthy either way** — silent/empty stdout can mean success,
  an explicit error can mean a transient state. Only `gh pr view --json state,mergedAt` is
  trustworthy, every time (re-confirmed S93 on #238, and S94 on #241/#242/#243/#244/#246/#247).
- **Write the BOOT handoff AFTER the merge, not before.** S94 wrote it while the PR was still open,
  so it shipped telling the next session to delete a branch already gone and close an issue already
  closed — needing a second doc-only PR to correct. The closeout ritual's step order (BOOT at 2,
  commit/push at 7) reads as if BOOT comes first; for anything whose truth depends on the merge
  landing (branch state, tracker state, merge commit sha), it does not.
- **A freshly-opened PR reads `BLOCKED`/`UNKNOWN` before CI reports — a timing state, not a problem.**
  `land` says "no checks reported (yet)"; a GET seconds later shows them QUEUED/IN_PROGRESS.
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("3 of 3 required status checks are expected", or `mergeStateStatus: BEHIND`). Fix:
  `gh api -X PUT repos/<r>/pulls/<n>/update-branch`, wait for the rerun, then merge.
- **Merging several same-session PRs in sequence: re-`git fetch`/`git pull` before every merge-into.**
  And **never `git checkout -- <file>` to unplant a staged positive-control payload** — it restores
  the planted version from the index; edit the lines out instead (re-confirmed S94).
- **`Closes #N` does NOT auto-fire in this repo** — PRs land on `dev`, not the default branch. Close
  issues explicitly, with an explanatory comment (S93 found #219/#220/#221 silently unclosed; S86
  established the comment rule).
- **GitHub's API can degrade on WRITES while READS stay fine** — verify with a GET before assuming a
  mutation failed either way.
- **`/code-review ultra`'s cloud launcher wants a base branch, not a path target** — the local
  `/code-review <target> <level>` is the one honoring a path/PR/branch argument. Paths passed to
  `ultra` are read as a free-text note and it diffs `dev`→`main` instead (S91, cost a free slot).

## §3 NAS and campaign operations

- **`nasctl` is read-only** — NAS mutations need the Class C mint path (mint and re-run as TWO
  separate calls, never chained with `&&`).
- **A guard block can be a MISFIRE — check before going near the mint path** (S85, ops#176). Rung 0:
  re-spell it (`Write`/`Edit` instead of a shell heredoc). **The `ssh nas` alias is genuinely
  read-only at the KEY level** (forced command, ops#82) — a refusal there is server-side, not a
  Claude guard, and is not the signal to start the mint dance; `ssh nas-admin` is the mutation-capable
  alias that actually triggers the Class C hook.
- **`secret-read-guard.sh` trips every NAS `scp` deploy** (S81/S82/S82b) — settled fallback: hand the
  owner the single command, saying explicitly it runs on the Mac. It also blocks reads of any
  secret-bearing config; the `command` prefix must **lead** the whole command to bypass it, and
  nesting the read inside `$(...)` or a loop still blocks.
- **Campaign clocks are LOCAL (EDT); most tool output is UTC — convert before comparing.** Check the
  actual process/log evidence, don't compute (S83, S91/DEC-0068, S92/DEC-0098, re-confirmed S94 on an
  arm-D swap).
- **`rx_experiment.sh` has no `ssh` calls of its own — it reads hardcoded NAS-only paths**
  (`/volume1/docker/weewx-rtldavis/...`) and is meant to run scp'd onto the NAS itself. Run its
  `status` (or any) subcommand from a local checkout and it silently reports empty defaults instead
  of erroring — `arm: NONE` since the Unix epoch, `installed: no`, `samples: 0` — because those paths
  just don't exist locally. Reads exactly like "campaign never installed" when it's actually live.
  Verify real state with `nasctl cat <project root>/rx_experiment.state` instead (S100).
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root, its LOG output does not**:
  `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the root; `.log`/`_data.log` under `logs/`. **So does
  `weewx.log`** — `logs/weewx.log`, not `weewx-data/weewx.log`.
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is correct;
  a holder older than 1800 s is broken automatically and loudly.
- **`due_arm()` never returns `NONE` once the pilot block has run** — check `current_arm()`/state +
  STOP/PAUSE directly, not log silence. *(An EMPTY schedule does return `NONE` — the DEC-0096
  stand-down state; `install` refuses it before it can matter.)*
- **Fresh/low soak counters usually mean a scheduled arm swap, not a fault** — the soak window is
  "since container start". Confirm against the state file *and* container uptime before treating it
  as anything else (S93, S94).

## §4 Liveness and deployment — proving a thing is actually running

- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **Adding a new driver-state read to `parse_raw` breaks every test fixture that predates it,
  silently, until the FULL suite runs** (#222). Any change making shared decode code read one more
  field from a driver-shaped object needs a full-suite run before trusting one new test file's green.
- **zsh reserves `$status` as an alias for `$?`** — a loop variable named `status` fails to assign.
  Minor, but it costs a retry if you reach for that name in a polling loop.
- **A clean image rebuild proves nothing for a MOUNTED file** (S101/DEC-0114) — `CONSTANTS.md`'s
  deploy-layers table names this, and it still bit a build event that read the table: `influx.py`'s
  new code was baked into a freshly-built, freshly-tagged, freshly-run image, and the running
  container still executed the OLD version, because the mount overrides whatever the image
  contains. `Successfully tagged` + a healthy new container ID prove the IMAGE changed, not that a
  mounted file's behavior did. Verify the actual runtime version banner in the log after every
  recreate that touches a mounted file's source, not just after a baked-file change.
- **The same trap recurs silently ACROSS sessions, not just within one deploy event** (S102/DEC-0116)
  — `loop_json_writer.py` had been genuinely stale for four weeks (last real edit 2026-07-27) while
  BOOT.md kept asserting "`dev`/prod in sync" through S99, S100, and S101's own v2.0.14 ship, because
  no session's verification pass happened to touch that specific mounted file. A "ship event went
  clean" claim only covers the files that event's own checklist actually checked — it is not evidence
  about every other mounted file in the deploy-layers table. Before trusting any "in sync" claim for a
  mounted file you're about to depend on, check that specific file directly (mtime/hash/grep for the
  feature, or a live output field), not the general fact that a recent image shipped clean.
