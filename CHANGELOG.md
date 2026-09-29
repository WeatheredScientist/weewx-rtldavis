# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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

## [S143] — 2026-09-27 — The loop feed moves into `weewx-data/feed/`, and `eh-proxy` now mounts only that (`eaglehunt-ops#348` complete, DEC-0202); PR #396 merged

- **PR #396 merged** (S142's DEC-0201 and handoff) as squash `0d79daf` at 22:30 ET. S142's worktree
  and branches were removed, along with the stale `claude/pensive-borg-1958f0` (its one commit
  landed as PR #338 on 2026-09-05).
- **`eaglehunt-ops#348` step 1 applied, owner-approved.** The dashboard (S316) and marvin (S54)
  agreed on a symlink transition that needs no synchronized window.
  - `[LoopJsonWriter]` `path`/`current_path` now point at `/opt/weewx-data/feed/` in the live conf
    and in the tenant-root `weewx.conf.rx-baseline`. The baseline went through the owner root route
    as t-weewx at 22:54:57 ET. The live conf went as 996 via `marvinctl exec` at 22:56:28, after a
    dry run. Both stay 0600, and the pre-edit copies are in `conf-archive/`.
  - `feed/` was created at 0755. weewx restarted at 22:56:50, and the writer's startup line names
    the feed paths. The first packet landed about 106 s later.
  - At 22:58:37 the top-level `loop-data.txt` and `current.json` were swapped atomically for
    relative symlinks into `feed/`.
  - Right after, eh-proxy served `/loopdata` 200 at 1.4 s old. There were 0 ERROR, CRITICAL or
    tracebacks since the restart, against 101 INFO lines.
- **`eaglehunt-ops#348` finished the same night.** marvin flipped `eh-proxy`'s mount to `feed/` at
  23:20:56 ET (MARVIN-DEC-0183), and the dashboard's check passed at 23:22. weewx removed the two
  symlinks at 23:26:57 as t-weewx, leaving `feed/` untouched. Afterwards eh-proxy served `/loopdata`
  200 at 0.2 s old, with 0 errors against 27 INFO lines. Each step was posted on #348 and rung to
  the other two repos. The #396 merge was also posted on `eaglehunt-ops#347`, so heartofgold can
  tick weewx's row.
- **Docs:**
  - DEC-0202.
  - `CONSTANTS.md`: the Loop-JSON and compat-path rows, plus a new live-config deviation row
    carrying marvin's two `feed/` rules.
  - `docs/INTERFACES.md`: the paths are configurable, and a consumer must bind the directory, not
    the files.
  - `docs/CONVENTIONS.md`: its S55-era infra table, a stale second copy that still named the NAS as
    prod, is now a pointer to `CONSTANTS.md` (BOOT job 8's CONVENTIONS item).
  - `docs/GOTCHAS.md` §1: `weewx.log` timestamps are ISO, so a syslog-shaped window filter reads as
    a false zero.
  - `docs/GOTCHAS.md` §3: `ssh -G` trips the marvin guard, and ConfigObj needs
    `interpolation=False`. The second was re-hit because §3 went unread before the marvin task.
- Gate: ruff clean · 516 passed / 17 skipped · mypy clean, 72 files (fresh cache) · secret gate 0 on the
  staged files, positive-controlled (identifier, private-IP and credential plants each exit 1).
