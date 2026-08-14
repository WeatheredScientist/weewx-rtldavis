# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S83] — 2026-08-14 — ops#169 answered: our yield is a near-no-op, the box has a nightly heavy window, and the filesystem was wrong (DEC-0092)

- **Answered coffee-radar's shared-NAS I/O lease proposal (ops#169), measured rather than
  estimated.** `binding` defaults to `archive`, so InfluxDB gets **1 record/60 s**; total weewx
  write bandwidth is order **tens of MB/day**. Our shape is metadata-heavy (~50–85k renames/day
  via `loop_json_writer.py`), not bandwidth-heavy — so downshifting frees almost nothing, and the
  counterpart accepted a near-no-op courtesy side as the honest answer rather than a refusal.
- **Drew the data-integrity line ops#169 asked us for.** InfluxDB deferral is safe — the *live*
  config was checked, not the shipped defaults: `[[Influx]]` sets only connection keys, so prod
  runs `stale=None` / `max_backlog=1e6` and a 30-min defer queues ~30 records against a million.
  The **SQLite archive write is the red line** (engine waits a hardcoded 120 s then restarts;
  `timeout=30` exists because a *reader* holding the lock 6 s once cost 5–10 min of prod), and
  loop-JSON is contractually fixed by INTERFACES §1.
- **Corrected a mechanism both sessions had adopted: `/volume1` and all 25 mounts under it are
  btrfs — only DSM's `/` is ext4.** There is no `jbd2` in either tenant's data path. Caught by
  reading `/proc/mounts` instead of inheriting the claim, *after* it was already in our draft.
  The strategic conclusion survives (`btrfs-transaction` is equally outside ioprio); write
  amplification is higher than the ext4 model predicts, and the mount is `relatime`, not
  `noatime`. Attribution independently confirmed impossible — `blkio/` holds only `reset_stats`,
  and cgroup v2's `io.*` postdates this 4.4.302+ kernel.
- **Found the box's real schedule, which outranks the protocol.** A sibling tenant's nightly
  maintenance runs **00:10 → ~03:00–05:10 every night** (6 nights verified, median ~4h20m), so
  **~72% of every 00:05 campaign block** sits under a heavy-I/O window nobody knew about; two more
  jobs fire at 00:05 itself, one of them our own `weewx-monitor` logrotate — the same minute as
  the swap's `harvest()`, which reads that log and its rotation. Task-id → owner mapping recorded
  in the gitignored local-infra doc; BOOT's copy is genericized (public repo).
- **Comparability is safe, and said so explicitly:** the square is a 4×4 Latin square run twice,
  so each arm takes the midnight slot exactly twice and a slot-level confound is absorbed by
  construction. The exposure is midnight *swap reliability* and *variance*, both uniform across
  arms. Job 1 gains a check-the-cluster-before-blaming-the-S82-state-machine caveat.
- **Blocker 1 gains a testable lead** (DEC-0067/0068): split freeze timestamps by hour-of-day
  against that nightly window. No prior analysis controlled for it because nobody knew it ran, and
  it is testable against rotated logs we already hold. Deferred post-square — `freeze_baseline.py`
  is itself a heavy sweep and would add load to the measurement it is explaining.
- **Coordination landed before any protocol constant was locked, via schedule disclosure rather
  than throttling:** the counterpart held its 12–20 h sweep past 08-22 and moved its 6-hourly job
  off :00 to :30 before block 1. Both verified here by process evidence, not relayed — the id=11
  output directory stamped 18:31 proves the new schedule *executed*, DEC-0074's principle applied
  to a neighbour.
- **Recorded but deliberately not acted on:** SQLite-on-CoW favors WAL, but the ~300% figure is
  single-writer and ours is the multi-process shape that bit us — **DEC-0071 stays closed**.
  `chattr +C` on the archive DB queued instead, with `noatime`, moving our logrotate off 00:05,
  and the freeze split. Also flagged for a design pass of its own — dataless freq-hop loop packets
  (DEC-0024) republish byte-identical loop-JSON under a refreshed timestamp.
- Gates: pre-commit ran ruff/mypy (no code files), tests, and the secret gate — plus a **positive
  control on `check_secrets.sh`**, which first appeared to show a seventh hole in the `_apppw`
  rule and did not: the payload used a key name outside `_key`. With the real `GMAIL_PASS` shape
  both quoted and unquoted forms tripped, confirming the DEC-0084 fix works. A *failing* positive
  control needs the same scrutiny as a passing one.

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
- **weewx 5.5.0 pre-adoption review: GREEN** (same day, post-close) — source-diffed all 11
  runtime-chain files between v5.4.0/v5.5.0 rather than trusting the changelog: 7 byte-identical
  (incl. `accum.py` — the campaign metric's write path — `restx.py`, `units.py`, the logger);
  weedb's `timeout` read + pragmas-as-mapping **verbatim** (DEC-0070/0071 behaviors survive);
  `manager.py`'s new locked-DB retry layers benignly atop our 30 s timeout. Verdict + v2.0.14 cut
  checklist on PR #158 — the bump is now execution-only.
- **#144's offset third quantified: station-side, ~+0.04 inHg high** — 8 days of archive
  barometer vs four METAR references (+0.038…+0.049, conversion validated against reported-SLP
  anchors), agreeing with hlf#302's seven forecast models; stable daily, ±0.015 diurnal wobble.
  Knob identified: the WeatherLink console's configured elevation (~37 ft equivalent) — owner
  check filed as ops#168; hlf#302 answered in full. One authorized read-only archive query
  (mint path), no repo changes.
- **ops#167 filed**: lead-time heads-up to HLF that archive `pressure`/`altimeter` go NULL at
  the v2.0.14 deploy (it reads those columns; hlf#302 adjacent).
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
*(S73–S81 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
