# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S82] — 2026-08-14 — The state-machine audit: five apparatus fixes shipped (DEC-0090), monitor package filed

- **The audit BOOT ordered ran (user's Fable 5 pick)** over `ops/rx_experiment.sh`'s
  guard/tick/abort/pause/resume machine and `weewx_monitor.py`'s alerting/reset logic, hunting
  the DEC-0088/0089 edge-vs-level class. Every finding verified against live logs and the
  episode ledger before any fix was proposed; two clean checks recorded so they aren't re-derived.
- **Five `rx_experiment.sh` defects fixed (PR #179, merged + deployed 10:38, sha `4438a2a3…`):**
  resume aligned to the pause floor (the occupied [50,60) band could enter a pause it could never
  exit → needless ceiling abort); `recovered_since()` + the guard's floor mean read the rotated
  monitor log (rotates 00:05 — the exact swap minute); a due swap defers during an active pause
  instead of swapping into the episode's health-check abort (BASELINE exempt — property #5);
  the guard stands down after the BASELINE self-terminator (was armed forever between campaigns);
  tick/guard/abort serialize behind a lock (the 08-11 02:05:03 guard/tick interleave was on
  record, and a full-budget health_ok outlives the 5-min cron period).
- **`soak_check.sh`'s reset counter was dead since S67** — it grepped `RESET: triggering`,
  retired by DEC-0074's rename; the impossible "1 ineffective of 0 fired" on this morning's soak
  was the tell. Now counts `RESET: running`.
- **Monitor-side trio specced and deferred to #180 (tier:mid):** memory-only episode state (a
  restart mid-episode loses the ledger row + RECOVERY edge), midnight rotation zeroing
  `wu_bad_windows` and falsifying pending reset verdicts, and `do_reset`'s email-less exception
  path (timed out live at 01:56:30 this morning).
- **Ops lane:** #163 closed (MANIFEST carry settled — OPS-DEC-0101/ops#158 precedent), ops#165
  filed (tier-sweep needs an exemption for decision-blessed carries), MANIFEST's self-measurement
  de-drifted to ~1.1K.
- **Morning square watch:** overnight STOP refusals were S81's already-resolved blockade tail;
  both 01:55/01:59 stalls diagnosed RF-class (known DEC-0081/0083 phenomenon); reception 71%
  within 1 sd of baseline. Holding on H all session; arm A due `08-15T00:05` on the new code —
  its first live exercise.
- 9 new tests (one renamed to the new semantics); 39/39 `test_rx_experiment.py`, 251/251 full
  suite; ruff/mypy/secret gate clean, positive control caught both planted payloads.

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
*(S73–S79 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
