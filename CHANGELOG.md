# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S113] — 2026-09-01 — Campaign D closes the gain axis at marvin: the curve is flat, no candidate shortlists (DEC-0128)

- **Campaign D ran exactly as pre-registered and self-terminated clean** — six 45-min gain-only
  blocks HIGH→LOW, 2026-08-31 21:01 → 09-01 01:30 ET, no aborts, prod restored 01:30:39.
- **Readout: P496 74.65 · P449 73.79 · P402 74.98 · P372 74.97 (incumbent) · P328 73.29 ·
  P207 68.17.** Gain 328–496 is one plateau — 1.70 pts of spread against a ~1.61-pt per-arm SE,
  best delta **+0.01**, nothing near DEC-0059's 2.0-pt bar. **A shortlisting pilot that shortlists
  nothing:** the multi-day confirmatory campaign held open under campaign C is withdrawn, not
  deferred. 207 is the one real result (−6.80, t=−3.75) and matches the physics — campaign A's
  near-parity for 207 was LNA-in, and DEC-0017's "207 optimal" is a with-preamp finding.
- **Larger, undesigned finding — three axes are now flat.** Like-for-like full-diurnal campaigns,
  LNA out both: 372 = Foundation 72.83 vs marvin 72.82; 496 = 74.83 vs 73.98. DEC-0118 moved the
  receiver measurably closer with fewer walls and reception did **not** move. With `-ex` already a
  wash (+0.45/−0.06), tuner gain, receive window and physical siting are all flat at ~73–75%: the
  missing ~25% is not SNR-limited and not reachable by tuning. **ROADMAP P2 closed** on that basis
  (its header still read "A COMPLETE, B LAUNCHED (S70)").
- No config change — gain holds at 372. `SCHEDULE=` emptied to the DEC-0096 stand-down, which also
  stops the TZ-corrected staleness tripwire failing every PR. Marvin's live copy still carries the
  elapsed schedule but is **inert** (state `BASELINE`; `tick` no-ops on `want == have`, `guard`
  exits at its `BASELINE` check) and its sha matches repo HEAD — the deploy rides the next real one.
- **New BACKLOG item replacing the tuning axes: "Where is the ~25% ceiling?"** — cheapest-first,
  starting with two free read-only checks (is `max_count`'s denominator honest given the 51-channel
  hop; settle `ppm`/`fc` by measuring the live `FreqError` distribution rather than sweeping it).
- Method gap recorded: `campaign_analyze.py`'s `fetch()` is still NAS-hardwired (pre-DEC-0118), so
  this is the second campaign read through a hand-assembled `marvinctl exec-ro` transport. Port it
  before a third.
- **Then ran both of that item's free checks the same session (DEC-0129).** (a) **The denominator is
  honest** — `loop_times` is exactly Davis's `(41+id)/16` s, so the missing ~25% is undecoded
  packets, not a measurement artifact; hypothesis rejected. Incidentally `max_count` varies 19–23
  where `iss_channel=1` implies a fixed 23, so the driver's `period` is not the archive interval
  (unresolved — the `ARCHIVE_STATS` line is not currently emitted), and **per-minute variance is
  entirely binomial** (predicted 9.2–9.9 sd at ~20–25 packets/min, measured 8.80 — no excess
  variance, so the sd≈9 the campaigns fought was counting statistics, not RF weather).
  (b) **`ppm`/`fc` is a dead axis and blocker 4 closes on measurement** — the offset is real and
  one-sided (+2206 Hz = +2.41 ppm, zero negative samples, contradicting the standing "it'll be
  centred" prior), but reception is flat across a 10× offset range (corr +0.075), so the AFC absorbs
  it entirely. `-noafc` is contraindicated by the same result rather than merely untested.
- **The ceiling is now characterized as deterministic, structural, and ours** — no excess variance,
  unresponsive to gain, receive window, siting and frequency offset. **The owner's field observation
  is the strongest input yet:** a real Davis console at comparable distance from the same ISS drops
  only single digits, so the signal is there and the ~20-pt gap belongs to our receiver, not the
  link. Leading untested hypothesis: 26 MHz / 51 channels versus an RTL-SDR's ~2.4 MHz means it must
  retune per hop. Next step is bounded and needs no prod access — the deployed Go source is publicly
  fetchable (`Dockerfile:46`) and has never been read directly.

## [S112] — 2026-09-01 — Full-history rewrite: privacy scrub of infrastructure identifiers and personal emails (DEC-0127)

- **The entire git history (661 commits, every branch and tag) was rewritten with `git-filter-repo`
  and force-pushed** to remove private-infrastructure identifiers from historical file versions and
  personal email addresses from early commit metadata. Owner-directed: privacy outranks history
  immutability. All SHAs changed — existing clones must re-clone. Verified clean with
  positive-controlled scans on every axis; zero forks existed; GitHub Support purge requested for
  server-side cached objects. `SECURITY.md` carries the public re-clone notice. Full trail:
  DEC-0127.
- Triggered by the S112 public-accessibility audit (four parallel reviews: doc/version drift,
  PII/secrets, code-comment quality, newcomer experience) — remaining findings are queued as
  follow-up work (`BACKLOG.md` §Public-maturity push, `BOOT.md` jobs 3–5), this session shipped the
  time-sensitive piece first.
- **Stale-schedule CI tripwire fixed to compare in the SCHEDULE's own timezone** —
  `test_current_schedule_is_not_fully_stale` used the runner's naive clock, so UTC CI runners fired
  it 4–5 h before the ET terminator passed; first bit PR #298 mid-Campaign-D. Verified with
  `TZ=UTC` before/after. Merged with the transparency PR (#298).
- Phase 0 before the rewrite: NAS SSH port rotated (owner, DSM), UniFi port-forwarding verified
  empty — the exposed values were never WAN-reachable. Ops session briefed cross-session for their
  own nas.env/alias/DEC follow-through.

## [S111] — 2026-08-31 — Campaign C's real verdict: 496 does not clear the adoption bar at marvin; 372 holds (DEC-0125)

- **ops#235 fixed mid-session (ops-side): `marvinctl exec-ro`'s missing `-i` flag was closing
  container stdin.** Verified end-to-end with the exact read DEC-0124 left blocked: a read-only
  `sqlite3` query piped through `exec-ro` against the live, mode-`0500` archive DB returned 1333
  clean rows, exit 0. Confirmed on ops#235.
- **Ran DEC-0069's own `campaign_analyze.py` logic (unmodified) against the real per-minute data.**
  Result: **A (372) 72.82% (n=368) vs B (496) 73.98% (n=350), B +1.16 pts — under DEC-0059's 2.0-pt
  adoption bar**, smaller than DEC-0124's coarse 5-min proxy (+1.87 pts), not larger.
- **Verdict logged as DEC-0125: 496 does not clear the bar at marvin's RF position — gain holds at
  372, no config change.** Per `BACKLOG.md`'s S107 pre-commitment, this is a standalone finding
  that Foundation's DEC-0115 answer doesn't transfer to marvin's site, not a reversal of DEC-0115.
  Also verifies `BOOT.md` job 4 (archive DB opens `mode=ro` cleanly under `journal_mode=DELETE`).
- **Reconciled:** `CONSTANTS.md`'s gain row/hardware-site prose/timeline, `docs/ROADMAP.md`'s
  Campaign B/C item (now closed as a marvin result too), `BACKLOG.md`'s gain re-sweep item (closed).
- **Fixed two stale claims `BOOT.md` was carrying from ops#233.** The restart-grant question is
  resolved (MARVIN-DEC-0099: the grant already exists, corrected upstream mid-Campaign-C — this
  file was still quoting the earlier "no grant exists" finding), and `usb_watchdog.sh`'s fate is
  decided (retiring, MARVIN-DEC-0100), not still open.
- **Campaign D pre-registered and shipped (DEC-0126): a marvin-site gain pilot, launching
  2026-08-31T21:00 ET.** Six gain-only blocks HIGH→LOW — 496, 449, 402, 372, 328, 207 — reusing
  Foundation's original pilot points plus 207 (dropped from campaign C on a Foundation-only
  judgment DEC-0125 just showed doesn't transfer). Arm-selection input only, never adoption
  evidence. `arm_cmd()` gains `P207`; `SCHEDULE=` populated; `campaign_analyze.py`'s `LEGENDS`
  gains `"D"`; `tests/test_rx_experiment.py` gains `_require_campaign_d()` + 3 structural tests,
  and `_require_campaign_b()`'s over-broad gate ("any P* row") is corrected to require the H hold
  specifically — the old gate would have misfired campaign B's assertions against campaign D's
  pilot-only shape. Full suite green (465 passed / 9 skipped).
- **Campaign D deployed and armed live on marvin, same session.** `rx_experiment.sh` shipped and
  hash-verified, Campaign C's stale baseline snapshot archived to `.campaignC` (was blocking
  `install`), `install` succeeded (fresh baseline snapshotted, schedule armed), `logs/campaign.inhibit`
  set, monitor confirmed healthy. No further action needed for the 21:00 ET launch. Also caught and
  reverted a wrong turn: attempted wiring `marvinctl pull`-based deploy for weewx before finding
  marvin's own MARVIN-DEC-0079, which already tried and rejected that design for this tenant (the
  on-disk layout doesn't match this repo's structure — deploy stays flat/scp, deliberately).

---
