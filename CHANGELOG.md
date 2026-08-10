# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
## [S68b] — 2026-08-09 — Forensics deployed and verified live; the smoke test then found a defect in them

- **Deployed from the merged tip `ad7e5a4` and verified.** `usb_forensics.sh` + `usb_reset.sh` as
  **root:root 755** (ownership is load-bearing — `usb_reset.sh` refuses a helper it does not own),
  `weewx_monitor.py` as the service account, 644; monitor 3870 → **8810**, `Monitor started`,
  polling normally, ~3.5 min gap inside the esynoscheduler window.
- **The sudo half is owner-run and cannot be batched.** The `nas-admin` alias lands on an
  unprivileged account with no NOPASSWD, and an agent session has no TTY: `-t` fails to allocate one, `-tt` forces a pty and then
  hangs on a live `Password:`. Leading the remote script with `set -e` made the failed attempt a
  clean no-op — verified afterwards: prod shas unchanged, zero `.bak` files created.
- **Smoke-tested on the real box, which is the point.** Pid discovery by `comm` works; dongle
  confirmed `1-3` / `0bda:2838` / `devnum=5`; the two root-only sections correctly self-labelled
  `DEGRADED … UNREADABLE, not empty` rather than looking like a released handle.
- **And it caught a defect in what had just shipped.** The capture reported `rtldavis` as 17 seconds
  old; it had been up **2.88 days** (`/proc/<pid>/stat` field 22 vs `/proc/uptime`, corroborated by
  the container Up 3 days and unbroken `weewx.log` output). `/proc/<pid>` **mtime is access time**,
  and the script reads files under that directory moments earlier. In a stall capture it would have
  asserted a restart that never happened — a fabricated event in the one artifact built to settle a
  question whose hypothesis is deliberately unsettled. Fixed in **PR #146**; HZ=100 confirmed, not
  assumed (250 or 1000 both date `rtldavis` before the container that spawned it).
- **This undercuts DEC-0074's own probe — [#147](https://github.com/WeatheredScientist/weewx-rtldavis/issues/147).**
  Its documented liveness check is `nasctl ls /proc/<newpid>` vs the file mtime: the same unsound
  signal. The **lesson** stands — liveness needs process evidence — but the probe must become a
  startup line in the log after the file mtime (what actually carried both the S67 and S68
  verifications), field 22 vs `/proc/uptime`, and new-pid-plus-old-pid-gone.

---
## [S68] — 2026-08-08 — Reset forensics built and armed (DEC-0075); secret gate's fifth hole closed (DEC-0076)

- **DEC-0075 — the next stall photographs itself.** `ops/usb_forensics.sh` brackets every reset with
  the host USB tree and the dongle's `devnum`, the **container's** view of `/dev/bus/usb` via
  `/proc/<pid>/root`, and whether the stalled `rtldavis` still holds an fd on the device. Those last
  two are the decisive pair: a stale view or a surviving handle confirms the hypothesis, and both
  clean means the stall is **not a USB fault** and the reset treats the wrong thing entirely.
  Read host-side through `/proc` rather than via `docker exec`, because this fires *during* a stall
  and a wedged container can block an exec indefinitely — the capture would hang on the very event it
  records. Pre/post fire from inside `usb_reset.sh`, the only root context, needing **no new sudoers
  grant**; the monitor fires only the `+RESET_VERIFY_S` capture and **labels it DEGRADED**, so an
  unreadable fd section can never be misread as a released handle. **Capture-only — DEC-0065's
  escalation ladder is untouched.**
- **An escalation introduced and closed in the same change.** Executing a helper from `usb_reset.sh`
  runs it as root under the NOPASSWD grant, and mode 777 is common on this NAS — a helper writable by
  `weewx-monitor` would have turned that narrow grant into arbitrary root execution. The script now
  verifies the helper is root-owned and root-only-writable, refuses **loudly** otherwise while still
  resetting, and `do_reset()` logs its output on a zero exit so the refusal cannot go silent.
  Checked, not documented (DEC-0040), and positive-controlled by neutering the check.
- **Why it was built before the evidence:** no stall since the corrected reset code went live
  2026-08-07 19:28 — zero `RESET`/`stalled` lines across the 08-07 and 08-08 monitor logs, both greps
  positive-controlled against 1440/521-hit `WINDOW` counts. Nothing to read retroactively, and the
  event is ~1/day and unpredictable, so the apparatus has to exist first.
- **DEC-0076 — the secret gate missed `GMAIL_PASS`-shaped keys.** The key list held `password` and
  `passcode` but nothing for the `_PASS` abbreviation, so `GMAIL_PASS = "..."` was undetected in
  every spelling — and that is the exact variable `weewx_monitor.py` uses for its Gmail credential.
  **Nothing was ever leaked through it** (no `_PASS` literal in the tracked tree; none on any ref in
  the full history). Found by DEC-0045's routine positive control before an *unrelated* commit, not
  by an audit. Two detectors, each proven necessary by removing it and watching its payloads leak:
  bare `pass` (not `passwd`, which would flag README's `NOPASSWD:` sudoers line), and a literal
  matcher for the four-group app-password form that slips past the 8-consecutive-character value
  rule. `PASS` is listed separately because detection is case-insensitive and the allow-list
  deliberately is not — without it the gate flagged this repo's own source. Harness **41 → 51** cases.
- **ROADMAP reconciliation:** blocker 4 had **no P0 line at all** — DEC-0074 raised it at S67 and no
  item was opened, so the sequenced plan did not carry its own top blocker. Added.
- Tests **169 → 184**. `usb_reset.sh` now also documented in README's Security Note and Setup, since
  its escalation surface changed.

---
