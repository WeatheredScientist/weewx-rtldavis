# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S88] — 2026-08-18 — weewx 5.5.0 staged for v2.0.14; the schedule gains a stand-down state (DEC-0096)

- **weewx 5.4.0 → 5.5.0 merged to dev (PR #208)** — the deliberate bump behind dependabot #158,
  per the issue-#78 flow (the dependabot PR is the notification; #158 closed with a pointer).
  Rides the v2.0.14 image cut. Upstream 5.5.0 notably adds retry-on-database-locked — the
  DEC-0070 failure class. Corrected en route: #158's red `tests` check was an artifact of its
  only CI run predating the S73 test correction on `main` (the pre-S73 first-row assertion
  against a schedule that had legitimately launched), not a 5.5.0 problem — current `main` would
  pass it today.
- **DEC-0096 (PR #209): an empty SCHEDULE block is now the explicit between-campaigns stand-down
  state.** Campaign B's terminator (08-23T00:05) is the v2.0.14 window's opening moment, and
  `tests` is a required check on both branches — without this, every PR of the cut would have
  queued behind a red staleness guard, with nothing honest to regenerate the table to. `install`
  refuses the empty block loudly; six structural tests skip on emptiness; the staleness guard's
  classification moved to `_schedule_state()` with its stale branch positively controlled
  (DEC-0045) so a fully-elapsed real schedule still fails exactly as before. The live schedule is
  untouched; the post-square emptying PR must land FIRST in the window. 299/299.
- Watches: 08-18 swaps `B→D` 00:05:02 (settle ~196 s) and `D→A` 06:05:02 (~144 s) both healthy,
  block 14 of 32 in progress; reception-floor dip recurred 03:30–03:45 ×2 on arm D — watch n=4,
  window still drifting later (02:15 → 03:25 → 03:30). Soak 16 pass / 2 expected-WARN.
- Docs: CONSTANTS' release row corrected — `prod-baseline-20260811` (`main` = `1cc9605`) landed
  at S73, the "promotion pending" note was stale. ROADMAP checked: no v2.0.14 line to reconcile,
  scheduled pass S96.

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

*(S73–S85 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
