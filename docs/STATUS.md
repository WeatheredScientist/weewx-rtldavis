# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**
- **This file is the single source of truth for the current session number and the next-session
  handoff** (DEC-0023). Every other doc — and Claude memory — points *at* this; none carries its own
  copy. Handoff state lives here (in the repo, visible on GitHub), never only in private memory.

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short — **prune at every session
close** (DEC-0030): shipped blocks out, superseded notes out; if CHANGELOG or a DEC already tells
the story, this file only points at it.

> **Current session: S54** (2026-07-28). **R1 landed in code (DEC-0055)** — the outside-temperature
> decode is now true two's complement, plus the `0xFF8` sentinel; 10 new tests, all three plausible
> regressions mutation-tested red; pytest 111 / ruff / mypy green. **Not released** — the driver is
> baked (DEC-0031), so this needs an image rebuild before first frost. **R2 (`MAX_PLAUSIBLE_TIPS`
> 60 → 16) was NOT taken up** — the owner wants more discussion first; the constant is untouched.
> See CHANGELOG `[S54]` and DEC-0055.

_Last updated: 2026-07-28 (S54)._

---

## Active thread

> **▶ Resume here (S54 → S55). R1 is CODED but NOT RELEASED — the release is the open item.**
> DEC-0055 shipped the signed temp decode + `0xFF8` sentinel into `rtldavis.py` on `dev`. Because the
> driver is **baked** (DEC-0031), prod still runs the unsigned decode: **an image rebuild + release is
> required before first frost**, or the bug is live all winter. Two follow-ons ride with it:
> (a) a companion **upstream PR** alongside lheijst#22 — the sign bug and the missing `0xFF8`
> sentinel are both inherited from upstream; (b) report R1's completion back on
> [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105).
> **R2 is still OPEN and deliberately untouched** — the owner wants to discuss `MAX_PLAUSIBLE_TIPS`
> 60 → 16 (closes the ≤0.30 in phantom-rain residual to ≤0.16 in) before any code. Do not implement
> it unprompted. R3 (wind spike guard) rides the dashboard side of the ops#105 thread; R4 (radiation
> night ceiling) and R5 (extra-station zero-QC docs note) are noted-not-built.
> S53 watch results: co-rejection **0 hits** in the deploy's first hour (expected-rare); #74
> calm-windDir WARNINGs confirmed present right up to the 22:18 recreate and absent after, but the
> post-deploy window was <1 day — **re-verify over a full day**. Humidity watch through
> 2026-07-27 23:14: still no DEC-0044 signature (996 samples, largest non-ERR-0004 step 6.1 pts).
> Soak 15 PASS / 0 WARN / 0 FAIL. DEC-0049 phantom-rainRate prediction remains unfired.
>
> **Standing rule (DEC-0046):** for any file we ship, ask **"which layer actually wins in prod?"** The
> **driver** is baked and the mount is inert (DEC-0031). The **config** is mounted and the image is inert
> (DEC-0046). They are inverses. A release that changes shipped config **must patch the live
> `weewx.conf` on the NAS in the same window** — and verify in the running system, never in the artifact.
>
> **Standing rule (DEC-0047):** the transcript is an egress path. Use **`readconf`** to read a config
> (section-scoped, fingerprinted) and **`scan-transcripts`** to audit; never a line-count window on a
> sectioned config.
>
> Run `ops/soak_check.sh` any time for a fresh acceptance-criteria verdict (its `EXPECT_IMAGE` default
> now tracks `:v2.0.9` — bump it in the same PR next time the deployed tag moves).

## Upstream — all three landed (S38)

- **[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22)** — the rain-counter
  wraparound fix. OPEN.
- **[Issue #15 comment](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128)** —
  **POSTED 2026-07-13** (owner-approved). The first comment on that thread since **2022-11-14**. Explains
  the duplicate-frame mechanism, the wraparound bug, and — new at S38 — that the phantom **rainRate is
  ISS-side, not a driver bug** (DEC-0042), which three people there had been hunting in software.
- **[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1)** — TLS verification
  on by default + four more. OPEN; that repo's first-ever PR, and it has been quiet since 2023, so it may
  simply sit.

**Watch for replies.** `lheijst` was active as recently as 2026-07-09.

## Shipped — nothing to do here

- **S53** (ops#105 cross-observable QC audit delivered — no code): per-observable verdict table
  (all encodings verified from source), historical sweep = archive CLEAN (ERR-0004 the only
  in-bounds escape ever; zero new ERR entries), consumer inventory completed (adds WU RapidFire +
  loop-JSON cache-forward + daily summaries), R1–R5 recommendations awaiting design agreement.
  Corrections to ops#103 recorded there: rain NOT closed (≤0.30 in residual), rx-collapse is a
  correlate not a fingerprint requirement. See CHANGELOG `[S53]` and the
  [audit comment](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5099627052).
- **S52** (**v2.0.9 shipped** — DEC-0054 frame-level co-rejection; ERR-0004 corrected in both stores
  with `windGust_qc`/`windSpeed_qc` flags; issues #74 + #76 closed; ops#103 answered, ops#104
  unblocked): see CHANGELOG `[S52]` and DATA_ERRATA `ERR-0004`. Rollback: `:v2.0.8` on the NAS;
  `loop_json_writer.py.bak-pre-v2.0.9`; `weewx.sdb.bak-err0004-20260727`.
- **S49** (issue #67 closed — mypy is now a real CI gate): 19 pre-existing mypy errors fixed (two
  genuine bugs in `ops/recover_sweep_results.py` — a mismatched tuple element type and two loop
  variables shadowing module-level names; one missing `types-requests` stub; 13 py2/py3-compat
  `try/except ImportError` false positives suppressed per-line, never blanket). CI's
  `.github/workflows/ci.yml:81` no longer has `|| true` — mypy failures now actually block CI,
  mirroring what #55 did for pytest via pre-commit at S48. No DEC entry (closes an enforcement gap,
  not a new decision). See CHANGELOG `[S49]`.
- **S48** (issues #55, #48, #45 closed): **#55** — pytest wired into `.pre-commit-config.yaml` as
  immediate local signal (the real hard gate was already `dev`'s branch protection). **#48** —
  DEC-0042 challenged and upheld: the WeatherLink reconciliation conflated `rain_qc` (3 counter
  points, 2.56″) with `rainRate_qc` (33 rate points, `rain = 0.0`); both independently require the
  console's absence, so it's confirmatory, not contradictory. **#45** — provenance audit, DEC-0053:
  `loop_json_writer.py`'s cache was unbounded, so a dead/rejected sensor could emit its last value
  forever under a live `dateTime`; now bounded per-field (300 s, 2 × `fetch_interval` for
  `barometer_inHg`). **Deployed and verified in prod** (scp'd, md5-matched, pyc cleared, container
  restarted; zero expiry warnings across a 453 s watch). Two identity gaps documented, not closed, in
  BACKLOG. Filed issue #67 (CI's mypy `|| true` never gates) — closed the next session, S49. See
  CHANGELOG `[S48]` and `[S48b]`.
- **S47** (backlog + branch cleanup — no release): `loopdata.py` mount + `[LoopData]` config section
  removed (DEC-0005, closed — live `weewx.conf` edited, `weewx-rtldavis-v2` recreated without the
  mount, verified clean restart); `ops/reception_service.py` deleted from the repo (confirmed vestigial);
  `rw350-test`/`rw400-test` Docker images deleted from the NAS (DEC-0048 fully closed); merged
  `worktree-s46-closeout-amendment` worktree + branch removed. No code/driver change, no image rebuild.
  See CHANGELOG `[S47]`.
- **S46** (humidity-spike watch checked directly, still unfired; `eaglehunt-ops#37` closed — all
  three Eagle Hunt repos confirmed on OPS-DEC-0019; routine `dev` housekeeping; **PR #63** fixed a
  CI break the closeout PR surfaced — unpinned `ruff` had drifted to 0.16.0 and was silently
  blocking the required `lint` check on `dev`, pinned to `0.5.7` matching DEC-0027; both #63 and
  the closeout PR #62 merged). No source/driver code changed; the CI workflow did. No release. See
  CHANGELOG `[S46]`.
- **S45** (PR #59 merged — OPS-DEC-0019 env-twin permission rules): `.claude/settings.json` gained
  the env-wrapped ask-rule twins for the two protected-branch `git merge` rules (matches the
  cross-repo pattern already used for `git push`), part of the OPS-DEC-0019 rollout
  (`eaglehunt-ops#37`). Mechanical, no code touched, CI green. See CHANGELOG `[S45]`.
- **S44** (soak-check false positive fixed; closeout skeleton adopted): `ops/soak_check.sh`'s
  phantom-rain detector was flagging normal post-tip rain-rate decay as the DEC-0042 signature —
  fixed to require no real tip in the preceding hour, verified live (49 → 0 false positives) against
  a real 2026-07-18 storm. **DEC-0052**: adopted eaglehunt-ops' locked closeout skeleton (adapted),
  closes weewx-rtldavis#56, reported to eaglehunt-ops#22. Both via PR #57. See CHANGELOG `[S44]`.
- **S43** (**v2.0.8 shipped** — Docker Hub `:v2.0.8` + `:latest` at digest `sha256:2c05493a`, GitHub
  release, `main` == prod, `prod-baseline-20260715`; prod recreated and verified): Reception Layer B
  (DEC-0024, fully resolved — WU-published count now matches unique record epochs exactly, confirmed
  53/53 over a 3-min window post-deploy; `weewx_monitor.py`'s live `WINDOW:` metric confirmed fixed
  too, now reading 67-81% matching the driver's trusted `rxCheckPercent` range instead of pinning near
  100%), the duplicate-frame counter (DEC-0035 — `duplicate frames this period: N` logging live),
  Cold-load Fix B + windchill (DEC-0051, closes issue #44 — `current.json` confirmed writing real data
  incl. `windchill_F`). Local pre-commit's `ruff-format` hook (silently contradicting DEC-0027 since
  S31) removed. See CHANGELOG `[S43]`.
  **Rollback:** `:v2.0.7` (`e22fea3c744c`) is still on the NAS; the pre-deploy `loop_json_writer.py`
  is at `loop_json_writer.py.bak-pre-v2.0.8`.
- **S38** (v2.0.5 → **v2.0.6** on Docker Hub; prod recreated + verified; `prod-baseline-20260713` tagged;
  `influx.py` drift closed; the `~/.claude/hooks/` enforcement layer live and tested; 47 MB reclaimed):
  see CHANGELOG `[S38]` and DEC-0038/0039/0040/0041/0042.
- **S39** (root-logger fix DEC-0043; nibble theory falsified DEC-0044): CHANGELOG `[S39]`. **Released in
  S41 as v2.0.7.**
- **S41** (**v2.0.7 shipped** — Docker Hub `:v2.0.7` + `:latest` at digest `sha256:31cad4d2`, GitHub
  release, `main` == prod, `prod-baseline-20260713b`; prod recreated and verified; **DEC-0046** — the baked
  config is shadowed by the prod bind-mount; `log_humidity_raw` now active): CHANGELOG `[S41]`.
  **Rollback:** `:v2.0.6` (`e23cabd53591`) is still on the NAS; the pre-deploy config is at
  `weewx-data/weewx.conf.bak-pre-v2.0.7`.
- **S41 (security)** — **DEC-0047**: the secret gate guards commits, not reads. A `sed -n '…,+44p'` on the
  live `weewx.conf` overran its section and leaked live credentials into the transcript. Now guarded
  mechanically: `~/.claude/hooks/secret-read-guard.sh` (38/38 both directions; mutation test → 18 red),
  `~/.claude/bin/readconf` (section-scoped, fingerprinted), `~/.claude/bin/scan-transcripts` (self-tests
  before every run). **Rotation still owed — see the section below.**
- **S40** (the secret gate scans comments like code — DEC-0045; suite 28 → 41; a full-history scan of all
  333 blobs proved the hole was never exploited): CHANGELOG `[S40]`. **DEC-0039's "28/28 proven" is
  superseded** — two of those 28 asserted a *commented-out* credential must PASS.

## Open threads (backlog — none of these block anything)

- **✅ rainRate — ANSWERED (DEC-0042) and the hardware action is now CLOSED (DEC-0049).** ISS-side sensor
  artifact, not RF and not the driver. **The owner inspected the hardware: it is new, and there are no
  faults** — the one failure, the anemometer, was replaced ~16–17 Jun 2026. That **excludes a defective
  part** and sharpens DEC-0042: it is *working* hardware reacting to condensation, so **there is nothing
  to swap and no part to order.** Nothing is being built — the event is rare, benign, corrected in-band
  (`rain_qc`, DEC-0032) and understood. A third event on the next calm, saturated, cooling night remains a
  free test, with a sharper prediction: **the tip counter still will not advance.** Do not re-derive
  DEC-0042.
- **✅ Cross-sensor coupling filter — PARKED, DELIBERATELY NOT BUILT (DEC-0044).** Do **not** pick this up
  as specced; its premise failed on our own data. **The mechanism is the open question, not the
  threshold** — the raw-byte capture in "Active thread" is what settles it. Full reasoning in DEC-0044.
- **Monitor alert on the new rejection signature (S33 follow-up #1)** — extend `weewx_monitor.py`'s
  rain-glitch email to SensorQC rejections; needs its own pattern + a rate cap so a flapping sensor
  can't spam. Only worth doing once we see the real rejection rate.
- **`DewpointCacher` × `SensorQC` interaction (S36, undecided).** The cacher carries `outTemp`/
  `outHumidity`/`radiation`/`UV` forward for up to 300 s, so a value SensorQC *rejects* gets refilled
  with the last good reading (~40 s old) rather than left null. The bad value never propagates either
  way — so this did **not** block v2.0.4 — but a rejected reading is currently indistinguishable from an
  absent one in the data (the rejection is still logged loudly). Decide whether that's right.
- **Gain 372, interim** (DEC-0017) — the sweep is now **part of DEC-0048's designed RX experiment**, not a
  standalone errand. Gain stays at 372 and `receiveWindow` stays at the upstream default until that runs.
  **Do not tune either by feel.**
- **✅ `loopdata.py` + `ops/reception_service.py` removed (S47).** Both confirmed vestigial (neither
  wired into `weewx.conf`'s `[Engine][Services]`) and cleaned up: `[LoopData]` section removed from
  the live `weewx.conf`, `weewx-rtldavis-v2` recreated without the `loopdata.py` mount (verified —
  clean restart, 6 mounts, records publishing), both files renamed aside on the NAS
  (`*.removed-S47`, not deleted, in case of rollback); `ops/reception_service.py` deleted from the
  repo (unimported, not baked into the Dockerfile). See DEC-0005, CHANGELOG `[S47]`.
- **Errata → dashboard contract (cross-repo, dash S69 Q3).** The owner wants corrected points visibly
  asterisked on the water-balance chart. **Half-solved:** InfluxDB corrected points now carry a sparse
  `rain_qc = 1` flag (DEC-0032, documented in INTERFACES.md), so the dashboard can render the marker
  straight from the data with no parallel list. The dashboard side still has to *read* it.

## Needs a check / housekeeping

- **⚠️ The freeze MECHANISM is still open (DEC-0036) — but the trigger and the fuel are both gone.**
  We never proved exactly which write blocked, and the evidence is gone. Do **not** invent one. What we
  now know for certain: the **trigger** (a bare `docker logs`) is blocked by a hook in both the agent and
  the shell; the **fuel** (StdPrint, ~25 MB/day to stdout) is removed (DEC-0041); and Synology's `db` log
  driver **cannot be size-capped** — it accepts `max-size` and ignores it (measured, and confirmed
  against the literature). If it ever recurs, capture `/proc/1/task/*/wchan` and `/proc/1/fd/*` **before**
  restarting anything.

- **The `db` log driver is uncapped and always will be.** All containers still run on it. That is now an
  accepted risk, not an oversight: the trigger is guarded, weewx's stdout is silent, and `influxdb`
  (~0.5 MB/day) plus HLF/eh-proxy (tens of KB) are not credible wedge candidates. Switching a container
  to `json-file` is the only way to bound its log, and it costs that container's DSM log tab. **Revisit
  only if a container starts generating real stdout volume.**

- **One `rtldavis process stalled` at the v2.0.7 startup (S41) — has not recurred across 2 further
  recreates (S43 v2.0.8 deploy, S47 loopdata-mount removal).** At 2026-07-13 15:30:35, three minutes
  after the container was recreated, weewx logged `CRITICAL Caught WeeWxIOError: rtldavis process
  stalled`, waited 60 s, and restarted the driver cleanly. Most likely the USB dongle being re-acquired
  while the old container was still releasing it (`kill` → `rm` → `run` in quick succession). S47 added
  a 3 s `sleep` between `rm` and `run` as a precaution and came back clean (records publishing within
  seconds, no stall logged). **Not a blocker; downgraded from an open watch** — treat a future stall as
  a one-off unless it shows up on consecutive restarts.

- **Security follow-ups are tracked in the gitignored local-infra doc, not here.** This repo is public;
  operational security state does not belong in it. Read that file when picking up security work.

- **✅ No real credential has ever been committed to any of the three repos.** S40 scanned all 333 blobs for
  commented credentials (zero). S41 scanned every live config value against the full history of all refs in
  all three repos (zero). One scare — a password apparently sitting in `weewx.conf.example` on `main` since
  S16 — was the example's own placeholder string. False positive, caught by re-checking evidence that looked
  internally weird (DEC-0047).

- **Unported from the dashboard:** its `.claude/agents/` routing definitions (its DEC-0093).
- **✅ The dashboard's stranded draft PR is GONE** (checked S41: all three repos have **zero** open PRs, and
  the dashboard's `promote-main` is no longer ahead of `dev`). Both sibling repos just have one uncommitted
  file each in their working copies.
- **NAS boot task fragility (S32):** after the next DSM update/reboot, verify the `weewx_monitor`
  scheduler task still runs as root (symptom: `sudo: a terminal is required` spam, no pidfile).
- **Docker Hub README auto-sync:** add repo secrets `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` to activate
  `.github/workflows/dockerhub-description.yml` (green no-op until then). Owner action.
- **✅ Branch/tag cleanup DONE (S41, S47).** The two branches this item named (`feature/rain-spike-filter`,
  `s32-reconcile-main`) **no longer existed** — the item was stale. What *did* exist was 8 merged
  `worktree-*` branches, all deleted (0 unmerged commits each; verified before deleting). S46's
  `worktree-s46-closeout-amendment` (merged via PR #64) was cleaned up the same way at S47. The repo now
  has exactly **`dev` and `main`**. `rw250-test` was retired at DEC-0048; `rw350-test` / `rw400-test`
  (same class, never on Docker Hub) were confirmed unused by any running container and deleted from the
  NAS at S47 — DEC-0048 fully closed.
- **Snow / freezing / no heating tape** (parked, owner's future thread). 2026 = learning year.

## Next session actions (S54 done → S55)

**This section is the repo-visible handoff.** Read it first when resuming. Session recaps for S46-S54
now live only in "Shipped" above and CHANGELOG — not duplicated here.

**▶ ON RETURN (S55), in order:**

0. **Release the R1 fix (DEC-0055) — this is the only item with a hard deadline.** The code is on
   `dev`; prod runs the **unsigned** decode until an image is rebuilt (DEC-0031: the driver is baked,
   an `scp` is a silent no-op). **Deadline: before first frost.** Same window: the companion
   **upstream PR** alongside [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22) (both the
   sign bug and the missing `0xFF8` sentinel are inherited upstream), and a note back on
   [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105) closing out R1.
   Carry DEC-0046 through the release: verify in the **running system**, not the artifact.

0b. **R2 is awaiting discussion, not implementation.** `MAX_PLAUSIBLE_TIPS` 60 → 16 (residual
   phantom-rain ceiling 0.30 → 0.16 in) was explicitly held by the owner at S54 for more design
   discussion. The constant in `rtldavis.py` is **unchanged**. Do not code it unprompted
   (PRINCIPLES §8).

1. **Continue the v2.0.9 watch (DEC-0054):** grep `weewx.log*` for `co-rejecting` (single-word
   pattern via nasctl — multi-word patterns silently match nothing) — 0 hits in the first hour
   post-deploy (22:18 2026-07-27). Each future hit is a frame v2.0.8 would have partially trusted;
   an rxCheckPercent dip corroborates but is NOT required (the 2026-07-17 corrupt frame arrived at
   77 %). **Re-check the #74 calm-windDir WARNINGs over a full day** — confirmed silent in the
   first post-deploy hour only. Run `ops/soak_check.sh` (S53: 15/0/0). First Dependabot run may
   open a deps PR — review, don't auto-merge (#78 mechanism).

2. **Keep watching the humidity-spike log — still nothing qualifying through S53 (2026-07-27 23:14;
   996 samples since S51's checkpoint, largest non-ERR-0004 step 6.1 pts).**
   `log_humidity_raw True` has been active since the v2.0.7 restart at 2026-07-13 15:27 EDT; S46
   checked the full window to its date, S51 re-checked 2026-07-24 → 2026-07-26 (2,755 samples,
   largest step −8.7 pts across a reception gap — not the signature). Grep for `humidity_raw=` in
   current + rotated `weewx.log*` (rotation is daily). Spikes run ~2–3/week clustered **11:00–16:00**
   — need the 16-37 % DEC-0044 signature (a single-step raw jump), not just an ordinary 5-10 %/min
   swing. It logs the full `pkt[4]`/`pkt[3]` — **no averaging, no free parameter** — which settles
   the nibble question **deterministically**: invert the bytes, re-decode under `0x2`/`0x8`/`0xE`
   (humidity's real single-bit neighbours — *not* solar or UV, which are 2 and 3 bits away), compare
   with the concurrent archived sensor. **The method and the arithmetic are in DEC-0044; do not
   re-derive them.** Decode of the logged word: `(pkt[4] << 8) + pkt[3]` in hex; RH =
   `(((pkt[4] >> 4) << 8) + pkt[3]) / 10`.

3. **Do NOT rebuild the coupling filter** (DEC-0044). Its premise failed on our own data. The mechanism
   is the open question, not the threshold.

4. **`ops/soak_check.sh`'s phantom-rain detector is now hardened (S44) — don't re-flag ordinary rain.**
   If it reports a nonzero count, that already excludes the normal post-tip decay window (1 hour); a
   real hit is worth taking seriously as the DEC-0049-predicted event, not re-litigating as a false
   positive first. S51's run: 0 rows in 1,214.

5. *(folded into step 1's deploy-window check — the S41 stall class stays clean through S48; only
   revisit if a stall shows up on consecutive restarts.)*

**Carry DEC-0046 into any future release:** the **driver** is baked and the mount is inert (DEC-0031); the
**config** is mounted and the image is inert (DEC-0046). Inverses. A release that changes shipped config
**must patch the live `weewx.conf` on the NAS in the same window**, and must verify in the **running
system**, never in the artifact — an image check would have said PASS.

**✅ The Fable cross-repo round HAPPENED (S42, DEC-0050)** — the etiquette question is settled;
`eaglehunt-ops` is live. New cross-repo findings go to its issue tracker, not into this file.

**Physical, not software (DEC-0042):** inspect the tipping bucket, the reed switch and its wiring. The
phantom rainRate is an ISS sensor artifact — condensation trips the rate timer without tipping the
bucket. **A third event is predictable on the next calm, saturated, cooling night**, which is a free test.

**Watch:** replies on [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22),
[issue #15](https://github.com/lheijst/weewx-rtldavis/issues/15) and
[david-lutz#1](https://github.com/david-lutz/weewx-influx2/pull/1).

**Also owed:** the security follow-ups tracked in the gitignored local-infra doc — not listed here,
because this repo is public. _(The dashboard's stranded draft PR #22 was resolved back in their S71;
that note was stale — a doc's claims decay, dash DEC-0104.)_

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for any
`git push`. **The driver is BAKED — never `scp` it (DEC-0031); `influx.py` IS mounted, so scp IS correct
for that one.** **`docker logs` without `--tail` is now blocked by a hook** in both the agent and the
shell — it is no longer merely a written rule (DEC-0040).
