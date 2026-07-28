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

> **Current session: S56** (2026-07-28), docs-only, nothing deployed. Confirmed prod healthy on
> v2.0.11 (co-rejecting watch 0 hits, positive-controlled) and ops#105 closed; found ops#110 newly
> opened (winter 2027 planning). **ROADMAP.md reconciled** (5 stale-done items corrected) then
> **fully restructured** — P1 + P1.5 folded into one arc covering v2.0.3–v2.0.11, a "Keeping this
> current" tripwire added (next check due **by S66**). **DEC-0057**: ROADMAP updates join the
> closeout ritual as step 5. See CHANGELOG `[S56]`.

_Last updated: 2026-07-28 (S56)._

---

## Active thread

> **▶ Resume here (S56 → S57). Docs-only session — nothing deployed, prod still v2.0.11
> (`0.20+ws.3`); still watch-and-discuss.** Re-verified prod health and the co-rejecting watch;
> reconciled and restructured ROADMAP.md; logged DEC-0057. CHANGELOG `[S56]` has the record.
> **(a) DEC-0056 is LIVE end-to-end** — cap 16 in the running driver, tripwire email verified
> (`--test-alert` received), WeatherLink playbook + revisit trigger in the DEC. R3 delivered
> dashboard-side (their S151, DEC-0167); R4/R5 noted-not-built.
> **(b) Watches** — co-rejection grep: **0 hits** through 11:48 07-28 (re-verified S56,
> positive-control-verified). #74 calm-windDir: last WARNING 21:59 07-27, zero since at a prior
> base rate of ~1/hr — one more full-day look and call it confirmed. Humidity: unfired (largest
> step 0.7 pts in the 240 samples to 08:52 07-28). DEC-0049 phantom-rainRate: unfired.
> **(c) Upstream replies** — NEW
> [lheijst#23](https://github.com/lheijst/weewx-rtldavis/pull/23) (temp sign + `0xFF8`, credits
> LloydR's #19 diagnosis) joins #22, issue #15 and david-lutz#1 on the reply watch.
> **(d) First frost is now the free live test**: expect ordinary negative temps, no bounds trips,
> no co-rejection storm (the suite swept −0.1…−39.9 °F; winter confirms it on air).
> **(e) Cross-repo:** [ops#110](https://github.com/WeatheredScientist/eaglehunt-ops/issues/110)
> opened — winter 2027 sky-state instrumentation (IR sky sensor), planning horizon only, tracked in
> ROADMAP's "Longer horizon."
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
> **Standing rule (DEC-0057, new):** a shipped/closed/reprioritized DEC gets its ROADMAP.md line
> updated the same session — closeout step 5, not deferred (CLAUDE.md Session ritual). ROADMAP.md's
> own "Keeping this current" section carries the next-check-due session number regardless.
>
> Run `ops/soak_check.sh` any time for a fresh acceptance-criteria verdict (its `EXPECT_IMAGE` default
> now tracks `:v2.0.11` — bump it in the same PR next time the deployed tag moves).

## Upstream — four live threads (S38, S55)

- **[lheijst/weewx-rtldavis#23](https://github.com/lheijst/weewx-rtldavis/pull/23)** — the temp-sign
  + `0xFF8` companion PR (S55, owner-reviewed before posting). Credits LloydR's #19 for the
  diagnosis; offers the masked 12-bit two's complement as an alternative (#19's 16-bit-signed ÷16
  leaks the `pkt[4]` flag nibble, +0.05 °F constant). OPEN.
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

- **S56** (docs-only, no deploy/no rollback needed — ROADMAP.md reconciled then fully restructured:
  P1 + P1.5 folded into one arc covering v2.0.3–v2.0.11, 5 stale-done items corrected, "Keeping this
  current" tripwire added, next check due by S66; DEC-0057 makes ROADMAP updates closeout step 5):
  see CHANGELOG `[S56]`.
- **S55c** (**v2.0.11 shipped** — DEC-0056 cap 16 live in prod; banner `0.20+ws.3`, digest
  `sha256:b8f35f36…`, `prod-baseline-20260728b`; monitor tripwire verified end-to-end
  (`--test-alert` received); ops#105 audit complete from this side): see CHANGELOG `[S55c]`.
  **Rollback: `:v2.0.10`** on the NAS and Docker Hub.
- **S55** (**v2.0.10 shipped** — DEC-0055 signed temp decode live in prod; Docker Hub `:v2.0.10`
  + `:latest` at digest `sha256:ee3027e1…`, GitHub release, `main` == prod,
  `prod-baseline-20260728`; prod recreated and live-verified: banner `0.20+ws.2`, `sensor_qc True`,
  records publishing, soak 13/2/0; upstream
  [lheijst#23](https://github.com/lheijst/weewx-rtldavis/pull/23) opened; R1 closed on ops#105;
  repo housekeeping back to exactly `dev` + `main`): see CHANGELOG `[S55]`.
  **Rollback: `:v2.0.9`** on the NAS and Docker Hub.
- **S54** (R1 coded — DEC-0055 signed decode + `0xFF8`, 10 tests, fork inventory updated; released
  the next session as v2.0.10): see CHANGELOG `[S54]`.
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
- **S44–S49 and earlier** — pruned to pointers (DEC-0030): the stories live in `CHANGELOG-ARCHIVE.md` (S51 and older) and the DEC index. Operationally still true from that era: the `~/.claude/` guard layer is live and tested (DEC-0040/0047), pre-commit is installed, and no real credential has ever been committed (S40/S41 full-history scans — also asserted under Needs-a-check below).

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

## Next session actions (S55 done → S56)

**This section is the repo-visible handoff.** Read it first when resuming. Session recaps live in
"Shipped" above and CHANGELOG — not duplicated here.

**▶ ON RETURN (S56), in order:**

1. **Watches (all read-only, nasctl):** (a) grep `weewx.log*` for `co-rejecting` (single-word
   pattern — multi-word patterns silently match nothing; positive-control any zero). 0 hits through
   09:00 07-28. Each hit is a frame v2.0.8 would have partially trusted; an rxCheckPercent dip
   corroborates but is NOT required. (b) **#74 calm-windDir WARNINGs** — last one 21:59 07-27,
   zero in the ~11.5 h after at a prior ~1/hr base rate; one clean full-day check closes it.
   (c) Run `ops/soak_check.sh` (S55 post-deploy: 13/2/0; `EXPECT_IMAGE` tracks `:v2.0.10`).
   (d) Dependabot may open a deps PR — review, don't auto-merge (#78 mechanism).

2. **Humidity-spike watch — still unfired through 08:52 07-28** (largest step 0.7 pts in the last
   240 samples; S53's checkpoint before that: 996 samples, max 6.1 pts). Grep `humidity_raw=` in
   current + rotated `weewx.log*` (daily rotation). Spikes run ~2–3/week clustered **11:00–16:00**
   — need the 16-37 pt DEC-0044 single-step signature, not an ordinary 5-10 %/min swing. **The
   method and the arithmetic are in DEC-0044; do not re-derive them.** Decode of the logged word:
   `(pkt[4] << 8) + pkt[3]` in hex; RH = `(((pkt[4] >> 4) << 8) + pkt[3]) / 10`.

3. **R2/DEC-0056 is fully SHIPPED (v2.0.11, S55c) — nothing left to cut.** If a rain-rejection
   email ever arrives on a genuinely wet day, that is the predefined DEC-0056 revisit trigger:
   reconcile against the WeatherLink console per the playbook and reopen the cap decision with
   that event's data. On a dry day it's the filter catching a glitch — log it and move on.

4. **Do NOT rebuild the coupling filter** (DEC-0044). Its premise failed on our own data. The
   mechanism is the open question, not the threshold.

5. **`ops/soak_check.sh`'s phantom-rain detector is hardened (S44) — don't re-flag ordinary rain.**
   A nonzero count already excludes the post-tip decay window; treat a hit as the
   DEC-0049-predicted event first, not a false positive. Latest run: 0 rows.

6. **At first frost:** the signed decode's negative branch gets its first live air test. Expected:
   ordinary sub-zero readings, no bounds trips, no co-rejection storm (the suite swept
   −0.1…−39.9 °F). If a cold snap instead lights up `co-rejecting` pairs, that is a DEC-0055
   regression — investigate before anything else.

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
[lheijst#23](https://github.com/lheijst/weewx-rtldavis/pull/23),
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
