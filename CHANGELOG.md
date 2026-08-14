# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S82b] — 2026-08-14 — Owner's reframe used: #180 deployed pre-square, #172/#144 merged for v2.0.14 (DEC-0091)

- **"We haven't started our campaign yet"** — the owner's reframe of the S82 close: block 1 was
  still hours out, so pre-block-1 is the RIGHT window for instrument changes, not a violation of
  mid-campaign discipline. All three backlog items knocked out same day.
- **PR #182 — the #180 monitor trio, merged AND deployed before the square** (scp 12:24 EDT,
  respawned pid 7625, `Monitor started` 12:25:21 — startup line after file mtime, DEC-0074): the
  open episode now mirrors to `logs/monitor_episode.state` and restores at startup (a restart
  mid-episode used to silently lose the ledger row + RECOVERY edge); log rotation voids a pending
  reset verdict instead of faking "verified effective" off the zeroed counter; `do_reset`'s
  exception path emails (it fired live at 01:56:30 that morning as a silent 15 s timeout).
  #180 closed. The whole square now runs on one monitor version.
- **PR #183 — #172 + #144, merged to `dev`, deploys with v2.0.14 post-campaign**:
  `barometer_fetch_epoch` (last *successful* WeatherLink fetch, published outside the TTL
  machinery — a staleness signal must never be omitted for being old) and honest-null
  `pressure`/`altimeter` (they carried sea-level values mislabeled as station pressure — the
  archive columns go NULL from v2.0.14; hlf#302 heads-up posted on #144). INTERFACES §1 updated;
  both issues commented and left open until the deploy.
- **v2.0.14 queue set**: weewx 5.5.0 (#158) + #172 + #144 + the `:latest` move once the square
  proves v2.0.13. Remaining #144 sliver: the +0.03 inHg offset quantification (method in the
  issue, read-only, campaign-safe).
- Mechanical: #183 branched before #182 merged → branch protection refused the merge until
  `gh api .../pulls/183/update-branch` + CI rerun (now a BOOT gotcha). ROADMAP's "lockfile is
  post-campaign work" corrected (DEC-0090 shipped it pre-square).
- 20 new tests across the two PRs; **271/271** on the merged tip; all gates green throughout.

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
*(S73–S80 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
