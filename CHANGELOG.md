# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S86] — 2026-08-17 — Watch-checkpoint discipline, LNA hardware history documented, scheduled ROADMAP reconciliation

- **Three daily-watch checkpoints through campaign B block 11, plus a dated hardware timeline in
  `CONSTANTS.md` — PR #203, merged.** `BOOT.md` now carries the night-3 finding: the reception-floor
  PAUSE pattern that hit ~02:15–02:45 on nights 1–2 shifted to ~03:25–04:20 on night 3 (4 cycles,
  not 2–3) — still n=3, still needs a proper test, but the shift argues against a pure tick-grid
  artifact. `CONSTANTS.md`'s Hardware/site section gained a dated timeline (station live 05-01,
  antenna 05-16, LNA ordered 05-27/activated ~06-01, anemometer replaced 06-16/17, LNA removed
  08-02) and dropped the stale "+ inline LNA" claim — the LNA has been out since 08-02, not
  present as the line previously implied. Prompted by an owner question re-examining whether the
  current elevated RF-dead episode rate is caused by the LNA removal: it isn't, directly — DEC-0083's
  onset (08-10 23:56) is 8 days after removal, and the intervening week was the quietest stretch in
  the whole 30-day record. Attribution among campaign B's high-gain arms / v2.0.12 / weather stays
  open, unchanged from DEC-0083.
- **ops#157 (VPN heads-up) closed** — the owner confirmed being back home off VPN, and NAS access
  was verified clean throughout the session (nasctl, ssh-backed calls, soak checks, no timeouts).
- **weewx-rtldavis#74 and #44 retroactively communicated** — both had been closed with zero
  comments (S52 and S43 respectively). Traced each to its actual fixing commit (`0b1ef85` for #74's
  calm-windDir log-level fix, `973235b` for #44's windchill/cloudbase fields, the latter's own
  commit message citing #44 directly) and added a comment naming it, rather than leaving the
  closure unexplained. Prompted by an owner ask to audit "any other issues we've closed" for the
  same gap, not just the one named.
- **`docs/ROADMAP.md`'s scheduled S86 reconciliation ran on time (tripwire: "by S86").** One stale
  item found and fixed: the freeze P0 item still stopped at DEC-0088's S80 rate correction and
  never picked up **DEC-0094 (S85)** — the hour-of-day split that refutes the nightly-maintenance
  hypothesis but finds the evening 18:00–21:00 window significant instead (P=0.0027). Everything
  else on ROADMAP verified current against DECISIONS.md/CHANGELOG.md/BOOT.md. Next tripwire: S96.
- **Board review confirmed nothing else is currently actionable for weewx** — checked the
  cross-project "Claude Code work" board (192 items, 9 not Done) directly rather than relying on
  `BOOT.md`'s own list. Everything weewx-relevant is either finished-and-queued for the v2.0.14
  deploy window (#144, #172, #158), explicitly not-owed (ops#169), or deliberately deferred
  (ops#173). **ops#175 (archive/InfluxDB retention policy) is the one real open item** — scoped
  for S87 on Opus (see `BOOT.md`'s job list for the reasoning).

## [S85] — 2026-08-16 — DEC-0093's gated half shipped (and its deploy plan was wrong); the NAS-LEASE spec reviewed; a new 02:15 watch

- **`current.json` cadence implemented — the dashboard answered dash#430 with 60 s and asked us to
  ship it.** `[LoopJsonWriter] current_interval` (default 60 s) throttles `current.json` only;
  `loop-data.txt` stays per-packet behind its hard 30 s liveness gate. First packet of a run always
  writes the snapshot; a failed write does not advance the timestamp; a backwards clock step forces
  one; `0` restores the S43–S84 behavior. **Measured by simulating a full day at 2.5625 s/packet:
  33,717 → 1,405 snapshot writes, 67,434 → 35,122 renames/day, 47.9% removed.** 8 new tests
  (**279** suite). Three existing tests were reading `current.json` to assert cache/TTL semantics
  and now read the live feed — which is what they always meant.
- **The deploy plan in DEC-0093 and BOOT was wrong, and checking caught it: `loop_json_writer.py`
  is MOUNTED, not baked.** `nasctl inspect` shows `<project root>/loop_json_writer.py` bind-mounted
  `ro` over the venv copy, and **the Dockerfile never `COPY`s it** — so "ships with the v2.0.14
  image cut" would have been **a silent no-op with a green checkmark** (DEC-0046's exact failure).
  Deploy is a file copy to the **project root** plus a restart; the copy in `weewx-data/bin/user/`
  is a **decoy**. `CONSTANTS.md`'s deploy-layer table did not list this file at all — now fixed,
  with `nasctl inspect` named as the authoritative per-file check.
- **Reviewed coffee-radar's NAS-LEASE spec (ops#169, for OPS-DEC-0107).** Seven findings, all
  adopted. The consequential one: the draft had Campaign B ending **08-22** and recorded a
  coffee-radar sweep as "HELD past 08-22" — the square actually runs to **08-23T00:05**, so acting
  on it would have dropped the box's heaviest foreign job into block 31/32, in the same evening
  window their own §8 ranks as most implicated. **That same bare date was also in coffee-radar's
  own `BOOT.md`/`BACKLOG.md`**; reviewing a document caught a live hazard in a neighbour's handoff.
  Also: `rx_experiment.lock` is ours, not HLF's; and §1's "CoW churn is unreachable by any
  tenant-side lever" was corrected to "unreachable by any *scheduling* lever — reducible by
  emitting fewer metadata operations," since our own cut is the counter-example.
- **Answered a question HLF's phase timeline made askable: is weewx a victim of their nightly
  window? Not detectably.** RF-stall episodes 4/15 in-window vs 2.9 expected (P=0.32), n=15 over
  31 days — the **second** independent failure mode to return a negative for that window after
  DEC-0094's freezes. Power caveat stated. Also flagged the limitation that bounds our value as a
  witness: **DEC-0067's gap taxonomy cannot distinguish "RF quiet" from "demodulator starved"**, so
  a weewx "no harm detected" is weak evidence the protocol must not over-trust.
- ⚠️ **NEW WATCH — the ~02:15–02:45 reception dip repeated on night two, on a different arm.**
  08-15: PAUSE 02:15/02:30/02:40 (arm A). 08-16: PAUSE 02:15/02:30 (arm B). All five auto-resumed.
  **A third metric nobody has tested by hour** — DEC-0094 tested freezes and S85 tested stall
  episodes, both negative; these are *reception-floor dips*. Recorded as a watch, not a finding:
  `02:15` is partly a 5-minute-tick artifact and two nights is two nights.
- **Campaign B clean through block 6** (`A`/`B`/`C`/`D` on 08-15, `D→B` and `B→C` on 08-16), every
  swap on time, none deferred. Settle series now n=6 — 82/139/198/137/197/79 s — confirming the
  S84 "not a trend" call: all fit `~20 s + k×60 s`, k = 1,2,3,2,3,1.
- **Cross-repo, all acknowledged:** ops#169 (footprint corrected, the hard 30 s floor declared for
  the spec, the nightly-window lead retracted, coffee-radar's ~19:00 job reported with limits),
  **ops#175 filed against us** (archive + InfluxDB retention — acknowledged with measured growth
  ~0.41 MB/day / ~6.4 yr to 1 GB, **design deferred to `BACKLOG.md`**), ops#173 (BOOT cap, updated
  figure), **ops#176 filed by us** (a `push-nas-guard` false positive whose printed remedy is to
  mint a Class C token for a local docs edit), ops#157 (VPN heads-up, ack'd).
- Docs/process: BOOT job 3 stopped quoting a cap figure that went stale on every edit and gives the
  measurement command instead; a guard-misfire rung 0 recorded (re-spell before minting); BACKLOG
  gained the NAS-LEASE adoption prerequisites, including that **our house `tmp`+`os.replace` idiom
  is forbidden for a lease file** (it strands the holder's `flock` on an unlinked inode).
- Gates at close: ruff clean, **279/279** pytest, mypy clean over 49 files, secret gate clean with
  its positive control at 54/54.

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
*(S73–S83 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
