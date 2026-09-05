# Roadmap — weewx-rtldavis

**Status:** Direction (what next, in what order). For *why* see DECISIONS.md; for *how* see
ARCHITECTURE.md; for *what's on the bench right now* see `BOOT.md` (the single source of truth for
the current session + active thread).
**Last updated:** 2026-09-04 (S124 — targeted line update per DEC-0057, not a full pass; tripwire
still S126. DEC-0141 opens the InfluxDB Foundation→marvin move — the first roadmap line the
Foundation decoupling (ops#260 / OPS-DEC-0188) has had here: S105/S106 classed DEC-0118/0119 as
incident response, and that was right for them, but this is planned work with a runbook, so it gets
a P1.8 line below rather than living only in `BOOT.md`.)
Prior: 2026-09-03 (S117 — targeted line update per DEC-0057, not a full pass; tripwire
now S126. DEC-0136 deployed DEC-0135's fix and confirmed it on production data, so P2's "re-baseline
by observation" plan moved from *proposed* to *live*; three corrections landed with it — the
monitor's thresholds do **not** go stale, "~99%" and the slot arithmetic answer different questions
though they agree, and "decoded" includes repeats.)
Prior: 2026-09-02 (S116 — **scheduled full reconciliation, tripwire fired on time**, the heaviest
pass since S66: P2's entire evidence base demoted and the `receiveWindow` item closed as
false-premise. **Recorded only in the guardrail section at the time, never promoted into this
banner — corrected at S117**, the same omission S92/S89 made and S96 caught.)
Prior: 2026-09-02 (S115 — targeted line update per DEC-0057, not a full pass; tripwire
still due S116.)
Prior: 2026-08-31 (S111 — targeted line update per DEC-0057, not a full pass; tripwire
still S116: DEC-0125 decided Campaign C's verdict (496 does not clear the bar at marvin's position,
372 holds) — closed the Campaign B item's marvin-remeasurement thread, which DEC-0124 had left open
last session. Nothing else touched.)
Prior: 2026-08-29 (S106 — **scheduled full reconciliation, tripwire fired on time**: every
open item diffed against DECISIONS.md/CHANGELOG.md/BOOT.md; nothing stale found. DEC-0119 — today's
ops#183 Influx outage, the `backfill_influx.py` fix, and the `weewx_monitor.py` alerter finding —
touches no P0–P3 line, the same call S105 made about DEC-0118's migration: it's incident response and
`BOOT.md`/`CONSTANTS.md` territory, not the sequenced plan. Next check: S116.)
Prior: 2026-08-29 (S105 — targeted line update per DEC-0057, not a full pass; tripwire
still S106: the P0 freeze item gained DEC-0118's incidental corroboration from the marvin migration
incident. Nothing else touched — the migration itself isn't a P0-P3 line, it's `BOOT.md`/
`CONSTANTS.md` territory.)
Prior: 2026-08-23 (S101 — targeted line update per DEC-0057, not a full pass; tripwire
still S106: the Campaign B item closed — DEC-0115 adopted gain 496, deployed at the same v2.0.14
event as DEC-0114's NAS-LEASE lock. Nothing else touched.)
Prior: 2026-08-20 (S97 — targeted line update, not a full pass: P3's INTERFACES.md line
corrected again — it claimed DEC-0053's station-identity finding (Finding 2) was already documented
in INTERFACES.md; it wasn't, until this session actually wrote it in, along with a Finding 3
pointer. See the guardrail section for detail.)
Prior: 2026-08-20 (S96 — **scheduled full reconciliation, tripwire fired on time**:
three stale items fixed — this banner itself (two targeted passes never promoted out of the
guardrail's shadow log), the Campaign A arm-winner **seal**, which DEC-0069 broke as a side effect
30 sessions ago while this file still asserted it held, and P3's INTERFACES citation list, three
DECs out of date. See the guardrail section for detail).
Prior: 2026-08-19 (S92 — targeted line update, not a full pass: the P0 freeze item gained
DEC-0102's 11.80x overnight iowait number. **Recorded only in the guardrail section at the time,
never promoted here — corrected at S96.**)
Prior: 2026-08-18 (S89 — targeted line update, not a full pass: the P0 freeze item gained
DEC-0097's RF-dead/freeze clock discriminator and DEC-0098's live probe. **Same omission as S92,
corrected at S96.**)
Prior: 2026-08-17 (S86 — **scheduled full reconciliation, tripwire fired on time**: the
freeze item (P0, line below) gained DEC-0094's evening-window finding, missing since S85; everything
else diffed clean against DECISIONS.md/CHANGELOG.md/BOOT.md — see the guardrail section for detail).
Prior: 2026-08-14 (S82b — targeted line update, not a full pass: the campaign-B entry's
"lockfile is post-campaign work" corrected — the S82 audit shipped it pre-square with four more
state-machine fixes, DEC-0090).
Prior: 2026-08-14 (S81 — targeted line update, not a full pass: Campaign B square dates
corrected again for the DEC-0089 recovery shift, 08-14→08-22 to 08-15→08-23, DEC-0089's resume-bug
fix noted inline).
Prior: 2026-08-13 (S80 — targeted line update, not a full pass: the P0 freeze-rate
figures corrected per DEC-0088, 1.49/1.48/day → 1.31/day).
Prior: 2026-08-13 (S79 — Campaign B square dates corrected again for the DEC-0087
recovery shift, 08-13→08-21 to 08-14→08-22, plus the new pause/resume mechanism noted inline).
Prior: 2026-08-12 (S76 — **scheduled full reconciliation, tripwire fired on time**:
freeze rate replaced with the measured DEC-0083 figures, USB-reset checkbox ticked to match a body
that had said CLOSED since S73). Prior: 2026-08-12 (S75 — Campaign B square dates corrected for the
DEC-0082 recovery shift, 08-12→08-20 to 08-13→08-21). Prior: 2026-08-11 (S73, two passes — GATE 2 outcomes into the
campaign-B/v2.0.12 rows, then the **USB-reset P0 row CLOSED by DEC-0081** same day: stall class
re-diagnosed as RF-dead episodes, remedies shipped in v2.0.13/ws.5). Prior structural change: 2026-07-28 (S56 — split: P4 + "Longer horizon" moved out to BACKLOG.md's new
"Long-term direction" section, per DEC-0058 — this file is now P0–P3 only, the actively sequenced
plan, so it doesn't get cluttered by uncalendared/aspirational items. Earlier same-session pass:
folded the old P1 + P1.5 sections into one continuous data-integrity arc covering v2.0.3–v2.0.11;
collapsed P0.5's mostly-done checklist to a pointer; added the staleness guardrail below.)

`BOOT.md` holds what's *in motion right now*; this holds the ordered, actively-sequenced plan
(P0–P3 only, per DEC-0058). BACKLOG.md holds unordered near-term ideas **and** long-term/
uncalendared direction — see its "Long-term direction" section for anything horizon-scale.

## Keeping this current (staleness guardrail)

This file went 20 sessions / 8 releases (S35 → S55c, v2.0.3 → v2.0.11) without being updated —
a user-asked audit found it, not anything structural. Two rules to not repeat that:

- **When a DEC lands that ships, closes, or reprioritizes a line item here, update that line in
  the same session** — the same discipline CLAUDE.md already requires for DECISIONS.md ("same
  session, not deferred"). Don't wait for a docs-diet pass or an audit to notice.
- **Next scheduled reconciliation check: by S126** (~10 sessions out). If the session counter is
  at or past S126 and this line still says S126, that itself is the signal it's overdue — run the
  same pass as S56, S66, S76, S86, S96, S106 and S116 did (diff every open/pending item here against
  DECISIONS.md, CHANGELOG.md and `BOOT.md`).
- Last full reconciliation: **S116, 2026-09-02** — tripwire fired on time, and this was the
  heaviest pass since S66. **Two findings.** (1) **P2's entire evidence base was demoted**: DEC-0134
  showed the ~25% the campaigns chased was a demodulator accounting artifact, so every ~73–75%
  figure in that section is a repeat fraction and every "axis is flat" verdict was measured with an
  insensitive instrument. DEC-0135 rewrote P2's header accordingly and withdrew DEC-0134's own
  "negative results remain valid as don't-re-sweep evidence" as too strong — campaigns A–D are
  **untested**, though still not worth re-running (headroom arithmetic under Campaign D). This is
  the first pass where the correction was to *evidence quality* rather than to a status. (2) The
  `receiveWindow` item had been open since S56 on a **false premise** — "cannot be read from logs"
  was an inference from one verbosity level, and three separate pieces of evidence (S114, S115,
  S116) each closed it independently without anyone noticing. Both findings share a shape worth
  naming: a claim that was true-as-observed got carried as true-in-general.
- Prior: **S106, 2026-08-29** — tripwire fired on time. **Nothing stale found** —
  the four open P0-P3 items (freeze root cause, DB-lock bound, `receiveWindow` confirmation,
  INTERFACES.md hardening) all diffed clean against `DECISIONS.md`/`CHANGELOG.md`/`BOOT.md`; none
  gained a new DEC since S105's last targeted pass. This session's own DEC-0119 (ops#183's Influx
  outage, the `backfill_influx.py` fix, the `weewx_monitor.py` alerter finding) touches none of
  them — same category as DEC-0118's migration, incident response rather than a P0-P3 line. First
  reconciliation pass to find zero staleness; every prior one (S66, S76, S86, S96) found at least
  one stale item, so a clean pass isn't yet enough of a pattern to loosen the ~10-session cadence.
- Prior: 2026-08-20 (S98 — two targeted line updates per DEC-0057, not a full pass; tripwire still
  S106): P0.5's Keep-a-Changelog/DECISIONS-skeleton follow-on struck through as retired (DEC-0109
  — unrecoverable rationale, no family-wide adoption to converge toward). P1's S52 bullet
  corrected: it claimed DEC-0054 "closed" ERR-0004, which overclaimed — DEC-0054 only closed the
  co-occurring-bounds-failure mechanism, and ERR-0006 proved the isolated-single-field-corruption
  mechanism recurs independently (DEC-0110 closes that residual gap via reception quality, not
  tighter bounds). Both found while doing the session's own work, not a scheduled audit.
- Prior: 2026-08-20 (S97 — targeted line update per DEC-0057, not a full pass; tripwire still
  S106): P3's INTERFACES.md line corrected. It had claimed DEC-0053's station-identity finding
  (Finding 2) was already documented in `INTERFACES.md` — checked directly against the file rather
  than taken on the line's own word, and it wasn't: only Finding 1 (the bounded cache) had actually
  made it in. `INTERFACES.md` §2 now carries Finding 2 (the series-key fork trap) and, as a bonus
  while touching the same paragraph, a one-line pointer for Finding 3 (SQLite's own missing
  correction flag, which stays in `DATA_ERRATA.md` on purpose). No other line moved; this was found
  while doing the P3 discovery pass itself, not by a scheduled audit.
- Last full reconciliation: **S96, 2026-08-20** — tripwire fired on time. **Three stale items found
  and fixed**, and the most interesting one is a failure mode this guardrail did not anticipate:
  **the top-of-file "Last updated" banner had itself gone stale.** S89 and S92 both ran targeted
  passes and recorded them *in this section* without promoting them into the top block, so the
  banner still read S86 while the content was current through S92 — the freshness signal aged while
  the file did not. A reader checking staleness the cheap way (read the banner) would have been
  told the file was three sessions more out of date than it was. **Rule going forward: a targeted
  pass writes BOTH places, or it is not done.** Second: P2's Campaign A block asserted *"Arm winner
  stays sealed until after B"* — DEC-0069 (S66) unsealed it as a side effect of validating
  `campaign_analyze.py` and published the per-arm ranking in the same breath, so the claim had been
  false for 30 sessions. Third: P3's INTERFACES item cited only DEC-0032/0053 as partial progress,
  missing DEC-0086, DEC-0091 and DEC-0093, all of which landed in that file since (verified against
  `git log -- docs/INTERFACES.md`, not inferred). Everything else diffed clean — 15 items checked
  (6 open, 9 done reverse-checked); the P0 freeze row is current through DEC-0102, the DB-lock and
  receiveWindow rows are unchanged and correct, and this session's own DEC-0107 (NAS-LEASE
  pre-flight) and issue #224 (dewpoint unit systems) touch no line here yet — the first because
  weewx has not adopted, the second because it is a bug fix inside a P1 arc already marked done.
- Prior full reconciliation: **S86, 2026-08-17** — tripwire fired on time. One stale item found and
  fixed: the freeze P0 item (line below) still stopped at DEC-0088's S80 rate correction and never
  picked up **DEC-0094 (S85)** — the hour-of-day split that refutes the nightly-maintenance-window
  hypothesis (9/40 freezes vs 7.2 expected, P=0.29) but finds the **evening 18:00–21:00 window
  significant instead** (12 vs 5.0, P=0.0027) — directly relevant to "why does weewx freeze" and
  missing from it for one session. Everything else verified current: Campaign B block already
  carried DEC-0094's tenant-window split, DEC-0087/0089/0090 pause/resume and lock fixes, and the
  08-15→08-23T00:05 schedule; the DB-lock, receiveWindow and P3 rows are unchanged and correct.
- Prior: 2026-08-19 (S92 — targeted line update per DEC-0057, not a full pass; tripwire is still
  S96): the P0 freeze item gained DEC-0102's overnight probe result — 11.80x iowait vs. a clean
  daytime baseline, the first hard number on the confound DEC-0092/0097 already flagged, but
  confounded itself by a concurrent ops#169 coffee-radar event and a mixed (not confirmatory)
  stall-timestamp cross-check. Root cause stays open. No other line moved.
- Prior: 2026-08-18 (S89 — targeted line update per DEC-0057, not a full pass; tripwire is still
  S96): the P0 freeze item gained DEC-0097's discriminator (RF-dead episodes cluster 00:00–04:00,
  **zero** stall-bearing events in the evening freeze window — the two phenomena keep different
  clocks, so the overnight dip must not be folded into the freeze item) and DEC-0098's live
  mechanism probe. No other line moved: DEC-0097 changed no code and closed a `BOOT.md` watch, not
  a ROADMAP item.
- Prior: 2026-08-14 (S83 — targeted line update, not a full pass: the campaign-B gate row still
  carried DEC-0083's 1.49/day after DEC-0088 corrected it to 1.31/day at S80, and the freeze row
  gained DEC-0092's hour-of-day hypothesis).
- Prior full reconciliation: **S76, 2026-08-12** — the tripwire fired on schedule and the pass ran.
  Two stale items fixed: the freeze row carried "~2-4 min, roughly once a day" for ~13 sessions
  and is now the measured 1.49/day, median 240 s (DEC-0083); and the **USB-reset P0 row was still
  an unticked checkbox while its own body had said "✅ CLOSED at S73" since S73** — the identical
  shape S66 caught on the tiering row, which is the second time this specific failure has appeared,
  so *check the box in the same edit that writes CLOSED into the body*. Verified current, no change
  needed: campaign B (launched/armed, S75 schedule shift already recorded), the DB-lock row
  (bounded, DEC-0070), `receiveWindow` (narrowed, still open), the P0.5 changelog-convergence
  follow-on, and P3.
- Prior full reconciliation: **S66, 2026-08-06** — all 8 open items diffed. Four were stale and
  fixed: the tiering migration was still unchecked *while its own body said "Executed S60"*; the
  v2.0.12 row had read "BUILDING 2026-08-02" for four sessions when that build no longer exists;
  campaign B's gates were listed as open after DEC-0069/0070/0071 cleared them; and the DB-lock row
  still said "flip WAL once ops#141 lands" **after DEC-0071 had abandoned WAL** — a same-session
  DEC-0057 update that was missed the day before, and exactly what this pass exists to catch. Also
  corrected: the P2 heading still announced "CAMPAIGN A RUNNING", and the archive-DB reader list
  still named the dashboard.
- Earlier: full pass **S56, 2026-07-28**. Targeted DEC-0057 passes at **S63** (DEC-0067) and
  **S66** (DEC-0069).

## The vision

**Own your weather data and let others own theirs.** An RTL-SDR passively intercepts the same
915 MHz Davis broadcast the console hears, so the readings become locally owned and re-pointable —
the "escape the WeatherLink lock" tool. The durable deliverable is not "a Davis driver" but a
**stable, documented data contract** (loop-JSON + InfluxDB schema, INTERFACES.md) that non-Davis
WeeWX, other sinks, and eventually CumulusMX can satisfy (PRINCIPLES §1). Published free under GPLv3
so the community can use and extend it.

## Priority vocabulary (shared across the Eagle Hunt family)

`P0` critical path / do first · `P1` important soon · `P2` later / measured · `P3` modularity ·
`P4` housekeeping / community. Horizon mapping: **short-term = P0–P1**, **medium-term = P2–P3**.
**This file stops at P3 (DEC-0058)** — P4 and anything uncalendared/aspirational lives in
BACKLOG.md's "Long-term direction" section instead, so the active plan doesn't get buried under
long-horizon items. ✅ = done; annotations mark items *found stale during an audit* rather than
deleting the history.

## Guardrails

Full operating rules live in CONVENTIONS / CLAUDE.md. The ones that bite most often: this repo is
**PUBLIC** (secret-scan gate, DEC-0012), **prod is sacred** (one dongle/receiver, deploy-to-dev-first,
DEC-0011), **hot-swap what you iterate / bake what you trust** (DEC-0004), discuss design before
coding, and the **No-Rewrite Rule** (DEC-0014).

---

# SHORT TERM (P0–P1) — foundational work, all ✅ DONE

Nothing below is the current focus — everything in this section has shipped. Current focus (watches,
open threads) lives in `BOOT.md`, not here.

## P0 — Governance bootstrap (S16–S20) — ✅ DONE
Prod-truth reconcile + `prod-baseline-20260704`, nine-file governance, CI/pre-commit + secret gate,
independent session numbering. See CHANGELOG-ARCHIVE `[S16]`–`[S20]`, DEC-0010…0017, DEC-0023.

## P0.5 — Governance alignment across the family (S23–S56) — ✅ DONE
Brought this repo's *form* into line with the sibling repos and external best practice, keeping
content isolated (ASSESSMENT.md §2): `docs/ASSESSMENT.md` cross-repo audit + Governance Standard v1,
GPLv3 `LICENSE`, `AGENTS.md` cross-agent entrypoint, ROADMAP restructured to shared P-tiers,
STATUS.md promoted to single source of truth for the session number, `cleanup_backlog.md` folded
into BACKLOG (S27), docs diet (DEC-0030, S35 — the family-wide pattern: dash DEC-0081 → hyperlocal
DEC-0095 → here), remote URL casing + stale-branch cleanup (S56). See CHANGELOG-ARCHIVE `[S23]` and
ASSESSMENT.md for detail — not re-narrated here.
- [x] ~~**Keep-a-Changelog headings + DECISIONS entry-skeleton convergence** (proposed S25, never
      picked up).~~ **RETIRED S98** — original rationale unrecoverable, no family-wide adoption to
      converge toward, and DEC-0109 judges it would fragment this repo's dense narrative style
      rather than help. See DEC-0109.
- [x] ~~**Session-context tiering migration — DEC-0063, decided S59, execute S60.**~~ **DONE S60**
      (this row said so in its own body while staying unchecked — caught by the S66 full pass). The third
      generation of the docs-diet idea (dash DEC-0081 → hyperlocal DEC-0095 → DEC-0030 here →
      ops `STANDARD.md`): `BOOT.md`/`CONSTANTS.md`/`MANIFEST.md`/`ARCHIVE/` replace the DEC-0030
      Tier-1 set. Adopted on measurement against ops#130's own recommendation to defer — Tier-1
      accretes **~1.1K tokens per session close**, so leanness here is a moment, not a trajectory.
      Both siblings already migrated. **Executed S60** — see CHANGELOG `[S60]`.

## P0.6 — Code-quality review + fixes (S24–S25, M-A S28) — ✅ DONE
Ranked findings in `docs/CODE_REVIEW_S24.md`; all fixes landed with regression tests — H1/H2/M3/U3
(S24), U1/U2 owm rebase, U4 TLS, M4 dead code, nits + SPDX headers (S25), M-A/L-B monitor
incremental read (S28). See CHANGELOG-ARCHIVE `[S24]`, `[S25]`, `[S28]`. Driver fixes shipped in
v2.0.3 (S30/S32).

## P1 — Data integrity & Sensor-QC hardening (S18–S55c) — ✅ DONE, watch-only
One continuous arc, not several separate efforts: RF/decode corruption that passes CRC has produced
impossible values (rain, wind, humidity, temperature) since S18, and each release below closed one
corruption class. Full decision trail in DEC-0021/0022/0024/0026/0029/0033/0037/0042/0044/0049/
0054/0055/0056 and CHANGELOG-ARCHIVE `[S18]`–`[S52]` / CHANGELOG `[S55]`–`[S55c]` — not re-narrated
here.

- **False-rain fix → v2.0.3** (S18–S32): DEC-0021 root cause (wraparound handler), StdQC tightening
  + driver spike filter + email alert; reception-metric Layer A (S22/S27) rebased on
  `rxCheckPercent` (S31, DEC-0024); honest-null dewpoint + clobber fix. Wild-glitch gate consciously
  waived on live evidence (DEC-0026).
- **Sensor-QC decode filter → v2.0.4** (S33–S34): DEC-0029, decode-layer `SensorQC` bounds filter +
  DewpointCacher timeout-null, closing DEC-0022.
- **Reception-metric over-count fixed → v2.0.8** (S43): both layers of DEC-0024 closed (monitor
  counts unique record epochs; driver stops publishing dataless freqError packets).
- **Frame-level co-rejection → v2.0.9** (S52): DEC-0054 — a bounds failure now nulls every field of
  its frame instead of just the failing one, closing the frame-co-rejection mechanism of ERR-0004
  (issues #74/#76). **Correction (S98):** this closed the case where ANOTHER field in the same
  frame also fails bounds — not the whole class. ERR-0006 (2026-08-20) proved an isolated
  single-field wind corruption, with nothing else in the frame to co-reject on, recurs
  independently; DEC-0110 closes that residual gap via an orthogonal signal (reception quality),
  not a tighter bounds/delta check.
- **Signed temp decode → v2.0.10** (S55): DEC-0055, fixes negative-temperature encoding and the
  `0xFF8` flag-nibble leak.
- **Cap-16 tuning → v2.0.11** (S55c): DEC-0056, decided on an evidence pass (R1/R2); monitor
  tripwire verified live end-to-end.

**Still open — ordinary watches, not a new arc.** Current status (co-rejecting grep, humidity-spike
signature DEC-0044, first-frost test of the signed-decode negative branch, DEC-0056's
rain-rejection revisit trigger) lives in **`BACKLOG.md` §Standing watches** — moved there from
`BOOT.md` at S67 (DEC-0072), since a watch that has not fired is not in-flight work. Not duplicated
here, and not evidence this P1 item is still "in progress." **`#74` calm-windDir left this list at
S59**, closed on five consecutive clean days with a positive control.

**Blocker discipline (DEC-0011):** no drop-in dev receiver — RF-dependent verification is calendar-
bound and done via reversible live hot-swap with an instant rollback path.

## P1.8 — Foundation decoupling: InfluxDB host move (ops#260 step 3, OPS-DEC-0188) — 🔶 IN PROGRESS (S124)

The last weather workload on Foundation is this repo's `influxdb` container; HLF and the
dashboard cut over 2026-09-04, so the decoupling — and the Foundation-dark drill that closes
ops#260 — now waits on weewx.

- [x] **Design + runbook (S124, DEC-0141):** `docs/INFLUXDB-MIGRATION.md` (measured state, three
      stages, cutover table, rollback) + `ops/weewx-influxdb.service`. Stopped-server raw tree copy
      of the v2.7.12 store (16.4 MB); container/unit inside the weewx manifest globs; consumers
      change one URL each.
- [x] **Stage 0–1 (S124, same night):** marvin installed the unit + pulled the image (MARVIN-DEC-0121);
      dark-parallel from a live snapshot passed 22:07 ET.
- [x] **Stage 2 cutover (S124, 22:13–22:43 ET, DEC-0142):** Foundation stopped 22:13:35, marvin
      store live 22:35:02, weewx publishing 22:43:16. **29-record gap (22:14–22:42) still to
      backfill** — S125.
- [ ] **Stage 3:** backfill; `SuccessExitStatus=2` unit re-install (marvin); `weewx-influxdb-backup`
      pre-dump timer (the store's first backup ever); docs in ops/dashboard; delete the final tars from
      the share; `BACKLOG.md`'s NAS-LEASE cross-host item closes as moot; weewx's section of the
      ops#260 drill; Foundation's stopped instance retires at ops#260 step 4.

---

# MEDIUM TERM (P2–P3) — after v2.0.11

## P2 — RF optimization, done honestly (PRINCIPLES §3) — **✅ CLOSED (S116, DEC-0134/DEC-0135; DEPLOYED S117, DEC-0136): there was never an RF problem to optimize**

> **Read this header before any figure below it.** The section originally closed at S113
> (DEC-0128) on "the gain axis is exhausted." That verdict survives; its *evidence* does not.
> DEC-0134 found that the ~25% shortfall every campaign was chasing was the Go demodulator
> discarding the transmitter's re-sent packets and booking each as a miss — real RF loss **0.3%**.
> **Every ~73–75% figure in this section is a repeat fraction, not link quality**, and every
> "axis is flat" result was measured with an instrument insensitive to the differences it was
> looking for. DEC-0135 therefore demotes campaigns A–D from *settled negative* to **untested**:
> a flat result from an insensitive instrument is not evidence of flatness. They are still not
> re-run — see the closing note under Campaign D for the headroom arithmetic that settles it.
DEC-0048 (S41) deferred this into one designed experiment; the apparatus (`ops/rx_experiment.sh` +
`tests/test_rx_experiment.py`, S56/DEC-0059) is now deployed and executing. The seven
pre-governance sweep scripts are deleted; two of them were silently broken.
- [x] **Phase 0: `FreqError` telemetry CONFIRMED TO EXIST** (S57) — found within 13s of a restart
      once a logger-level gotcha was fixed (DEC-0060). `ppm`/`fc` measurement-by-value is a
      deliberately deferred follow-up, not done this campaign (arms run unmeasured `0`/`0`).
- [x] **Campaign A — LNA in circuit — ENDED EARLY 2026-08-02, 12 of 32 blocks.** Ran clean
      07-30 00:05 → 08-02 00:05 (12/12 swaps healthy, zero aborts), then aborted on the B→D swap
      when the receiver went silent for reasons unrelated to the arm — a 105-minute total RF
      outage (**ERR-0005**). The abort was **correct**: `health_ok()` waits for an archive record
      and none existed in the window (last 00:04:20, next 01:24:24), so DEC-0061's budget
      arithmetic is upheld, not implicated. STOP sentinel left in place deliberately; A is not
      resuming. Its surviving value is what DEC-0064 always said it was — the LNA-in
      characterization (922 samples, mean 72.4) and the multi-day drift error bar. **The arm-winner
      seal is BROKEN and has been since S66** — DEC-0069 unsealed it as a side effect of validating
      `campaign_analyze.py` (the recomputed ranking A 74.81 / C 74.37 / D 74.17 / B 73.87, spread
      0.94 pts, no arm near adoption) and says so on the record: *"it was a side effect, not a
      decision."* What survives is the calendar condition, not the secrecy: the formal A-vs-B
      comparison still waits for B's close, and must be read on the same per-minute metric.
      Settles DEC-0017 (**absorbed**). Tracked at
      [ops#114](https://github.com/WeatheredScientist/eaglehunt-ops/issues/114).
- [x] **v2.0.12 release — DEPLOYED to prod 2026-08-10 (S70); Hub push PENDING.** Promoted via
      PR #151 (`main` = `7b6fd42`), built **natively on the NAS** (`9db5c1ddaac3` — the arm64
      laptop can no longer cross-build linux/amd64, DEC-0078), deployed with `-e BIAS_TEE=0` and
      verified in the **running system** per DEC-0046: ws.4 banner in the live log, bias-tee-off
      startup line, DEC-0062 redaction line, soak identity canaries green (16 pass / 1 warn / 0
      fail). `EXPECT_*` bumped in the same deploy, honoring its own header rule. **Hub push landed at S70
      close** — config digest verified identical to the NAS build (`9db5c1…`); layers rode the
      save→load→push path near-uncompressed (~283 MB vs ~120 MB typical), content-identical,
      compression tightening rides the CI-build follow-up (DEC-0078). ✅ **`:latest` moved to
      v2.0.12 at GATE 2 (S73)** — config digest `9db5c1…` verified identical across both tags
      (manifest digests differ by push-path compression only). Nothing remains on this item.
- [x] **Campaign B — LNA physically removed — CLOSED (S101, 2026-08-23): gain 496 adopted (DEC-0115).**
      Self-terminated on schedule (`BASELINE`, 2026-08-23T00:05). Clean 32/32-block final square
      (2026-08-15 → 08-23): gain 496 beats 372 by +2.00 points, exactly clearing DEC-0059's bar;
      extraction axis a wash. Deployed to prod at the same ~08-23 v2.0.14 event (DEC-0114). A
      narrower follow-up sweep near 496 considered and declined for now — see DEC-0115. Nothing
      remains on this item **as a Foundation result** — ⤷ **the answer was re-measured at marvin's
      RF position — campaign C ran clean 2026-08-30T21:24 → 2026-08-31T11:00 ET (S107 DEC-0121
      design; S108 DEC-0122 shifted the launch from the pre-registered 08-31 to tonight; DEC-0123
      fixed a mid-campaign scheduler gap), and the verdict is now DECIDED (DEC-0125, S111): **496
      does not clear DEC-0059's 2.0-pt adoption bar at marvin's position** — real per-minute,
      freeze-aware readout (`campaign_analyze.py`'s own logic, pulled via ops#235's newly-fixed
      `marvinctl exec-ro` stdin path) gives A (372) 72.82% vs B (496) 73.98%, **+1.16 pts**, smaller
      than the coarse 5-min proxy's +1.87 lean and still under the bar either way. Gain holds at
      372 — no config change — and this is a standalone finding that Foundation's DEC-0115 answer
      doesn't transfer to marvin's closer, fewer-walls position, not a reversal of DEC-0115 itself.
      This item is now CLOSED as a marvin result too; a longer multi-day campaign remains an open
      idea in `BACKLOG.md` if the question is worth resolving further, not a follow-up owed here.**
      Two reasons this was not a re-litigation of a closed item: the host move put the receiver at a
      measurably closer, fewer-walls position, and prod was running **372, not the adopted 496** at
      the time this re-measurement was queued — the 08-29 migration incident set it without a
      controlled comparison and the aborted campaign's exit trap codified it (owner's call: hold 372
      until measured — now measured, and holding on the evidence rather than the accident). Early
      prior: marvin @372 already measured 73.88%, within ~0.95 pts of Foundation @496, so 496
      repeating its +2.00 here was never assumed, and the campaign confirmed that caution. DEC-0066's
      hold released on its own terms: the gates were closed on measurement (DEC-0069/0070), A's
      figures confirmed clean (DEC-0077), and the "instrument trusted" condition met. The first
      launch night (08-09) was scrubbed at 00:58 on a dead VPN — the runbook's postpone-24h
      contingency, prod untouched. Deployed 08-10 morning: campaign A archived (`.campaignA`),
      B's script sha-verified from the merged tip, container swapped, `install` clean. **Pilot
      08-11T00:35–04:20 (first honest no-LNA measurement), square 08-12 → 08-20T00:05**; GATE 2
      pilot readout Tuesday daytime. Read only via `ops/campaign_analyze.py --campaign B`
      (DEC-0069); A's anchor is arm A **74.81%** on the same tool.
      **GATE 2 PASSED (S73, 2026-08-11): arms {372, 496} confirmed; square running 08-12 →
      08-20T00:05.** The pilot itself aborted at 02:11 after two of five arms — P496 75.56 %
      (n=33) ≥ P449 72.65 % (n=15), so the curve is not peaking below 449 and the high arm
      stands; the low arms fed no decision the square doesn't answer itself. The abort cause was
      **not reception**: a zombie-stall (see the USB-reset row below) dragged the monitor's
      30-min aggregate to 39 % while per-minute archive reception stayed ~72 %. **DEC-0080's
      radiation correction applied same day, to the live conf AND `weewx.conf.rx-baseline`** (a
      live-only apply would be wiped by `restore_baseline` — hazard caught at apply). The 08:55
      re-arm then exposed a second `health_ok` budget bug — 180 s never modeled RF acquisition
      (~127 s measured this boot vs ~0 s on P449's) and aborted a healthy, publishing driver by
      seconds; `HEALTH_TRIES` 36 → 60 with the four-term arithmetic pinned in tests (S57's
      regression class, one term deeper). Known cosmetic: `rx_experiment_data.log`
      rows tagged P449 between 01:23 and 08:55 include the stall + baseline morning —
      `campaign_analyze.py` is unaffected (it reads swap-time blocks, not harvest tags). Minor
      apparatus defect found: tick and guard raced each other's restarts at 02:05 (no lock);
      converged safely via the sticky STOP. *The lock shipped S82 (DEC-0090), ahead of the
      square, alongside four more state-machine fixes from the same audit — not post-campaign
      after all.*
      *Explain the outages* — substantially met at DEC-0067: the recurring class is **process
      freezes, not RF loss**, bounded and pre-dating the LNA removal, while ERR-0005 is a
      **single incident**. **Bound re-measured S76 (DEC-0083): 1.49/day, median 240 s** over
      30.3 d — the long-carried "~1/day, ~3.5 min" understated both by ~40 %. **Corrected to
      1.31/day by DEC-0088 (S80)**; this row was missed by that session's targeted pass and is
      fixed here at S83 — the same carried-stale-figure shape the guardrail above has now caught
      **S85 (DEC-0094) splits it by hour and the result is a NEGATIVE: the nightly maintenance
      window holds 9 of 40 freezes vs 7.2 expected (P=0.29) — it explains nothing. The evening
      18:00–21:00 does carry signal (12 vs 5.0, P=0.0027), corroborating DEC-0068 rather than
      this row. Mechanism still unproven, so the gate's verdict is unchanged.**
      three times. **S83 (DEC-0092) adds a testable hypothesis, not a new number:** split the
      freeze timestamps by hour-of-day against the sibling tenant's nightly 00:10→~04:30
      maintenance window, which no prior analysis controlled for because nobody knew it ran. *Watchdog* — done (S63). *Metric freeze-aware* — **done
      (DEC-0069)**, and the gate turned out to be mostly a **resolution** problem: the old 5-minute
      aggregate let one frozen minute wreck four good ones (~0.8 pts), while per-minute
      `rxCheckPercent` puts the real correction at **±0.03 pts against a 2.0-pt bar**. *DB lock* —
      **bounded (DEC-0070)**, outages ~30 s not ~10 min, and **WAL was tried and abandoned
      (DEC-0071)**, so there is nothing further to wait for. **Nothing remains to build before B
      launches.**
      **First honest no-LNA telemetry already accruing** — ~14 h at gain 372 gave mean 72.6% with
      no hour-07 notch, against campaign A's pooled 72.4%. Treat that as suggestive only: A's
      figure pools all four arms including gain 207, so it is biased low, and the clean comparison
      is B's 372 anchor against A's — which is exactly why 372 is in both campaigns.
      **S75 (2026-08-12): a third same-day RF-dead episode (18:05, 08-11) left the square stalled
      on H overnight, missing the 00:05 A-arm swap entirely — the sticky STOP blocked every tick
      through the whole window, unattended. DEC-0082 recovered it by shifting the entire remaining
      schedule +24h (preserving the balanced-Latin-square design rather than accepting a
      permanently lost block); deployed and STOP cleared same session. Square now runs
      **08-13 → 08-21T00:05**, not the originally-planned 08-12 → 08-20T00:05 above.
      **S79 (2026-08-13): the same failure shape recurred** — arm A's block 1 swapped in cleanly at
      00:05:02 but aborted 1h50m later (01:55:02) on a lagging 30-min-mean trip, four minutes after
      the underlying 11-min RF-dead episode had already self-recovered; STOP then sat unattended
      for 7.5+ hours. DEC-0082's same recovery applied again: square now runs **08-14 →
      08-22T00:05**, not the 08-13 → 08-21T00:05 above (PR #171). This time also produced a
      structural fix rather than only a one-off recovery: **DEC-0087** changes the guard so an
      RF-dead reception dip PAUSES (no config/container touched) and auto-resumes on the monitor's
      own RECOVERY signal, escalating to the unchanged sticky abort only past a 120-min ceiling
      with no recovery — scoped to RF-dead only, schedule slots staying fixed either way (PR #173).
      Intended to make this class of unattended-multi-hour-halt rare going forward; whether it
      actually does is itself now trackable (see BACKLOG's standing watches for the pause/resume
      incident count once it starts accumulating data).
      **S81 (2026-08-14): DEC-0087's first live firing exposed a bug in itself.** A PAUSE tripped
      correctly at 19:40:05 on three short reception dips, but `recovered_since()` only checked
      for a `RECEPTION RECOVERY` log line — an ALERT→RECOVERY *edge* — and reception recovered
      gradually without ever re-triggering a fresh ALERT, so no RECOVERY line ever fired despite
      ~2h of healthy `[OK]` readings. The pause rode the full 120-min ceiling into a needless
      ABORT, and the resulting STOP again sat unattended overnight, straight through arm A's
      `00:05` swap. **DEC-0089** fixes it: `recovered_since()` also checks the monitor's ordinary
      periodic `[OK]`/`[LOW]` line (a level signal, not an edge) as an additive fallback. Square
      shifted +24h a third time: now runs **08-15 → 08-23T00:05**, not the 08-14 → 08-22T00:05
      above (PR #177). Two sessions running with one novel blind-spot bug each in just-shipped
      campaign automation (DEC-0088, DEC-0089) — a dedicated state-machine audit is scoped for
      the next session (`BOOT.md`), not just another reactive fix.
- [x] **Campaign D — marvin gain pilot — CLOSED (S113, DEC-0128): the curve is flat; the gain
      axis is exhausted at marvin.** Pre-registered S111 (DEC-0126) as the shortlisting step
      DEC-0125 showed had never been run at this site. Ran exactly as designed — six 45-min
      gain-only blocks HIGH→LOW, 2026-08-31 21:01 → 09-01 01:30 ET, no aborts, self-terminated and
      restored prod at 01:30:39. **P496 74.65 · P449 73.79 · P402 74.98 · P372 74.97 · P328 73.29 ·
      P207 68.17.** Gain 328–496 is one plateau — 1.70 pts of spread against a ~1.61-pt per-arm SE,
      best delta **+0.01**, nothing near the 2.0-pt bar. **A shortlisting pilot that shortlists
      nothing: no candidate remains worth a confirmatory square, so the multi-day follow-up
      `BACKLOG.md` held open under campaign C is withdrawn, not deferred.** 207 is the one real
      result (−6.80, t=−3.75) and agrees with the physics — campaign A's near-parity for 207 was
      **LNA-in**, and DEC-0017's "207 optimal" is a with-preamp finding. Gain holds at 372, no
      config change; `SCHEDULE=` stood down (DEC-0096). **What closes this section:** like-for-like
      full-diurnal campaigns, LNA out both — 372: Foundation 72.83 vs marvin 72.82; 496: 74.83 vs
      73.98. DEC-0118 moved the receiver measurably closer with fewer walls and reception did not
      move. With `-ex` already a wash (+0.45/−0.06), that is **three axes — gain, receive window,
      siting — all flat at ~73–75%**, so the missing ~25% is not SNR-limited and not reachable by
      tuning. The open question is no longer *which setting* but *where the ceiling is*; candidates
      are in `BACKLOG.md`, cheapest-first, and none is another CLI sweep. **S115 (DEC-0133):** the
      ceiling is **frequency-independent** (the channels-46–48 RFI cluster is explained and worth
      ~2 pts) and the bulk of the loss is **periodic at ~7.75 s wall-clock, not hop-locked** —
      `BACKLOG.md` item 8 is the designed capture that names the oscillating part. **RESOLVED
      the same session (DEC-0134):** the capture ran; the "ceiling" is the Go demodulator's
      byte-only duplicate filter discarding the ISS's genuine repeat packets and booking each as
      a miss — real RF loss 0.3%. There is no RF ceiling. Fix (a time-gated duplicate check,
      Go rebuild) is S116's lead item; every ~73% baseline in this section is the ISS's repeat
      fraction, not link quality.
      **S116 reconciliation (DEC-0135) — the fix is built, and the campaigns are NOT re-run.**
      The time-gate landed with the repeat suppressed one layer up; validation is pre-registered
      against the S115 capture and needs no deploy. Two corrections to what is written above.
      **(a)** DEC-0134's "their *negative* results … remain valid as don't-re-sweep evidence" is
      **too strong** and is withdrawn: campaign B's own run-to-run scatter (sd 8.47 at 496,
      sd 4.67 at 372) exceeded the entire real signal, so A–D are **untested**, not settled.
      **(b)** They are nonetheless not worth re-running. Total remaining headroom is **~6 pts worst
      case** — 0.3% real loss, ~2 pts of channels-46–48 RFI (DEC-0133), ~4 pts of RF-dead runs ≥10
      (blocker 2) — against DEC-0059's **2.0-pt adoption bar**, and both named mechanisms are
      already identified and **not gain-responsive**. A re-sweep would re-measure axes we have
      independent reason to believe are flat, for a prize that mostly is not on them.
      **Instead: re-baseline by observation** — run the fix several days and read the honest number.
      Free, no apparatus, no pre-registration, no prod disruption. ~99% closes the question;
      materially lower is a new signal a campaign could, for the first time, actually resolve.
      **The real prize is diagnostic:** an RF-dead episode is currently buried in ~27% of background
      pseudo-loss, so against a flat ~99% baseline **blocker 2 becomes measurable for the first
      time** — which is worth more than any gain setting this section ever tested.
      **S117 reconciliation (DEC-0136) — DEPLOYED, and confirmed on production data.** `v2.0.15`
      cut over 2026-09-03 07:17:53 EDT (16m09s outage). Validation met every pre-registered
      number (`missed` **81 → 0**, `repeat` 0 → 79, `duplicate` 89 → 6), and prod's own INFO frame
      counters confirm it independently: duplicate frames/period **6.23 → 0.57** with repeat frames
      at **5.81**, population conserved — **27.2% of transmissions are repeats**, against
      DEC-0134's ~27%. The "re-baseline by observation" plan above is now **live and is S118's
      job 1**. Three corrections to what is written above and elsewhere in this file.
      **(a)** The monitor's thresholds do **NOT** go stale, contrary to the standing assumption:
      measured 73.2% before vs 75.5% after, because its `len(set(epochs))` metric already counts
      hop packets and saturates. Only `rxCheckPercent` consumers need re-keying.
      **(b)** "~99%" is `rxCheckPercent`'s answer over `hops = accepted + missed`, which is
      self-referential; over the steady-state window excluding **128 s** of cold-start acquisition
      the slot arithmetic also gives **~100%**, so the two agree — but they are different questions
      and should not be quoted interchangeably.
      **(c)** A `repeat` falls through to the normal path and emits a `msg.ID=` line, so "decoded"
      **includes** repeats: 274 accepted, **195 unique**.
      **S122 reconciliation (DEC-0137→0138→0139) — a second, independent `rxCheckPercent`
      artifact found and closed: the metric's denominator, not its repeat-dedup.** `#317`:
      `max_count = period // 2.8125` floored a full minute to 21 slots instead of ~21.33, making
      `count <= max_count` fail by construction and reading 101–105% on fully-received minutes
      (197/360 records, 55%, over 100% in the 12:00–18:00 pre-fix window). Fixed by denominating
      on the ISS's own inter-arrival clock (`round((last − prev) / loop_time)`), shipped as
      `v2.0.16` (31 s cutover, DEC-0138), confirmed on the first fully-post-cutover window
      (0/360 over 100%, DEC-0139) — `#317` closed. `docs/DATA_ERRATA.md`'s `DISC-0001` carries
      this as a second boundary. `v2.0.16` promoted to `main` the same session (`prod-baseline-
      20260904`); Docker Hub push still pending (`ops#265`).
- [x] ~~**Deploy the escalating watchdog (DEC-0065) to the NAS**~~ — **DONE** and genuinely live; it
      handled every stall on 2026-08-06 within seconds. ⚠️ **But the evidence originally cited here
      was the wrong kind, and S67 corrected it (DEC-0074).** "Matches the repo tip byte-for-byte,
      with zero resets or escalations since" proves the FILE, never the PROCESS — and "zero resets"
      can mean nothing was listening just as easily as nothing needed doing. That exact reasoning,
      applied to a *different* script, produced a whole decision entry on a false premise at S67.
      Liveness now has its own assertion in `ops/soak_check.sh`. **Cite process evidence, not a
      checksum** — but **not `/proc/<pid>` mtime**, which is access time and was measured reporting
      17 s for a 2.88-day-old process (S68b, #147). Use a startup log line after the file mtime,
      `/proc/<pid>/stat` field 22 vs `/proc/uptime`, and new-pid-with-old-pid-gone.
- [x] ~~**P0 — explain the two unexplained 08-02 outages**~~ — **substantially answered by DEC-0067
      (S63).** They were two different phenomena filed under one name. The driver's own 150 s
      watchdog is the discriminator and had been reporting correctly all along: it fires only when
      the main thread is executing, so a >150 s output gap **with** `rtldavis process stalled` is
      RF loss and a **silent** one is a process freeze. ERR-0005 fired it 21 times → genuine RF
      outage, and **0 detections on every other day measured** → a single incident, not a pattern.
      The 13:47 dropout fired nothing → **the receiver was fine and the process was frozen.**
      **Still open, tracked below: why it freezes.** ERR-0005's own root cause also remains
      unestablished, but it no longer gates campaign B on its own.
- [x] **P0 — why do the USB resets fire but never work? (DEC-0074, DEC-0075)** — ✅ **CLOSED S73**
      (checkbox corrected S76: the body below has said CLOSED since S73 while the box stayed
      unticked — the exact shape S66's pass caught on the tiering row). 3/3 failed on
      2026-08-06 (`RESET ineffective`, bad windows 8 → 10 → 15), 9/9 on 08-02. The watchdog works and
      is reporting that **the remedy does not**. *This line was missing until S68* — DEC-0074 raised
      the defect at S67 and no ROADMAP item was opened for it, so the repo's sequenced plan did not
      carry its own top blocker. **Apparatus LIVE since 2026-08-09 (DEC-0075)** — deployed from
      merged tip `ad7e5a4` and verified; `ops/usb_forensics.sh` brackets every reset with host and
      in-container USB state plus `rtldavis`'s open handles, so the next stall answers the question
      instead of repeating it. ✅ **CLOSED at S73 (DEC-0081) — the deep-read ran same-day and
      re-diagnosed the class.** The differential (3 capture sets, full night timeline,
      cross-repo load correlation; three read-only subagents + main-thread synthesis) found:
      the device never re-enumerates (DEC-0075's stale-devnum prediction was a
      measurement-design error — unbind/rebind doesn't re-enumerate), the driver's watchdog
      and respawns **work** (my earlier "no respawn" reading was log-blindness — re-inits log
      `startup process`, not `Starting up weewx`), and the stalls are **RF-dead episodes**:
      serially-silent children across multiple gain configs, recovery time-correlated, never
      action-correlated. Resets are theater for this class (~17 attempts, 0 fixes, 1 suspected
      harm — ERR-0005's recreate-fix now reads as episode-end coincidence, vindicating
      DEC-0065). ⤷ **S107 (DEC-0120) acts on that conclusion rather than only recording it:** the
      reset is no longer the assumed remedy. `REMEDY_MODE` selects one — `usb_reset` stays the
      default for existing Synology installs (this is a published extension, and the zero-efficacy
      record is *our* hardware), `restart_unit` is marvin's, `none` is detect-and-escalate. The
      Foundation body is deliberately not ported to marvin, where a hardcoded Synology bus path
      would no-op or reset another tenant's device. **Not deployed** — see `BOOT.md`.
      **Shipped same day (v2.0.13/ws.5 + monitor, before the square's first
      block):** resets demoted to one hedge (`RESET_MAX_TRIES=1`), child reaping (the one real
      process bug — kill-without-wait stacked three zombies under one weewxd), `STALL
      DIAGNOSIS` + `DATA DROUGHT` self-classification at the source, and the `episodes.log`
      ledger (the LNA-verdict datum). **What remains open is the episode root cause**
      (interference vs no-LNA margin vs site — episodes predate the LNA removal), a
      post-campaign characterization question riding the A×B readout. Minor: the deployed
      copy's `started=` field is unreliable until PR #146 is merged and that one file re-installed
      (#147) — the decisive signatures are unaffected. ✅ **Blocker 5 CLOSED (DEC-0077):** reset gaps
      do not contaminate campaign A. 11 resets (not nine), all 08-02; the archive went normal → 105
      absent rows → NULL → normal, already excluded because DEC-0069 drops the record either side of
      *any* gap without consulting the class. No present-but-low rows — the only real exposure.
      Campaign A's figures stand.
- [ ] **P0 — why does the weewx process freeze? (DEC-0067, DEC-0068)** **Rate and duration are
      measured, not eyeballed, as of S76 (DEC-0083): 1.49/day, median 240 s, min 180 s, max 840 s**
      — 45 silent off-slot archive gaps over 30.3 d, against the "~2-4 min, roughly once a day"
      this line carried for ~13 sessions. **Now a re-runnable tool, not a one-off (DEC-0085,
      S77): `ops/freeze_baseline.py` reproduces these figures (1.48/day) and adds the
      rolling-window placement the original one-off never did — unremarkable across 24h–72h
      (36.6–78.3rd pct), moving independently of the same-day record-max stall reading.
      **Corrected again S80 (DEC-0088): the tool's swap detection was schedule-only and missed ad
      hoc restarts (abort recovery, pause escalation) as a source of expected downtime, counting
      7 of them as freezes. True rate 1.31/day, 40 events over 30.5 d, not 1.49/1.48 — all four
      rolling windows read unremarkable.** **S85 (DEC-0094) split the rate by hour-of-day — a real
      lead, not a rate correction: the sibling tenant's nightly maintenance window tested NEGATIVE
      (9/40 freezes vs 7.2 expected, P=0.29), but the evening 18:00–21:00 window is significant
      (12 vs 5.0, P=0.0027), corroborating coffee-radar's own ~19:00 correlation (DEC-0068) across
      10 distinct dates. Mechanism still unproven — DEC-0068 measured the main thread `S`, never
      `D`, so "correlates with" is not yet "is blocked by" — next step is a mechanism probe during
      an evening window, not more timestamp counting.** **S89 (2026-08-18, DEC-0097/0098): the probe
      exists and is running** (`ops/proc_probe_nas.sh`, NAS-resident, ends 08-19 05:00) — it measures
      **cumulative** per-thread `iowait_sum`/`block_max`/schedstat rather than instantaneous state,
      because "`S`, never `D`" is a sampling-coverage artifact: `block_max` shows a **4041 ms** block
      in a 4 h span with no evening in it, so blocking demonstrably happens. **DEC-0097 also
      separates the two phenomena by clock** — RF-dead episodes cluster **00:00–04:00**
      (stall-bearing 7/9 vs 1.50, P=0.00009) with **zero** in this evening freeze window, so the
      overnight "reception dip" is *not* this item and must not be folded into it. **S92
      (2026-08-19, DEC-0102): the probe ran its full window and found its first hard number** —
      overnight (00:00–05:00) iowait is **11.80x** a clean daytime baseline (5.82x D-state-hit
      ratio), the strongest signal in the whole dataset, directly measuring the confound DEC-0092
      already named (sibling-tenant maintenance) and DEC-0097 flagged as undischarged. A
      minute-level cross-check against that night's actual RF-dead stall timestamps was mixed, not
      confirmatory (the single highest-iowait hour has zero stalls) — **root cause stays open**;
      DEC-0102 has the full record, including a concurrent ops#169 coffee-radar event that may or
      may not overlap this specific measurement. *When
      recomputing, drop `interval != 1` rows first: the
      S37 backfill wrote `interval=15` rows that read as 28 phantom 900 s freezes and inflate the
      rate ~60 %.* Individual events seen 07-30 08:04 (**LNA in**), 08-02 13:46, 08-03 02:59,
      08-03 23:23 (262 s, S64), and two more caught S65 (08-04 17:48 and 19:13 EDT). All threads stop together and nothing is logged;
      `weewxd`'s own main thread reads `S`, never `D`, across every capture so far — leans against
      the original "blocked on the bind-mounted log volume" hypothesis. **DEC-0068 (S65): this NAS
      also runs coffee-radar, and it was confirmed running (via `nasctl inspect`, not a name match —
      its scheduled job never sets `--name`) during one freeze, with loadavg spiking to 12.39 against
      a 0.3–0.7 baseline — a real contributor, not a full explanation.** The other S65 freeze, same
      night, had neither coffee-radar nor elevated load. n=1 correlated out of 3 captured freezes;
      not a settled base rate. `ops/freeze_watch.sh` (S65, now committed — no longer a scratchpad
      rebuild every session) is the tool for any further capture. **S105 (2026-08-28/29, DEC-0118):
      independent corroboration on entirely different hardware, found by accident during the marvin
      migration, not a targeted probe.** A live incident during cutover reproduced DEC-0067's exact
      discriminator (150s-raise + ~60s-respawn) and it fired *only* under a bad USB controller —
      zero occurrences across the following hour of healthy operation on the same box. Supports
      "environmental/hardware-triggered" over a weewx-code regression, but doesn't identify the
      NAS's own trigger (marvin's mechanism — a chipset USB controller — has no NAS equivalent to
      point at; the NAS has no comparable second controller to swap). Not a new probe result, an
      incidental one. **Root cause is not fully explained, but campaign B does not need it to be** — and as of **DEC-0069 (S66) the metric gate
      is CLOSED**, leaving the line below as B's sole remaining gate. DEC-0069 also bounds how much
      these freezes were ever worth to the campaign: **±0.03 points** on a pooled arm mean against a
      2.0-point adoption bar, once the metric is read at the resolution it is actually stored at.
      Ruled out already: NAS-wide stall, the S37 stdout wedge,
      CPU-quota throttling, `pressure_service`. Upstream hit this and worked around it without
      diagnosing it (`get_stderr()`'s 10 s cap).
- [x] ~~**P0 — make the campaign metric freeze-aware**~~ — **CLOSED by DEC-0069 (S66).** Two parts,
      and the larger one was a *resolution* problem, not a freeze problem: `harvest()` read the
      monitor's **5-minute** `RECEPTION:` aggregate, where one frozen minute drags a whole bucket
      (measured 16 % / 27 % against ~72 %) — that is where the ~0.8-point estimate came from. The
      same measurement is stored **per minute** in the archive DB as `rxCheckPercent`, where a freeze
      damages one record. Exclusion is **structural** (drop the record either side of any gap, plus
      NULL, plus non-physical `rx > 100`), never magnitude-based — a threshold would discard genuine
      deep fades and bias every arm upward. Net effect on a pooled arm mean: **±0.03 points** against
      a 2.0-point bar. New tool `ops/campaign_analyze.py` (+14 tests); `ops/rx_experiment.sh`
      deliberately untouched. Campaign A recomputed: spread **0.94 pts**, no arm near adoption.
- [ ] **P0 — the `database is locked` defect** — **BOUNDED at S66 (DEC-0070); no further work
      planned.** Stays open because the defect is capped rather than eliminated, not because
      anything is queued — WAL was the remaining idea and DEC-0071 abandoned it. Root
      cause is a pair of untouched defaults: `journal_mode=delete` (a reader's SHARED lock blocks the
      writer) plus weedb's **5 s** SQLite timeout (`weedb/sqlite.py:136`), so six seconds of reader
      cost a CRITICAL + weewx's hardcoded 120 s wait + restart ≈ **5–10 min**. **Shipped `timeout = 30`
      in the live `weewx.conf`** — outages now capped at ~30 s, verified in the running system.
      **⛔ WAL WAS TRIED AND ROLLED BACK — do not retry it (DEC-0071, S66).** HLF shipped the
      directory mount (ops#141); WAL went live 06:56 EDT on 08-06 and HLF **froze on a stale
      snapshot within minutes**. Two blockers, both missed by DEC-0070: a Docker `:ro` bind makes the
      **files** read-only (DEC-0070's test chmod'd only the *directory*, so it never reproduced the
      condition — structurally blind, DEC-0035 again), and SQLite creates `weewx.sdb-wal` mode
      **0555**, so even a read-write mount leaves a non-root reader unable to write it. Rolling back
      cost a **~6 min crash loop**. `journal_mode = DELETE` is now pinned by a `[[[pragmas]]]`
      subsection so an accidental flip cannot recur. **`timeout = 30` is the fix, not an interim** —
      it delivers most of WAL's practical benefit at none of this risk. Remaining detail below
      **pre-dates the LNA removal**
      (08-01 15:08, 08-02 19:45; earlier S59) — and **independent of the freezes above**. DEC-0067
      decomposed the 10-min outage: ~106 s of hung uploader threads + **120 s of weewx's own
      hardcoded wait** + ~5 min restart, so the thread hang is only ~18 % of it — the identical
      lock on 08-01 cost 4 min because the threads exited in 0.26 s. **Lead fix: the archive DB is
      not in WAL mode**, the standard cause of exactly this contention — *tried, see above*. If this
      ever recurs **despite** the 30 s cap, that means a reader held the lock >30 s and is a
      different problem; bound the uploader-thread joins then. **Archive DB readers (corrected S66,
      DEC-0070 — this row previously named "the dashboard"):** scanning every container that mounts a
      weewx path finds only `hyperlocal-forecast-api`, `eh-proxy` (parent dir, read-only), and weewx
      itself. Plus the NAS monitor (read-only, 6-hourly) and `weectl`.
- [x] ~~24 h **receiveWindow sweep**; reconcile image tag ↔ Dockerfile~~ — **dissolved by DEC-0059.**
      `-ex N` ≡ `receiveWindow 300+N` (upstream sums them), so the window is a mounted-config knob,
      no rebuild, and it is simply the second factor of the campaigns above. The `rw*` image tags
      were redundant, not merely misnamed.
- [x] ~~Confirm the running binary's `receiveWindow` (ARCHITECTURE §6)~~ — **CLOSED (S116):
      `receiveWindow = 300`, the upstream default, unpatched.** The premise above was wrong: the
      deployed binary *does* emit a startup settings line. S56 concluded otherwise from its absence
      in `weewx.log` and container stdout at normal verbosity, but the driver gates it behind
      `debug_rtld`. **Three independent confirmations, none of them a rebuild:** S114's debug window
      logged `user.rtldavis DEBUG info: … ex=0 receiveWindow=300 actChan=[4]` (DEC-0130); S115's
      standalone capture printed the same banner from the deployed binary directly; and S116 read
      the deployed source itself (`main.go:129`, `receiveWindow = 300`) while building DEC-0135's
      patch. The Dockerfile's in-build `grep -R receiveWindow` echo is a standing fourth check.
      *Lesson, and it is this file's own recurring one: "cannot be read from logs" was an inference
      from one verbosity level, carried as a fact for 60 sessions.*
- [x] ~~Investigate rebuilding `rtldavis` from newer Go source for `FreqError`/`ChannelIdx`
      telemetry~~ — **moot.** S57 confirmed the *currently deployed* binary already emits it; no
      rebuild needed for this purpose.

## P3 — Modularity toward multi-source (PRINCIPLES §1)
- [ ] Harden INTERFACES.md as the stable contract; document it well enough for a non-Davis WeeWX or
      CumulusMX producer to satisfy it. (Partial progress, and more than this line used to claim:
      DEC-0032's `rain_qc` flag, DEC-0086's `barometer_inHg` WeatherLink-passthrough provenance,
      DEC-0091's `barometer_fetch_epoch` + honest-null pressure/altimeter, and DEC-0093's
      `current.json` cadence decoupling are all documented there. **Corrected S97:** this line
      previously also claimed DEC-0053's station-identity finding was documented — it was not; only
      DEC-0053's cache-bounding finding (Finding 1) had actually made it into the doc. §2 now carries
      the missing station-identity/series-key trap (Finding 2), closing that gap for real. Finding 3
      (the SQLite archive's own missing correction flag) stays in `DATA_ERRATA.md` on purpose —
      INTERFACES.md scopes itself to the two *published* surfaces, and SQLite is neither. This item
      is about closing what remains, not starting from zero.)
- [x] Remove the vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005) — done S47.

---

**P4 and long-term/uncalendared direction moved to BACKLOG.md's "Long-term direction" section
(DEC-0058, S56)** — credential hygiene follow-ups, multi-source adaptability, the governance
template harvest, and the winter-2027 sky-state instrumentation (ops#110) all live there now,
not here.
