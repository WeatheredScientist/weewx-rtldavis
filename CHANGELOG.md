# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S150] — 2026-10-06 — WeatherLink's `bar_absolute` becomes weewx's `pressure` (DEC-0209, `eaglehunt-ops#357` option A); v2.0.20 in prod the same night

- **v2.0.20 is in prod since 2026-10-06 22:15:14 ET.** PR #433 moved the stamp; built on marvin
  from `dev`@`9a86c97` (image `f617c9ca…`); `exec-ro` sha of the seven baked modules against
  v2.0.19: only `pressure_service.py` differs, equal to `dev`'s. The first fetch (22:17:19) logged
  `station pressure 29.534`; the first record (22:18:00) carries `pressure 29.534`, `altimeter
  30.130` against the derived rows' 29.526 / 30.122 — a +0.008 inHg step, `barometer` unchanged
  (DISC-0002 filled). Zero WARNING/ERROR lines since the restart; three archive minutes lost to it.
  `soak_check.sh`: 19 passed, 0 warnings, 0 failures (an earlier run inside the acquisition gap
  flagged ARCHIVE STALLED, as expected). `:v2.0.20` pushed to Docker Hub with `marvinctl push` at
  22:19 ET, Hub's digest equal to prod's (`f617c9ca…`). Tagged `v2.0.20` on `9a86c97` with a GitHub
  release.
- **`pressure_service.py` reads `bar_absolute` beside `bar_sea_level` and injects it as `pressure`**
  when the packet's is null; weewx's `prefer_hardware` keeps it, so the archive's station pressure is
  measured and `altimeter` derives from it instead of from the reversed sea-level value. Without the
  key nothing changes (one warning). Five new tests; the S82b injection test split in two. Baked, so
  it rides a v2.0.20 release — not built this session.
- **Both consumers answered on `eaglehunt-ops#357`** (dashboard 09-29, HLF S362, rung from here):
  neither reads `pressure_inHg` or `altimeter_inHg`; HLF needs the value in the archive. The owner
  chose (A). `DISC-0002` records the boundary (timestamp and shift filled at the deploy); INTERFACES
  §1 rewritten; the ROADMAP line closed; CWOP noted as the one uploader that moves (it posts
  `altimeter`).
- **The station's response carries the key (owner-run probe, the in-session `marvinctl exec` was
  classifier-denied as a production read):** the barometer sensor's record (type 242, data
  structure 19) reads `bar_absolute = 29.534` beside `bar_sea_level = 30.127`, `bar_offset = 0`,
  inHg — one record, the shape the code assumes. The probe printed key names and `bar_*` values
  only.

## [S149] — 2026-10-02 — v2.0.19 in prod (DEC-0208): weewx 5.5.2, the rapidfire endpoint confirmed live

- **weewx 5.5.0 → 5.5.2 is live as `:v2.0.19` since 2026-10-02 00:18:38 ET.** PR #429 moved the
  Dockerfile stamp and `soak_check.sh`'s fallback (`ws.6` canary unchanged: no driver change); built
  on marvin from `dev`@`fee78e3`. `exec-ro` against v2.0.18: the Go binary and the five baked
  modules are sha-identical, only the engine differs. `soak_check.sh`: 19 passed. Tagged `v2.0.19`
  with a GitHub release.
- **`:v2.0.19` is on Docker Hub: the first real `marvinctl --tenant weewx push`** (00:31 ET, exit 0).
  The manifest's `publish` line had been ratified since 2026-09-04, so `eaglehunt-ops#265`'s trigger
  fired; commented there. Hub's digest equals prod's index digest. `:latest` stays at v2.0.13 (owner
  route); v2.0.17 and v2.0.18 were never pushed.
- **The one prod-visible change is confirmed.** The rapidfire thread now posts to
  `rtupdate.wunderground.com`. Its failures never reach `weewx.log`, so the check was external: the
  station's public wunderground.com page read CONNECTED, 2 seconds old, after the restart.

## [S148] — 2026-09-30/10-01 — #423's swap path proved end to end as `t-weewx`; `weewx.service` under #360's flags, accepted

- **No campaign was queued** (the schedule has been empty since DEC-0128), so the owner chose a
  test-only one: new arm `T` (prod's cmd plus an explicit `-ex 0`, the flag's default), then
  `BASELINE`, driven by two hand-started passes of `weewx-rx-experiment.service`. No timer and no
  `install`: the tenant-root snapshot was verified byte-identical to the live conf, and the state
  file was seeded over sftp. PR #427; its dates moved once when it sat unmerged past the first
  terminator.
- **Both passes worked.** 2026-10-01 21:04:30 ET, `NONE -> T`: config write verified, restart through
  `sudo -n marvin-own weewx restart`, healthy in 106 s via `systemctl is-active`. 22:31:22,
  `T -> BASELINE`: live conf restored byte-exact (mode 0600 kept), harvest wrote 17 rx and 85 dup
  rows under `T`, no mail failure. Schedule stood down again on the closeout PR.
- **`eaglehunt-ops#360`: the 21:04:30 restart was also `weewx.service`'s flag restart.**
  `NoNewPrivs: 1`, every capability set 0, uid 996. One record lost (21:05), 21:06 partial with
  `rxCheckPercent` NULL, 21:07 at 100%. Posted; heartofgold confirmed on the box.
- `GOTCHAS.md` §3: `marvinctl grep` also refuses `/` in a pattern. S144 rolled to the archive.

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
- **Merged and one prod restart.** #424 and #425 are on `dev` (`a039a65`); #420 closed. At marvin's
  request (`eaglehunt-ops#360`, `MARVIN-DEC-0191`) `weewx-influxdb.service` was restarted 13:53:45 ET
  to pick up `--cap-drop ALL` and `no-new-privileges`: `NoNewPrivs: 1`, `CapBnd` 0, the next archive
  post went through. The `weewx.service` restart is left for the owner's window.

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
