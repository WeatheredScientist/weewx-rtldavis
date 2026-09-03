# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S115] — 2026-09-02 — DEC-0133: RFI explains channels 46–48 but only ~2 pts; the bulk of the loss is a fixed ~7.75 s wall-clock modulation, not hop-locked

- **DEC-0133 (analysis, no capture, no prod change).** Crossed S114's `rtl_power` CSV against
  DEC-0130's 51-channel miss histogram with the demodulator's ±134 kHz passband applied: in-band
  exposure picks out exactly channels 46/47/48 (8/6/6 bursts, none for 45/49) — an FHSS neighbour on
  a ~400 kHz comb — so DEC-0132's "the tie weakens" was a bare-MHz artifact. The cluster is ~250 of
  3,806 misses (~2 pts); the other 48 channels sit flat at 69.7 ± 10: **the ceiling is
  frequency-independent.**
- **New finding:** the 3,047 miss timestamps are periodic in wall-clock time — Rayleigh peak at
  7.7495 s (z = 97) vs z = 4 for the hop-locked 11/4-hop alternative; gaps peak at 3 hops,
  autocorrelation undecayed to 60 hops, consecutive misses anticorrelated, smooth modulation (miss
  probability ~0.17 → 0.5). Isolated single misses carry 21.9 of the window's 32.2 pts. Host stalls
  ruled out read-only (cgroup pressure zero; loss identical to 0.01 pt across Foundation and marvin).
- **Blocker 6 reframed** ("what oscillates at ~7.75 s or an alias in the shared chain"); `BACKLOG.md`
  ceiling item rewritten with item 8, a designed ~25 min dongle-exclusive capture (`rtl_test` at the
  Go geometry, standalone `rtldavis -v` for per-packet freqError, full-band `rtl_power -i 1`).
- **Data loss noted:** the Sep 1 debug window's received-packet lines rotated away unharvested —
  only S114's `missed` grep survives (session scratch). Trap logged in `docs/GOTCHAS.md` §3.
- S111's entry rolled verbatim to `CHANGELOG-ARCHIVE.md`.

## [S114] — 2026-09-02 — Spectrum capture finds wideband RFI, not a clean 925.5–926.5 MHz interferer (DEC-0132); ops#253 fully closed; PR #305 merged

- **Merged PR #305** (Foundation's stopped weewx container decommissioned).
- **ops#253 closed, both stages.** Marvin's `exec_devices` grant (`0bda:2838` via a per-device
  udev rule, owner-ratified S114) had only been smoke-tested with `rtl_test` before this session.
  Ran the real thing: `weewx.service` stopped (~6 min outage, self-service), a 5-min `rtl_power`
  sweep of 924.5–927.5 MHz through `marvinctl exec-ro`, prod restarted clean.
- **DEC-0132: the capture's noise floor was flat and stable all 5 minutes** (no rolloff shape —
  evidence against a static gain rolloff or fixed antenna null), **but 16 of 60 ten-second windows
  carried transient bursts (5–34 dB above floor) spanning 925.15–927.48 MHz** — nearly the whole
  capture band, not confined to DEC-0130's flagged 925.5–926.5 MHz channels 46–48 (only 7 of 16
  fall there; the single largest, +34.5 dB, hit 927.34 MHz, well outside it). Reading: RFI
  strengthens as the mechanism, but the exclusive tie to channels 46–48 weakens. Blocker 6 stays
  open — free next step (cross the spike frequencies against DEC-0130's histogram) queued for
  S115, explicitly on Fable per the owner's call, since it's open-ended analysis, not execution.

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
