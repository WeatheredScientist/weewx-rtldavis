# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S81] — 2026-08-14 — DEC-0087's first live pause/resume exercise found a bug in itself, fixed as DEC-0089

- **Arm A never swapped in overnight.** Session start (~08:15) found `current_arm()` still `H`
  and a STOP sentinel blocking every tick since `21:45:01` the night before — arm A's `00:05`
  slot never happened.
- **Reconstructed against the actual logs, not assumed.** Three short reception dips
  (2026-08-13 19:14–19:38) tripped DEC-0087's `PAUSE` at `19:40:05` — its first-ever live firing.
  Reception then read healthy continuously (`[OK]`, 65–81%) from `19:43` for almost two hours,
  but `recovered_since()` only checks for a `RECEPTION RECOVERY` log line — an ALERT→RECOVERY
  *edge* — and none fired again because reception never dropped low enough to re-trigger a fresh
  ALERT. The pause rode the full 120-minute ceiling into `ABORT: RF-dead pause exceeded 120min
  without recovery` at `21:45:01`.
- **DEC-0089 — the fix**: `recovered_since()` now also checks the monitor's ordinary periodic
  `RECEPTION: NN% ... [OK]`/`[LOW]` line (logged every ~5min regardless of ALERT state) as an
  additive level-signal fallback to the edge check — same lesson as DEC-0088, one session later:
  a just-shipped correction carried its own undiscovered blind spot. 4 new tests, including the
  exact incident fixture with its assertion flipped (the regression test). 30/30
  `test_rx_experiment.py`, 242/242 full suite.
- **Recovery**: schedule shifted +24h a third time (DEC-0082's unchanged mechanism) — arm A now
  due `2026-08-15T00:05`, square `08-15 → 08-23T00:05`. Fix + shift deployed together to the NAS
  (sha-verified) before clearing STOP, so no tick could land between a fixed-but-unshifted or
  shifted-but-unfixed state.
- **Post-clear log silence traced and confirmed as expected**, not a second incident: `due_arm()`
  returns the pilot block's trailing `H` row (never a literal `NONE`) until the square's first
  row arrives, matching `current_arm()`, so `tick`'s silent no-op runs for as long as nothing is
  due. New `BOOT.md` gotcha.
- Shipped as PR #177, merged to `dev` (`6079053`).
- **Next session scoped**: a dedicated audit of `rx_experiment.sh`'s full guard/pause/abort/resume
  state machine + `weewx_monitor.py`'s alerting/reset logic, hunting for other edge-vs-level
  signal mismatches — two sessions running with one each (DEC-0088, DEC-0089) is a pattern worth
  a deliberate pass. User's explicit choice: run it on **Claude Fable 5** (judgment/investigative
  work per AGENT-ECONOMY.md).

---
## [S80] — 2026-08-13 — freeze_baseline.py's ad hoc-restart blind spot found and fixed (DEC-0088)

- **Freeze-rate corroboration (job 3) surfaced a tool bug, not a trend.** The 48h window S79
  flagged had cooled to unremarkable on re-run, but 24h/36h had newly gone elevated (95.9th/94.0th
  pct) — until the freshest event (2026-08-13 10:24–10:27) turned out to line up almost exactly
  with this session's own tick log (`10:25:01 tick: swapping A -> H`), the S79 abort's self-heal
  restart, not a freeze.
- **Root cause**: `classify()`'s swap detection only recognized the fixed 0/6/12/18 schedule — no
  way to see a restart `rx_experiment.sh` triggers off it (an abort's baseline restore, a
  DEC-0087 pause escalation, a tick self-heal). Verified directly against the log, not just
  inferred: the 2026-08-12 "19:55 freeze" already on record **is** the `19:55:35 ABORT` →
  `19:55:36 RESTORING baseline snapshot` restart's own footprint.
- **Fix**: `classify()` now also cross-references every logged `tick: swapping`/`RESTORING
  baseline snapshot` line as ground truth, padded 3min back / 12min forward. RF-dead precedence
  unchanged and re-tested against the new path.
- **Corrected reading**: 7 of 47 previously-counted "freezes" reclassified as swap — rate
  1.54/day → 1.31/day, all four rolling windows (24h/36h/48h/72h) flip from elevated/85–95th pct
  to unremarkable (49–67th pct). Not a one-off: DEC-0087 guarantees more ad hoc restarts going
  forward, so the bug's main damage was still ahead of it.
- 5 new tests (ad hoc detection, pad boundaries, RF-dead precedence over the new path, a positive
  control encoding the exact 10:24 event that found this). 17/17 `test_freeze_baseline.py`,
  238/238 full suite, ruff clean, mypy clean.
- Shipped as PR #175, merged to `dev` (`8104c30`). BACKLOG.md's S79 freeze-rate watch item closed
  out with the correction (append-only, per convention). Campaign B untouched — no NAS/container
  write this session.

---
## [S79] — 2026-08-13 — Arm-A abort reconstructed and recovered; DEC-0087 pause/resume ships

- **Arm-A swap verified** (`00:05:02 swapping H -> A`, `00:08:24 arm A live and healthy`) — S78's
  open item. Ran clean 1h20m at 66–79% reception before aborting.
- **Stall burst (DEC-0083) plateau CONFIRMED** — fourth flat reading: 48h/72h still exactly
  record-max 6/6, 24h back to 1 (68th pct), no new episode since 08-12 01:36. Freeze rate's 48h
  window read elevated for the first time (92.5th pct) — one window, not yet a confirmed trend.
- **Arm-A aborted at 01:55:02** (`30-min mean reception 43% < 50% floor`), fully reconstructed: a
  clean ~11-min RF-dead episode (01:40–01:51, `RECEPTION ALERT` → `rtldavis process stalled` →
  `RECEPTION RECOVERY: 62% avg after 9min`), the lagging 30-min mean tripping 4 minutes after
  recovery. `rx_experiment.STOP` then sat uncleared 7.5+ hours, spanning the 06:05 slot.
- **PR #171 — schedule shifted +1 day** (DEC-0082's exact recovery mechanism, applied again):
  33 square rows, verbatim arm sequence, arm A's block 1 now at `2026-08-14T00:05`. 17/17
  `test_rx_experiment.py` unmodified.
- **DEC-0087 (PR #173) — RF-dead reception dips now PAUSE instead of hard-aborting.** Scoped to
  the guard's reception-floor check only (not freezes, not tick's own write/health-check aborts).
  A floor trip writes a non-sticky `PAUSE` marker — no config/container touched — and every guard
  tick checks for `weewx_monitor.py`'s own `RECEPTION RECOVERY` line (-> auto-resume) or a
  120-min ceiling with no recovery (-> escalate to the unchanged `trip_abort()`). Schedule slots
  stay fixed either way — a paused arm just gets fewer live minutes that block, not a moved clock
  boundary. 9 new tests. 224 → 233 tests.
- **PR #170 — BOOT/BACKLOG write-up merged.** All three PRs (#170, #171, #173) merged to `dev`
  same session; #171/#173 touch disjoint regions of `ops/rx_experiment.sh` and merged independently.
- **Deployed and verified**: `ops/rx_experiment.sh` scp'd to the NAS (sha-matched), `STOP` cleared
  (Class C, owner-approved). The very next tick self-healed `swapping A -> H` (the shifted schedule
  correctly overrode the stale live-state A), `arm H live and healthy` at 10:27:19. `soak_check.sh`:
  15 pass / 2 warn / 0 fail post-deploy, both warnings known/expected shapes.
- Green gate: ruff clean, 233 tests, mypy clean on 48 files. `BACKLOG.md` gets a new standing
  watch for the pause/resume incident-tracking half of the original ask, deliberately deferred
  until the mechanism has real data.

---
*(S73–S78 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
