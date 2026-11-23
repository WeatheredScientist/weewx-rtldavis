# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S211 → S212)

### What's settled (do not re-derive)

**v2.4.0 runs in prod since 2026-11-04 18:36:38 ET** (image `82220200…`, banner `0.20+ws.10`):
DEC-0229's arrival-time gate in Go, `-tolerance` default 100 ms; `-tolerance 0` in the live `cmd` is
the no-rebuild off switch. Rollback: `:v2.3.0-prod-pre-v2.4.0` (`71c201b6…`). **P0.8 phase 6 is
built out**; only its acceptance test is left. ROADMAP reconciled S202; **next check S212.**

**DEC-0229 in one line:** a CRC-valid noise frame re-anchored the hop clock (2 to 5 min loss); the
gate drops a frame over 100 ms off schedule. ERR-0012's on-schedule frames are out of its reach.
Time-gate drops (`Go time gate dropped`; the burst gate is separate) through 11-21: none followed
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
after `RTLDAVIS_EXIT_AFTER` = 3 consecutive decoder exits; CI proves it) and DEC-0240 (#587; DEC-0244 corrects its file). **Decided S204, not built:** DEC-0238 (librtlsdr → osmocom v2.0.3, `797f814` +
sha256 as on `s202-v4l-test`, after a prod soak). **DEC-0244** (#596/#597, `dev`): the starter runs the loop writer and DewpointCacher, `[[Influx]]` idles on `replace_me`, mount `bin/user` imports. **DEC-0242** (#558): `influx.py` `0.20+ws.3`, the
dead NAS-LEASE yield removed, `lease_dir` ignored with one INFO line; on `dev`, so it ships to prod
at the next `marvinctl pull` + restart (tenant root's `dev` checkout): **no pull during the soak.**
Rollout after it: pull, restart, verify sha + `service version is 0.20+ws.3`; owner deletes
`lease_dir` from the live conf and `weewx.conf.rx-baseline`; heartofgold may drop `/nas-lease`.
Tag `influx-v0.20+ws.3` (the workflow publishes the zip) is the owner's go. **Next DEC: DEC-0246.**

**DEC-0238's soak (SWAPPED 11-23 7:58:14 AM ET):** `v2.4.0-v4l-test` (`b599bf27…`; verified S204 on
marvin: `librtlsdr.so.2.0.3`, driver sha `7b6fb60a…` = prod's) as `:marvin-live`, 24 h settle, then
seven days 00:00 to 00:00 ET. PASS: 0 gaps over 90 s, 0 stalls, 0 `rtldavis exited`, 0 `PLL not
locked`, mean `rxCheckPercent` ≥ 99.5. Rollback `tag …:v2.4.0 …:marvin-live` + restart. **Order:**
marvin's physical move first (heartofgold BACKLOG A9, about 30 min gap; the v3 returns to `5-1`;
their runbook step H posts the gap times on ops#440 and rings us), swap **at least 2 days after
it**, score against post-move days (report the pre-move week too); DEC-0236 starts the day after the
soak ends (heartofgold A5). Never swap inside DEC-0236's window.

**DEC-0236:** the NAS run is pre-registered on ops#440 (readout `ops/ab_frames.py`): frame-level
agreement with prod, gain 372, 24 h burn-in then seven days; it judges a reference receiver, never
the V4L against the v3. **V4L (S202):** the NAS stick is a Blog V4L; only librtlsdr v2.0.3 drives
it. Test tags `v2.4.0-v4l-test` and `v2.4.0-v4l-rtl433-test`; source branch **`s202-v4l-test`
pushed S204 as a record, never merged.** Findings: `docs/RTLSDR-V4-AND-PINNING.md`.
**NAS shakedown** `weewx-v4ltest` (confined, 300 s, default gain) runs until DEC-0236's start;
nothing from it counts; alive 11-15 21:40 ET.

CI fails, not skips, the Go gate tests (DEC-0230). DEC-0233: `docs/INTERFACES.md` is a
specification. **Check a MANIFEST edit with ops' `checks/manifest-coverage-sweep.sh` before landing
it** (fixture mode, `MANIFEST_COVERAGE_FIXTURE_DIR`, reads the local branch; positive-controlled).
DEC-0239: pytest fails a PR over the BOOT/MANIFEST caps (`tests/test_tier_caps.py`); MANIFEST 879/1000 tok at S205.

Standing facts: images are multi-arch (DEC-0214/0215); SemVer per DEC-0222; the loop writer and
`influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under `--cap-drop ALL`.
**#475 is parked on purpose.** Tests are pytest-only (#502). `doctor` exits 13 on marvin, correctly.
**Running code inside the prod container is a classifier-gated "production read"**; `exec-ro` on an
image is not. `marvinctl push` publishes a versioned tag (Class B, never `latest`). The v3's grant is
narrowed to its port: **tell marvin before moving its jack.**

### ▶▶ S211 JOB LIST

00. **Owner first.** (a) DEC-0232 step 7's migration-day rebuild, owner's yes (Class C):
   `weectl database rebuild-daily … --date=2026-11-21 -y` through `marvin-sudo` (runbook step 7),
   then step 5's check; after 11-28, step 8 deletes `weewx.sdb.pre-dec0232`. (b) After a NAS reboot, re-read `weewx-v4ltest`'s USB node. (c) **#584:**
   DEC-0245 (S211): B, a driver check of `windGust10` against received wind, accepted, not built;
   re-run the design's readout after a 25 mph event first (`docs/WINDGUST-PLAUSIBILITY-DESIGN.md`).
0. **DEC-0238's soak:** marvin's move is done (11-21: archive gap 13:40 to 14:03 ET, v3 back on
   `5-1`, ops#440). 11-22 clean (1,440/1,440, rxCheck 99.94%). **Swapped 11-23 7:58:14 AM ET** (posted on ops#440);
   settle to 11-24 7:58 AM, scored 11-25 to 12-02 00:00 ET. Still to confirm: the decoder's `dongle:` line names the v3. V4L bare (11-22). Daily reads per the bars. After it: one readout, post it, then (PASS) the Dockerfile pin change.
1. **The next minor image**, after the soak: DEC-0235 + DEC-0232 + DEC-0237 + DEC-0240 + DEC-0244 + DEC-0238's
   pin; build, prove, release, SemVer minor with DEC-0237's, DEC-0240's and DEC-0244's notes; DEC-0242's rollout
   rides the same window; then prod's `RTLSDR_DEVICE` = the v3's serial (owner-run unit edit).
2. **DEC-0236's run**, after the soak: prod's two logging edits inside the burn-in (in place, never
   copied off the box), restart, check `data:` lines; after the window, one `ops/ab_frames.py`
   readout; revert. **Then #586**: the Zaphod dev/test receiver (`docs/ZAPHOD-DEV-RECEIVER-DESIGN.md`,
   proposed; its DEC is assigned when it's accepted) takes the V4L the day after this window ends.
   Every step runs through Zaphod's own session, on the owner's yes there.
3. **Decisions and design:** the S197 cross-repo drift ops issue (owner's go); ops#449 closes when
   the sweep reads `dev`; optional Go patch (exit when `ReadAsync` returns, its own DEC).
4. **Gate results since 11-21 10:55 ET**; around 2026-12-04 re-run `ops/garbage_gap_corr.py` over 30
   days (#536 open until then).
5. **Upstream:** lheijst/rtldavis#2, weewx-influx2#1, matthewwall/weewx-wcloud#6, #514; the devsel
   patch on the owner's go. Keep `docs/UPSTREAM-THREADS.md` current.
6. **Needs the owner:** the hot-swap code (#553). The owner's shell now sets
   `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1`: a worktree needs `scripts/.identifiers` copied in.
7. **Phase 6's acceptance test** and the first arm64 run against a live radio.
8. **Watch only:** `no bar_absolute` · WU gold star · OWM/Windy rain in mm (ERR-0010) · `Go burst
   gate dropped a frame` (last 11-08) · first `unhealthy` · `rejecting implausible`, `unknown message
   type`, loopjson `not finite`. ops#440 cleanup at the end (`BACKLOG.md`). **Zaphod dev receiver (V4L, WSL2):** owner-paced; plan `docs/ZAPHOD-DEV-RECEIVER-DESIGN.md`; Zaphod's session
   runs it. Carry-forwards: `BACKLOG.md`.

## Current state (S211)

| Thing | State |
|---|---|
| Prod | marvin, `v2.4.0` as `:marvin-live` since 2026-11-04 18:36:38 ET, weewx 5.5.2, gain 372. Writer 1.2.0 since 2026-11-12 22:42 ET |
| InfluxDB / monitor | `weewx-influxdb.service`; monitor sha `2f8a1eda…` (S193's message-only edit live at next restart), `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB `5-1`; 11-05 to 11-21: one gap (11-20 02:23, 4 min) plus S210's restart (11-21 11:23) |
| `main`/`dev` | `main` = v2.4.0 (`c376037`, `prod-baseline-20261104`); `dev` (`d0bc77b`) adds DEC-0232/0235/0237/0240/0244 (next image), DEC-0242's `influx.py` (next pull) and loopjson 1.2.0 (live) |
| Docker Hub | `:latest` = `:v2.4.0`, multi-arch; digests in `CONSTANTS.md`; plus the two V4L test tags |
| Trackers | repo: #579 (DEC-0237), #553, #536, #475 parked, #380, #514, #586, #584 · ops: #465, #440, #449, #110 |

## Blockers

Unchanged from S145 except blocker 1: 1 freeze mechanism (DEC-0068/0094): short gaps measured
(DEC-0229); the 10-22 62 min outage was RF-class stalls, not #579's shape (S204); the long tail stays
unexplained, 2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch.

## Model tier

S211 and S212: Sonnet.

## Gotchas — `docs/GOTCHAS.md`

§1 any tool's zero/green · §2 any PR, merge or handoff write · §3 NAS, marvin or campaign · §4
judging live, dead or shipped.

_Last updated: 2026-11-22 (S211)._
