# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S78] — 2026-08-12 — Guard abort reconstructed and cleared: first freeze pair to gate the campaign

- **`rx_experiment.STOP` fired at 19:55 local** (`30-min mean reception 47% < 50% floor, arm H`).
  Reconstructed via `ops/freeze_baseline.py`: two back-to-back FREEZE events (19:46→19:50 240s,
  19:55→20:02 420s) — no stall line, correctly absent from `stall_baseline.py`'s episode list.
  **First known freeze pair severe enough to trip the campaign's own abort floor** (freezes were
  characterized as "gates nothing", DEC-0081/0083). Reception recovered to 67–84% within 10 min,
  healthy since.
- **STOP cleared** (owner-approved in chat, Class C), well ahead of the `2026-08-13T00:05` arm-A
  due time — no schedule shift needed this time, unlike DEC-0082. Landed in PR #168. Treated as a
  `BOOT.md`/`BACKLOG.md` finding, not a new DEC — refines an already-decided characterization
  rather than making a new design call.
- **Stall burst (DEC-0083): third flat reading (S76/S77/S78)** — 48h/72h still record-max 6/6 with
  no further growth, starting to lean plateau per S77's own threshold. 24h dropped to 1 episode
  (68th pct); acute rate quiet ~19h at check time.
- `ops/soak_check.sh`: 16 pass / 1 expected warn / 0 fail. Green gate: ruff clean, 224 tests, mypy
  clean on 46 files — no code touched this session, docs only.
- **Swap verification still open**: arm-A due `2026-08-13T00:05` had not yet occurred at session
  close — carried to S79.

---
## [S77] — 2026-08-12 — Freeze rate gets its own tool (DEC-0085); barometer's WeatherLink-passthrough provenance documented (DEC-0086)

- **DEC-0085 — `ops/freeze_baseline.py` ships**, completing DEC-0083's explicitly-flagged
  follow-up (BOOT/BACKLOG both warned the freeze number would decay without it). Reuses
  `stall_baseline`'s stall data and `campaign_analyze`'s DB constants rather than re-deriving
  either; `window_start()` extracted out of `stall_baseline.py` (+2 tests) so both tools share the
  same left-censoring boundary. Live run reproduces DEC-0083 almost exactly (21 RF-dead/12
  arm-swap/45 freeze exact, median 240s exact, rate 1.48 vs. 1.49/day). New: a rolling-window
  placement for the freeze side the original one-off never had — unremarkable across 24h–72h,
  moving independently of the same-day record-max stall reading. 210 → 224 tests (+12 in the new
  file, +2 for `window_start()`).
- **DEC-0086 — `barometer_inHg` is an unflagged, already-corrected WeatherLink passthrough.** The
  VP2+ ISS never transmits pressure over RF; `pressure_service.py` polls WeatherLink's cloud API
  and relays its already sea-level-corrected `bar_sea_level` as-is, with no `_qc` flag distinguishing
  it from RF-derived fields. Documented in `docs/INTERFACES.md` §1; cross-posted as a heads-up to
  `eaglehunt-weather-dashboard#377` and `eaglehunt-ops#162`.
- **eaglehunt-ops housekeeping:** #158 closed (duplicate of already-settled #153/#155 under
  OPS-DEC-0101), #160 closed (scope complete — see DEC-0085 above, plus the standing-watches sweep
  was already done per BACKLOG.md), #159 commented (weewx's open bullet answered by DEC-0083/0085).
- **`docs/CONVENTIONS.md`:** stopped hardcoding a model name in the commit-trailer convention
  (caught stale — said `Opus 4.8` while the session ran Sonnet 5).
- **Housekeeping:** 10 stale, already-merged feature branches deleted (local + remote,
  `s73`–`s76`-prefixed) — none touched `origin/dependabot/pip/weewx-5.5.0`, still deliberately open.

## [S76] — 2026-08-12 — Stall rate measured, not eyeballed (DEC-0083); secret gate's sixth hole closed (DEC-0084)

- **DEC-0083 — S75's "trending hot" survives measurement, but its evidence did not.** Over 30.5 d
  and 31 rotations the 48 h and 72 h windows ending now hold **6 episodes each, the record
  maximum** (98th pct); 24 h is 96th pct but off its peak of 5, so the burst may be easing.
  **The unit had to be fixed first**: a stall *line* is not an event — the 150 s watchdog re-raises
  every ~3 m 40 s, so 08-02 is **21 lines and one episode**. Clustering gives 15 episodes, stable
  at 30/45/60 min, and **reproduces DEC-0081's independently-derived boundaries** for the 08-10/11
  night exactly.
- **Three corrections to how S75 reached it.** Onset is **08-10 23:56**, not ws.5 — the v2.0.13
  container started 18:05 local on 08-11, so **5 of the 6 burst episodes predate it**; the ledger's
  19-hour field of view was mistaken for the phenomenon's onset. Not a simple LNA effect either:
  LNA-in 0.40/day → LNA-out 08-02→08-10 **0.13/day, the quietest stretch in the record** →
  08-10→now **2.43/day**. And "2→4 ledger rows" **compared two instruments** — row 3 is
  drought-only and `DATA DROUGHT` appears zero times in every pre-ws.5 log.
- **DEC-0081 amended: its LNA dates are wrong.** "08-02 and 08-06 were LNA-in" — the LNA came out
  **mid-ERR-0005, early 08-02** (S61: none existed yet; S62: "first honest no-LNA telemetry
  accruing"; S70: "out since 08-02"). **08-06 was LNA-OUT**; 08-02 only straddles. The clause's
  point survives on 08-02 alone.
- **New sanctioned readout `ops/stall_baseline.py`** (+7 tests, 203 → 210) — states its
  left-censored window and threshold sensitivity every run. Building it exposed a bias in its own
  first cut: anchoring "current" on the last stall guarantees the window contains it, so the check
  would read hot right after every episode. Fixed to anchor on now.
- **Secondary sweep (ops#160 job 3): freeze rate measured at 1.49/day, median 240 s** against the
  inherited "~once/day, ~3.5 min" — right order of magnitude, **~40 % understated**, refines rather
  than overturns. **A 60 % confounder was removed first**: the S37 backfill's `interval=15` rows
  read as 28 phantom 900 s freezes, caught only because individual events were printed rather than
  the summary rate. **Co-rejection watch re-verified 0 through 08-12 and positive-controlled**
  (stale at "through 08-01"); phantom-rainRate already instrumented in `soak_check.sh`.
- **DEC-0084 — secret gate hole class 6, found free by the routine pre-commit positive control.**
  `_assign` needs 8+ *consecutive* value chars and a Google app password breaks that run every 4;
  `_apppw` required **quotes**. So an **unquoted** app password was missed in every spelling —
  and unquoted is the **native form of `weewx.conf` (ConfigObj) and `monitor.env`**, the two files
  that must never be committed. Gitignored, so nothing leaked. **It survived S68 because that fix
  planted the quoted literal, went green, and never asked the neighbouring spelling.** Fix is
  key-anchored (an unanchored shape match would flag ordinary English prose); **one allow-list
  widening refused** — five of the six historical holes were allow-list defects, so
  `monitor.env.example`'s placeholder moved to `YOUR_GMAIL_APP_PASSWORD` instead. Harness holes
  27–29, **54 passed / 0 failed**. **The new detector then went red on the DEC entry documenting
  it** — the first draft wrote the literal shape into `DECISIONS-FULL.md`, and the gate caught it,
  exactly as `check_secrets.sh`'s own comment predicts. A decision log earns no exemption
  (DEC-0045); both spellings are now described rather than written.
- **ops#147 closed out from this repo's side** — weewx's §11 adoption named (DEC-0072 for item 1,
  DEC-0074-as-corrected for item 3); it was the one thing the thread was still waiting on here.
- Green gate: ruff clean, **210 tests**, mypy clean on 44 files. *A first mypy run reported
  "Success" on 42 files while silently skipping both new ones — `git ls-files` lists tracked files
  only. Staged first, then re-ran: 5 real errors.*

---
*(S73–S75 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
