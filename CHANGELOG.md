# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S71] — 2026-08-10 — ops#148/#7 closed; ERR-0005 backfilled; solar diode-floor traced and designed

- **ops#148 closed.** `MANIFEST.md`'s `CHANGES-FROM-UPSTREAM.md` row widened to name all 9
  uncovered files — it already documents each one's provenance (4 vendored forks, 5 original), so
  this was a one-line widen, not a new row. Verified against the sweep's own bare-filename matching.
- **DEC-0079 — opted into `.claude/transient-state` (ops#113).** Tracked file created (force-added
  past the local `.git/info/exclude`, same precedent as `settings.json`), convention documented in
  `CONVENTIONS.md`. Left empty — no current state meets the motivating shape that isn't already
  prominent in `BOOT.md`.
- **`BOOT.md` ordered backlog resequenced:** `#144` (console pressure / `pressure_service.py` field
  collision) then `ops#141` (HLF archive-directory mount) queued for after GATE 2, each flagged with
  why it's design work rather than mechanical execution.
- **ERR-0005 backfilled.** 7 records at `interval=15` inserted into the archive (backed up first:
  `weewx.sdb.bak-S71-preBackfill-20260810-124656`), daily summary rebuilt, matching InfluxDB points
  written flagged `backfill=1.0`. **Both machine history APIs failed first** — WU's `v2/pws/history/all`
  401'd, WeatherLink v2's `v2/historic/{id}` (same credentials `pressure_service.py` uses hourly)
  returned an empty `{}` with a 200 — neither carries historical-read entitlement on this account.
  Sourced from a manual WeatherLink/WU website read instead; recorded in `DATA_ERRATA.md` so a future
  backfill skips straight to that.
- **Solar radiation diode-floor bias — diagnosed, fix designed, not yet applied.** Owner recalled a
  prior fix; traced via the owner's own claude.ai search (this repo's git history and archive both
  start 2026-05-19, so nothing here predates it) to a June 2026 dashboard-only presentation-layer
  filter. Verified against the *current* dashboard: still correct for live numeric displays, but the
  24h chart panel (`eh-charts.js`) queries InfluxDB raw with no filter — regressed during the
  dashboard's July supercard refactor, the second time a per-path filter has been dropped on
  refactor. Decision: fix at the source here instead of patching the dashboard a third time. Two
  designs drafted and compared (`StdCalibrate` magnitude-match vs. a `weewx.almanac`-based
  elevation-gated service); full brief for the next session in
  [`docs/handoffs/S71-radiation-floor-design.md`](docs/handoffs/S71-radiation-floor-design.md).
- Green gate re-run clean throughout (185 tests).

---
## [S70] — 2026-08-10 — v2.0.12 promoted and built; campaign B GO, first launch night scrubbed on a dead VPN

- **Campaign B: GO.** Assessed against DEC-0066's hold: both gates closed on measurement
  (DEC-0069/0070), campaign A uncontaminated (DEC-0077) — the "instrument trusted" condition is
  met. The swap-night constraint is moot: the LNA has been out since 08-02, so the launch is a
  container swap + install, all remote.
- **Release v2.0.12 promoted** (PR #151): dev → main, `main` = `7b6fd42`. Image delta vs v2.0.11
  is four baked files (BIAS_TEE env, DEC-0062 redaction, driver stderr drain + ws.4 bump) —
  observability only, pre-registered as the one-image-for-B plan (DEC-0064).
- **The arm64 laptop can no longer build this image** — `docker build --platform linux/amd64`
  dies in tar with `Function not implemented` (ENOSYS under emulation), and the failure hid
  behind a `| tail` pipeline exit 0 until the log was read (the green-checkmark trap, again).
  Built **natively on the NAS** instead (v2.0.3 precedent): `9db5c1ddaac3`, verified by an
  explicit `BUILD-EXIT=0` marker. Hub push deferred (docker save → laptop → push from a home
  network); `:latest` waits for prod proof.
- **The 08-09 launch night was scrubbed at 00:58** — the VPN dropped end-to-end (ppp0 gone,
  route fell back to the foreign LAN's gateway) with the 00:35 first pilot row already passed.
  The runbook's postpone-24h contingency, exercised as designed: prod untouched, campaign A's
  script + STOP sentinel still in place, nothing half-deployed. Schedule regenerated +1 day
  (39 rows, S62's constant-offset method): **pilot 08-11T00:35, square 08-12 → 08-20T00:05**.
- No stall overnight (blocker 4 still waiting); prod healthy through the NAS build (v2.0.11,
  Up 4 days).
- **Deploy executed 08-10 morning, campaign B ARMED.** Campaign A archived (five artifacts →
  `.campaignA`, including the root-owned STOP sentinel the runbook's list omitted — a tick
  refuses while it exists); B's `rx_experiment.sh` deployed from merged tip `b7a07e1` and
  sha-verified (`6a99c949`); container swapped in one nohup'd batch (VPN-drop-safe after the
  previous night's lesson), `SWAP-EXIT=0`. Verified in the running system per DEC-0046: ws.4
  banner, `Bias-tee disabled (BIAS_TEE=0)` line, DEC-0062 redaction line, loop-JSON advancing,
  reception 70% → 57/59% through the swap dip → **70% [OK]** recovered. `install` clean at
  09:40: baseline snapshotted, **pilot 08-11T00:35, square 08-12 → 08-20T00:05**. Soak with the
  new expectations: **16 pass / 1 warn (settling reception) / 0 fail**.
- **DEC-0078 — image builds move to the NAS.** The laptop failure above is deterministic, so the
  NAS-native path is now the release mechanic, with Hub publication decoupled (`save` → laptop →
  `push`, only after prod proof — Hub lags prod until pushed, documented in CONSTANTS). CI
  builds noted as the structural fix, backlogged. `EXPECT_*` flipped to v2.0.12/ws.4 in the same
  deploy; ROADMAP P2 reconciled (DEC-0057): release item closed, campaign B item now LAUNCHED.
- **`:v2.0.12` pushed to Docker Hub at S70 close, digest-verified end to end:** the Hub
  manifest's config digest is the NAS build id (`9db5c1…`) — what the public pulls is provably
  what prod runs. One recorded blemish: the save→load→push path re-pushed the layers
  near-uncompressed (283 MB vs ~120 MB typical; same 8 layers, each ~2.2×) — content-identical,
  harmless, tightening deferred to DEC-0078's CI-build follow-up. `:latest` deliberately still
  v2.0.11 until the station proves the release (GATE 2). ops#152 closed on the measured green
  sweep.

---
## [S69] — 2026-08-09 — Tier files back under cap (ops#152)

- **BOOT.md 10,617 → 7,557 chars (cap 10,000); MANIFEST.md 4,055 → 3,936 (cap 4,000)** — the
  tier-sweep filing folded into a session close, as the filing prescribes. BOOT per STANDARD rule 1:
  the blocker-5 closure was told three times, the forensics deploy-and-verify story twice, and the
  footer re-told the whole body — each now once, reasoning left in DEC-0075/0077. Three gotchas
  deleted as second copies of canonical docs: the secret gate's "nothing to scan" (CONVENTIONS),
  "which layer wins in prod" (CONSTANTS), session-number authority (CLAUDE.md). MANIFEST per rule 9:
  teaching parentheticals compressed; no row deleted.
- **No stall capture yet** (blocker 4) — `logs/usb-forensics/` holds only the 08-09 smoketest and
  verify files, so the S70 job is unchanged: the event is the only thing left.
- S66 rolled to `CHANGELOG-ARCHIVE.md` verbatim (the ~3-session window).

---
## [S68c–d] — 2026-08-09 — Blocker 5 closed on measurement (DEC-0077); DEC-0074's probe corrected (#147)

- **DEC-0077 — reset gaps do NOT contaminate campaign A.** Blocker 5, answered by measurement rather
  than argument. Every rotated monitor log spanning campaign A (`.11`=07-29 … `.4`=08-05) grepped:
  **11 resets, all on 08-02** (00:11:23 → 01:27:20), seven of eight days empty — independently
  corroborating DEC-0067's "0 detections on every other day". The archive across the incident reads
  **00:04 = 72.73% normal → 80 rows absent → 01:24 NULL → 25 rows absent → 01:51 NULL → 01:52 back in
  range**: exactly the tool's documented **lock/outage** shape.
- **Why that settles it: classification is descriptive, exclusion is structural.** DEC-0069 drops the
  record either side of *any* gap plus every NULL, never consulting the class — so the reset-adjacent
  records were already excluded, and the 105 absent minutes contribute nothing because absent rows
  are not zeros. DEC-0074's framing (gaps "sorted into freeze/swap/lock") was the wrong thing to
  worry about. **The real exposure was present-but-low rows**, which nothing excludes because the
  tool refuses magnitude thresholds by design — and there are none.
- **Narrow amendment:** DEC-0069's taxonomy is complete for *shapes*, not *causes* — a USB reset is a
  fourth cause of the lock/outage shape. Treatment keys on shape, so no analyzer change.
- **Two bounded residuals, neither gating:** 01:52 (57.14%) survives the rule because it neighbours a
  NULL *row* rather than a gap — ≈0.04 pts on a 6 h block against a 2.0-pt bar; and 105 min vanished
  from one arm's block, costing precision rather than bias, since a receiver outage is not a property
  of the arm.
- **Correction to the record:** the log shows **11** resets, not nine. ERR-0005 and DEC-0065 both say
  "nine in 75 minutes" and call 01:27:17 "reset #10"; it is the 11th, span 76 min. Nothing downstream
  depended on it — DEC-0065's argument is about unbounded retry, which 11 strengthens.
- **DEC-0074's liveness probe corrected where it is documented (#147).** Its body, index row and the
  ROADMAP watchdog item all cited `/proc/<pid>` mtime, which S68b measured as access time. Amended in
  place rather than superseded: no decision changed, only its instrument. The lesson stands; the
  three checks that hold are a startup log line after the file mtime, `/proc/<pid>/stat` field 22 vs
  `/proc/uptime`, and new-pid-with-old-pid-gone.
- **Staleness sweep, again.** BOOT's blocker 4 still read "not yet deployed", its monitor row cited
  the pre-deploy sha, and the campaign-B paragraph still gated on blocker 5. All corrected, plus an
  internal contradiction BOOT had acquired (9/9 vs 11).
- **`Closes #N` does not work on this repo's flow.** #147 was still open while BOOT claimed it
  closed: GitHub auto-closes only on a merge to the **default branch, `main`**, which advances only
  at a prod-baseline release. `git log --grep` shows the pattern used on `dev` before, so this is not
  a one-off. Recorded in `docs/CONVENTIONS.md` §Git workflow — close explicitly, or say "addressed in
  #M" and leave it open on purpose; keep the trailer as a cross-reference, never the mechanism.
- **BOOT was a second copy of the runbook it points at.** It exceeded the DEC-0072 cap four times in
  one day and each overrun was paid for by shaving words — which DEC-0072 explicitly rejects. The
  cause was structural: six campaign-B launch steps sat directly under a line saying
  `docs/CAMPAIGN-B-RUNBOOK.md` governs the night. Verified absent from the runbook first, then
  **moved** there verbatim (not deleted) as a new "Release mechanics" section. BOOT 2516 → **~2332**,
  ~7% headroom rather than the 0.2% shaving bought.
- **Forensics reinstalled and the fix verified on hardware (S68e).** The `/proc`-mtime fix from
  #146 is now the deployed copy (`dc7912ae`, root-owned), and a live capture confirms it:
  `age=259633s` (3.0 days, matching container uptime) beside `proc-dir-mtime` labelled "ACCESS
  time, NOT start". The two fields visibly disagree in the artifact, with the right one marked.
  Verified rather than assumed, since the earlier smoke test is what found the defect at all.
  **#147 closed by hand**, #148 merged. Nothing pending deployment.
- **The session's recurring shape, worth naming:** three distinct staleness classes — the deploy
  state, DEC-0074's probe, the `Closes #N` trailer — all the same defect. *A claim that was true when
  written, with nothing that would fail when it stopped being true.*

---
