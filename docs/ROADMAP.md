# Roadmap — weewx-rtldavis

**Status:** Direction (what next, in what order). For *why* see DECISIONS.md; for *how* see
ARCHITECTURE.md; for *what's on the bench right now* see `BOOT.md` (the single source of truth for
the current session + active thread).
**Last updated:** 2026-11-25 (S212 — **scheduled full reconciliation, on time**: seven lines moved, detail
in the guardrail section. Next check: S222.)
Earlier banner entries (S56 to S210c, one per targeted or full pass) are in `docs/ROADMAP-ARCHIVE.md`, Blocks 1 and 7.

`BOOT.md` holds what's *in motion right now*; this holds the ordered, actively-sequenced plan
(P0–P3 only, per DEC-0058). BACKLOG.md holds unordered near-term ideas **and** long-term/
uncalendared direction — see its "Long-term direction" section for anything horizon-scale.

## Keeping this current (staleness guardrail)

This file went 20 sessions / 8 releases (S35 → S55c, v2.0.3 → v2.0.11) without being updated —
a user-asked audit found it, not anything structural. Two rules to not repeat that:

- **When a DEC lands that ships, closes, or reprioritizes a line item here, update that line in
  the same session** — the same discipline CLAUDE.md already requires for DECISIONS.md ("same
  session, not deferred"). Don't wait for a docs-diet pass or an audit to notice.
- **Next scheduled reconciliation check: by S222** (~10 sessions out). If the session counter is
  at or past S222 and this line still says S222, that itself is the signal it's overdue — run the
  same pass as S56, S66, S76, S86, S96, S106, S116, S126, S136, S146, S156, S172, S183, S192, S202 and S212 did (diff every
  open/pending item here against DECISIONS.md, CHANGELOG.md and `BOOT.md`).
- Last full reconciliation: **S212, 2026-11-25** — **on time** (due S212). Every open line was read
  against DEC-0230 to DEC-0248, `CHANGELOG.md`, `BOOT.md` and the open issues. **Seven lines moved:**
  P0.8 phase 2 (DEC-0238's soak is running, DEC-0247 joins the owed image, confirm-on-reject follows in
  its own minor, DEC-0246's release gate); P1's header, its cap-16 line (DEC-0248 withdraws DEC-0056's
  safety claim) and its "Still open" list (DEC-0245 and DEC-0248 accepted, not built; DEC-0247 on
  `dev`); P1.9's #536 item (fifteen live drops, and the 11-20 gap the gate missed); the P0 freeze row
  (the same gap); P2's closing sentence (it did not name the apparatus decision left open). Classed, no
  line: DEC-0230, DEC-0231, DEC-0239 (CI and tier gates), DEC-0236 and #586 (`BOOT.md` job 2), C1
  (held) and C4 (accepted, DEC-0229) of the outside review. Not added: #475 (parked), #514 and #380
  (watches), ops#465 (weewx's part is done: DEC-0243, DEC-0244).
- Earlier full reconciliations (S56 to S202) are in `docs/ROADMAP-ARCHIVE.md`, Blocks 2 and 7,
  verbatim, S210c's targeted pass with them. The pattern they record: a status carried past the DEC that changed it, found by diffing
  every open line against `DECISIONS.md`, `CHANGELOG.md` and `BOOT.md`.
- Earlier: full pass **S56, 2026-07-28**; targeted DEC-0057 passes at **S63** and **S66**.

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

## P0.7 — Code audit + fixes (S145–S146) — ✅ DONE: every finding closed (S181)
Whole-tree audit at `7d06cbf` (DEC-0205): six read-only reviewers, 39 findings, every high one
re-verified by the main thread before filing. The ten high items (#402–#411, `eaglehunt-ops#358`)
are fixed (PRs #412–#418) and **shipped**: the monitor's fixes (#413) went live with a restart on
2026-09-29 09:31 ET, and the driver and uploader fixes (#412, #414) as the v2.0.18 image at
16:37 ET (DEC-0206). The medium/low items in `docs/CODE_REVIEW_S145.md` are now scheduled by P0.8:
phases 1–3 fixed 10, 11, 12, 15, 17, 19, 20, 32, 35, 36 and 38 (S158–S163, shipped by v2.0.21 or
the mounted `influx.py`), and the rest were phase 5 (S172), done S178–S181. The secret gate's four detector holes (#421)
are closed (S151, DEC-0210). Same shape as P0.6 above
(`docs/CODE_REVIEW_S24.md`).

## P0.8 — Public readiness (S156–) — 🔶 OPEN, ordered by what a new user hits first
Follows DEC-0213 (the README, `docs/DEPLOY.md` and `examples/` rewritten for a new user, PR #449).
The announcement waits for phases 1 and 2 and for the dashboard going public. Phases run in order;
items inside a phase don't depend on each other. Phases 1, 3, 4 and 5 are collapsed to one line each at
S210c; their full text, with every PR and issue number, is `docs/ROADMAP-ARCHIVE.md` Block 3.

- [x] **Phase 1 — what a new user copies** (#451 to #455, S158/S159). Quickstart proven on a fresh Linux
      host: container half S162 (arm64), host steps 10-23 in marvin's disposable guest (ops#427), the
      three systemd-unit checks S187 (2026-11-02, ops#439, `marvin-vm --usb-host`).
- [~] **Phase 2 — the image, one release at a time.** v2.0.21 released S169; since then v2.1.0 (S176,
      DEC-0222's first minor: the burst gate and `windGust10`), v2.2.0, v2.3.0 and v2.4.0 (S190,
      DEC-0229's time gate). **Prod ran v2.4.0 from 2026-11-04 18:36:38 ET to the 11-23 soak swap (below); `:latest` = `:v2.4.0`**
      (multi-arch). Left: the first arm64 run against a live radio (README says smoke-tested until
      then). **Owed: the next minor image**, baked on `dev` and not in prod: DEC-0235 (device pinning:
      `RTLSDR_DEVICE`, `doctor`'s listing), DEC-0232 (the `windGust10` column for new installs; prod migrated S210
      2026-11-21), DEC-0237 (#579: the driver exits the container after three consecutive decoder
      exits), DEC-0240 (the starter conf ships every uploader off) and DEC-0244 (the starter runs the
      loop writer and DewpointCacher, Influx idles on `replace_me`, the mount's `bin/user` imports),
      DEC-0247 (a failed thermistor is no reading; message 9's gust only from the wind channel), plus
      DEC-0238's librtlsdr v2.0.3 pin, **not built**: its prod soak of the library alone is running
      (swapped 11-23 7:58 AM ET, scored 11-27 to 12-04 00:00 ET; the prod line above is v2.4.0's tree on
      that library, `v2.4.0-v4l-test`). After a PASS the pin joins this image. **Then, in its own minor:**
      confirm-on-reject (DEC-0248), on the owner's yes and cap choice. Each release carries a one-line
      reason for its number; a major needs the owner's explicit yes (DEC-0246). DEC-0242 (`influx.py` `0.20+ws.3`) rides
      the mounted checkout, not the image. **V4L (ops#440):** the NAS stick is a Blog V4L, which the
      image's librtlsdr (osmocom v2.0.2+2) does not support and v2.0.3 does
      (`docs/RTLSDR-V4-AND-PINNING.md`); DEC-0236's NAS run judges a reference receiver and is not
      evidence for that bump. Release history and merged PRs: archive Block 3.
- [x] **Phase 3 — tests that cannot fail, then the bugs they hide** (#456, S159, PR #464; audit 32's
      240 s init grace rode v2.0.21, audit 20 fixed in the mounted `influx.py`).
- [x] **Phase 4 — upstream, in the owner's voice** (S180/S181: weewx-contrib#2, weewx-packages#6, a
      comment on lheijst/rtldavis#2, the weewx-influx2#1 reply). Nothing left but watching for
      answers: `BOOT.md` job 5 and `docs/UPSTREAM-THREADS.md`. `weewx-packages/weewx-rtldavis` is the
      live continuation; the lheijst repos have been quiet since 2023.
- [x] **Phase 5 — cleanup, no user-visible change** (audit 13 to 14, 18, 21 to 28, 30 to 31, 37, 39;
      S178 to S181; DEC-0226 settled the license tags). Nothing left.

- [~] **Phase 6 — the install path (DEC-0225, S182; built DEC-0227, S184, and DEC-0228, S185).**
      Twelve commands plus a hand edit become four commands and no edit. **Shipped S184 as v2.2.0
      (in prod 2026-10-31 10:51 ET):** `docs/QUICKSTART.md`, `scripts/host-setup.sh`, compose plus
      `.env` (PR #519), and the image half (PR #520): the entrypoint seeds the config into an empty
      mount, first-run env vars read once, startup summary line, `HOME=/tmp` and `BIAS_TEE=0` as
      image defaults; the README quick start is the short one (PR #521). **Shipped S185 as v2.3.0
      (in prod 2026-11-01 11:31 ET):** proposal E, `doctor`, an informational `HEALTHCHECK` on
      `weewx.log` and an entrypoint that dispatches its first argument (PR #527, DEC-0228), and
      proposal F, `WEEWX_DRIVER=simulator` at seed time (PR #526); release prep PR #528. **Left:**
      the acceptance test (a stock 64-bit Pi OS plus the quick start, timed, by someone who has not
      read the repo). Research: `docs/INSTALL-RESEARCH.md`.
      **S210c:** DEC-0240 and DEC-0244 later corrected the starter conf the entrypoint seeds (every
      uploader off; the writer and DewpointCacher on); they ride the next minor image (phase 2).
Errors in the Go decoder itself are their own track, P1.9 below; its image changes ride phase 2's
release or the one after.

## P1 — Data integrity & Sensor-QC hardening (S18–S55c) — ✅ DONE; two follow-on designs accepted, not built
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
  tripwire verified live end-to-end. **Corrected S211 (DEC-0248):** the claim that 16 is "safe at every gap
  length" is withdrawn (188 days of data: 10 tips in one minute, 19 in two); the cap stays 16.
- **Battery-flag co-rejection → v2.0.17** (S144): DEC-0203/DEC-0204 — a co-rejected frame now takes
  its battery-low bit with it, and a message type no Davis transmitter sends (0x0, 0x1, 0xB, 0xD,
  0xF) condemns a frame outright. Corrupt frames at reception collapses had produced one-minute
  false ISS low-battery readings and, occasionally, a phantom gust. The monitor now reports the ISS
  battery flag in each 6-hourly reception summary and emails once when it persists across healthy
  reception; four reports have read `OK -- flag clear`. Not yet seen live: a `frame failed
  message-type proof` line (it needs a glitch; 8 in 31 days, none since the cutover).
- **Rain recovery phantom → v2.0.21** (S160, shipped S169): DEC-0218 — a counter that dipped and
  came back (115 → 114 → 115) booked the climb back as up to 16 tips on a clean frame, unlogged; a
  reading after a rejected one is now judged against the last accepted count first. Exhaustive
  over every counter triple; the always-resync stays, so no stall is possible.

**Still open — ordinary watches, not a new arc.** Current status (co-rejecting grep, humidity-spike
signature DEC-0044, first-frost test of the signed-decode negative branch, DEC-0056's
rain-rejection revisit trigger) lives in **`BACKLOG.md` §Standing watches** — moved there from
`BOOT.md` at S67 (DEC-0072), since a watch that has not fired is not in-flight work. Not duplicated
here, and not evidence this P1 item is still "in progress." **Designed and accepted S211, not built:**
DEC-0245 (the driver nulls an ISS 10-minute gust that received wind cannot support, #584; re-measure
after a 25 mph event first) and DEC-0248's confirm-on-reject (`docs/RAIN-CAP-DESIGN.md`; owner's yes and
cap choice). **On `dev`, next minor image:** DEC-0247. **`#74` calm-windDir left this list at
S59**, closed on five consecutive clean days with a positive control.

**Blocker discipline (DEC-0011):** no drop-in dev receiver — RF-dependent verification is calendar-
bound and done via reversible live hot-swap with an instant rollback path.

## P1.8 — Foundation decoupling: InfluxDB host move (ops#260 step 3, OPS-DEC-0188) — ✅ CLOSED (S126), weewx's slice
The `influxdb` container moved from Foundation to marvin (S124, DEC-0141, DEC-0142; runbook
`docs/INFLUXDB-MIGRATION.md`); weewx's Foundation-dark drill ran clean S125; the last open items (the
tar deletion, ops#260 step 4) closed S126. Checklist, times and the S125 details: archive Block 4.

---

# MEDIUM TERM (P2–P3) — after v2.0.11

## P1.9 — Fix corruption at the decoder (Go), not only downstream (S156–) — 🔶 REOPENED S188: steps 1–3 done, step 4 in prod since S190 (v2.4.0, DEC-0229), its 30-day re-run due about 2026-12-04
P1 closed every corruption class with filters in the Python driver; the source is in the Go decoder
and is still there. What the Go side has shown, and where each stands:

- **Repeat packets booked as misses** (DEC-0134): fixed by our `-dupwindow` time gate
  (`patch/rtldavis-dupgate.patch`, DEC-0135, v2.0.15), offered as lheijst/rtldavis#7. Done.
- **One burst decoded twice, the second copy sometimes corrupted** (DEC-0033, DEC-0035): the clean
  copy is dropped as a duplicate; a corrupted one differs, so it passes the filter, and about 1 in
  65,536 also passes CRC and arrives as a valid-looking frame. Cause found at S173 (DEC-0223): a
  burst whose matching preamble offsets cross a 512-sample block boundary is sliced in both blocks.
  Gate in prod since v2.1.0 (S176); the first watch was clean (S178). Done.
- **CRC failures were dropped silently** (`protocol.go` ~L218): counted since v2.0.21 (#458,
  DEC-0216). Baseline: about 9,700 near-burst failures a day beyond chance, so roughly one
  CRC-valid phantom a week. Done.
- **Which upstream version the bundled source is** (`BACKLOG.md`, open since S21): #450 pins it;
  S178 diffed it against `lheijst/rtldavis` master: every Go source file is byte-identical. Done.
- **A noise decode re-anchors the hop clock** (DEC-0229, S188): upstream hops on any CRC-valid
  frame from an active ID with no arrival-time check, so a chance CRC pass at a random moment costs
  51 blind hops and a re-init, 2 to 5 min with no station. Measured: 12 of 15 driver-rejected
  garbage frames in 30 days were followed by exactly that loss (40 archive records, #536). Built
  S189, in prod since S190 (v2.4.0). **Corrected S192:** this said "not released".

Steps, in order:

- [x] #458 **Measure.** *(built S157, DEC-0216, PR #461; in prod with v2.0.21 since 2026-10-26;
      baseline recorded and closed S173)* Count CRC failures per hop slot and how many fall within
      ~100 ms of an accepted frame; surface it through the driver's counter line. The upstream diff
      moved to `BACKLOG.md`.
- [x] #459 **Fix.** *(designed and built S173, DEC-0223; in prod with v2.1.0 since 2026-10-28
      15:40 ET, S176; the first watch was clean, S178)* A content-agnostic burst gate in Go keyed on the frame's position in the sample
      stream, not the hop slot (the receiver has retuned before the next block's copy arrives).
      Window: one packet's airtime, 1,344 samples. Credits LloydR's lheijst/rtldavis#2. The Python
      filters stay as the backstop. Live check: the driver's `largest duplicate gap` line.
- [x] **Offer upstream** *(S180, 2026-10-29, owner's go: the mechanism posted as a comment on
      lheijst/rtldavis#2, pointing at `patch/rtldavis-burstgate.patch`; no PR, the repo is quiet
      since 2023 and the continuation has its own gate)*.
- [ ] #536 **Time gate.** *(measured and designed S188; DEC-0229 accepted and built S189; in prod
      since 2026-11-04 18:36:38 ET as v2.4.0, S190; fifteen live drops to 11-25 07:57 ET (three to
      11-14, four 11-18 to 11-21, eight 11-23 to 11-25, read S212), none followed by a gap (seven of them in the 48 h after the
      11-23 soak swap, against eight in the 18.6 days before it, with CRC failures per minute unchanged:
      unexplained, watch it through the soak); **one gap it missed, 11-20 02:23 to 02:27 ET, after a CRC-valid 83.6 mph frame it passed
      (S210b)**; the other gaps 11-17 to 11-25 are the 11-21 restart and receiver move and the 11-23 soak
      swap; the soak image carries the same gate; closes on the 30-day re-run; CI fails, not skips,
      the Go gate tests since DEC-0230)* Once
      synced, drop a CRC-valid frame more than 100 ms off the expected slot before it can re-anchor
      the hop clock, hop, or reach the driver; log it and count it as `offsched=N` in the minute
      line; reset the crcstats slot label on re-init. `patch/rtldavis-timegate.patch` after the
      burst gate, a `tests/go/` replay, then a release and a 30-day re-run of the S188 correlation.
      Does not touch on-schedule bit-error frames (ERR-0012's class; a `windGust10` cross-check is
      the separate candidate for those; its archive backstop, the `windGust10` column, is DEC-0232).

Not here on purpose: the RF-dead episodes (`BOOT.md` blocker 2, DEC-0081), where the Go child goes
silent and recovers with time. Nothing has shown a decoder bug behind them yet; if #458's counters
or a capture do, it gets a step here.


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
`tests/test_rx_experiment.py`) was deployed and ran campaigns A to D. **Nothing here is open except the
two P0 rows at the end of this section and the apparatus decision (DEC-0241, deferred).** Every closed item below is one line; the full text of each, with
every figure and S-number, is `docs/ROADMAP-ARCHIVE.md` Block 5 (verbatim).

- [x] **Phase 0: `FreqError` telemetry exists** (S57, DEC-0060); rebuilding for it was moot.
- [x] **Campaign A (LNA in) ended early 2026-08-02** (ERR-0005's 105-minute outage); its arm ranking
      was unsealed by DEC-0069, spread 0.94 pts, no arm near adoption. Settles DEC-0017.
- [x] **v2.0.12 deployed 2026-08-10** (S70); `:latest` moved at GATE 2 (S73).
- [x] **Campaign B (LNA removed) closed S101: gain 496 adopted at Foundation (DEC-0115)**; campaign C
      re-measured at marvin's position and **496 does not clear DEC-0059's 2.0-pt bar there: gain holds
      at 372 (DEC-0125, S111)**. The campaign scheduler's recovery fixes (DEC-0082, 0087, 0089, 0090)
      are in the archive.
- [x] **Campaign D (marvin gain pilot) closed S113 (DEC-0128): the gain curve is flat** (328 to 496 one
      plateau; 207 is the one real loss). With the receive window and siting also flat, DEC-0134 then
      found the "missing ~25%" was the Go demodulator booking the ISS's repeat packets as misses (real
      loss 0.3%); the fix deployed as v2.0.15 (DEC-0136, 27.2% of transmissions are repeats).
      DEC-0135: A to D are **untested**, not settled, and not worth re-running (about 6 pts of headroom
      against a 2.0-pt bar); re-baseline by observation instead. Two more `rxCheckPercent` artifacts
      closed: #317 (v2.0.16, DEC-0138) and #402 (v2.0.18).
- [x] **Escalating watchdog live** (DEC-0065); S67's lesson (DEC-0074): cite process evidence, never a
      checksum or `/proc/<pid>` mtime.
- [x] **The two 08-02 outages explained** (DEC-0067): the driver's 150 s watchdog separates RF loss
      (it fires) from a process freeze (silent).
- [x] **USB resets never work: CLOSED S73 (DEC-0081)** — the stalls are RF-dead episodes; resets are
      theater for that class. DEC-0120 made the remedy configurable (`REMEDY_MODE`); v2.0.13/ws.5 shipped
      the child reaping and `episodes.log`. The episode root cause stays open (`BOOT.md` blocker 2).
- [x] **Campaign metric made freeze-aware** (DEC-0069, `ops/campaign_analyze.py`): ±0.03 pts against a
      2.0-pt bar.
- [x] **`receiveWindow` = 300, the upstream default** (S116, three confirmations); the sweep was
      dissolved by DEC-0059.
- [x] **Apparatus retired (DEC-0250, S213, #553; supersedes DEC-0241):** `rx_experiment.sh`, its unit
  and timer, `tests/test_rx_experiment.py` and the campaign B runbook moved to `ARCHIVE/rx-campaign/`.
  The driver's hot-swap (DEC-0117) stays; heartofgold removes the deployed unit (ops issue).

- [ ] **P0 — why does the weewx process freeze? (DEC-0067, DEC-0068)** Open; the mechanism is
      unproven. **Rate: 1.31/day, 40 events over 30.5 d (DEC-0088; ~1.51/day excluding an incident day,
      DEC-0198, which reconfirms it), median ~240 s (DEC-0083)**, re-runnable with
      `ops/freeze_baseline.py` (drop `interval != 1` rows first or the S37 backfill adds 28 phantom
      freezes). **By hour:** the nightly maintenance window tested negative (9/40 vs 7.2, P=0.29,
      DEC-0094); the evening 18:00–21:00 window is significant (12 vs 5.0, P=0.0027), corroborating
      DEC-0068's coffee-radar correlation; RF-dead episodes keep a different clock, 00:00–04:00
      (DEC-0097), and are not this item. Overnight iowait read 11.80x a clean daytime baseline
      (DEC-0102): the confound named, not confirmed. Ruled out: a NAS-wide stall, the S37 stdout wedge,
      CPU-quota throttling, `pressure_service`. DEC-0118's marvin-migration incident reproduced the
      discriminator only under a bad USB controller (environmental, not a code regression).
      **Leads:** every corrupt-frame battery flip in S144's sample (DEC-0203), and a CRC-valid 83.6 m/s
      frame on 2026-10-30 (S187), was the last line before a silence of about 3 to 4 minutes.
      **Short gaps (2 to 5 min) are a mechanism, not a lead (S188, DEC-0229):** upstream re-anchors the
      hop clock to any accepted frame, so a noise decode costs 51 blind hops plus a re-init park; 12 of
      the 15 garbage frames the driver rejected in 30 days were followed by one, and weewxd resumed by
      itself. The fix is P1.9 step 4, in prod since 2026-11-04 (v2.4.0); one short gap since has that
      shape (11-20 02:23 ET, P1.9 #536). **Not explained:** the 10-22
      62 min outage (two RF-class stalls, no decoder exit, S204) and DEC-0083's long tail. **Inferred,
      not measured (S201):** #579's shape (a vanished dongle never exits the container; **decided S204,
      DEC-0237: the driver exits after three consecutive decoder exits, baked on `dev`, next minor
      image**) or the osmocom librtlsdr USB hang fixed in v2.0.3 (`65f0658`; DEC-0238's pin, soak
      running). Campaign B's metric gate is closed (DEC-0069). Full trail, S-numbers and tool notes:
      archive Block 5.
- [ ] **P0 — the `database is locked` defect** — **BOUNDED at S66 (DEC-0070); no further work planned.**
      Open because the defect is capped, not eliminated. Cause: `journal_mode=delete` (a reader's SHARED
      lock blocks the writer) plus weedb's 5 s SQLite timeout; six seconds of reader cost a CRITICAL,
      weewx's hardcoded 120 s wait and a restart, 5–10 min. **`timeout = 30` in the live `weewx.conf` is
      the fix, not an interim**: outages capped at about 30 s. **⛔ WAL was tried and rolled back — do
      not retry it (DEC-0071):** a Docker `:ro` bind makes the files read-only and SQLite creates
      `weewx.sdb-wal` mode 0555, so HLF froze on a stale snapshot within minutes and the rollback cost a
      ~6 min crash loop. `journal_mode = DELETE` is pinned by a `[[[pragmas]]]` subsection. If it recurs
      despite the cap, a reader held the lock over 30 s: a different problem, bound the uploader-thread
      joins then. Archive-DB readers (DEC-0070): `hyperlocal-forecast-api`, `eh-proxy` (read-only
      parent dir), weewx itself, the monitor (read-only, 6-hourly) and `weectl`. Full text: archive
      Block 5.

## P3 — Modularity toward multi-source (PRINCIPLES §1)
- [ ] Harden INTERFACES.md as the stable contract; document it well enough for a non-Davis WeeWX or
      CumulusMX producer to satisfy it. **Written S199 (DEC-0233): `docs/INTERFACES.md` is a
      specification** — three surfaces (loop JSON, InfluxDB, and the SQLite archive as §3, which states
      Finding 3's missing correction flag), a §0 rules and meanings table, a row per field with
      InfluxDB's three tiers, one contract version (1.1), one owner; the history moved verbatim to its
      Appendix A. The per-DEC progress list this line carried (DEC-0032, 0053, 0086, 0091, 0093, 0200,
      0202, 0209, 0211, 0220, 0221, 0224, the S146 and S97 corrections, ops#442) is in
      `docs/ROADMAP-ARCHIVE.md` Block 6. **DEC-0232** (S198b) gives the archive a `windGust10` column
      (built; prod migrated and backfilled S210, 11-21 summaries rebuilt S211, `docs/WINDGUST10-MIGRATION.md`). Audited S197
      (`docs/INTERFACES-AUDIT-S197.md`, 16 findings): parts 1 to 4 and 8 done S199, parts 5 to 7 shipped
      as `loopjson` 1.2.0 (next line). What remains is the ops issue below.)
- [x] `loopjson` 1.2.0, DEC-0233 parts 5 to 7 — **shipped S201 (DEC-0234)**: the `contract` key
      (1.2), finite-only output, and `contract/` (JSON Schema, fixtures, `check_contract.py`) tied to
      the writer by tests; release `loopjson-v1.2.0`, in prod since 2026-11-12 22:42 ET.
      **S208 (DEC-0243):** the extension states its floor, WeeWX 5.0 or later; CI's `weewx-range` job
      proves every 5.x minor. **S209 (DEC-0244):** the image's starter conf runs the writer (next image).
- [ ] One ops issue for the cross-repo drift `docs/INTERFACES-AUDIT-S197.md` lists (draft in S201b's
      notes; owner's go to post). CumulusMX stays out until someone wants it.
- [x] Ship `loop_json_writer.py` as an installable WeeWX extension (`weewx#440`, the dashboard's
      DEC-0348 ask) — **designed S153, shipped S155 (DEC-0211)**: release `loopjson-v1.0.0` of this
      repo, proved on a clean WeeWX 5.5.2; prod writes `writer: loop_json_writer/1.0.0`. The
      adopter README is `extensions/loopjson/README.md`, linked from the main README since S156.
- [x] Ship `influx.py` as an installable WeeWX extension (#474, dash#936 section A.2) — **shipped
      S165 (DEC-0219)**: release `influx-v0.20+ws.2`, proved in CI on WeeWX 5.5.2 with the
      Simulator; the image installs it from this repo since v2.0.21. Upstream had not moved since
      2021 (`distutils`, TLS verification off). **S207d (DEC-0242, #558):** `0.20+ws.3` drops the dead
      NAS-LEASE yield; `lease_dir` stays accepted and ignored with one INFO line. On `dev`; it reaches
      prod at the next pull and restart, and the tag `influx-v0.20+ws.3` is the owner's go. **S209
      (DEC-0244):** the extension's installer idles `[[Influx]]` on `replace_me`.
- [x] Opt-in extra fields and `loop_interval_s` in the loop-JSON feed (#473) — **designed S166/S168
      (DEC-0220, DEC-0221), built S170, shipped S171**: release `loopjson-v1.1.0`, in prod since
      2026-10-27 09:16 ET. Prod has set `extra_fields = windGust10` since 2026-10-28 15:40 ET
      (DEC-0224). The image's contract label was settled by DEC-0222 (SemVer against the data
      contract) and v2.1.0 (S176).
- [x] Remove the vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005) — done S47.

---

**P4 and long-term/uncalendared direction moved to BACKLOG.md's "Long-term direction" section
(DEC-0058, S56)** — credential hygiene follow-ups, multi-source adaptability, the governance
template harvest, and the winter-2027 sky-state instrumentation (ops#110) all live there now,
not here.
