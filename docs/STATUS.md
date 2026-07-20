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

> **Current session: S44** (2026-07-19). **No release — a soak check + two closeout items.**
> `soak_check.sh` on the still-running v2.0.8 (up 98h) surfaced a false **PHANTOM RAIN EVENT**: 49
> archive rows with `rainRate>0`/`rain=0` on 2026-07-18, which looked like the DEC-0049-predicted
> third condensation event. Cross-checked against the full day's archive: it wasn't — 3 **real**
> bucket tips that day, a falling barometer (29.93→29.78 in) and rising gusts (to 8 mph) confirm an
> actual storm, and every flagged row is just the ISS's own rain-rate message decaying after a real
> tip (one decay tail ran 38 min). **Fixed:** `ops/soak_check.sh`'s phantom-rain detector now
> excludes rows with a real tip in the preceding hour — re-verified live, 49 → 0 false positives, all
> other checks unchanged. The DEC-0049 prediction (a real condensation event, tip counter never
> advancing) is still unfired. Humidity-spike watch: still negative, largest jump ~7.5 %RH/min (894
> samples this container lifetime), same magnitude as S43's reading, well under the 16–37% DEC-0044
> signature. **DEC-0052:** adopted eaglehunt-ops' locked closeout skeleton (OPS-DEC-0016), adapted —
> `CLAUDE.md`'s old two-paragraph closeout split is now one 6-step list, docs-diet ritual and the
> stricter local commit/push rule kept as addenda; closes weewx-rtldavis#56, reported to
> eaglehunt-ops#22. Both landed via PR #57 (dev). Full story: CHANGELOG `[S44]`.
> `log_humidity_raw` still ACTIVE — the next midday spike settles the nibble question (see [S41]).

_Last updated: 2026-07-19 (S44)._

---

## Active thread

> **▶ Resume here (S44 → S45). Nothing is half-shipped and no PR is open.** The one still-open thread
> is the humidity-spike watch (see banner above and "Next session actions" — `log_humidity_raw`
> capture is live, no qualifying spike yet). The DEC-0049 phantom-rainRate prediction (a real
> condensation event with the tip counter not advancing) also remains unfired — S44's event turned
> out to be real rain, not that.
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
> now tracks `:v2.0.8` — bump it in the same PR next time the deployed tag moves).

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
- **Vestigial `loopdata.py`** — mounted + `[LoopData]` present but in no active service list; safe to
  remove, not urgent.
- **Likely-vestigial `ops/reception_service.py` (found S43).** Its `ReceptionMonitor` WeeWX service
  isn't in `weewx.conf`'s `[Engine][Services]` at all, and per `git log --follow` has sat untouched
  since S16 — never wired in. It is not what generates the reception emails (`weewx_monitor.py` is,
  and is active). Same class as `loopdata.py`; confirm and remove, not urgent.
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

- **⚠️ WATCH: one `rtldavis process stalled` at the v2.0.7 startup (S41).** At 2026-07-13 15:30:35, three
  minutes after the container was recreated, weewx logged `CRITICAL Caught WeeWxIOError: rtldavis process
  stalled`, waited 60 s, and restarted the driver cleanly. It **self-recovered** and has not recurred;
  reception went straight back to 100 % and archive records land every minute. It is the **only** stall in
  the whole day's log — including across the `:v2.0.6` restart that morning — so it is new to this boot.
  Most likely the USB dongle being re-acquired while the old container was still releasing it (`kill` →
  `rm` → `run` in quick succession). **Not a blocker and nothing is owed** — but if a stall shows up on the
  *next* restart too, it is a real startup race and needs a settle-delay between `rm` and `run`.

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
- **✅ Branch/tag cleanup DONE (S41).** The two branches this item named (`feature/rain-spike-filter`,
  `s32-reconcile-main`) **no longer existed** — the item was stale. What *did* exist was 8 merged
  `worktree-*` branches, all deleted (0 unmerged commits each; verified before deleting). The repo now has
  exactly **`dev` and `main`**. `rw250-test` is retired (DEC-0048); it was **never on Docker Hub**, so the
  misnomer was only ever ours. `rw350-test` / `rw400-test` are the same class and should follow.
- **Snow / freezing / no heating tape** (parked, owner's future thread). 2026 = learning year.

## Next session actions (S44 done → S45)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S44 (2026-07-19):** soak check on v2.0.8 (still up, 98h+) surfaced a false phantom-rain
positive (49 rows) — cross-checked against the archive and confirmed it was real rain (a storm on
2026-07-18: 3 real tips, falling barometer, rising gusts), not the DEC-0042 signature. Fixed
`ops/soak_check.sh`'s detector to require no real tip in the preceding hour; re-verified live, 0 false
positives. Humidity-spike check: still negative (894 samples, largest jump ~7.5 %RH/min). **DEC-0052**
adopted eaglehunt-ops' closeout skeleton (adapted); `CLAUDE.md`'s closeout ritual is now one 6-step
list. Both landed via PR #57. `weewx-rtldavis#56` closed, outcome reported to `eaglehunt-ops#22`. See
CHANGELOG `[S44]`.

**▶ ON RETURN (S45), in order:**

1. **Check the log for a humidity spike — the capture is LIVE.** `log_humidity_raw True` went active with
   the v2.0.7 restart at 2026-07-13 15:27 EDT. Grep `weewx.log` for `humidity_raw=`. Spikes run ~2–3/week
   clustered **11:00–16:00** — S43/S44 checked ~2,950 samples combined, no qualifying spike yet (largest
   7.5 %RH/min, need the 16-37 % DEC-0044 signature). It logs the full `pkt[4]`/`pkt[3]` — **no
   averaging, no free parameter** — which settles the nibble question **deterministically**: invert the
   bytes, re-decode under `0x2`/`0x8`/`0xE` (humidity's real single-bit neighbours — *not* solar or UV,
   which are 2 and 3 bits away), compare with the concurrent archived sensor. **The method and the
   arithmetic are in DEC-0044; do not re-derive them.**

2. **Do NOT rebuild the coupling filter** (DEC-0044). Its premise failed on our own data. The mechanism
   is the open question, not the threshold.

3. **`ops/soak_check.sh`'s phantom-rain detector is now hardened (S44) — don't re-flag ordinary rain.**
   If it reports a nonzero count, that already excludes the normal post-tip decay window (1 hour); a
   real hit is worth taking seriously as the DEC-0049-predicted event, not re-litigating as a false
   positive first.

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
