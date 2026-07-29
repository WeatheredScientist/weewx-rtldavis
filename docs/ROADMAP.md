# Roadmap — weewx-rtldavis

**Status:** Direction (what next, in what order). For *why* see DECISIONS.md; for *how* see
ARCHITECTURE.md; for *what's on the bench right now* see STATUS.md (the single source of truth for
the current session + active thread).
**Last updated:** 2026-07-28 (S56 — split: P4 + "Longer horizon" moved out to BACKLOG.md's new
"Long-term direction" section, per DEC-0058 — this file is now P0–P3 only, the actively sequenced
plan, so it doesn't get cluttered by uncalendared/aspirational items. Earlier same-session pass:
folded the old P1 + P1.5 sections into one continuous data-integrity arc covering v2.0.3–v2.0.11;
collapsed P0.5's mostly-done checklist to a pointer; added the staleness guardrail below.)

STATUS.md holds what's *in motion right now*; this holds the ordered, actively-sequenced plan
(P0–P3 only, per DEC-0058). BACKLOG.md holds unordered near-term ideas **and** long-term/
uncalendared direction — see its "Long-term direction" section for anything horizon-scale.

## Keeping this current (staleness guardrail)

This file went 20 sessions / 8 releases (S35 → S55c, v2.0.3 → v2.0.11) without being updated —
a user-asked audit found it, not anything structural. Two rules to not repeat that:

- **When a DEC lands that ships, closes, or reprioritizes a line item here, update that line in
  the same session** — the same discipline CLAUDE.md already requires for DECISIONS.md ("same
  session, not deferred"). Don't wait for a docs-diet pass or an audit to notice.
- **Next scheduled reconciliation check: by S66** (~10 sessions out). If the session counter is
  at or past S66 and this line still says S66, that itself is the signal it's overdue — run the
  same pass as S56 did (diff every open/pending item here against DECISIONS.md, CHANGELOG.md, and
  STATUS.md's "Shipped" log).
- Last full reconciliation: **S56, 2026-07-28** (this pass).

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
open threads) lives in STATUS.md, not here.

## P0 — Governance bootstrap (S16–S20) — ✅ DONE
Prod-truth reconcile + `prod-baseline-20260704`, nine-file governance, CI/pre-commit + secret gate,
independent session numbering. See CHANGELOG-ARCHIVE `[S16]`–`[S20]`, DEC-0010…0017, DEC-0023.

## P0.5 — Governance alignment across the family (S23–S56) — ✅ DONE except one follow-on
Brought this repo's *form* into line with the sibling repos and external best practice, keeping
content isolated (ASSESSMENT.md §2): `docs/ASSESSMENT.md` cross-repo audit + Governance Standard v1,
GPLv3 `LICENSE`, `AGENTS.md` cross-agent entrypoint, ROADMAP restructured to shared P-tiers,
STATUS.md promoted to single source of truth for the session number, `cleanup_backlog.md` folded
into BACKLOG (S27), docs diet (DEC-0030, S35 — the family-wide pattern: dash DEC-0081 → hyperlocal
DEC-0095 → here), remote URL casing + stale-branch cleanup (S56). See CHANGELOG-ARCHIVE `[S23]` and
ASSESSMENT.md for detail — not re-narrated here.
- [ ] **Only remaining item:** Keep-a-Changelog headings + DECISIONS entry-skeleton convergence
      (proposed S25, never picked up).

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
  its frame instead of just the failing one, closing ERR-0004 (issues #74/#76).
- **Signed temp decode → v2.0.10** (S55): DEC-0055, fixes negative-temperature encoding and the
  `0xFF8` flag-nibble leak.
- **Cap-16 tuning → v2.0.11** (S55c): DEC-0056, decided on an evidence pass (R1/R2); monitor
  tripwire verified live end-to-end.

**Still open — ordinary watches, not a new arc.** Current status (co-rejecting grep, `#74`
calm-windDir, humidity-spike signature DEC-0044, first-frost test of the signed-decode negative
branch, DEC-0056's rain-rejection revisit trigger) lives in STATUS.md's "Active thread" — not
duplicated here, and not evidence this P1 item is still "in progress."

**Blocker discipline (DEC-0011):** no drop-in dev receiver — RF-dependent verification is calendar-
bound and done via reversible live hot-swap with an instant rollback path.

---

# MEDIUM TERM (P2–P3) — after v2.0.11

## P2 — RF optimization, done honestly (PRINCIPLES §3) — **CAMPAIGN A RUNNING (DEC-0059)**
DEC-0048 (S41) deferred this into one designed experiment; the apparatus (`ops/rx_experiment.sh` +
`tests/test_rx_experiment.py`, S56/DEC-0059) is now deployed and executing. The seven
pre-governance sweep scripts are deleted; two of them were silently broken.
- [x] **Phase 0: `FreqError` telemetry CONFIRMED TO EXIST** (S57) — found within 13s of a restart
      once a logger-level gotcha was fixed (DEC-0060). `ppm`/`fc` measurement-by-value is a
      deliberately deferred follow-up, not done this campaign (arms run unmeasured `0`/`0`).
- [ ] **Campaign A — LNA in circuit — ARMED, starts 2026-07-30 00:05.** 2×2 factorial gain
      {372, 207} × ex {0, 50}, Latin square, 6 h blocks, 8 days; self-terminating completion
      **~2026-08-07**. The 07-29 attempt ran 80 min and aborted on two apparatus defects
      (DEC-0061 — a health-check budget ~25s short of what a restart structurally needs, and an
      alert path that was inert); both fixed and redeployed, and the schedule was regenerated from
      a clean day boundary because the aborted run damaged three Latin-square cells. Settles
      DEC-0017 (**absorbed**). Tracked at
      [ops#114](https://github.com/WeatheredScientist/eaglehunt-ops/issues/114).
- [ ] **QUEUED BEHIND CAMPAIGN A — cut an image release carrying DEC-0062** (not RF work; parked
      here because the campaign is what gates it). `pressure_service.py` no longer logs credential
      material, but it is **BAKED** (`Dockerfile:117`) — fixed in the repo, inert in prod until an
      image rebuild. A rebuild restarts prod, and restarting under a running factorial would
      confound its arms, so it waits for ~08-07. Fold in anything else baked that has accumulated
      by then, and carry DEC-0046 into the release: verify in the **running system**, never in the
      artifact.
- [ ] **Run campaign B — LNA physically removed**, gain arms centered higher (~{372, 496}); the
      optimum moves up once ~20 dB of front-end gain is gone. Schedule written after A reports.
- [x] ~~24 h **receiveWindow sweep**; reconcile image tag ↔ Dockerfile~~ — **dissolved by DEC-0059.**
      `-ex N` ≡ `receiveWindow 300+N` (upstream sums them), so the window is a mounted-config knob,
      no rebuild, and it is simply the second factor of the campaigns above. The `rw*` image tags
      were redundant, not merely misnamed.
- [ ] Confirm the running binary's `receiveWindow` (ARCHITECTURE §6) — **narrowed, still open.** It
      cannot be read from logs: the deployed binary is older than upstream master and lacks master's
      startup settings line (absent from both `weewx.log` and container stdout, checked S56). Needs
      the deployed `src.tgz` read directly, or a rebuild. No longer blocks the campaigns.
- [x] ~~Investigate rebuilding `rtldavis` from newer Go source for `FreqError`/`ChannelIdx`
      telemetry~~ — **moot.** S57 confirmed the *currently deployed* binary already emits it; no
      rebuild needed for this purpose.

## P3 — Modularity toward multi-source (PRINCIPLES §1)
- [ ] Harden INTERFACES.md as the stable contract; document it well enough for a non-Davis WeeWX or
      CumulusMX producer to satisfy it. (Partial progress: DEC-0032's `rain_qc` flag and DEC-0053's
      station-identity/correction-flag findings are already documented there — this item is about
      closing the remaining gaps, not starting from zero.)
- [x] Remove the vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005) — done S47.

---

**P4 and long-term/uncalendared direction moved to BACKLOG.md's "Long-term direction" section
(DEC-0058, S56)** — credential hygiene follow-ups, multi-source adaptability, the governance
template harvest, and the winter-2027 sky-state instrumentation (ops#110) all live there now,
not here.
