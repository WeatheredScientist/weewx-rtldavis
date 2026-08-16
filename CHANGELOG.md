# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S84] — 2026-08-15 — The dataless-write proposal was already fixed in S43; the real amplification is `current.json`, which nothing reads (DEC-0093)

- **Asked (out of ops#169) whether `loop_json_writer.py` should skip dataless LOOP packets — it
  already does, one level up.** DEC-0024 Layer B (S43) stashes freq-hop packets and `continue`s
  (`rtldavis.py:1507-1517`), so `new_loop()` cannot fire on one; `PacketFactory.create()` does still
  *yield* them, which is what the reading saw, but `genLoopPackets` filters them first. The `~40%`
  figure was `66/166` — DEC-0024's own **pre-fix** 1.66×. **Verified live rather than from source**
  (DEC-0074): the monitor reads `WINDOW: 12–18/21 (57–86%)`, `RECEPTION: 72–74%` — the post-Layer-B
  signature; the inflation's signature is this metric pinning near 100%.
- **Measured what DEC-0092 estimated:** ~22,500 loop packets/day → **~45,000 renames/day**, refining
  its `50–85k` (whose upper bound was the pre-Layer-B rate). DEC-0092's last post-square queue item
  is answered and retired in place, in the house `Update (Sxx)` pattern.
- **`current.json` has no consumer anywhere.** The eh-proxy's only `/weewx-data` read is
  `loop-data.txt`; no runtime reference exists in the dashboard, in hyperlocal-forecast, or in this
  repo outside the writer and its tests; the dashboard's roadmap still carries Cold-load Fix B's
  consumer half **open at P0**. So half of all writes go to a file nothing reads — the whole 40% the
  proposal chased, but real. **Direction: decouple its cadence to 30–60 s (~47% of renames removed),
  gated on the dashboard confirming.** Not shipped; **no code changed** (PRINCIPLES §8, DEC-0014).
- **Recorded why content-based suppression is rejected, so it is not re-proposed.** The eh-proxy
  503s at `now - dateTime > 30` and the dashboard reads that 503 as its one proof the station is
  down, while `wind_speed` is set unconditionally including `0.0` when calm — a calm night would
  report a **healthy station as offline**. The "suppression is more honest" argument inverts
  DEC-0006/0053's two independent freshness axes (per-field TTL vs feed liveness).
- **Doc contradiction corrected:** INTERFACES §1 and the writer's docstring had claimed since S43
  that the dashboard fetches `current.json` at boot; it never did. INTERFACES §1 now also records
  the **30 s liveness gate** — DEC-0092 called loop-JSON "contractually fixed" without the number
  that makes it so. **Cross-repo reconciliation still owed** (weewx documented the whole feature as
  done; the dashboard holds the accurate half).
- **Link declined:** DEC-0068 measured the main thread `S`, never `D`, during a load-12 freeze, so
  less writer I/O is **not** evidence toward the freeze blocker (DEC-0067/0068).
- Docs only, plus a docstring in `loop_json_writer.py` (no behavior change).
- **Amended same day (S84b) — the NAS came back in reach and the square was verified after all.**
  `H -> A` at `00:05:01` (`arm A live and healthy` `00:06:23`), `A -> B` at `06:05:01` (healthy
  `06:07:20`); on arm **B**, no STOP, no PAUSE. **DEC-0087/0089 got their first live exercise and
  held:** one ~20-min blackout (02:00–02:22, reception `30→2→16→1→0%`) produced **three**
  pause/resume cycles as the 30-min mean lagged the recovery, and **pre-DEC-0087 the first trip
  would have been a sticky STOP that killed the block unattended.** Resumes 2 and 3 came from
  `recovered_since()`'s second path (`RECEPTION: 73% [OK]` at 02:31:43 / 02:41:44) — **DEC-0089's
  fix is what carried them**, since only one `RECEPTION RECOVERY` edge line exists. Whether the
  blackout was RF or a process freeze is **not established** (DEC-0067: both read identically on
  this metric) and it sits inside DEC-0092's nightly heavy-I/O window — logged as blocker 1's lead,
  not scored as an RF result. S84's "NAS unroutable" note was true when written and is now stale.
- **Later the same day (S84d, DEC-0094) — the hour-of-day freeze split ran, at zero prod cost, and
  refuted the lead it was meant to test.** DEC-0092 deferred it post-square as "a heavy sweep";
  that priced a *fresh* `freeze_baseline.py` run, but the script prints every individual event by
  design and those listings survive in session transcripts, so the split was arithmetic over
  already-collected data — no ssh, no archive query, no load on the square. **Nightly maintenance
  window (00:10–04:30): 9 of 40 freezes vs 7.2 expected, P=0.29 — it explains nothing.** The
  evening does: **18:00–21:00 = 12 vs 5.0 (P=0.0027)**, coffee-radar's ~19:00 window 7 vs 2.5
  (P=0.011), over 10 distinct dates — turning DEC-0068's "n=1, not a base rate" into **30% of
  freezes in 12.5% of the day**. Stated with its limits: found post hoc, and the omnibus X²=30.8
  (df=23, crit 35.2) does **not** reject uniformity, so it corroborates DEC-0068 rather than
  proving it. Used the **DEC-0088-corrected run only**, verified by a positive control (the
  documented 08-12 19:55 restart is absent from it, present in the pre-fix runs) and by parsed
  count matching claimed count. **Side result: the 08-15 02:00–02:22 blackout was RF-dead, not a
  freeze** — three `rtldavis process stalled` lines sit inside it, which is DEC-0067's own rule;
  S84b's open question closed by one grep. Blocker 1 stays open — mechanism still unproven.
- **Cross-repo brought current at close (S84e).** **ops#169** updated with both DECs: our 08-14
  footprint figure corrected (`~45k`, not `50–85k` — the upper bound was a pre-fix rate), **~47%
  declared removable unilaterally with no lease at all**, `loop-data.txt` declared a **hard 30 s
  floor** for the lease spec (a deferral past it is a consumer-visible outage, not a preference),
  the nightly-window freeze lead **retracted** from our side of that thread, and coffee-radar's
  ~19:00 job reported as correlating with 30% of our freezes — limits stated, no schedule change
  requested. **ops#173** (BOOT over cap) acknowledged with the measurement and the post-square plan,
  plus the general point that a repo running a live time-boxed experiment exceeds a static cap
  structurally, which is a different condition from neglect. **ops#157** (owner on VPN through
  ~08-16) acknowledged — it explains this session's NAS gap, and weewx re-derived that condition
  instead of reading the heads-up that already said it. **dash#430** filed, awaiting their answer.
- **S85: dash#430 answered 60 s, so DEC-0093's gated change is IMPLEMENTED (not yet deployed).**
  `[LoopJsonWriter] current_interval` (default **60 s**) throttles `current.json` only;
  `loop-data.txt` stays per-packet because its `dateTime` sits behind the 30 s proxy liveness gate.
  First packet of a run always writes the snapshot (a restart republishes immediately), a failed
  write does not advance the timestamp (one transient failure can't suppress it for an extra
  interval), a backwards clock step forces a write, and `current_interval = 0` restores the
  S43–S84 behavior. **Measured by simulating a full day at 2.5625 s/packet: 33,717 → 1,405
  snapshot writes, 67,434 → 35,122 renames/day, 47.9% removed** — matching DEC-0093's projection.
  8 new tests (23 in the file, **279** suite); three existing tests were reading `current.json` to
  assert cache/TTL semantics and now read the live feed, which is what they always meant.
- **The deploy plan was wrong and the check caught it: `loop_json_writer.py` is MOUNTED, not
  baked.** `nasctl inspect` shows `<project root>/loop_json_writer.py` bind-mounted `ro` over the
  venv copy, and **the Dockerfile never `COPY`s it** — so "ships with the v2.0.14 image cut", which
  both DEC-0093 and BOOT had said, **would have been a silent no-op with a green checkmark**
  (DEC-0046's exact failure). Deploy is a file copy to the **project root** plus a restart; the
  copy in `weewx-data/bin/user/` is a **decoy**. `CONSTANTS.md`'s deploy-layer table did not list
  this file at all — now fixed, with `nasctl inspect` named as the authoritative per-file check and
  the two other mounted modules added.
- Gates at close: ruff clean, **271/271** pytest (**279/279** after S85's tests), mypy clean over
  49 files, secret gate clean with
  its positive control at 54/54. Campaign B verified live at 10:39 EDT (arm B, reception 69–77%
  [OK], no STOP/PAUSE/lock). PR #158 deliberately still held for the v2.0.14 post-campaign cut.

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
*(S73–S82 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
