# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S106] — 2026-08-29 — ops#183's Influx outage remediated and fully backfilled (DEC-0119); weewx_monitor.py's alerter found blind since the marvin cutover

- **weewx's InfluxDB uploads were down 00:14→12:08:27 ET (~11h54m).** Root cause was `eaglehunt-ops`
  deleting an InfluxDB token it didn't know `influx.py` also wrote with — weewx's own `weewx.conf`
  was never at fault, confirmed unchanged since 08-23. Fixed with a new dedicated, never-shared write
  token, installed and verified by a marvin-side session (this repo has no path to edit that file
  directly). Full narrative: DEC-0119, `eaglehunt-ops`#183/`OPS-DEC-0162`.
- **The entire outage window is backfilled** — 712 archive records posted, 0 errors, via
  `ops/backfill_influx.py`, run against the live production archive from inside the marvin container.
- **`ops/backfill_influx.py` had two real bugs, found running it live for the first time** (PR #282):
  a committed `INFLUX_ORG` placeholder that would have failed every POST, and a read-write
  `sqlite3.connect()` that fails against a read-only export. Fixed, plus hardening:
  `--server-url`/`--db-path` overrides and `$INFLUX_TOKEN`/`$INFLUX_ORG` env-var sourcing so a
  credential never has to be a CLI literal.
- **`weewx_monitor.py` sent ~14h of false "STILL DOWN" alerts** — it watches a hardcoded Foundation
  log path the marvin NFS overlay doesn't cover (`weewx-data/` is live-mirrored, `logs/` is not), so
  it froze at cutover and alerted on the age of a dead file, not station health. The false alerts'
  outage-shaped noise is part of why the real Influx outage went unnoticed until mid-morning.
  Disabled on Foundation; no marvin-side replacement exists yet. A second stale watcher
  (`usb_watchdog.sh`) found in the same sweep, filed on `eaglehunt-ops`#233.
- **All twelve publish legs verified independently healthy** (WU, PWSWeather, CWOP, AWEKAS, WOW,
  WeatherCloud, OWM, Windy, Influx, Ogoxe) via the newly-live `marvin-weewx` `marvinctl` alias — this
  repo's own session's first real use of that access.

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
---
*(S73–S103 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
