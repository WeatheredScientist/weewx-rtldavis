# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3. A public, published WeeWX extension (Docker Hub + GitHub
releases), GPLv3. Its real contract is the **data it emits** (loop-JSON + InfluxDB line protocol),
not any one consumer. The dashboard is a **separate repo** — no dashboard changes here.

---

## ▶ Resume here (S202 → S203)

### What's settled (do not re-derive)

**v2.4.0 runs in prod since 2026-11-04 18:36:38 ET** (image `82220200…`, banner `0.20+ws.10`):
DEC-0229's arrival-time gate in Go, `-tolerance` default 100 ms; `-tolerance 0` in the live `cmd` is
the no-rebuild off switch. Rollback: `:v2.3.0-prod-pre-v2.4.0` (`71c201b6…`). **P0.8 phase 6 is
built out**; only its acceptance test is left. ROADMAP reconciled S202; **next check S212.**

**DEC-0229 in one line:** a CRC-valid noise frame re-anchored the hop clock (2 to 5 min loss); the
gate drops a frame over 100 ms off schedule. On-schedule bit-error frames (ERR-0012) are out of its
reach. A `Go time gate dropped a frame` line is the proof of a drop. **Two so far, neither with a
gap (11-05, 11-07; `docs/ROADMAP.md` P1.9). Clear 11-07 12:01 to 11-13 23:10 ET.** The crcstats
line is lowercase, so `grep CRC` is a false zero. Gap check: `grep Added`, keep the `record 2026-…`
stamps, flag steps over 90 s (each minute logs twice). A past day's log is `weewx.log.YYYY-MM-DD`;
`marvinctl grep` takes one token and an absolute path.

**DEC-0234 (S201b):** `loopjson` 1.2.0 **in prod since 2026-11-12 22:42:25 ET** (writer sha
`8c2365d6…`); `check_contract.py` + schema ship in release `loopjson-v1.2.0`. Rollback: owner-run
`git -C /srv/docker/weewx checkout 694938f -- loop_json_writer.py`, then restart.

**DEC-0235 (S201a):** the Go decoder **ignored `-d`**; the devsel fix (`RTLSDR_DEVICE`, `doctor`
listing, exit 15) is on `dev`, **baked: not in prod until the next image.** **Next DEC: DEC-0236.**
**V4L (S202, ops#440):** the owner's NAS stick is a Blog **V4L** (R828S), not a V4. The image's
librtlsdr (osmocom v2.0.2+2) does not support it (R820T, "PLL not locked", stall loop); osmocom
v2.0.3 does (`0204c9c`), and the V4L **decodes on it**. amd64 test tags on Hub, **not for prod**:
`v2.4.0-v4l-test` (`b599bf27…`) and `v2.4.0-v4l-rtl433-test` (`ac19bbe2…`, + rtl_433 25.12), built on
marvin in `builds-v4l-test/` from local branch `s202-v4l-test` (unpushed). Findings:
`docs/RTLSDR-V4-AND-PINNING.md` (V4L addendum).

**NAS test bed (ops#440; heartofgold and ops drive it, the owner runs each line on Foundation):**
confined container `weewx-v4ltest` (uid 0, `--cap-drop ALL`, `--network none`, 256m, one device
node, `--restart no`), data `/volume1/docker/weewx-v4ltest`, seed interval 300 s and default gain,
so it is a **shakedown, not the A/B**. Nothing from it counts until the pre-registration is posted.
`v2.4.0` ran confined on DSM; the trial's earlier container is kept as evidence until the end.

S192's cruft audit "Deliberately kept" list is settled. CI fails, not skips, the Go gate tests
(DEC-0230). DEC-0232: a `windGust10` archive column, prod by the owner-run
`docs/WINDGUST10-MIGRATION.md`. DEC-0233: `docs/INTERFACES.md` is a specification (contract 1.2).
**Check a MANIFEST edit with ops' `checks/manifest-coverage-sweep.sh` before landing it.**

Standing facts: images are multi-arch (DEC-0214/0215); SemVer per DEC-0222; the loop writer and
`influx.py` ship as extensions, prod mounts both; `t-weewx` (996:986) runs under `--cap-drop ALL`.
**#475 is parked on purpose.** Prod log `/srv/docker/weewx/logs/weewx.log`, rotated daily. Tests are
pytest-only (#502). `doctor` exits 13 on marvin (dongle held by prod), correctly. **Running code
inside the prod container is a classifier-gated "production read"**: plan for the owner to run it.
`marvinctl build` takes a directory under the tenant tree and `marvinctl push` publishes a versioned
tag to the ratified Hub repo (Class B, never `latest`, cannot delete). Prod's librtlsdr is still
v2.0.2+2; the grant for the v3 is narrowed to its port, so **tell marvin before moving the v3's jack**.

### ▶▶ S203 JOB LIST

00. **Owner first.** (a) DEC-0232's migration doc, then `ops/windgust10_check.sql`. (b) Ops note,
   owner's go: dashboard DEC-0442 §3.2's `MAX(windGust)` fallback re-admits ERR-0012. (c) **The next
   minor image** (DEC-0235 A to C + DEC-0232, and decision 0b): build, prove, release; then prod's
   `RTLSDR_DEVICE` = the v3's serial (heartofgold unit edit, owner-run).
0. **Decisions (Opus).** (a) **#579:** a vanished dongle never exits the container: `weewxd --exit`
   vs a stall watchdog; a DEC. (b) **librtlsdr v2.0.3 pin bump** (now with a concrete reason: the V4L
   works only on it; plus the USB-hang fix `65f0658`): a DEC with a v3 soak on prod. (c) **The NAS
   A/B pre-registration, owed on ops#440 before the measured run:** frame-level agreement as the bar
   (not "within 5 points" of a metric near 99.9%), 60 s records on a fresh database, gain arms
   (372 like-for-like), NTP, duration, and the stated limit that antenna, position and host differ
   with the stick. Heartofgold's finish conditions: the fix in a real release, the NAS restored.
   (d) The S197 cross-repo drift ops issue (draft in S201b's notes; owner's go). (e) ops#449 closes
   when the sweep reads `dev`. (f) Design first: #561, #553 (DEC-0014). (g) Owner: #558. (h) ROADMAP diet.
1. **ops#440 follow-ups:** answer heartofgold's reads; AcuRite listens each pause `weewx-v4ltest`
   (gap times reported, none in the measured run); end-state cleanup (`BACKLOG.md`: Hub test tags,
   marvin's `builds-v4l-test/` and two test images). Commit or drop branch `s202-v4l-test`.
2. **Gate results since 11-13 23:10 ET:** any `gate` line (keep bytes and offset) and any gap with
   none. Around 2026-12-04, re-run `ops/garbage_gap_corr.py` over the 30 days after the deploy;
   #536 stays open until then.
3. **Upstream threads:** lheijst/rtldavis#2 comment, weewx-influx2#1, matthewwall/weewx-wcloud#6, and
   #514. Offer the devsel patch upstream on the owner's go. Keep `docs/UPSTREAM-THREADS.md` current.
4. **Needs the owner:** GitHub About text and topics; `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the
   shell profile; the hot-swap code (#553, S196 recommends removal). **#457:** `MANIFEST.md` is 6
   tokens over its cap.
5. **Phase 6's acceptance test:** a stock 64-bit Pi OS plus `docs/QUICKSTART.md`, timed, by someone
   new. First arm64 run against a live radio still open.
6. **Watch only:** `no bar_absolute` (DISC-0002) · WU gold star · OWM/Windy rain in mm (ERR-0010) ·
   `Go burst gate dropped a frame` (last 11-08 19:50:07 ET) · first `unhealthy` · any `rejecting
   implausible`, `unknown message type` or loopjson `not finite` WARNING. **Second dongle A/B
   reminder Sat 2026-12-05 09:00 ET** (a decoder swap needs a DEC). Carry-forwards: `BACKLOG.md`.

## Current state (S202)

| Thing | State |
|---|---|
| Prod | marvin, `v2.4.0` as `:marvin-live` since 2026-11-04 18:36:38 ET, weewx 5.5.2, gain 372. Writer 1.2.0 since 2026-11-12 22:42 ET |
| InfluxDB / monitor | `weewx-influxdb.service`; monitor running sha `2f8a1eda…` (the checkout holds S193's message-only edit, live at the next monitor restart), `REMEDY_MODE=none` |
| Reception | 99.9% mean at USB `5-1`; 0 archive gaps 11-05 00:00 to 11-13 23:10 ET |
| `main`/`dev` | `main` = v2.4.0 (`c376037`, `prod-baseline-20261104`); `dev` adds docs, tests, CI, DEC-0232's and DEC-0235's baked changes (next image) and loopjson 1.2.0 (mounted, live) |
| Docker Hub | `:latest` = `:v2.4.0`, multi-arch; digests in `CONSTANTS.md`; plus the two V4L test tags above |
| Trackers | repo: #579, #553, #558, #561, #536, #475 parked, #380 info, #514 · ops: #440, #449, #110 (Jan-Feb), #344 |

## Blockers

Unchanged from S145 except blocker 1: 1 freeze mechanism (DEC-0068/0094): short gaps measured
(DEC-0229); the long tail may be #579's shape or the librtlsdr USB hang (both inferred), 2 RF-dead
root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch.

## Model tier

S202: Sonnet 5.5 throughout (reconciliation, gate read, tracker answers, the test images); no bare
`/model`, nothing to restore. S203: Opus 5.5 at `medium` for decisions 0a to 0c, Sonnet for the rest.

## Gotchas — `docs/GOTCHAS.md`

§1 any tool's zero/green · §2 any PR, merge or handoff write · §3 NAS, marvin or campaign · §4
judging live, dead or shipped.

_Last updated: 2026-11-14 (S202: ROADMAP reconciled; V4L test tags on Hub; NAS shakedown under way)._
