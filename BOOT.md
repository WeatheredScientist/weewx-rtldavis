# BOOT — weewx-rtldavis

**Always-load, tier 1; maintainer context (contributors: `README.md`, `CONTRIBUTING.md`).** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S213 → S214)

### What's settled (do not re-derive)

**v2.4.0 in prod 2026-11-04 to 11-23 (soak image since, below)** (image `82220200…`, banner `0.20+ws.10`):
DEC-0229's arrival-time gate in Go, `-tolerance` default 100 ms; `-tolerance 0` in the live `cmd` is
the no-rebuild off switch. Rollback: `:v2.3.0-prod-pre-v2.4.0` (`71c201b6…`). **P0.8 phase 6 is
built out**; only its acceptance test is left. ROADMAP reconciled S212; **next check S222.**

**DEC-0229 in one line:** a CRC-valid noise frame re-anchored the hop clock (2 to 5 min loss); the
gate drops a frame over 100 ms off schedule. ERR-0012's on-schedule frames are out of its reach.
Time-gate drops (`Go time gate dropped`; the burst gate is separate) through 11-25: none followed
by a gap. **One gap it missed (S210b):** 11-20 02:23 to 02:27 ET, after a CRC-valid 83.6 mph frame
it passed, the pre-DEC-0229 shape; evidence for #536. The crcstats line is lowercase, so
`grep CRC` is a false zero. Gap check: `grep Added`, keep the `record 2026-…` stamps, flag steps over
90 s. A past day's log is `weewx.log.YYYY-MM-DD`; `marvinctl grep` takes one token and an absolute
path.

**DEC-0234:** `loopjson` 1.2.0 **in prod since 2026-11-12 22:42:25 ET** (writer sha `8c2365d6…`).
Rollback: owner-run `git -C /srv/docker/weewx checkout 694938f -- loop_json_writer.py`, restart.
**DEC-0232 migrated on prod S210** (11-21, backfilled; the runbook says what's left).
**Baked on `dev`, not in prod until the next minor image:** DEC-0235 (devsel: `RTLSDR_DEVICE`,
`doctor` listing) DEC-0232's starter schema (new installs) and DEC-0237 (#579: the driver raises `RtldavisDecoderFatal`
after `RTLDAVIS_EXIT_AFTER` = 3 consecutive decoder exits; CI proves it) and DEC-0240 (#587; DEC-0244 corrects its file) and **DEC-0247** (#610, outside review: failed thermistor = no reading, message-9 gust only from the wind channel). **DEC-0238's pin** (librtlsdr v2.0.3) is built on held
**`s212-librtlsdr-pin`** (`1cba5bc`, pushed, no PR until PASS) with `docs/RELEASE-NOTES-NEXT.md` (v2.5.0 draft, checklist). **DEC-0244** (#596/#597, `dev`): the starter runs the loop writer and DewpointCacher, `[[Influx]]` idles on `replace_me`, mount `bin/user` imports. **DEC-0242** (#558): `influx.py` `0.20+ws.3`, the
dead NAS-LEASE yield removed, `lease_dir` ignored with one INFO line; on `dev`, so it ships to prod
at the next `marvinctl pull` + restart (tenant root's `dev` checkout): **no pull during the soak.**
Rollout after it: pull, restart, verify sha + `service version is 0.20+ws.3`; owner deletes
`lease_dir` from the live conf and `weewx.conf.rx-baseline`; heartofgold may drop `/nas-lease`.
Tag `influx-v0.20+ws.3` (the workflow publishes the zip) is the owner's go. **Next DEC: DEC-0251.**

**DEC-0238's soak (SWAPPED 11-23 7:58:14 AM ET):** `v2.4.0-v4l-test` (`b599bf27…`; verified S204 on
marvin: `librtlsdr.so.2.0.3`, driver sha `7b6fb60a…` = prod's) as `:marvin-live`, 24 h settle, then
seven days. PASS: 0 gaps over 90 s, 0 stalls, 0 `rtldavis exited`, 0 `PLL not
locked`, mean `rxCheckPercent` ≥ 99.5. Rollback `tag …:v2.4.0 …:marvin-live` + restart. DEC-0236 starts the
day after it ends (heartofgold A5). Never swap inside DEC-0236's window.

**DEC-0236:** the NAS run is pre-registered on ops#440 (readout `ops/ab_frames.py`): frame-level
agreement with prod, gain 372, 24 h burn-in then seven days; it judges a reference receiver, never
the V4L against the v3. **V4L (S202):** the NAS stick is a Blog V4L; only librtlsdr v2.0.3 drives
it. Test tags `v2.4.0-v4l-test` and `v2.4.0-v4l-rtl433-test`; source branch **`s202-v4l-test`
pushed S204 as a record, never merged.** Findings: `docs/RTLSDR-V4-AND-PINNING.md`.
**NAS shakedown** `weewx-v4ltest` runs until DEC-0236's start. **V4L ~98%** since the antenna was raised away from the electronics (11-26 afternoon); 2 AM backup dip now ~1 pt. Keep it there for DEC-0236.

CI fails, not skips, the Go gate tests (DEC-0230). DEC-0233: `docs/INTERFACES.md` is a
specification. **Maintainers: check a MANIFEST edit with ops' `checks/manifest-coverage-sweep.sh` before landing
it** (`MANIFEST_COVERAGE_FIXTURE_DIR` reads the local branch; not a contributor step).
DEC-0239: pytest fails a PR over the BOOT/MANIFEST caps (`tests/test_tier_caps.py`).

Standing facts: images are multi-arch (DEC-0214/0215); SemVer per DEC-0222; the loop writer and
`influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under `--cap-drop ALL`.
**#475 is parked on purpose.** Tests are pytest-only (#502). `doctor` exits 13 on marvin, correctly.
**Running code inside the prod container is a classifier-gated "production read"**; `exec-ro` on an
image is not. `marvinctl push` publishes a versioned tag (Class B, never `latest`). The v3's grant is
narrowed to its port: **tell marvin before moving its jack.**

### ▶▶ S213 JOB LIST

00. **Owner first.** (a) DEC-0232 step 7 done 11-24 (rebuilt 11-21, step 5's check read back);
   after 11-28, step 8 deletes `weewx.sdb.pre-dec0232`. (b) After a NAS reboot, re-read `weewx-v4ltest`'s USB node. (c) **#584:**
   DEC-0245 (S211): B, a driver check of `windGust10` against received wind, accepted, not built;
   re-run the design's readout after a 25 mph event first (`docs/WINDGUST-PLAUSIBILITY-DESIGN.md`).
0. **DEC-0238's soak PASSED** (S213, owner's call): closed early 11-27 4:45 PM ET on 4.4 clean days
   (0 faults; rxCheck 99.93 to 99.96%; amendment in `DECISIONS-FULL.md`). Next: the PR for
   `s212-librtlsdr-pin`. The NAS USB fault test stays proposed (`docs/RTLSDR-V4-AND-PINNING.md`).
1. **The next minor image**, after the soak: DEC-0235 + DEC-0232 + DEC-0237 + DEC-0240 + DEC-0244 + DEC-0247 +
   DEC-0238's pin; build, prove, release by the notes file's checklist; DEC-0242's rollout
   rides the same window; then prod's `RTLSDR_DEVICE` = the v3's serial (owner-run unit edit).
2. **DEC-0236's run**, after the soak: prod's two logging edits inside the burn-in (in place, never
   copied off the box), restart, check `data:` lines; after the window, one `ops/ab_frames.py`
   readout; revert. **Then #586**: the Zaphod dev/test receiver (`docs/ZAPHOD-DEV-RECEIVER-DESIGN.md`,
   proposed; its DEC is assigned when it's accepted) takes the V4L the day after this window ends.
   Zaphod's session runs it, on the owner's yes.
3. **Decisions and design:** the S197 drift ops issue (drafted S213); ops#449 closes when
   the sweep reads `dev`; optional Go patch (exit when `ReadAsync` returns, its own DEC).
   Outside review (S211): C1 burst carry-over held (no conflicts seen), C3: confirm-on-reject on held `claude/c3-rain-confirm-a9f413` (`454f638`, DEC-0249, cap 45), own minor after the next image; S3 settled (the hygiene sentence, not the rows).
4. **Gate results since 11-21 10:55 ET**; around 2026-12-04 re-run `ops/garbage_gap_corr.py` over 30
   days (#536 open until then).
5. **Upstream:** lheijst/rtldavis#2, weewx-influx2#1, matthewwall/weewx-wcloud#6, #514; the devsel
   patch on the owner's go. Keep `docs/UPSTREAM-THREADS.md` current.
6. **DEC-0250:** once heartofgold drops the rx unit, cut it from `ops/tenant_mounts.py`. The owner's shell sets
   `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1`: a worktree needs `scripts/.identifiers` copied in.
7. **Phase 6's acceptance test** and the first arm64 run against a live radio.
8. **Watch only:** `no bar_absolute` · WU gold star · OWM/Windy rain in mm (ERR-0010) · `Go burst
   gate dropped a frame` (last 11-08) · first `unhealthy` · `rejecting implausible`, `unknown message
   type`, loopjson `not finite`. ops#440 cleanup at the end (`BACKLOG.md`). Carry-forwards: `BACKLOG.md`.

## Current state (S213)

| Thing | State |
|---|---|
| Prod | marvin, soak image `v2.4.0-v4l-test` since 11-23 7:58 AM ET, weewx 5.5.2, gain 372. Writer 1.2.0 since 2026-11-12 22:42 ET |
| InfluxDB / monitor | `weewx-influxdb.service`; monitor sha `2f8a1eda…` (S193's message-only edit live at next restart), `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB `5-1`; 11-05 to 11-21: one gap (11-20 02:23, 4 min) plus S210's restart (11-21 11:23) |
| `main`/`dev` | `main` = v2.4.0 (`c376037`, `prod-baseline-20261104`); `dev` (`3f11a5b`) adds DEC-0232/0235/0237/0240/0244/0247 (next image), DEC-0242's `influx.py` (next pull) and loopjson 1.2.0 (live) |
| Docker Hub | `:latest` = `:v2.4.0`, multi-arch; digests in `CONSTANTS.md`; plus the two V4L test tags |
| Trackers | repo: #579 (DEC-0237), #536, #475 parked, #380, #514, #586, #584 · ops: #465, #440, #449, #110 |

## Blockers

Unchanged from S145 except blocker 1: 1 freeze mechanism (DEC-0068/0094): short gaps measured
(DEC-0229); the 10-22 62 min outage was RF-class stalls, not #579's shape (S204); the long tail stays
unexplained, 2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch.

## Model tier

S213: Opus 5.5. S214: Sonnet.

## Gotchas — `docs/GOTCHAS.md`

§1 any tool's zero/green · §2 any PR, merge or handoff write · §3 NAS, marvin or campaign · §4
judging live, dead or shipped.

_Last updated: 2026-11-26 (S213)._
