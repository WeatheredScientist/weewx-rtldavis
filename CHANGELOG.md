# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S57b] — 2026-07-29 — campaign A aborted after 80 min; two defects fixed (DEC-0061), schedule regenerated, re-armed

- **Campaign A aborted 12:13 EDT in its third block.** The safety model worked: baseline snapshot
  restored, sticky STOP sentinel set, prod left healthy on `gain 372` — verified. The one thing it
  failed to do was tell anyone.
- **Defect 1 — the health check was too small by construction.** `health_ok` allowed ~90s for a new
  archive record after a restart, but a restart needs boot (~25s) + up to a full 60s archive
  interval + ~30s write lag ≈ **115s worst case**. Measured on the failure: `weewxd` init 12:11:46,
  first record 12:13:30, abort fired 12:13:27 — **three seconds early**. Arm B had won the same coin
  flip 80 minutes before. Now `HEALTH_TRIES=36` (~180s), and the test asserts the *arithmetic*
  rather than the literal, so lowering it fails with the reason attached.
- **Defect 2 — every alert this script could send was inert.** `send_mail` sourced `monitor.env`
  without exporting, so its `python3` child saw nothing and died on `KeyError: 'ALERT_FROM'`. True
  since the file was written; never disproved because no alert had ever fired. Extracted
  `load_env()` (`set -a`/`set +a`), tested against a real child process, mutation-verified. Confirmed
  live against the real `monitor.env` after deploy (booleans only, never values) — all `True`.
- **Schedule regenerated for a 2026-07-30 start** (completes 08-07). The 07-29 run lost `A@00:05`,
  took a partial `B@06:05` and lost `C@12:05` — three damaged Latin-square cells, the exact
  time-of-day confound the design exists to remove. ~10h of delay bought a valid experiment.
- **Re-armed:** fixed script deployed (sha `88c1aeaf…`, byte-verified against the merged `dev` tip),
  stale state reset to `NONE` (otherwise the first tick would have harvested a baseline-config period
  and recorded it as arm-B data), STOP cleared, the aborted run's 88 samples rotated aside. Campaign
  starts itself at 00:05.
- Also corrected a comment promising a `schedule --generate <date>` mode that **has never existed**;
  the dev-side recipe that actually produces the table is recorded in its place.
- Gates: pytest **123 passed** (was 120), mypy clean. See DEC-0061.

---
## [S57] — 2026-07-29 — Phase 0 confirms FreqError telemetry (DEC-0060); RX campaign A deployed and running

- **Phase 0 answered:** `FreqError` telemetry exists in the deployed driver — confirmed within 13s
  of a restart (`Hop: {ChannelIdx:0 ChannelFreq:902419338 FreqError:0 Transmitter:0}`). Getting
  there took a real correction: the first attempt (`debug_rtld=2` alone, ~19:11 EDT 07-28) produced
  zero evidence for ~7h because the live `[Logging][[[user]]]` logger was at `INFO`, independent of
  `debug_rtld` — `dbg_rtld()` calls `log.debug()`, silently dropped regardless of verbosity. Fixed
  with a scoped `[[[user.rtldavis]]]` DEBUG logger entry (DEC-0060), not the broader `[[[user]]]`.
  Both changes fully reverted once confirmed (09:34 EDT 07-29). Honest tally: elevated-debug window
  ran ~14.5h against a planned 3h (a session gap), `weewx.log` grew to ~8.8 MB vs. a normal
  ~4 MB/day — non-critical, but a real DEC-0041 bloat instance. `ppm`/`fc` measurement-by-value
  deliberately deferred, not blocking the campaign.
- **`ops/rx_experiment.sh` deployed and running.** Scp'd to the NAS project root (sha-verified),
  `install` run (baseline snapshotted). Owner created the two DSM Task Scheduler entries (`tick`,
  `guard`, 5 min, root); first automatic tick swapped to arm B (gain 207, `-ex 0`) at 10:52:37 EDT.
  Campaign A runs unattended for 8 days, self-terminating to baseline (~2026-08-06 expected).
- **DEC-0059 status updated** (deployed/running, was design-only) and **DEC-0060 added** (the
  logger-level gotcha, so it isn't re-derived next time debug output is needed). ROADMAP.md P2
  section reconciled: Phase 0 checked off, campaign A marked running, the "rebuild for FreqError
  telemetry" item closed as moot (the current binary already has it).
- **Cross-repo:** [ops#112](https://github.com/WeatheredScientist/eaglehunt-ops/issues/112) closed
  with the full finding; [ops#114](https://github.com/WeatheredScientist/eaglehunt-ops/issues/114)
  tracks the running campaign; [ops#113](https://github.com/WeatheredScientist/eaglehunt-ops/issues/113)
  (the transient-state tracking proposal, filed this session) was independently built and closed by
  ops the same day — worth adopting `.claude/transient-state` here for future transient prod state.

---
## [S56d] — 2026-07-28 — S56 closeout

- Handoff rewritten so S57 opens on the three RX items in order (Phase 0 → deploy → regenerate the
  schedule if the start date slipped), with the standing watches demoted below them.
- Docs diet (DEC-0030): `[S53]` rolled verbatim to `CHANGELOG-ARCHIVE.md`; entries here now run
  S54–S56, and the S56 entries were **reordered newest-first** — they had landed S56, S56c, S56b,
  contradicting this file's own "most recent first" rule.

---

## [S56c] — 2026-07-28 — the RX experiment gets an apparatus (DEC-0059); 7 dead sweep scripts deleted

Design + tooling only — **nothing deployed, prod untouched** (still v2.0.11, gain 372).

- **`-ex N` ≡ `receiveWindow 300+N`** — upstream sums them and `receiveWindow` appears nowhere else,
  so the window axis is a mounted-config knob and **no arm of the experiment needs an image
  rebuild**. The `rw250/rw350/rw400` images were redundant, not just misnamed (DEC-0048). Read from
  upstream master; the deployed binary is older and unverified directly — caveat recorded.
- **Measured baseline replaces "~67–70%"**: 447 samples → **73.3%, sd 4.67**, autocorrelation ~0,
  no diurnal cycle. So 24 h/arm resolves 1.1 pts and DEC-0017's "1–2 weeks" was ~7× overkill.
- **`ops/rx_experiment.sh`** — Latin-square scheduler with literal-only arms, atomic verified writes,
  byte-exact whole-file revert, sticky STOP sentinel, self-termination to the production baseline,
  and a mailer independent of `weewx_monitor.py`. Verified end-to-end against fixtures.
- **`tests/test_rx_experiment.py`** (8 tests) — drives the real shell functions; includes a DEC-0045
  positive control proving the old global-regex approach corrupts the same fixture, and a machine
  check that the Latin square is balanced (mutation-tested: it goes red on a one-row typo).
- **Deleted all 7 pre-governance sweep scripts.** `gain_sweep.sh` and `fc_sweep.sh` counted
  `RAW_DATAPACKET_MATCH`, which prod no longer logs — they would have reported 0.0% for every arm
  and looked like they worked. `gain_sweep.sh` also used a 2.5 s denominator against our 2.8125 s
  ISS. The one durable finding living only in `fc_sweep.sh`'s header was moved to BACKLOG first.
- **DEC-0008's `set_gain.sh` exemplar superseded** — the kill/start codification moves to
  `restart_container()`; the rule itself is unchanged.
- Secret gate caught the test fixture's credential-shaped line; fixed the fixture, **not** the
  allow-list (DEC-0045).

---

## [S56b] — 2026-07-28 — ROADMAP.md split to P0–P3; long-term direction moves to BACKLOG.md (DEC-0058)

Same session, second act. Docs-only, nothing deployed.

- **STATION_NAME check:** before doing any work, live-verified the NAS `monitor.env` —
  `STATION_NAME="Eagle Hunt PWS"` was already set (since S31). BACKLOG.md's note was stale (dated
  "observed S27," pre-fix); corrected, no NAS mutation needed.
- **DEC-0058:** `docs/ROADMAP.md` trimmed to P0–P3 only (the actively-sequenced plan). P4 +
  "Longer horizon" (credential hygiene, multi-source adaptability, the template harvest, ops#110)
  moved to a new "Long-term direction" section in `BACKLOG.md` rather than a fourth document.
  `CLAUDE.md`'s doc-map annotated with the split.
- While editing `BACKLOG.md`, found and pruned a second stale copy of the already-resolved (S48)
  May rain-total item — same fact CHANGELOG `[S56]`'s ROADMAP pass had already corrected once, in
  the other file.
- **Self-caught bug:** the DEC-0057 append (`[S56]`, above) had matched an `old_string` that didn't
  include the file's true last line, stranding an orphaned original fragment (`*silently*.`) after
  everything inserted, and papering over it with an invented duplicate sentence. Fixed before
  appending DEC-0058: restored the original DEC-0056 closing line, removed the invented text.

---

## [S56] — 2026-07-28 — ROADMAP.md reconciled and restructured; DEC-0057 adds it to the closeout ritual

Docs-only, nothing deployed. Prompted by a routine status check that turned into an audit.

- Confirmed prod healthy on v2.0.11: co-rejecting grep 0 hits (positive-control-verified against a
  known-present pattern), ops#105 confirmed CLOSED. Found ops#110 newly opened (winter 2027
  sky-state instrumentation — IR sky sensor alongside the lightning detector; planning horizon
  only).
- **ROADMAP.md reconciliation pass:** found and fixed 5 items shown open that had already shipped —
  the `cleanup_backlog.md` fold-in (done S27), remote-URL-casing + stale-branch cleanup, P1.5's
  "deploy pending" (shipped v2.0.4, S34), the May rain-total reconciliation (done S48), and the
  README public-onboarding refresh.
- **Fuller restructure:** folded the old P1 ("false-rain fix") and P1.5 ("Sensor-QC hardening")
  sections into one continuous data-integrity arc that now actually covers what shipped since —
  v2.0.4 through v2.0.11 (sensor-QC filter, reception-metric fix, frame-level co-rejection, signed
  temp decode, cap-16 tuning) — previously unrepresented on the page entirely. Collapsed P0.5's
  mostly-done checklist to a pointer. Added the ops#110 item under Longer Horizon.
- **DEC-0057:** ROADMAP.md joins the closeout ritual as step 5 — same-session update whenever a DEC
  ships/closes/reprioritizes a line item — plus a "Keeping this current" tripwire inside
  ROADMAP.md itself (next full check due **by S66**). CLAUDE.md's closeout steps renumbered
  (5→6 model-tier restore, 6→7 commit+push).

---

## [S55c] — 2026-07-28 — v2.0.11 shipped: cap 16 live in prod; ops#105 audit closed from this side

Third act of the day, owner-approved after the ops relay flagged the gap: DEC-0056's cap was merged
but inert (the driver is baked, DEC-0031 — v2.0.10 was built before PR #93). Released same-day so
R2 actually protects the station.

- **Release:** `DRIVER_VERSION` → **0.20+ws.3**, Dockerfile header → v2.0.11 (one PR this time,
  #95); promoted via #96 (merge `a4628769`); NAS build from the md5-verified tree (the build
  script's tree gate caught my own stale ws.2 assertion from the v2.0.10 template and refused to
  build until corrected — the check working as designed, on its author); pushed `:v2.0.11` +
  `:latest` (digest `sha256:b8f35f36…`); prod recreated 11:00 EDT; live-verified banner
  `0.20+ws.3`, sensor_qc active, records publishing, soak 13/2/0 (restart-window WARNs). Tagged
  **`prod-baseline-20260728b`**;
  [GitHub release v2.0.11](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.11).
  **Rollback: `:v2.0.10`.** Fifth consecutive clean recreate; no stall.
- **Monitor tripwire live end-to-end:** owner killed the old monitor 10:28, scheduler respawned it
  on the reframed code (sha-verified), startup email received, `--test-alert` fired through the
  new wording and received.
- **Prod moved v2.0.9 → v2.0.10 → v2.0.11 in one day** (R1 then R2), each with its own baseline
  tag and retained rollback.
- **ops#105: both code items (R1 + R2) now released, deployed, live-verified** — audit umbrella
  closeable from this repo's side
  ([completion note](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5105845282)).
- Docs: CONVENTIONS/CLAUDE quick-ref → v2.0.11 / `prod-baseline-20260728b` / rollback `:v2.0.10`;
  soak `EXPECT_IMAGE` default → `:v2.0.11`.

---

## [S55b] — 2026-07-28 — R2 decided and coded: `MAX_PLAUSIBLE_TIPS` 60 → 16 (DEC-0056), rejection email reframed as the tripwire

Same session, second act: the owner opened the R2 design discussion, an **evidence pass over the
full 70-day archive** settled it, and the owner approved the package (PR #93).

- **The evidence** (pre-correction backup, 95,901 minutes, 490 wet): worst real minute **7 tips**;
  worst real 3-min window **exactly 16** (2026-06-14 storm — still passes, the check is
  `delta > max_tips`); reception during rain never below 50%; in-service gaps near rain: two
  1-minute events ever; rain-counter rejections at cap 60 in the 30-day logs: **zero** (all five
  "implausible" hits are SensorQC wind/humidity). Physics: at the bucket's ~4 s/tip ceiling a
  genuine delta can exceed 16 only across a >64 s gap — longer than any gap observed during rain.
  **Reframing:** weewx `[StdQC]` (0.3 in/min) already discarded anything over 30 tips, so
  "60 → 16" really exposes only the never-occupied 17–30 band.
- **The worry that shaped the package** (owner: don't lose an intense storm to an over-tight
  filter): the change ships with the failure mode converted from silent-permanent to
  loud-bounded-recoverable — `weewx_monitor.py`'s existing DEC-0021 glitch email is reframed as
  the **DEC-0056 tripwire** (prompts the WeatherLink cross-check; a rejection on a wet day is the
  predefined revisit trigger), a **recovery playbook** is written into DEC-0056 (console
  reconciliation via the ERR process), and a **driver↔monitor marker contract test** pins the
  alert to the driver's exact wording. Confirm-on-reject documented as the designed escalation if
  the tripwire ever fires on real rain.
- Tests 111 → **112**: boundary 16-passes/17-rejects, the 06-14 evidence vectors, cap-60-era
  cases retuned as documented rejects; cap and marker assertions both **mutation-tested red**.
- **Deployment split:** the monitor (mounted layer) deployed NAS-side same session — scp'd from
  the merged tip, sha-verified `383f5baa…`, restarted via the scheduler respawn. The driver cap
  (baked layer, DEC-0031) **rides `dev` until the next image cut (v2.0.11)** — prod's running
  driver keeps cap 60 until then; a hardening, not a live bug, so it forces no deploy.
- R2 closed out on [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105).

---

## [S55] — 2026-07-28 — v2.0.10 shipped: the signed temperature decode is live in prod; upstream PR #23 opened

**The R1 release (DEC-0055), executed end-to-end** — prod ran the unsigned decode until 09:28 EDT.

- **Version bump first** ([#88](https://github.com/WeatheredScientist/weewx-rtldavis/pull/88)):
  `DRIVER_VERSION` 0.20+ws.1 → **0.20+ws.2** — the banner is the live-verify marker (DEC-0046), so
  a driver release must be distinguishable in the running log — plus the missing 2026-07-28
  DEC-0055 entry in the driver's header change list, README, and the CHANGES-FROM-UPSTREAM version
  table (`influx.py` stays ws.1, untouched). Dockerfile header → v2.0.10
  ([#90](https://github.com/WeatheredScientist/weewx-rtldavis/pull/90); every release since v2.0.6
  bumps it). Promoted dev → main (PRs #89 + #91, merge `2d3bc09a`), CI green throughout.
- **Built on the NAS from the verified tree** (S52 pattern: staged tarball → fresh
  `build-v2.0.10/`, with `rtldavis.py` md5-checked against `git show` before the build could
  start); pushed `:v2.0.10` + `:latest`, digest `sha256:ee3027e1…`. weewx stays pinned 5.4.0
  (#78) — no silent drift this rebuild.
- **Prod recreated** from the re-captured live inspect config (kill→rm→3 s→run; no mounted-layer
  changes this release — `loop_json_writer.py`/`influx.py` untouched since v2.0.9).
  **Live-verified (DEC-0046):** banner `0.20+ws.2`, `sensor_qc True`, records arriving, outTemp
  74.1 °F sane, soak **13 PASS / 2 WARN / 0 FAIL** (both WARNs restart artifacts). No startup
  stall — 4th consecutive clean recreate. Tagged **`prod-baseline-20260728`**;
  [GitHub release v2.0.10](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.10).
  **Rollback: `:v2.0.9`** on the NAS and Docker Hub.
- **Upstream [lheijst#23](https://github.com/lheijst/weewx-rtldavis/pull/23) opened**
  (owner-reviewed verbatim), companion to #22. Found while drafting: **upstream #19 (LloydR) had
  already diagnosed the sign bug** — its 16-bit-signed ÷16 form carries the `pkt[4]` flag nibble
  into the value (a constant +0.05 °F on digital frames) and lacks `0xFF8`; #23 credits the
  diagnosis and offers the masked 12-bit form as an alternative, non-stepping per #22's precedent.
- **R1 closed out on [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5104787452)**;
  **R2 untouched** (owner holds it for design discussion).
- Housekeeping: two stale `.claude/worktrees/` (+ their `claude/*` snapshot branches, 0 unique
  commits) removed; four merged `s54-*` branches deleted local + origin — the repo is back to
  exactly `dev` + `main`. Session-start watches: co-rejection 0 hits (positive-control-verified),
  #74 calm-windDir silent 10.6 h post-v2.0.9 (last WARNING 21:59, 19 min before that deploy),
  humidity largest step 0.7 pts in 240 new samples, soak 10/5/0 pre-release.
  `ops/soak_check.sh` `EXPECT_IMAGE` default → `:v2.0.10` (STATUS's standing instruction). No new
  DEC — the session executed DEC-0031/0038/0046/0055 as designed.

---

## [S54] — 2026-07-28 — R1 landed: outside-temperature decode is now signed two's complement (DEC-0055); not yet released

Owner approved **R1** from the S53 ops#105 audit; **R2** (`MAX_PLAUSIBLE_TIPS` 60 → 16) held for
further discussion and is untouched.

- **`rtldavis.py`** — the 12-bit digital temperature field is decoded as **two's complement**
  (`(temp_raw - 0x1000) / 10.0` when bit 11 is set), and `0xFF8` joins `0xFFC` as a no-sensor
  sentinel. Unsigned, a −5 °F reading decoded to 404.6 °F (207 °C), tripped the −40…65 °C SensorQC
  bounds, and — since v2.0.9 — **co-rejected the entire frame** (DEC-0054), so an ordinary cold
  snap would have nulled wind + payload every ~30–60 s and saturated the corruption alarm we are
  currently watching. Analog/thermistor branch untouched.
- **Deliberate one-LSB deviation from weewx-meteostick** (DEC-0055): its
  `-(temp_raw ^ 0xFFF)` is *one's* complement — 0.1 °F warm on every negative, maps `0xFFF` and
  `0x000` both to 0.0 °F, and flips the truncation bias at zero. Its two real contributions (the
  field is signed; the `0xFF8` sentinel) are adopted.
- **`tests/test_temp_twos_complement.py`** — 10 new tests: −40 °F frame, the `0xFFF` case that
  distinguishes this from meteostick, both sentinels, a DEC-0054 **co-rejection non-fire** sweep
  (−0.1…−39.9 °F), plus two positive controls (frame-builder round-trip; proof the bounds gate
  really fires on the old unsigned decode). All three plausible regressions **mutation-tested red**.
  Also fixed a real cross-module test-isolation trap: these suites share `sys.modules` and replace
  `weewx.wxformulas` wholesale, so the stub is now additive and resolved through `rtldavis.weewx`
  (the object the driver actually dereferences) rather than `sys.modules['weewx']`.
- **`CHANGES-FROM-UPSTREAM.md`** — two DEC-0034 fork-inventory gaps closed. DEC-0054 (frame-level
  co-rejection, shipped in v2.0.9 at S52) had never been recorded there and is now behavior
  change **11**. The `rtldavis.py` delta was **recounted against the real upstream baseline** —
  fetched from the same `weewx-contrib` `src.tgz` the Dockerfile builds from, which this repo does
  not vendor: **+477 / −88** (1422 → 1811 lines), replacing S37's **+263 / −51**. That figure was
  one commit stale the day it was written (it is the exact count at `cd49214`, and the S37 commit
  recording it also added the fork-identity header). The reproduce recipe now ships next to the
  number, so the next recount is a paste rather than an archaeology session.
- **Upstreaming table** — gained the temp-sign candidate (the prose already claimed 10 was part of
  the intended contribution), and two **stale statuses corrected**: it still read *"draft comment …
  not posted"* and *"not yet offered"* for work that has been live upstream since S38 —
  [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22) and
  [david-lutz#1](https://github.com/david-lutz/weewx-influx2/pull/1) are both OPEN, and the issue #15
  comment was posted 2026-07-13. The table was written at S37 and never re-read after the PRs landed.
- **Stray `0` file removed** from the repo root ([#86](https://github.com/WeatheredScientist/weewx-rtldavis/pull/86)) —
  a zero-byte artifact committed by accident in `5e3c3dd` (S41) alongside `ops/soak_check.sh`, a
  script dense with redirects; a stray `2>0` for `2>&1` is the likely mechanism. It landed as
  `0 | 0` and was never referenced: nothing redirects to it, the `Dockerfile` `COPY`s only named
  files (no root glob, so it never entered the image), and there is no packaging manifest to sweep
  it up. Tracked files 82 → 81.
- Gates: pytest **111 passed**, `ruff check` clean (0.5.7, DEC-0027), `mypy --ignore-missing-imports
  --no-strict-optional .` clean on 33 files.
- **Not released.** The driver is baked (DEC-0031) → needs an image rebuild + deliberate release,
  deadline **before first frost**. A companion upstream PR belongs alongside lheijst#22.

---
