# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S87] — 2026-08-17 — The soak was lying about a healthy station; retention settled as accept-and-monitor (DEC-0095)

- **`ops/soak_check.sh` measured every age against a clock captured before its own remote body —
  PR #206.** `now` was taken at the top of the ssh block, then ages were computed against it at the
  bottom, after `docker logs`, a full `weewx.log` window read and a `docker exec` sqlite loop. Every
  age was understated by exactly the block's runtime. That runtime was ~2 s historically (every
  recorded value 1–29 s, all inside the monitor's 30 s poll) and 15–100 s under load by 08-17, so
  the monitor's log mtime always landed *after* `now`, the age went negative, and the `-ge 0` guard
  reported a perfectly healthy watchdog as **`MONITOR LOG STALE … wedged`** — for ten days, on every
  run. The watchdog was in fact polling on the dot: 19:10:17 → :47 → 19:11:18 → :48 → 19:12:18, no
  gaps. **The quieter half mattered more:** the same stale clock fed `record_age_s`, the DEC-0036
  freeze detector, whose 180 s threshold silently became 180+runtime (measured 195–280 s) — least
  sensitive exactly when the box is loaded, which is when freezes happen (DEC-0088: median 240 s).
  Both ages now read the clock at the point of measurement, the runtime is reported rather than
  hidden, and the monitor verdict splits into its four real outcomes (dead / no log / clock skew /
  wedged). Also retires the reception check's hardcoded 80% floor, which read **one** 60 s window of
  21 packets — sd ~9.7 pts at this station's measured 73.3% baseline (DEC-0059) — and so warned on
  most healthy runs, 20 pts tighter than the monitor's own `WU_RF_MIN_PCT=60`; the soak now reports
  the monitor's five-window average and its `[OK]/[LOW]` verdict instead of keeping a second
  threshold beside it. New `tests/test_soak_check.py` drives the real script with `ssh` stubbed;
  every "no longer cries wolf" assertion is paired with a positive control that the check still
  fires, verified by running the suite against the pre-fix script (7 fail, all three teeth-controls
  pass).
- **DEC-0095 — retention is accept-and-monitor, not archive-then-prune, and the monitor executes.**
  Answers the weewx half of ops#175. Measured read-only 08-17: archive **33.61 MB = 0.89% of
  MemTotal 3.69 GiB**, 5.1 TB free disk, **1,392 rows/day at 275 B = 0.37 MB/day, ~7.3 yr to 1 GB**,
  InfluxDB engine 14 MB; `dbstat` puts 32.94 of 33.61 MB in the single `archive` table. HLF's
  DEC-0156/0174 **method** transfers and its **conclusion** does not — DEC-0174 justified retention
  on the working set at ~8.0 M hot rows against *this same 3.69 GiB box*, and we have 66× fewer
  rows. Three further grounds: the `archive` table is the deliverable rather than a regenerable
  diagnostic (a passively intercepted station cannot backfill); upstream already bounds long reads
  by aggregation (114 `archive_day_*` tables, ~0.1 MB); and the one cost this DB's history documents
  is CoW fragmentation, for which retention is the wrong lever (`chattr +C` queued, DEC-0092,
  confirmed unapplied). Because accept-and-monitor is worthless as prose (DEC-0040), the reversal
  condition ships as code: the soak reports the archive against **10% of MemTotal** (~386 MB, ~2.6 yr
  out) and crossing it reopens the DEC. The **InfluxDB half is deliberately left open against the
  dashboard** (DEC-0010) — weewx proposes no horizon for a shared bucket.
- **Campaign B watch: block 12 of 32**, `A→B` swap on time at 18:05:02, settle 136 s (n=7, still not
  a trend). STOP/lock absent, arm `B` live, square through `08-23T00:05`.
- **Recorded as a lead, not a finding:** at 19:16 EDT — inside DEC-0094's significant 18:00–21:00
  band — NAS loadavg was **9.05/11.39/8.75** on 4 cores, driven by ~220% CPU of `chrome-headless`
  (coffee-radar) plus ~14 MB/s sustained writes on `md2`. No process was in `D` state and weewxd's
  threads were all `S`, so tenant load is established but *blocking* is not — which is precisely
  blocker 1's open question. One instant is not a probe; sampling across a window is the next step.

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

*(S73–S84 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
