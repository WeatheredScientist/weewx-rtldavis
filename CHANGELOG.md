# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S105] — 2026-08-28/29 — Production migrates from the NAS to marvin (DEC-0118); a live USB-controller incident root-caused and fixed mid-cutover

- **The weewx-rtldavis container now runs on `marvin`, a new self-hosted Debian hypervisor, not the
  NAS ("Foundation").** Moved up from a planned Saturday to Friday night on the owner's call, same
  dark/calm/zero-solar reasoning. Coordinated live across four repos (weewx, marvin, eaglehunt-ops,
  eaglehunt-weather-dashboard; hyperlocal-forecast looped in) via direct cross-session messaging.
  Succeeded. Full narrative: DEC-0118.
- **Transparent to consumers by design.** marvin's NFS export overlay-mounts directly over the NAS
  path dashboard/HLF already use — no compose edits, just a container restart once the overlay
  landed. Both verified live post-cutover.
- **A ~90-minute live incident mid-cutover was the host's USB controller, not RF.** Chased through
  gain (496→372, no change), `-fc`/`-ppm` (no historical sweep data exists to test — confirmed, not
  assumed), and a process-freeze read via DEC-0067's own discriminator (self-corrected once the
  watchdog started visibly cycling) before landing on the real cause: every USB port on the host's
  B850 chipset controller breaks RTL-SDR hop-tracking under sustained streaming; the CPU-attached
  controller is clean. Confirmed with `rtl_test` directly, not weewx.
- **Bonus: real independent corroboration for DEC-0067/0081.** The 150s-stall-raise + ~60s-respawn
  cycle those decisions predicted matched almost exactly during the incident, and fired *only* under
  the bad controller — zero occurrences across the following hour of healthy operation. Supports
  reading those freeze episodes as environmental/hardware, without closing the general question.
- **A live SQLite backup gap was caught and closed same night, not left for the next scheduled run**:
  marvin's `/srv` restic backup fires at 03:30 and `weewx.sdb` is now continuously written there. A
  `.backup`-API dump timer (SQLite's Online Backup API, safe against a concurrent writer) deployed
  and armed for 03:15, mirroring an existing sibling-tenant pattern on the same host.
- **Gain is 372, not 496 — provisional, not a re-adoption.** The controller was the actual incident
  cause, so DEC-0115's measured-best 496 never got a clean test at marvin's RF position. A proper
  re-sweep is backlogged, not urgent.
- **`CONSTANTS.md`'s infra section rewritten** for the new host — container location, project root
  (real path on marvin + the NAS-side compat path, now a read-only NFS overlay), deploy-layer "wins
  in prod" targets, release/rollback mechanics (image unchanged, transferred via `docker save`/`load`;
  a new host-level rollback net alongside the existing image-tag one). Flagged, not silently assumed:
  several rows (build-host capability, `weewx.conf.rx-baseline` presence, missing-tools list) are
  open questions this session didn't have time to verify — `BOOT.md` job 8.
- **`t-weewx`'s `marvinctl` self-service access is not live** — deploys to marvin from this repo still
  need a marvin-side session for now. Tracked as `eaglehunt-ops`'s own follow-up.

---
## [S104] — 2026-08-26 — Every mounted file audited against `dev` (one 7.5-week-stale, harmless); a prod restart bounded by elimination; two DSM tasks found still firing after Campaign B closed

- **Job 4 done: audited the whole mount list, not just the files a deploy happened to touch.** Worked
  from `nasctl inspect` rather than the deploy-layers table, since the table was the thing under test.
  `influx.py` and `loop_json_writer.py` are byte-identical to `dev`; the live config still carries all
  six DEC-0070 deviations; `hotswap_control_file` is absent, so DEC-0117 is *verifiably* off in prod
  rather than assumed off.
- **`ogoxeUploader.py` was 7.5 weeks stale — byte-identical to `7e79d15`, its own S16 prod import.**
  Two `dev` commits had never reached the NAS. Identified without reading the live file, by hashing
  every historical revision of the repo copy until one matched. Content is harmless: an SPDX line,
  the GPLv3 section 5(a) fork notice from DEC-0034, and one `log.debug()` that reported a key which is
  never set and so always printed `None`. No data-path change; the Dockerfile never `COPY`s the file,
  so the published image carries no compliance gap either. Deploy folded into the next image cut,
  where the recreate makes a mounted file take effect for free. Same detection gap as DEC-0116 — no
  new DEC, that row already names the class.
- **The deploy-layers table itself was wrong, which is the durable part.** It grouped
  `ogoxeUploader.py` and `sortedcontainers` as "same pattern" as the row above; neither held.
  `ogoxeUploader.py`'s mount source is `weewx-data/bin/user/` — the exact directory the preceding row
  calls a DECOY for `loop_json_writer.py`, so two adjacent rows asserted opposite truths. And
  `sortedcontainers` is a vendored third-party *directory* bind with no repo copy at all, so "in sync
  with `dev`" was never a meaningful question about it — a comparison that is undefined, not passing.
  Both rows corrected and split ([#278](https://github.com/WeatheredScientist/weewx-rtldavis/pull/278)).
- **Filed the generalization cross-repo as ops#214**, at ops's flag: deploy verification checks the
  file it deployed and never the whole mount list, and every repo in the forum mounts config into
  containers. Routing, not prescribing.
- **The unexplained 2026-08-25 21:40 EDT prod restart: cause absent from every artifact this repo
  keeps, but bounded tightly.** Ruled out on evidence — host/daemon event (every other container's
  uptime spans it), weewx crash (zero `CRITICAL`), graceful stop (no shutdown markers, so SIGKILL),
  the restart policy (`RestartCount: 0`, `Created` predates it — stopped-and-started, never
  recreated), the monitor (it observed and emailed; zero action lines), the campaign harness, and a
  USB reset. What remains is a deliberate external kill+start. Written up in `BACKLOG.md` so the
  elimination is not re-walked. Prod healthy since: 70–78% reception, no alerts.
- **Found while investigating it: Campaign B's two DSM scheduled tasks are still firing**, three days
  after it closed — `tick`/`guard` passes every few minutes, churning lock contention. State is
  `BASELINE`, so nothing is at risk, but "nothing further scheduled" was only ever true of the
  campaign, never of the scheduler. Owner action; they are visible only in the DSM UI. Also the
  leading hypothesis for the restart above.
- **Backlogged, not built: off-site backup is a mirror, not versioned** (ops#209 — the DS918+ runs
  Cloud Sync, so deletes and corruption propagate). The live config and the archive database have no
  versioned copy anywhere, and the eight `.bak-*` archive copies share a volume with the thing they
  guard. Owner's call: address it *after* the migration onto `marvin`, since the design should target
  the destination host rather than the one being left.
- Housekeeping: ops#203 closed with a comment (verified by GET); ops#213's marvin ssh changes checked
  against this repo and confirmed a no-op — no runbook, no cockpit reference, no password-auth
  assumption anywhere.

---
## [S103] — 2026-08-26 — Gain / receive-window hot swap built (DEC-0117): a validated control file, plus the post-swap watchdog grace that keeps it from tearing the driver down

- **Picked up the last open `BACKLOG.md` idea / [ops#179], filed at S89 and deliberately unstarted
  until Campaign B closed.** S89's analysis held up on re-inspection: nothing prevented a hot swap
  but the trigger. `gain` and `-ex` are startup-only CLI flags on the Go binary, `rtldavis.py` never
  inspects them, `ProcManager.startup(cmd, …)` already takes the command as a parameter, and the
  150 s watchdog exercises that kill→respawn cycle routinely.
- **Built as a watched control file carrying bounds-checked integers only — never a command string.**
  `hotswap_control_file` (unset = feature off, stock behavior). The driver polls it about every 10 s
  at the top of `genLoopPackets` — no thread, no signal handler, since `get_stderr()` already budgets
  10 s per pass — and on an mtime change validates, splices into the running command, and respawns.
  Only `gain` (0–496) and `ex` (0–1000) are accepted: `cmd` reaches `shlex.split()` → `Popen`, so a
  raw-command channel would be arbitrary code execution inside the container for anything able to
  write that NAS path. Tests pin that rejection explicitly.
- **The hazard S89's note missed, and the reason this needed design work:** `time_last_received` is a
  **local** in `genLoopPackets` and is *not* reset by a child respawn, while a fresh child is
  legitimately silent for the US 133 s radio init period. A naive `shutdown()`→`startup()` inherits a
  stale timer, trips the 150 s stall watchdog mid-init and tears the driver down — reintroducing the
  abort-on-unhealthy-swap failure class the feature exists to retire, on *every* swap. Every swap now
  resets the four watchdog counters and widens the threshold to `HOTSWAP_GRACE_S = 240` until the
  first packet (a flat 150 s left only 17 s of margin over that init period), reverting as soon as
  anything is received.
- **Also: rollback** to the last known-good command if the new one fails to start (a bad gain must
  not cost us the receiver), **an atomic ack file** recording status and the measured respawn gap —
  which self-measures ops#179's constraint 4, the never-measured RTL-SDR re-open time — and the
  control file **honored at init before the first spawn**, so a container restart cannot silently
  revert a swapped gain while the ack still advertises it (DEC-0116's exact shape).
- **Green gate: 428 passed / 8 skipped** (26 new), ruff clean, mypy clean (65 files), secret gate
  clean. The three loop-level tests are **mutation-verified** — removing the grace, the reset, or the
  rollback each turns the suite red — with a positive control proving the same silence *without* a
  swap still stalls at 150 s. One secret-scanner false positive fixed at source by renaming a local
  (`key = …`) rather than widening the allow-list.
- **Not in prod.** `rtldavis.py` is a **BAKED** file, so this ships only with an image rebuild, and
  the feature is off until the config key is set. `ops/rx_experiment.sh` still swaps arms by
  rewriting the mounted config and restarting — converting it is a separate change, and the one that
  must not land mid-campaign.

---
*(S73–S102 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
