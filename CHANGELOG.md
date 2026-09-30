# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S147] — 2026-09-30 — `rx_experiment.sh` runs as `t-weewx` (#423, MARVIN-DEC-0189)

- **Campaigns would have refused at preflight, and then aborted.** marvin moved
  `weewx-rx-experiment.service` from root to `t-weewx`. Preflight's `systemctl cat` went through
  `marvin-own`, which grants no read verbs; new `RX_READ_SYSTEMCTL` (default plain `systemctl`) does
  the reads. `health_ok` also ran `docker inspect` every pass, which fails without the docker group,
  so every swap would have timed out; new `weewx_running()` asks `systemctl is-active` in systemd
  mode. Docker mode is unchanged. Five tests; three fail against the old script.
- **Mirrors and docs.** `ops/weewx-monitor.service` and `ops/weewx-rx-experiment.service` are now
  verbatim copies of marvin's installed units (credential file under `/etc/marvin/env.d/weewx/`, the
  old tenant path a root-owned symlink that must stay a symlink). `ARCHITECTURE.md` corrected.
- **Not verified:** no arm swap has run end to end as `t-weewx`. The first campaign is that test.
- **weewx 5.5.0 → 5.5.2 staged for v2.0.19 (DEC-0207), not built.** PR #420's green checks proved
  nothing (CI installs only pytest; the tests stub weewx). New `ops/weewx_bump_check.sh` boots a
  scratch station on the Simulator with our baked modules; it passes on 5.5.2 and fails on 5.5.0. The
  one prod-visible change: with `rapidfire` and `archive_post` both on, 5.5.2 posts the rapidfire
  thread to `rtupdate.wunderground.com` (5.5.0 used the archive URL for both). Dependabot now
  targets `dev`; #420 targeted `main`.

## [S146] — 2026-09-29 — v2.0.18 in prod (DEC-0206): DEC-0205's driver and uploader fixes, the monitor's #413 restarted; ROADMAP full pass; ERR-0010; a wrong INTERFACES claim corrected

- **Deployed, the owner's go at each prod step (DEC-0206).** #419 (Dockerfile stamp, `soak_check.sh`
  canaries) merged 09:30 ET and was pulled. The monitor restarted 09:31:16 (`Remedy armed: … none`,
  clean for seven hours). The image built in 13 s on BuildKit's cache (09:31:33 to 09:31:46) and was
  verified by `exec-ro` sha256 of 224 baked files against v2.0.17: exactly four differ, each equal to
  `dev`@`4fd9039`. Cutover 16:37:37: banner `0.20+ws.6`, 129 INFO and 0 errors in four minutes, soak
  19/0/0, first real record 100% (16:38 and 16:39 missing while the hop re-acquired).
- **Tagged `v2.0.18` on `4fd9039` with a GitHub release.** Not on Docker Hub (`eaglehunt-ops#265`).
  #402 to #405 closed with deploy evidence; #421 filed for the secret gate's four detector holes.
- **Records.** #408 recorded as deliberate (the parent init would start a second set of Wunderground
  threads). ERR-0010 logs OWM's 10× low `rain_1h` and Windy's wrong-window `precip` since 2026-05-21.
  ROADMAP tripwire ran: four lines moved, P0.7 opened, next check S156.
- **INTERFACES.md was wrong and is corrected.** It said the archive's `pressure` and `altimeter`
  columns go NULL (DEC-0091). They are derived by `StdWXCalculate` from the sea-level `barometer`
  and populated in 99.5% of rows. Found while answering `eaglehunt-ops#357` (HLF's `bar_absolute`
  ask); the design is not started, and the reply on the tracker gives two shapes. The stale comment
  in `pressure_service.py` waits for that work, since editing it changes the baked file.
- **Other tracker.** `eaglehunt-ops#360` answered for weewx (cap-drop, no-new-privileges and
  `nosuid,nodev` are all fine; two gaps named).
- Closeout: DEC-0206; GOTCHAS gains eight traps (§1 ×3, §2 ×3, §3 ×2); S143 rolled to the archive.
  S145's seven worktrees and fourteen local branches removed after each was checked against its
  merged PR. heartofgold's CHANGELOG row pushed (`ebe2a59`).

## [S145] — 2026-09-28/29 — Code audit (DEC-0205): 39 findings, the ten high ones fixed on seven PRs; driver to 0.20+ws.6 (unreleased)

- **Audit.** Six read-only reviewers (Sonnet ×5 by file set, Haiku ×1 cross-ref) over the whole tree
  at `7d06cbf`; every high finding re-verified by the main thread before filing. Record:
  `docs/CODE_REVIEW_S145.md`. Two subagent false zeros caught by hand (GOTCHAS §1).
- **Filed.** #402 driver slot-count seed off by one · #403 monitor FULL OUTAGE phase dependence ·
  #404 an unknown `REMEDY_MODE` runs the USB reset · #405 OWM/Windy rain in cm, not mm · #406 ws.N
  stagnant since 2026-08-11 · #407 soak_check image default stale · #408 OgoXe init divergence
  undocumented · #409 secret gate lacks a control per class · #410 vacuous tests · #411 order-dependent
  suite · `eaglehunt-ops#358` (private) planted addresses.
- **Fixed and merged to `dev` 2026-09-29 (owner's go, squash, each behind green checks).** #412 driver (ws.6, 14 header entries) · #413 monitor · #414
  uploaders · #415 gate (63 → 160 controls; mutation kills 35 → 101 of 110) · #416 `tests/conftest.py`
  · #417 soak_check · the docs PR (README table, influx ws.2, inventory recount +1239/−167, lheijst#23
  status, OgoXe notice, this closeout). Combined tree: 591 passed / 17 skipped in both orders.
  Issues #406–#411 closed at merge; #402–#405 stay open until v2.0.18 and the monitor restart.
- **S144 job 1 done:** `ISS battery: OK` in three 6-hourly reports. **Job 2 moot:** the dupgate patch
  applies clean (offset 0, fuzz 0) to today's tarball.
- Closeout: DEC-0205 logged; DEC-0199 amended; `MANIFEST.md` row for the review record; GOTCHAS §1/§2
  gain four traps.

## [S144] — 2026-09-28 — DEC-0200 verified overnight; #394's ISS battery flag surfaced by the monitor and cleaned at the source (DEC-0203); v2.0.17 in prod (DEC-0204); `CONSTANTS.md` marvin rows re-verified

- **DEC-0200 verified (job 1).** 733 of 734 dark archive rows from 09-27 17:41 to 09-28 12:32 ET
  read UV 0. The other is the partial first record of S143's restart (22:59, after two minutes with
  no rows). None fell in (0, 0.05), and none was an exact 0.02 or 0.04. The same query flags all 747
  dark rows of the pre-fix night (positive control). Recorded in DEC-0200's own row and body.
- **#394 triaged, designed with the owner, and built (job 2, DEC-0203).** `txBatteryStatus` was
  archived and shipped to InfluxDB and WeatherCloud, but shown nowhere. All 10 of its historical flips
  were corrupt frames at outage onsets, not the battery.
  - `weewx_monitor.py`: each 6-hourly RF email gains an `ISS battery:` line. A one-shot low-battery
    email fires at 5 or more flagged minutes with healthy reception in one block, and re-arms after a
    clear block. No archived minute would ever have tripped it.
  - `rtldavis.py`: a co-rejected frame now drops its battery flags, and message types
    0x0/0x1/0xB/0xD/0xF condemn a frame like a bounds failure. 9 of the 10 flips now drop at the
    source. It also closes the 09-22 phantom-gust and 09-25 baseline-poisoning paths.
  - 16 new tests. Pre-fix, 4 fail on their own assertions, and mutations of the gate, the latch and
    the key set are each caught. Gates: ruff clean, pytest 532 passed and 17 skipped, mypy clean over
    73 files. The secret scan is clean, with its identifier, IP and credential checks each
    positive-controlled.
  - Mid-decision, the owner was quoted "8 of 10" for the driver fix, a count that treated delta
    trips as proof. The corrected tally (6 by bounds, 9 with the message-type proof) went back to
    the owner before any code. The trap is now in `GOTCHAS.md` §1.
  - PR #399 merged at 13:21 ET (`1dd3026`). The monitor was deployed self-service at 13:21:52
    (sha matches `dev`); its first `ISS battery:` line is due in the 18:00 RF report.
- **v2.0.17 built and cut over, on the owner's go at each prod step (DEC-0204).**
  - PR #400 (`f255efb`) added a `.dockerignore` allowlist, since marvin's build verb is a plain
    `docker build` of the tenant root, which also holds the archive, conf backups and InfluxDB
    data. It added a test pinning the list to the Dockerfile and a v2.0.17 version comment.
  - Built on marvin from the tenant root with a 217 kB context. Checked against v2.0.16 by the
    sha of every baked file, only `rtldavis.py` (now `dev`'s) and the Go binary differ; the
    binary differs because of S126's GPLv3 notice (same `go1.26.0`).
  - Cutover at 13:32:38 by retagging `:marvin-live` and restarting. It booted clean, and the
    first record came at 13:34.
  - Tagged `v2.0.17` on `f255efb`, with a GitHub release. Not pushed to Docker Hub
    (`eaglehunt-ops#265`).
  - #394 closed with the deploy evidence.
- **Reception at the new USB port (job 3): no change.** It averaged 99.9% at both `7-1.2` (3.9 days)
  and `5-1` (20.5 days), with every hour within ±0.4 points. The move was missing from
  `CONSTANTS.md`'s hardware timeline and is now added.
- **`CONSTANTS.md` marvin rows re-verified (job 7).** The tenant root, both containers' user, image
  and mounts, and the rollback images all match. Three stale rows were corrected: releases retag
  `:marvin-live` rather than use `set-image` (its deploy dir is empty), marvin is the build host,
  and `:v2.0.14` is still present. The host-tools row is moot for this tenant. The local-infra-doc
  row stays unverified, since the read guard blocks it, correctly.
- lheijst/rtldavis#7 still has no reply (job 5). Jobs 4, 6 and 8 carry forward unchanged.
