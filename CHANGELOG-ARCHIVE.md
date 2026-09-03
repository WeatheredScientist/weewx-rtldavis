# Changelog Archive — weewx-rtldavis

**Append-only archive · read on demand (DEC-0030).** Older session entries moved here **verbatim**
from `CHANGELOG.md`, which keeps only the last ~3 sessions live (the Tier 1 session read). Same
format: most recent first, session-tagged (`[S16]`, `[S17]`, …), release tags called out inline.
Nothing here is rewritten — text moves, history stays greppable.

---

## [S111] — 2026-08-31 — Campaign C's real verdict: 496 does not clear the adoption bar at marvin; 372 holds (DEC-0125)

- **ops#235 fixed mid-session (ops-side): `marvinctl exec-ro`'s missing `-i` flag was closing
  container stdin.** Verified end-to-end with the exact read DEC-0124 left blocked: a read-only
  `sqlite3` query piped through `exec-ro` against the live, mode-`0500` archive DB returned 1333
  clean rows, exit 0. Confirmed on ops#235.
- **Ran DEC-0069's own `campaign_analyze.py` logic (unmodified) against the real per-minute data.**
  Result: **A (372) 72.82% (n=368) vs B (496) 73.98% (n=350), B +1.16 pts — under DEC-0059's 2.0-pt
  adoption bar**, smaller than DEC-0124's coarse 5-min proxy (+1.87 pts), not larger.
- **Verdict logged as DEC-0125: 496 does not clear the bar at marvin's RF position — gain holds at
  372, no config change.** Per `BACKLOG.md`'s S107 pre-commitment, this is a standalone finding
  that Foundation's DEC-0115 answer doesn't transfer to marvin's site, not a reversal of DEC-0115.
  Also verifies `BOOT.md` job 4 (archive DB opens `mode=ro` cleanly under `journal_mode=DELETE`).
- **Reconciled:** `CONSTANTS.md`'s gain row/hardware-site prose/timeline, `docs/ROADMAP.md`'s
  Campaign B/C item (now closed as a marvin result too), `BACKLOG.md`'s gain re-sweep item (closed).
- **Fixed two stale claims `BOOT.md` was carrying from ops#233.** The restart-grant question is
  resolved (MARVIN-DEC-0099: the grant already exists, corrected upstream mid-Campaign-C — this
  file was still quoting the earlier "no grant exists" finding), and `usb_watchdog.sh`'s fate is
  decided (retiring, MARVIN-DEC-0100), not still open.
- **Campaign D pre-registered and shipped (DEC-0126): a marvin-site gain pilot, launching
  2026-08-31T21:00 ET.** Six gain-only blocks HIGH→LOW — 496, 449, 402, 372, 328, 207 — reusing
  Foundation's original pilot points plus 207 (dropped from campaign C on a Foundation-only
  judgment DEC-0125 just showed doesn't transfer). Arm-selection input only, never adoption
  evidence. `arm_cmd()` gains `P207`; `SCHEDULE=` populated; `campaign_analyze.py`'s `LEGENDS`
  gains `"D"`; `tests/test_rx_experiment.py` gains `_require_campaign_d()` + 3 structural tests,
  and `_require_campaign_b()`'s over-broad gate ("any P* row") is corrected to require the H hold
  specifically — the old gate would have misfired campaign B's assertions against campaign D's
  pilot-only shape. Full suite green (465 passed / 9 skipped).
- **Campaign D deployed and armed live on marvin, same session.** `rx_experiment.sh` shipped and
  hash-verified, Campaign C's stale baseline snapshot archived to `.campaignC` (was blocking
  `install`), `install` succeeded (fresh baseline snapshotted, schedule armed), `logs/campaign.inhibit`
  set, monitor confirmed healthy. No further action needed for the 21:00 ET launch. Also caught and
  reverted a wrong turn: attempted wiring `marvinctl pull`-based deploy for weewx before finding
  marvin's own MARVIN-DEC-0079, which already tried and rejected that design for this tenant (the
  on-disk layout doesn't match this repo's structure — deploy stays flat/scp, deliberately).

---

## [S110] — 2026-08-31 — Campaign C completed clean; the 372-vs-496 verdict is blocked on ops#235 (DEC-0124), now flagged a priority

- **Campaign C ran its full 10-row schedule clean, no aborts, self-terminated to `BASELINE` at
  exactly 11:00:00 ET** — confirmed against the actual deployed script on marvin, not assumed from
  the design doc. `weewx.service` healthy on gain 372 since the restore.
- **The 372-vs-496 verdict is NOT decided (DEC-0124).** A coarse proxy (monitor's 5-min aggregate,
  not the sanctioned metric) leans toward 496 (+1.87 pts, n=76/70) but sits under DEC-0059's
  2.0-pt bar and is explicitly not the call — DEC-0069 exists because that coarse metric absorbs
  freeze-contamination bias. The real per-minute readout needs marvin-side archive-DB access that
  doesn't exist: `ops/campaign_analyze.py` is NAS-only, and `marvinctl` has no SQL verb
  ([ops#235](https://github.com/WeatheredScientist/eaglehunt-ops/issues/235), filed weewx S107).
- **`marvinctl exec-ro` tested as a workaround and confirmed non-functional**, with a positive
  control: the stdin-pipe idiom forwards nothing, and the `-c` argv path rejects quotes/parens
  even at zero literal whitespace, so no real code can be passed through it either way. Findings
  added to ops#235 rather than filing a duplicate. **ops#235 is now flagged a priority** — it
  blocks a live RF-gain decision, not a convenience read.
- **`ops/rx_experiment.sh`'s `SCHEDULE=` stood down to the empty form (DEC-0096)** now that the
  terminator has passed — the staleness guard test was correctly red until this landed. Full suite
  green after: 457 passed / 14 skipped (structural schedule tests correctly self-skip against an
  empty schedule).

## [S108] — 2026-08-30 — Campaign C launches tonight instead of tomorrow (DEC-0122); a missing marvin scheduler found and fixed mid-campaign (DEC-0123)

- **Campaign C launched 2026-08-30T20:00, a day earlier than DEC-0121's pre-registered 08-31**
  (DEC-0122). The reason to wait — letting the freshly-deployed monitor prove itself across a
  log-rotation boundary before trusting it as the abort tripwire — turned out to be moot: marvin has
  no logrotate configured for `weewx.log` at all. Owner's call, with a fresh hands-off-the-guest
  declaration for tonight's window (PR #290, MARVIN-DEC-0088). `SCHEDULE=` shifted by a pure −1
  calendar day; blocks, clock times, and the `A B B A B A A B A B` order are all unchanged, so
  DEC-0121's notch balance is untouched.
- **Discovered live, mid-campaign: nothing was advancing the schedule or checking the abort
  condition.** DEC-0118's move to marvin never carried over Foundation's DSM cron that drove
  `ops/rx_experiment.sh tick`/`guard` every 5 min. Block 1 sat un-advanced after its manual launch,
  and `guard` — the campaign's only abort-on-bad-reception check — never ran. New
  `ops/weewx-rx-experiment.service`+`.timer` (root, marvin-pinned env, PR #292 — DEC-0123) shipped
  and was installed on marvin the same night; confirmed firing since 22:18:16 ET, having self-healed
  the overdue block 1→2 swap on its first pass.
- **This session's own closeout ritual did not run** — landed via 3 merged PRs (#290/#291/#292) with
  no `BOOT.md` rewrite, no CHANGELOG entry, no DEC rows. **Completed retroactively by S109**, which
  also confirmed (via live marvin/ops sessions) that two risks flagged after the fact — the unrotated
  `weewx.log`'s growth rate and marvin's new second tenant (`t-hlf`, ops#234) — are both clear for
  tonight's run; only the unrelated Gmail SMTP failure (reception-summary alerting, needs the owner's
  Google account access) remains open. No code changed in S109 — docs and decision records only.

## [S107] — 2026-08-30 — Alerting rebuilt for marvin (DEC-0120): input staleness becomes its own state, the USB remedy stops being assumed; today's gain campaign refused on power grounds

- **`weewx_monitor.py`'s 14 h of false alerts were a structural defect, not a wrong path (DEC-0120,
  answers [ops#233]).** Every threshold in the file is "nothing seen for N seconds", and a frozen
  input satisfies all of them at once — so it could not distinguish *the station is down* from *I am
  blind*. Repointing the path would have fixed the instance and left the mechanism. Blindness is now
  checked **before** any threshold, on the worse of the log's mtime and the newest parsed line's
  timestamp, raised as a **distinct alert class**, and it suspends uploader/reception judgement while
  it holds.
- **ops#233's premise corrected: marvin's `logs/weewx.log` is alive, local and healthy** — growing
  continuously, rotating daily. The "no path to the log" problem exists only when looking from
  Foundation; on marvin the service-alerting and reception halves port on an environment variable.
- **The USB unbind/rebind is no longer assumed — `REMEDY_MODE` selects it.** `usb_reset` stays the
  DEFAULT (this is a published extension; our zero-efficacy evidence across ~17 events is from our
  hardware), `restart_unit` is marvin's (a `weewx.service` restart IS a full container recreate —
  `docker run --rm` + `ExecStartPre=docker rm -f` — the remedy that resolved ERR-0005), `none` is
  detect-and-escalate. The Foundation body is deliberately **not** ported: it unbinds a hardcoded
  Synology bus path, and marvin's controller roles differ (`MARVIN-DEC-0051`), so on a two-tenant box
  it would no-op or reset someone else's device.
- **Campaign inhibit added** — a campaign restarts weewx once per arm, and a remedy landing mid-arm
  corrupts the block being measured. Action is suppressed; detection and alerting are not, and the
  skip logs the action it *would* have taken.
- **New `ops/weewx-monitor.service`**, shipping at `REMEDY_MODE=none`. **Nothing deployed this
  session** — tonight's campaign restarts weewx per arm, so a monitor landing first would fight it.
- **Today's requested 4-hour gain campaign was refused on the repo's own power math.** DEC-0059
  measured 24 h/arm resolving 1.1 points; a 4 h window splits to ~2 h/arm, giving a minimum
  detectable effect of **~3.8 points against a 2.0-point effect of interest** — ~3.6× too short, and
  it would have returned "no difference" nearly regardless of truth. Confirmed two independent ways.
  A properly-powered 2-arm run needs ~15 h. Owner's call: overnight instead.
- **The replacement campaign is pre-registered before any data exists** (`BACKLOG.md`): 2 arms
  (372 vs 496 — 207 dropped as known-worst and barely separable), 15 h, 90-min blocks, 5 per arm,
  order `A B B A B A A B B A` balanced so the ~2-pt hour-07 notch lands on both arms, exit trap,
  abort floor, and a pre-committed reading of both outcomes.
- **Power re-checked against marvin's OWN measured noise rather than Foundation's inherited figure.**
  ~15 h of post-bind gain-372 telemetry already in the archive gave 21 full 40-min blocks with
  `NULL_COUNT` 0: **block sd 1.403 pts at 40 min → 0.936 at 90 min, 0.84× the sd implied by
  DEC-0059** — marvin is quieter, so the 15 h design clears the 2.0-pt bar at **MDE ~1.66** rather
  than scraping it.
- **A prior recorded before the run, precisely so it cannot be back-fitted after:** marvin at gain
  372 already measures **73.88%**, within ~0.95 pts of Foundation at 496 (74.83) and ~1.05 above
  Foundation at 372 (72.83). Uncontrolled cross-environment comparison, so a prior and not a result
  — but 496 repeating its 2.00-pt win at the new position is not the safe assumption.
- **Incidental: zero gaps in ~15 h**, against the freeze blocker's NAS-era 1.31/day (~0.8 expected).
  First post-migration data point on that blocker. Flagged, not concluded.
- **Found, not fixed:** prod is running **gain 372 while DEC-0115 adopted 496** — the 08-29 migration
  incident set it without a controlled comparison and the aborted campaign's exit trap codified it.
  Owner's call: hold 372 until measured. Also, marvin's `weewx_monitor.py` is **stale against `dev`**
  (the [ops#214] silent-drift family), and `BOOT.md`'s job 5 (`debug_rtld` 3→2) is stale — live
  config is already at 1.

- **The campaign apparatus learned marvin, and now refuses to run without its safety net (DEC-0121).**
  `ops/rx_experiment.sh` rewrites the live config and restarts prod unattended overnight. Against the
  new host four things were wrong and **three failed silently**: the docker path was hardcoded; the
  restart mechanism would have taken **prod down** (`docker kill`+`start` against a `docker run --rm`
  unit — the kill destroys the container and the start has nothing to start); the abort tripwire had
  **no input** (it reads `weewx_monitor.log`, which nothing writes on marvin, so the campaign would
  never abort however bad reception got); and a pre-migration baseline snapshot sits there latent.
  New `preflight` mode gates `install`, demands a *fresh* monitor log, and has **no `--force`**.
- **`RX_RESTART_MODE`** selects `docker` (NAS, unchanged default) or `systemd` (marvin, where a unit
  restart is also a full container recreate). Existing NAS installs are untouched by the edit.
- **The pre-registered block order was wrong, and laying it against a clock is what caught it.** The
  morning notch is not one hour but **hours 07–09 at 2–3.5 pts down** — larger than the 2.0-pt effect
  — and the first order put blocks 8 and 9 both on B, loading **1.67 of 2.0 notch block-equivalents
  onto gain 496**, the arm expected to win. It would have manufactured a false negative. Balancing a
  linear trend is not balancing a localized dip. The shipped order splits notch exposure **1.00/1.00**
  with drift still 27/28 — both balances at once.
- **Campaign C's schedule is live in `SCHEDULE=`** (2026-08-31T20:00 → 09-01T11:00, 10 × 90-min
  blocks, self-terminating to BASELINE) and **machine-checked with a positive control** asserting the
  old order still reads lopsided. Campaign B's structural tests are **guarded, not deleted** — the
  block rotates between campaigns.
- **Ordering corrected: the monitor deploys BEFORE the campaign**, not after. It *is* the abort
  tripwire's input. The earlier "deploy after" reasoning (avoiding per-arm restart fights) is already
  handled by the campaign inhibit.

[ops#233]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/233
[ops#214]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/214

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

## [S102] — 2026-08-25 — Ops-tracker verification sweep: #144/#172/#204 checked live (not memory), two didn't hold up; `loop_json_writer.py`'s stale mount found and fixed (DEC-0116)

- **An `eaglehunt-ops` session asked to confirm four post-v2.0.14 items were live and close whichever
  were done: ops#179, #144, #172, #204.** Checked each against the running container directly instead
  of trusting the ship announcement. ops#179 matched ops's own description (still unstarted,
  untouched). #144 held up and closed clean: `fetch_interval=300` confirmed live via `readconf --nas`,
  the triple-field null fix baked into the running image, owner's item-1 decision already final.
- **#172 and #204 did NOT hold up — DEC-0116.** Both features live in `loop_json_writer.py`, a
  **mounted** file per `CONSTANTS.md`'s deploy-layers table. The deployed copy was still the
  2026-07-27 version: hash mismatched `dev`, missing both `current_interval` and
  `barometer_fetch_epoch` entirely, confirmed by a live `current.json` read with the field absent and
  `current.json`/`loop-data.txt` sharing an identical mtime (per-packet writes, not throttled). Same
  deploy-layer trap DEC-0114 caught for `influx.py` three days earlier, just outside that event's own
  verification scope — `dev` and prod were **not** actually in sync as `BOOT.md`'s S101 close claimed,
  for this one file.
- **Fixed live, with the owner's explicit go-ahead:** deployed current `dev`'s `loop_json_writer.py`
  to its NAS mount source, hash-verified the match, `docker kill` + `docker start` (DEC-0008). Confirmed
  post-restart: `barometer_fetch_epoch` appeared on the first WeatherLink poll, and `current.json`'s
  60s throttle is now measurably active (mtimes diverge from `loop-data.txt`'s per-packet writes).
  #172/#204 closed with the live evidence in the closing comments. Ops looped throughout via direct
  session-to-session messages, including the correction on the two claims that didn't hold up.
- **Lesson for next time (DEC-0116):** an image bump proves the baked layer moved; it says nothing
  about any mounted file not specifically re-verified that session. The deploy-layers table's other
  mounted files (`ogoxeUploader.py`, `sortedcontainers`, `weewx.conf`) remain independently unverified.
- **Gates:** 402/402 (8 skipped, unchanged — no code touched this session), ruff clean, mypy clean
  (64 files, `.mypy_cache` cleared first), secret gate clean.

---
## [S101] — 2026-08-23 — v2.0.14 ships (weewx 5.5, NAS-LEASE adoption); Campaign B closes, gain 496 adopted

- **Merged S100's closeout PR (#273), then ran the ~08-23 v2.0.14 build event.** Campaign B
  self-terminated on schedule (`BASELINE`, 2026-08-23T00:05); built natively on the NAS from
  `origin/dev`@`efeeebd` under `ops/nas_build.py`'s NAS-LEASE holder wrapper. Ships DEC-0110
  (reception-quality wind guard), DEC-0111 (`influx.py` NAS-LEASE courtesy yield), #233, #224, and
  weewx 5.4.0 → 5.5.0 (pinned since S88, `ca3c024` — this is the first release to actually carry
  it, since `dev` has been running ahead of prod).
- **Three real problems found and fixed live during the deploy, not glossed over:**
  1. `docker` wasn't on the non-interactive SSH PATH — first build attempt crashed instantly
     (`FileNotFoundError: docker`); fixed by passing the full `/usr/local/bin/docker` path.
  2. A retried build genuinely hung 70+ minutes at 0:00 accumulated CPU on a `weectl`
     syslog-handler crash mid-Step 7/30 (verified via `ps aux`, not inferred from log silence) —
     killed on owner instruction, stale lease cleared, log rotated, retried clean in ~360s.
  3. `influx.py`'s DEC-0111 code never reached the running container despite a fresh image —
     it's a MOUNTED file, so the image rebuild didn't touch the NAS-side mount source, which still
     held the old `ws.1` code. Caught by checking the live version banner post-deploy (not assumed
     from a clean-looking recreate); fixed via a separate `scp` + restart, checksum-verified.
- **DEC-0114: NAS-LEASE adoption locks** (the §5 event DEC-0104/DEC-0107 deferred).
  `RENEWAL_FLOOR_S` re-pinned 600 → 420 against tonight's real measured build duration; `TTL_S`
  held deliberately generous at 3600 given the hour-plus hang above was a real, non-capacity
  failure mode. Also added `LEASE_DIR` mount (`-v /volume1/docker/nas-lease:/nas-lease:ro`) and
  `weewx.conf`'s `[[Influx]] lease_dir = /nas-lease`.
- **Live NAS-LEASE contention with `hyperlocal-forecast` resolved via direct session-to-session
  coordination** — a new standing SOP this session (message the other repo's live Claude session
  directly for time-sensitive shared-resource questions, always loop `eaglehunt-ops` too, not just
  on decisions needing sign-off). HLF found and killed a concurrent lease-unaware manual job of
  their own, then their own stuck `daily-maintenance` run, after an owner priority call
  (`OPS-DEC-0136`). Verified independently at each step, not taken on report.
- **DEC-0113 applied live**: `[DavisPressure] fetch_interval` 3600 → 300, verified.
- **DEC-0115: Campaign B closes, gain 496 (arm B) adopted as the new RF baseline.** Clean 32/32-block
  final square (2026-08-15 → 08-23, after excluding 6 pooled aborted/restarted attempts the
  analysis tool's own default run would otherwise have mixed in): **A (372/ex0, incumbent) 72.83% ·
  B (496/ex0) 74.83% (+2.00) · C (372/ex50) 73.28% (+0.45) · D (496/ex50) 74.77% (+1.94)**. Gain
  axis clearly favors 496; extraction axis a wash. The margin is exactly at DEC-0059's 2.0-point
  adoption bar, not comfortably above it — adopted anyway given the consistent direction across
  both the interim and final readouts. A narrower follow-up sweep near 496 considered and declined
  for now (pilot data suggests a flat curve there). Deployed to both live `weewx.conf` and
  `weewx.conf.rx-baseline` (a live-only edit would be silently wiped by the next campaign's own
  restore path). `ops/rx_experiment.sh`'s `SCHEDULE=` block emptied per its own stand-down
  convention (DEC-0096) now that the campaign is complete.
- Post-deploy verification: driver banner unchanged at `0.20+ws.5`, `influx.py` now `0.20+ws.2`,
  no new CRITICAL/ERROR since restart, `weewxd` on 5.5.0.
- **`CONSTANTS.md`, `docs/DECISIONS.md`/`DECISIONS-FULL.md`, `docs/ROADMAP.md` updated same
  session** — release/rollback table, live-config-deviations table (3 new/updated rows), hardware
  timeline, reception baseline figure (73.3%/gain-372 → 74.83%/gain-496), Campaign B roadmap item
  closed.

---
## [S100] — 2026-08-22 — Verification-only session: clean pickup confirmed, Campaign B on track, new GOTCHAS entry for `rx_experiment.sh`'s local-run trap

- **No code shipped this session** — a status-check pickup, not a coding session. Clean-pickup gate
  ran clean: `dev` up to date with origin, working tree clean, 410/410 (unchanged from S99, no
  regressions).
- **Daily square watch (BOOT job 2, deferred at S99) run for real.** `ops/soak_check.sh`: 17 pass /
  2 warn / 0 fail, same two known warns (chatty stdout #253, USB hedge during RF-dead) — matches
  S98's last-known figure exactly, no drift.
- **Caught `ops/rx_experiment.sh status` giving a false-empty read when run from a local checkout**
  (`arm: NONE` since epoch, `installed: no`, `samples: 0` — looks exactly like "campaign
  self-terminated," which would have wrongly cleared job 1's precondition). The script has no `ssh`
  calls of its own and only resolves real state when it's actually running on the NAS. Verified the
  real state directly with `nasctl cat` on `rx_experiment.state`: Campaign B is genuinely still
  live, **arm D**, last swap **2026-08-22 00:07:25** — on schedule for its **08-23T00:05**
  self-termination. Documented the trap in `docs/GOTCHAS.md` §3 so the next session (or anyone else
  running this script) doesn't have to rediscover it.
- **Owner asked whether `eaglehunt-ops#180` needed an update.** Verified live via `gh issue view`:
  already closed at S99 with an accurate closing comment (remediation code-complete, only the
  v2.0.14 deploy gate remains, already tracked here) — nothing had changed since, so no new comment
  was needed.
- **Gates:** ruff clean, **410/410** (unchanged — no code touched), mypy clean (64 files,
  `.mypy_cache` cleared first), secret gate clean.
- Model tier: ran on Sonnet 5 throughout, confirmed directly rather than inferred — no restore owed.

---
## [S99] — 2026-08-22 — Ops-tracker close-out sweep: 5 issues closed, #233/#252 fixed and shipped, #144 resolved (DEC-0113)

- **Opened on a stale handoff and closed it first.** `BOOT.md`'s resume header still read "S98 →
  S99" and its footer "S98 close" despite two PRs (#269, #270) already merged under S99 branch
  names — an earlier S99 instance had deliberately held off on its own closeout after
  `eaglehunt-ops#195` flagged a possibly-concurrent session. Confirmed no other weewx session was
  active (this session's own `ListAgents`) and both loose ends that issue named — a stray remote
  branch, a stale detached-HEAD worktree — were already gone. Closed `eaglehunt-ops#195` with that
  confirmation.
- **`eaglehunt-ops#180` (the S91 audit heads-up) closed: all 8 remediation issues (#219–226) are
  confirmed closed**, `#227`'s sequencing plan fully executed. Only the deploy gate (the ~08-23
  v2.0.14 image) remains, already tracked here.
- **`#233` fixed: `ProcManager.shutdown()` now kills its own Popen handle directly**, belt-and-braces
  alongside the existing `pidof` name-match sweep, which had no fallback if it ever missed a
  still-live child. Regression test reproduces the exact gap (pidof matches nothing, child genuinely
  still alive) with a positive control. Baked file — ships to prod with the v2.0.14 image.
- **`#252` fixed: `ops/soak_check.sh`'s window computation and restart-loop detector now share one
  `$LY+$L` read** (yesterday's rotated log + today's), replacing the window cut's silent
  `ln=1`-widens-to-the-whole-file fallback when a container start predates midnight — the exact
  false-WARN shape the issue reported (driver-identity canary silently unverified, among others).
  Two new tests extract and run the real deployed bash block against synthetic logs, since the
  existing suite stubs `ssh` entirely and never exercised this layer. Not baked — a repo script, live
  the moment it's on `dev`. Both landed together in PR #271 (merged, `071f684`).
- **`#144` fully resolved (DEC-0113).** Item 2 (triple-field bug) was already fixed pre-session
  (S82b). Item 3 (hourly `fetch_interval`): checked WeatherLink v2's actual documented ceiling
  (1,000 calls/hour + 10/s) rather than the original guess ("what I thought the free tier allowed");
  300s uses ~1.2% of it and cuts the archived barometer from a 60-min staircase to a 5-min one.
  Queued as a live `weewx.conf` edit (confirmed via `nasctl conf` as the winning MOUNTED layer),
  held to the same v2.0.14 restart as everything else behind Campaign B's comparability discipline —
  new rows in `CONSTANTS.md`'s deviations table and this file's job list. Item 1 (the ~0.03 inHg
  console-vs-METAR offset): put to the owner directly, who confirmed the console's elevation-based
  correction is working as designed for the surveyed 550 ft (the DEC-0086 mechanism, not in
  question); closed with no change, the residual already absorbed downstream by HLF's per-source
  correction. Issue stays open pending the v2.0.14 deploy, same pattern as `#172`/`#204`/`#253`.
- **The ~08-23 v2.0.14 build is now a seven-purpose event**: `#224`, DEC-0110, DEC-0111, `#233`
  (all baked), plus DEC-0113's live `fetch_interval` edit — `#252` needs no deploy step at all.
- **Also closed: `#239`**, a stale, fully-contained InfluxDB-gap courtesy notice with nothing
  pending.
- **Gates:** 410/410 full suite (was 397, +13, 0 regressions), ruff clean, mypy clean (64 files,
  `.mypy_cache` cleared first), secret gate clean, positive-controlled throughout. PR #271 merged;
  branch cleaned up (local + remote), steady state verified after.

---

## [S98] — 2026-08-20 — Phantom 37 mph gust diagnosed and corrected (ERR-0006); reception-quality wind guard ships (DEC-0110); P0.5's last follow-on retired (DEC-0109)

- **Owner-reported phantom 37 mph gust at 11:12 EDT, diagnosed to source and corrected (ERR-0006).**
  Same class as `ERR-0004` (2026-07-27), recurring independently: `rxCheckPercent` for that one
  archive minute collapsed to 9.2% (vs. 60–90%+ every surrounding minute), a genuine RF-dead
  episode (weewx.log silent 11:11:35→11:15:22, confirmed not a restart). One of the few packets
  that passed CRC that minute carried a corrupted wind byte; every other field in the row read
  normally, so nothing tripped DEC-0054's frame co-rejection. Investigated and ruled out `#225`
  item 2 (rain-rate co-rejection gap, fixed same day in PR #260 but not yet deployed) as the
  mechanism here — rainRate was clean. Archive row nulled + daily summary rebuilt (day-max now 19
  mph, genuine); InfluxDB point deleted and rewritten minus the 7 wind-derived fields, with
  `windGust_qc=1`/`windSpeed_qc=1` flags (24 fields verified, matching `ERR-0004`'s own precedent
  exactly) — the dashboard's read-only proxy token can't write/delete (confirmed 403), so the
  correction used `weewx.conf`'s own uploader token instead. Wunderground/CWOP/PWSWeather/OWM/etc.
  already have the bad value; that's permanent, same as `ERR-0004`. Cross-verified independently by
  an eaglehunt-weather-dashboard session (InfluxDB via its own query path) and an eaglehunt-ops
  session (raised `#225` item 2 and a container-restart confound as candidate mechanisms; both
  checked directly and ruled out for this incident) — good example of the coordination working.
- **Reception-quality wind guard ships, closing the ERR-0004/ERR-0006 blind spot (DEC-0110).**
  Neither the bounds check nor the 75 mph delta cap can distinguish this corruption from a genuine
  squall gust of similar magnitude — `ERR-0004`'s own writeup already established that tightening
  either risks false-rejecting real weather. Measured first, before designing anything (93 days,
  129,607 records): genuine high wind and severe reception collapse have never co-occurred at this
  station (lowest `rxCheckPercent` among 220 records with `windGust>=10mph`: 54.5%; 87 of 89
  `rxCheckPercent<20%` records stayed calm at 0–4 mph) — so a guard combining both signals can't
  false-null a real gust, with wide margins on both sides. `dewpoint_service.py`'s `DewpointCacher`
  gains a `NEW_ARCHIVE_RECORD` binding (`rxCheckPercent<20%` AND `windGust>10mph` → null the wind
  triple + derived fields), confirmed via `weewx.conf`'s own `[Engine][Services]` order to run
  before `StdArchive`'s write and every RESTful uploader. Explicitly does not reach Wunderground's
  RapidFire feed (publishes pre-archive-close — a live ticker, not an archive of record). 11 new
  tests including both incidents replayed verbatim as positive controls. Ships with the ~08-23
  v2.0.14 build (baked into the image), same gate as `#225`.
- **ROADMAP.md's P0.5 fully closed (DEC-0109).** Its last follow-on ("Keep-a-Changelog headings +
  DECISIONS entry-skeleton convergence," proposed S25, ~72 sessions unclaimed) is retired, not
  picked up: the original rationale is unrecoverable (no surviving transcript), no sibling repo
  adopted anything to converge toward (checked all three), and `DECISIONS-FULL.md` already grew
  its own working skeleton independently of `CHANGELOG.md` — nothing left to reconcile. Judgment
  call, not just absence of evidence: this repo's entries are dense, cross-referencing narratives
  that an external single-facet schema would likely fragment rather than clarify.
- **A `ROADMAP.md` overclaim caught while closing the loop on the above.** Its P1 arc credited
  DEC-0054 with "closing ERR-0004" outright — true only for the co-occurring-bounds-failure
  mechanism, not the whole class, which `ERR-0006` just proved recurs independently. Corrected in
  place rather than left standing.
- **Cross-repo, same session:** fixed a `secret-read-guard.sh` false-positive gotcha in
  eaglehunt-ops (`command` escape-hatch anchoring + a co-occurrence false-positive class), found
  and flagged via `spawn_task` while doing unrelated ops work; landed there as OPS-DEC-0115, tested
  and deployed.
- **Gates:** 397/397 full suite (was 386, +11 new, 0 regressions), ruff clean, mypy clean (63
  files, `.mypy_cache` cleared first), secret gate clean. PR #265 merged to `dev`.

---

## [S97] — 2026-08-20 — S91 audit fully closed (#225/#226); NAS-LEASE holder client built + verified (DEC-0108); INTERFACES.md's two DEC-0053 gaps actually documented

- **The S91 audit's 8-issue sequence (#219–226) is now fully closed.** #225 (5 QC-completeness
  findings, all dormant on this station's single-ISS config) and #226 (4 public-facing CLI/config
  bugs) were the last two, both shipped this session (PRs #258, #260); #219–224 had already landed
  in prior sessions. Tracking issue #227 closed with the full sequence noted. #226 item 1 is the
  standout for impact beyond this station: the shipped config template carried a literal,
  unsubstituted `[options]` token that any new user following the documented setup shipped straight
  into `weewx.conf`, silently discarding the auto-appended `-tf`/`-tr` flags and falling back to
  868MHz EU instead of 915MHz US with zero error. 23 new regression tests across the two PRs.
- **`ops/nas_build.py` — weewx's NAS-LEASE holder client — built, tested, and verified against the
  real NAS, ahead of the ~08-23 build (DEC-0108).** A generic lease-wrapper (`--job <name> --
  <command>`): `O_CREAT|O_EXCL` acquire, explicit `fchmod 0644` (the exact umask near-miss
  `NAS-LEASE.md` v1.4 documents and DEC-0107 found on the box), `flock` held for the wrapped
  command's run, stale-break only when flock is free **and** `expires_at` has passed, release with a
  truthful outcome (`clean`/`build-failed`/`crashed`) wrapped in `try/finally`. Generic over any
  command so it covers both of weewx's named holder cases (image build, manual bulk analysis) from
  one script. **Scope decision, recorded in DEC-0108:** the observer/downshift side is deliberately
  not built — weewx has no live downshift lever to act on a "held" verdict yet, so a courtesy read
  with nothing to act on has unclear benefit today; revisit once the InfluxDB `post_interval` lever
  ships. 14 tests against a real `flock()` on a `tmp_path` dir, not mocked. **Later in the session,
  ran it for real** against the actual shared `LEASE_DIR` (a clearly-labeled dry-run job, TTL 60s) —
  clean `acquired`/`released` pair logged, directory left exactly as found, no stray lease file.
  Floor/TTL ship as §5's provisional 600s/3600s, to be re-pinned against the real ~08-23 build's
  measured duration; the adopting DEC itself still waits for that event on purpose.
- **`INTERFACES.md` actually documents both of DEC-0053's open findings now — ROADMAP had been
  overclaiming this since S48.** Tracing ROADMAP's P3 line (which asserted DEC-0053's
  station-identity finding was "documented there") against the actual file found that only Finding 1
  (bound the loop-JSON cache) had made it in. Finding 2 — InfluxDB carries no station-identity tag,
  and adding one later forks a parallel series instead of annotating it — is now written into §2,
  along with a one-line pointer to Finding 3 (the SQLite archive's own missing correction flag,
  deliberately left in `DATA_ERRATA.md` where DEC-0053 always said it belonged). ROADMAP's P3 line
  corrected in the same pass, with the guardrail's own "targeted pass writes both places" rule
  followed this time. PRs #261, #262.
- **Session-start concurrency, resolved cleanly.** A live peer session (`weewx-rtldavis-e4`, S96)
  was still finishing as this session started; coordinated directly rather than duplicating work.
  The peer's handoff corrected an early misreading on this session's part — ops#169's current
  title/body read as an unresolved coffee-radar heads-up, but the actual unresolved thread had
  already closed as DEC-0104/DEC-0107, verified independently against `DECISIONS.md` rather than
  taken on the peer's word alone. Mid-session, coffee-radar (`coffeeradar-28`) cross-checked the
  ~08-23 timeline directly; confirmed, and told them the holder client was now built and verified,
  not just designed.
- **Interim Campaign B readout, informational only — square left running untouched per owner
  instruction.** Using `ops/campaign_analyze.py --since <the live attempt's epoch>` (the raw log
  pools 6 aborted attempts back to 08-11; the tool's own pooling warning caught it): at 22 of 32
  blocks, arm B (gain 496, ex 0) leads arm A (372, anchor) by +2.25 pts, and D leads C by +1.16 pts
  at ex 50 — gain wins both head-to-heads; the ex axis itself reads as a wash (+0.93 pts one way,
  −0.16 the other). Already exceeds campaign A's entire 4-arm spread (0.94 pts). Explicitly not a
  verdict — the runbook's own rule is not to read partial results, and DEC-0102's overnight iowait
  confound is still open.
- **Two secret-read-guard false positives found and worked around, worth a note to ops.** The guard
  blocked a plain `scp` upload of this repo's own already-secret-gated script (never touches
  `weewx.conf`), and separately a `tail` on the NAS-LEASE attribution log (plain JSONL, no
  credentials) — both keyed on the command verb/NAS-host pattern rather than which file is actually
  touched. The documented `command` escape hatch resolved both, but only once `command` was the
  **literal first word** of the whole invocation — `cmd; command scp ...` still triggered it,
  `command bash -c '...scp...'` did not. Flagged via `spawn_task` for ops to fold into the guard's
  own documentation rather than left as a per-session rediscovery.
- **Green gate at close:** ruff clean, **386/386**, mypy clean (62 files), secret gate clean and
  positive-controlled mid-session (planted a fake key, confirmed the catch, restored from a
  pre-mutation backup rather than `git checkout` since the index held the payload). Soak at close:
  17 pass / 2 warn / 0 fail — same two known warns (chatty stdout #253, USB hedge during RF-dead).
- Model tier: ran on Sonnet 5 throughout, confirmed directly rather than inferred — no restore owed.
- Five PRs merged this session: #258 (#226), #259 (DEC-0108), #260 (#225), #261 (INTERFACES.md
  Finding 2), #262 (INTERFACES.md Finding 3). Steady state verified `dev` + `main` only after each.

---
## [S96] — 2026-08-20 — ops#169 closed end-to-end (DEC-0107); #224 unit systems fixed; ROADMAP tripwire fired

- **ops#169 / NAS-LEASE: every open item closed in one session, and all three box-level fixes rest on
  direct observation rather than report.** The round was run session-to-session with coffee-radar
  (their S205) at the owner's direction, with eaglehunt-ops informed throughout. Landed: `chmod 666`
  on `heavy-io.log`, `chmod 0777` on `LEASE_DIR` (sticky dropped), `chattr +a` on the log,
  `NAS-LEASE.md` **v1.4 / OPS-DEC-0110**, and HLF's create-mode patch (their PR #388, `066bbf9f`).
- **The finding that moved it: both weewx lease roles run non-root, and neither is what the other
  tenants assumed.** coffee-radar reasoned the uid gaps were moot for us because our client would run
  as root "like your `rx_experiment` tasks" — those *are* DSM root tasks, but neither is the lease
  client. The observer is `weewx-monitor` (uid 1031, DEC-0009 least-privilege) and the holder is a
  separate non-root account, established from the ownership of every `build-v2.0.*` directory rather
  than inferred. **weewx is the first tenant the gaps actually bite** — HLF and coffee-radar are both
  uid 0, which is exactly why three nights of clean production never surfaced them. Widening the
  monitor's sudo grant to dodge a file mode was considered and **rejected**: it trades a documented
  security decision for a `chmod` someone else can make.
- **`chattr +a` was deliberately not closed on its no-error exit.** That is its normal success
  signature and coffee-radar's reading was reasonable — but **this box is the origin of our
  accepts-and-silently-ignores precedent** (DEC-0036: Synology's `db` driver takes `max-size` and
  discards it, 7 h of prod lost to a cap that was never real). One owner-run `lsattr` returned
  `-----a------------` and converted inference to observation. A write-based probe was explicitly
  refused — it would confirm the attribute by attacking the attribution record.
- **We priced the cost of our own recommendation in writing.** Dropping sticky widens §11's already-
  accepted wrong-lease-deletion race from same-owner to any-tenant: a buggy unlink of a *valid* lease
  leaves the holder renewing into an unlinked inode while every observer reads the slot free. Still
  the right trade against option (b)'s *guaranteed* silent stranding of the least-privileged tenant,
  but recorded rather than discovered later. Break-by-takeover-in-place was considered and
  **discarded with the reason**, checked against HLF's real acquire/release code, so it stays dead.
- **Two findings came from the other tenants looking at our situation, and both changed what
  shipped.** coffee-radar noticed sticky was *incidentally* the only thing protecting the log from
  unlink — unpriced because it had only ever been weighed against §3's break clause — and flagged
  that the holder's literal account name was heading into a persisted record. That name is the
  owner's personal login, absent from all tracked files, and our adopting DEC lands in a **public,
  permanent** repo: the hazard was ahead, not behind. HLF, patching the line we reported, found **a
  second create we had not flagged** (the steal-then-acquire retry) — the branch that only runs after
  a crash, i.e. when the lease matters most.
- **DEC-0107 is deliberately NOT the adopting DEC.** Landing one locks §5's constants for every
  tenant (HLF's DEC-0177 was the first), so it must lock a *corrected* spec. Adoption now waits on
  nobody but us and lands with the client at the **~08-23 v2.0.14 build**, which §8 designates as the
  protocol's first cross-tenant holder exercise. Declared floor 600 s / TTL 3600 s, flagged as dated
  data to be re-pinned against that build's real duration.
- **#224 shipped: `dewpoint_service.py` now branches on `usUnits`** (PR #255). The file had no
  `usUnits` check anywhere — `dewpointF`/`heatindexF` unconditionally, plus two wind thresholds
  documented in mph compared against packet values that are km/h or m/s under
  `target_unit=METRIC`/`METRICWX`, both documented options in our own `weewx.conf.example`. Masked in
  prod only by the shipped US default. **Fixed the way WeeWX's own `wxxtypes.py` does, NOT via the
  issue's proposed `weewx.units.to_US()`** — `loop_json_writer.py` uses to_US legitimately because it
  *emits* US-suffixed fields, but this service writes into the live packet, so a to_US fix without
  the return trip would put degF into a metric packet: the same bug one layer along.
- **The wind half failed in both directions, each silently** — as m/s the 200 mph ceiling is ~447 mph
  and the guard was **inert**; as km/h it is ~124 mph and the guard **nulled real weather**. Readings
  are now normalised to mph at each comparison, keeping one documented threshold set instead of three
  to keep in sync. Pre-fix logs printed km/h values labelled `mph`; they now carry the reading's own
  unit. Suite **339 → 349**.
- **Two process findings from doing it.** The mutation check corrected our own documentation: 7 of 10
  new tests fail against the pre-fix file, not the 8 the docstring claimed. And the new tests **passed
  in isolation while asserting nothing in the full suite** — the weewx stubs live in `sys.modules` and
  are shared, so `dewpoint_service.weewx` is whichever stub won the import race; fixed by patching
  through the module under test and restoring after.
- **ROADMAP scheduled reconciliation ran — tripwire fired on time, three stale items fixed** (PR
  #256, bumped to S106). The most interesting: **the "Last updated" banner had itself gone stale.**
  S89 and S92 recorded targeted passes in the guardrail section without promoting them into the top
  block, so the banner read S86 while content was current through S92 — the freshness signal aged
  while the file did not. Also: P2 asserted the Campaign A arm-winner seal held, which DEC-0069 broke
  as a side effect **30 sessions ago**; and P3's INTERFACES citation list was three DECs out of date
  (verified against `git log -- docs/INTERFACES.md`, not inferred).

---

## [S95] — 2026-08-20 — The reported crash-loop was scheduled swaps (DEC-0106); `soak_check.sh` gains a restart-loop detector

- **#245 / ops#184 (tier:frontier) refuted on measurement, and closed.** The report — `RestartCount: 0`
  while stdout showed RTL-SDR re-detection cycling inside a 30-line tail — was read as a crash loop.
  It was not. **Aug 15–19: exactly 4 weewxd startups a day, every one at HH:05 ±30 s**, which is
  precisely Campaign B's four scheduled arm swaps, 6 h apart, with **zero off-schedule restarts in
  five days**. The contrast case is in our own history: 2026-08-06's `journal_mode` crash-loop ran
  **7 starts in 7 minutes** (43–90 s apart). The healthy and pathological signatures differ by three
  orders of magnitude — the evidence was never ambiguous, nothing had ever put the two side by side.
- **Why it looked exactly like a loop — three things compounding, none of them careless.** Container
  stdout carries no timestamps; **`docker restart` never increments `RestartCount`**, so the reported
  zero was truthful *and* uninformative about the process; and the container object was 8 days old and
  *restarted* rather than recreated, so its stdout accumulated every restart into one stream. ~32
  routine restarts stack consecutively, and a 30-line tail catches ~4 of them that are in fact six
  hours apart. Corroborated by count: all three restart markers read **exactly 27** in a `--tail 200`
  window — itself truncation at ~7 lines/start, so the true figure is ~32 = 8 days × 4/day.
- **The owner's "a lot more crashes lately, it used to be super stable" is correct, and the cause is
  benign.** Measured across a month of rotated daily logs: **0/day between campaigns** (Jul 20–24,
  Aug 3–14), **4/day during them** (Aug 15–19). Every elevated non-campaign day has a known cause —
  Aug 6 = 7 (the WAL loop), Aug 11 = 10 (the v2.0.13 deploy), Aug 10 = 3 (v2.0.12). The zeros were
  **positive-controlled** (DEC-0045), not assumed: Aug 3's log runs full of data through 23:59 with
  zero `weewxd` events. So the rate genuinely rose; every one of the new restarts is deliberate.
- **HLF's staleness is not ours — redirected, not absorbed.** Through their reported window
  (19:45–20:07Z) weewx was adding archive records **and** publishing to InfluxDB every minute,
  successfully, no errors. The day's four driver stalls sat at 02:55–05:29 EDT (DEC-0097's overnight
  cluster), hours away. ops#184 deliberately **left open** — its HLF redirect is still an open action
  item for another repo, and closing it would bury that.
- **The monitoring gap this exposed, fixed (DEC-0106).** `soak_check.sh` counted startup banners with
  `grep -c` then tested only non-zero — 1 and 50 read identically green, which is what the S94 soaks
  ran through twice while #245 was live. **Raising it to a count would not have worked:**
  `entrypoint.sh` `exec`s weewxd, so weewxd is pid 1, its death takes the container with it, and
  every container lifetime holds **exactly one** banner. A loop is structurally invisible inside a
  per-container window. The detector therefore reads a **fixed 6 h window** and fails when consecutive
  starts are **<1800 s apart** — swaps are 21,600 s, loops are 43–90 s, so the threshold sits in a gap
  two orders of magnitude wide. **Positive-controlled over 7 cases** against the real Aug-6
  timestamps, including both sides of the boundary (1799 s fires, 1800 s does not) and a loop hidden
  beside a legitimate swap.
- **A rotation trap, caught in verification and proven in production.** The first draft grepped only
  the current `weewx.log` — which **rotates daily**, so a 6 h window run after midnight spans two
  files. The first live run (00:0x EDT) found the window's only start in the **rotated** file, so the
  unfixed version would have returned **0 — a false green**, at exactly the hour DEC-0097's stalls
  cluster. Now reads yesterday's rotated file first. Same trap the `mon_resets` check already
  documented for `weewx_monitor.log`; `docs/GOTCHAS.md` §1 gains both.
- **Found, filed, deliberately not fixed here** (DEC-0014, keep the change small): the soak's
  *pre-existing* window computation has the same rotation blindness — after midnight it collapses to
  the new day's log, which is why four window-scoped checks currently WARN as artifacts rather than
  findings. And the long-standing `stdout is chatty — 162 lines` WARN is now **explained**: accumulated
  restart output on a long-lived container, permanent until the next recreate, not "freeze fuel" —
  it has been read as expected noise for weeks.
- **Nothing deployed.** `ops/soak_check.sh` is a laptop-side diagnostic; prod remains **v2.0.13** /
  driver ws.5, untouched. Campaign B checked during the session, healthy. Gates: ruff clean,
  **339/339**, mypy clean (57 files), secret gate clean **and positive-controlled** (all three planted
  payload shapes caught, exit 1).

---

## [S94] — 2026-08-19 — #223 shipped (DEC-0103); ops#169 unblocked by correcting our own DEC-0099 (DEC-0104); BOOT.md diet, under cap (DEC-0105)

- **#223 (`dewpoint_service.py` wind-plausibility filter, frontier) fixed, tested, PR #241.** Its
  four defects were one design gap, exactly as the issue argued: `_filter_wind` never adopted the
  resync-on-reject and co-null behavior `rtldavis.py`'s `SensorQC` already established in this repo.
  **The fix is one distinction, applied consistently** (DEC-0103): a **bounds** reject — an
  impossible reading, or a gust below its own speed — is positive proof of corruption, so the
  baseline is left untouched; a **delta** reject may be a genuine gust front, so the baseline
  **always resyncs, even when rejecting**. (1) That resync closes the deadlock: previously a
  rejected step froze `last_wind_speed` permanently and every later reading was nulled against a
  baseline the weather had left behind, until the weewx process restarted — a 300 s TTL
  (= `QC_RESEED_SECONDS`) adds a second, independent escape. (2) `windDir` is now co-nulled in every
  reject branch; a bare heading with no speed previously reached loop-JSON, InfluxDB and every
  uploader, and this matches the driver's own two precedents while staying narrower than DEC-0054's
  frame-level co-rejection, which delta correctly still never triggers. (3) Cold-start warmup samples
  are bounds-checked before they can seed a wrong baseline and trigger (1). (4) `windGust` is
  bounds-checked independently of `windSpeed`'s presence — unreachable with today's driver, included
  because the driver-agnostic goal is the same one that decided (below) not to import from the driver.
  10 new tests (`tests/test_dewpoint_wind_filter_223.py`). 339/339 full suite (329 baseline + 10 new),
  ruff/mypy clean (57 files), secret scan positive-controlled clean.
- **The port-vs-import call, decided and recorded (DEC-0103).** Importing `SensorQC` from
  `rtldavis.py` is the cheaper move and was rejected: `dewpoint_service.py` has zero driver imports
  today, and `docs/INTERFACES.md` commits it to being re-pointable at non-Davis WeeWX. Coupling a
  driver-agnostic LOOP-packet service to a vendored fork carrying USB and subprocess concerns, to
  reuse ~20 lines of pure logic for a single field, costs more than the duplication. Recorded
  because the reasoning is invisible from the code — a later reader should know the second filter is
  a considered port, not drift.
- **The first pre-fix proof was worthless and looked convincing.** All 10 new tests "failed" against
  the stashed pre-fix file — every one with `TypeError: unexpected keyword argument 'now'`, i.e. the
  signature change, not the defects. Re-run through a shim giving the old `_filter_wind` the new
  signature so only behavior was under test: **6 of 8 behavioral checks fail pre-fix with the exact
  predicted symptom, 0 after**, and the 2 convention locks pass on both sides by design. The
  generalizable form of DEC-0045's rule, from the other side: *a failing test is no more evidence
  than a passing one if it fails for the wrong reason.*
- **`dewpoint_service.py` confirmed BAKED, not mounted** — established with `nasctl inspect` and
  positive-controlled against a known-mounted file, not assumed from its sibling `pressure_service.py`.
  `CONSTANTS.md`'s deploy-layer table did not list the file at all (the same omission S85 found for
  `loop_json_writer.py`, which would let a change "ship" with an image cut and silently do nothing —
  DEC-0046's exact failure); it gains the row. **Nothing deployed this session**: the fix ships on an
  image rebuild, gated behind v2.0.14.
- **[ops#169] promoted to job 2 on owner instruction — and researching it overturned our own
  DEC-0099, logged as DEC-0104.** The owner raised its priority ("next few sessions for sure") and
  then corrected the approach: *"ask the repo… you have coded all of this, so you should be able to
  find answers."* Re-reading `eaglehunt-ops/NAS-LEASE.md` against our own record found three things.
  (1) **DEC-0099's gating premise was wrong.** It deferred adoption to the v2.0.14 container recreate
  because `influx.py` cannot see `LEASE_DIR` from inside the container — true for that one lever,
  over-generalized into a gate on the whole client (and an earlier commit this session amplified it
  into `BOOT.md` as a hard deadline). §9 had already settled it the other way: weewx's client's
  *"natural home is host-side"*, chosen precisely to avoid a release-class recreate. **Holder** (wrap
  the NAS image build) runs on the host; **observer** (read lease, append `heavy-io.log`) is
  `weewx_monitor.py`, already resident with a 30 s poll — neither needs a container change. Only the
  InfluxDB `post_interval` **yield** lever does. (2) **The "two strands" are one:** coffee-radar's
  disk-contention handshake IS this lease — their DEC-0181 Stage 2 landed *as* OPS-DEC-0107. The
  question we nearly posted to ops#169 was already answered in coffee-radar's own `BACKLOG.md`, one
  grep away. (3) **★ weewx's adoption LOCKS §5's constants for every tenant** (unlocked "until the
  second adopting DEC"; HLF's DEC-0177 was first) — a governance act arriving disguised as merge
  order, flagged to ops so other tenants can amend first. Pre-flight verified rather than assumed
  (DEC-0074): `LEASE_DIR` exists at `/volume1/docker/nas-lease/` mode 1777 (owner step already done),
  `heavy-io.log` live with HLF renewing in production (~8.7 h held 08-19, released
  `outcome: step-failures`). **DEC-0099's index row gains a correction pointer rather than being
  edited** — a decision is superseded, never rewritten in place. Position posted to ops#169.
- **Three of this session's six PRs were corrections of its own errors, each caught by re-reading
  rather than by getting it right first.** #242: `BOOT.md` was written before the merge landed, so it
  shipped telling S95 to delete a branch already gone and close an issue already closed. #243: the
  model-tier line asserted "a restore is owed" from OPS-DEC-0010's rule while a read already showed
  `sonnet` — **the identical mistake S89 made and was corrected on by ops**; all five scopes verified
  intact, nothing owed. #246: the DEC-0099 correction above. The generalizable lesson, now in
  `BOOT.md`: for anything whose truth depends on a merge landing, the handoff is written *after* it,
  even though the closeout ritual lists BOOT at step 2 and push at step 7.
- Daily square watch, checked twice. Start: **arm C**, 16 pass / 2 expected-WARN, reception 71%/62%.
  Close: **arm D as of 08-19T18:08:23 EDT** — a scheduled swap mid-session, confirmed against the
  state file *and* container uptime (19 min) rather than inferred from the fresh counters; 16 pass /
  2 expected-WARN, reception 72%/86%. No STOP/PAUSE/lock either time. Untouched by this session's work.
- ROADMAP checked: neither DEC-0103 nor DEC-0104 ships/closes/reprioritizes a P0–P3 line (#227's
  remediation is tracked on the issue tracker, and ops#169 appears on ROADMAP only inside DEC-0102's
  narrative record, not as a line item) — nothing to reconcile, tripwire unchanged, still due by S96.
- Model tier: escalated to Opus for #223's frontier design work. **Floor verified intact across all
  five scopes at close — nothing to restore** (see #243 above for why that is checked, not inferred).
- **`BOOT.md` diet done on owner instruction — 4,866 → 2,406 tok, under the 2,500 cap for the first
  time since before S83 (DEC-0105, ops#173).** Done days ahead of the ~08-23 plan. The starting point
  was worse than ops#173 last recorded (4,427 at S86) because this session added ~1,000 of its own.
  **Four prior rule-1 trimming passes at S84 had moved the file ~50 tok net** — deleting resolved
  items cannot keep pace with a file that absorbs a session's state every close, so the remaining
  bulk was diagnosed as *misfiled rather than stale*: the gotchas block was **41% of the file** and
  nothing in it expires at a session close. Moved to **`docs/GOTCHAS.md`**, four sections deep, with
  a `MANIFEST.md` row whose "load when" names a trigger rather than a topic — an index entry saying
  "read this sometimes" is unread, not lazily loaded. Then What's-settled and job 2 compressed to
  conclusions now that DEC-0103/DEC-0104 hold the detail (the ops#169 briefing alone was ~700 tok
  restating DEC-0104). **Rejected:** distributing the entries into `CONVENTIONS.md`/`ARCHITECTURE.md`
  by topic — each would land in a defensible home but the class would stop existing, and the class is
  the point. **A rule-5 trap caught mid-task:** the first draft of the new file also copied in the
  gate commands, the baked-vs-mounted deploy table and the pyc cache from the canonical docs; it read
  as completeness and is precisely STANDARD rule 5's defect (a second copy is what drifts). Eight
  entries removed, exclusion stated inline. **Cost taken deliberately:** `MANIFEST.md` 1,096 → 1,226,
  including correcting its own stale "~1.1K" self-figure — 130 tok there bought ~1,700 out of the
  always-load tier. **ops#173 left open on purpose**, result posted to the thread: `MANIFEST.md` is
  still over its own cap, and the automated sweep — not this repo — should be what calls it green.
- **A second follow-up PR (#249) fixed two stale references the diet itself created** — job 6 still
  read "diet at the square's close, still deferred on purpose", and the gotchas pointer cited a §5
  that no longer existed after the rule-5 removals merged it into §4. Same shape as #242: a doc
  describing a state that changed while it was being written. Caught by re-reading the finished file
  rather than trusting the edits.

---

## [S93] — 2026-08-19 — Channel-gating fixed (#222), #227's sequence now 4 of 8 shipped; #223 scoped

- **#227's sequenced plan: #222 (channel-gating consistency, mid) fixed, tested, merged.** Three
  instances of the same root cause — channel routing not consistently enforced across sibling
  decode/config paths. (1) Wind bytes decoded unconditionally from any of 4 configured channel
  roles instead of gating on the already-computed `wind_channel` — fixed by wrapping the decode
  block in the missing gate, sibling to the message_type dispatch that follows it. (2) `rain_count`
  (message_type 0xE) had no channel check, unlike its sibling `rain_rate` a few lines earlier —
  fixed by copying that existing gate. (3) `ch_to_xmit()` accumulated transmitter bits with no
  check the 5 configured channel numbers are pairwise distinct, so a duplicate silently corrupted
  the `-tr` bitmask into a different channel than either role was configured for — fixed with an
  explicit `ValueError` in `__init__`, matching the sibling frequency-validation two lines above it.
  9 new tests (`tests/test_channel_gating.py`), all 4 bug-repro cases confirmed to fail pre-fix via
  `git stash`. Wiring `wind_channel` into `parse_raw()` broke 13 pre-existing tests across 4 files
  whose minimal fake-driver fixtures predated the change and had no `wind_channel` key — fixed by
  adding it to each, not a behavior change. **PR #238, merged** (`f31438d`). 329/329 full suite
  (320 baseline + 9 new), ruff/mypy clean (56 files), secret scan positive-controlled clean.
- **#219/#220/#221 closed on GitHub** — merged in S92 but never explicitly closed (this repo's
  `Closes #N` doesn't auto-fire since `dev`, not `main`, is where PRs land). Each closed with a
  comment cross-referencing its PR and merge commit, per `CONVENTIONS.md`'s explicit rule. #227's
  sequence now correctly reads 4 of 8 shipped on GitHub, not just in `BOOT.md`'s own tally.
- **#223 (`dewpoint_service.py` wind-filter redesign, frontier) scoped, not implemented** — read
  and grounded all 4 sub-bugs against current code (deadlock from missing resync-on-reject with no
  TTL; `windDir` surviving a rejected `windSpeed`/`windGust`, confirmed by the two existing tests
  that seed a `windDir` value and assert nothing about it; the unfiltered warmup buffer that seeds
  bug 1; `windGust` unguarded when `windSpeed` is `None`, confirmed unreachable by this repo's own
  driver today). Identified the fix pattern to port (`SensorQC.check()`'s always-resync-the-baseline
  + TTL-gated reseed) and flagged one open design call for the actual session: porting the pattern
  locally vs. importing `SensorQC` from `rtldavis.py`, which would break `dewpoint_service.py`'s
  current zero-coupling to the driver. Deliberately held for its own dedicated session per #227's
  own note and the frontier tag — no code written.
- **Session survived a mid-session crash cleanly** — verified on resume that nothing drifted (git
  state, PR #238's CI/mergeability all exactly as left) before continuing, rather than assuming the
  transcript was still ground truth.
- Daily square watch (once, session start): 16 pass / 2 expected-WARN (chatty stdout + ineffective
  USB hedge, both already-known), reception 75% 5-window avg / 62% last window, arm B unchanged
  since 08-19T06:06:26, no STOP/PAUSE/lock. Model tier confirmed Sonnet at session start (fresh
  session, nothing elevated to restore from S92's #219 escalation).
- **None of #222 deploys yet** — `rtldavis.py` is baked into the image, holds for the v2.0.14 cut
  (~08-23) same as the rest of #227's plan.
- ROADMAP checked: nothing this session ships/closes/reprioritizes a P0–P3 line — no DEC logged
  (routine audit-remediation fixes don't generate their own DEC, same as #219/#220/#221 in S92).
  Tripwire unchanged, still due by S96.

---

## [S92] — 2026-08-19 — Overnight-probe finding shipped (DEC-0102); 3 of 8 code-audit fixes merged (#219/#220/#221)

- **Job 2 closes: DEC-0098's probe ran, and DEC-0102 records what it found.** Resolved the
  probe's unrecorded-timezone question by process evidence, not computation — `proc_probe_nas.sh`
  stopped cleanly on schedule at 05:00 EDT. Ingesting its data exposed and fixed a real bug in
  `proc_probe.py --analyze`: a second named window's data was silently absorbed into "control" the
  first time both existed in the same CSV, inverting the evening-window ratio. Headline result:
  overnight (00:00–05:00) iowait is **11.80x** a clean daytime baseline — the first hard number on
  the confound DEC-0092/DEC-0097 already flagged — but confounded itself by a concurrent ops#169
  coffee-radar event, and a minute-level cross-check against that night's actual stall timestamps
  came back mixed, not confirmatory. **Root cause of blocker 2 stays open**; a single clean re-run
  won't settle it, since DEC-0092's confound recurs every night. ROADMAP's P0 freeze line updated;
  ops#169 notified. **PR #231, merged.**
- **Job 7 (S91 audit remediation, #227's sequenced plan): 3 of 8 items fixed, tested, and merged.**
  **#219** (ProcManager subprocess-lifecycle, frontier — Opus, explicit user-approved escalation):
  `shutdown()`'s unguarded `get_pid()` call skipped the S73/DEC-0081 zombie-reap fix on exactly the
  case it's most needed; `AsyncReader`'s EOF-sentinel bug (`''` vs binary `b''`) busy-spun a reader
  thread on every child exit and — worse than filed — left abandoned `ProcManager` instances' reader
  threads with no termination path at all; `get_stderr()` could block ~2x its documented 10s cap.
  Design validated with a Plan-agent pass before implementation; 4 new tests, each confirmed to fail
  against git-stashed pre-fix code. **PR #232, merged.** **#220** (`DATAPacket.IDENTIFIER` silently
  dropped every battery-low frame — not just battery status, but wind/temp/humidity/rain too, mid):
  one-line regex fix, dispatch-ambiguity rigorously verified against the only other packet type
  first; 3 new tests. **PR #234, merged.** **#221** (4 unguarded divide-by-zero/negative-shift
  crashes — thermistor, both rain-rate branches, `iss_channel=0`, an unhandled CRC `ValueError`
  confirmed to exit the daemon entirely, mid): guard-and-degrade, matching the pattern already
  established elsewhere in the file; 8 new tests. **PR #235, merged.** Follow-up issue **#233**
  filed (`shutdown()` has no direct kill/terminate, tier:mid, not urgent) — found pressure-testing
  #219, kept out of its scope.
- **All 5 PRs merged same session** (the four above plus this session's own closeout, #236), each
  verified via `gh pr view --json state,mergedAt` rather than `gh pr merge`'s own untrustworthy
  output; four hit the expected branch-behind-base gotcha once an earlier one landed, fixed with
  `update-branch` + wait-for-CI each time. Re-verified on the real merged `dev`: **320/320 tests**,
  ruff/mypy clean. All 5 feature branches deleted, steady state restored to exactly `dev` + `main`.
- NAS cleanup: `proc_probe_nas.sh` + its two logs removed from the NAS on owner instruction,
  verified gone via read-only `nasctl ls`.
- **None of this deploys yet** — `rtldavis.py`/`proc_probe.py` changes hold for the v2.0.14 image
  cut (~08-23) per DEC-0064; merging to `dev` doesn't touch the live station. Campaign B checked
  twice this session (start and close), healthy both times, untouched throughout.

---

## [S91] — 2026-08-19 — Full code audit (BOOT job 7): security fixes shipped (DEC-0101), 26 correctness findings filed as a sequenced plan (#219–227)

- **The owner's planned focus for the session, decided at S90 close.** Two independent halves, run
  as separate multi-agent passes rather than one combined effort.
- **Security pass**: 4 DEC-primed finder agents (one per file: `rtldavis.py`,
  `pressure_service.py`/`dewpoint_service.py`, `weewx_monitor.py`, `ops/rx_experiment.sh`) + an
  Opus-tier adversarial verification pass over everything they surfaced. **DEC-0101**: SMTP
  connections skipped TLS certificate verification at both alert-mail call sites
  (`weewx_monitor.py`'s continuously-running production monitor, `ops/rx_experiment.sh`'s campaign
  abort-notification path) — `smtplib`'s default with no `context=` is unverified, exposing
  `GMAIL_PASS` to an on-path attacker; `influx.py` already does this correctly elsewhere in the
  repo, this was a regression against an established in-house pattern, not a novel ask. Second
  finding: the WeatherLink API key could leak into `weewx.log` via exception text on any connection
  failure (reproduced empirically) — a new gap, not a DEC-0062 regression, since the credential
  only exists at runtime inside the exception's `__str__()`, invisible to DEC-0062's AST-based
  regression test. Both fixed, both guarded by new/extended tests with positive controls. **PR
  #229, merged.**
- **Bundled into the same PR**: a `docs/DECISIONS.md` structural fix — DEC-0093 through DEC-0101
  had been sitting under `## Open / deferred` despite every one being `Accepted` (found by the
  ultrareview cloud pass, which also caught the S91 session's own DEC-0101 addition landing in the
  same wrong spot). Fixed via a scripted, assertion-guarded reorder rather than a hand-retyped edit
  — the block was too large to safely retype by hand.
- **Also merged this session, unrelated to security but surfaced by the same ultrareview pass**: a
  pre-3.12 Python `SyntaxError` in `ops/proc_probe.py` (a conditional inside an f-string's `{}`
  spanning two lines needs PEP 701) — would have broken every entrypoint of the tool BOOT job 2
  depends on, on any pre-3.12 interpreter. All locally-available interpreters here are 3.12+, so
  this session's own probe harvest was never at risk, but it's a real bug in a public repo. **PR
  #228, merged.**
- **Correctness pass**: 10 independent finder angles (5 correctness + 3 cleanup + altitude +
  conventions, per the local `/code-review` skill's own methodology, adapted for a path-target
  full-file audit rather than a diff) against `rtldavis.py` + `dewpoint_service.py`, followed by
  Opus-tier adversarial verification of all 21 surviving candidates (batched by theme into 4
  verification passes) and a sweep pass that found 6 more. **26 distinct findings survived** (20
  confirmed, 6 plausible); 2 further candidates were independently **REFUTED** — a suspected
  packet-duplicate-detector aliasing bug turned out inert, because the Go binary already dedups
  byte-identical frames upstream and every packet carries monotonic counters that make the
  equality-based dedup check always-true regardless. **Filed as GitHub issues, not fixed this
  session** — the volume made same-session fixes impractical, and several (the ProcManager
  subprocess-lifecycle bugs, the dewpoint wind-filter redesign) are explicitly judgment-tier design
  work better done as their own deliberate sessions. Grouped into 8 issues (#219–226) by shared root
  cause rather than filed 1:1; sequenced with model tiers and deploy gating in tracking issue
  **#227**, the map for the next several sessions of this work.
- **Standout findings** (full detail in #219–226, not re-narrated here): an uncaught exception on
  CRC mismatch that can crash the whole weewxd daemon (found independently by 5 of the 5
  correctness-angle finders); `ProcManager.shutdown()`'s zombie-reap skip on an unguarded
  `pidof` call (also 5x-corroborated — the repo's own existing test monkeypatches around it with a
  comment admitting the gap); a regex bug that silently drops an entire transmitter's data whenever
  its battery goes low, leaving 5 status fields permanently dead; the shipped config-generator
  template shipping a literal unreplaced `[options]` token that would break any new user's first
  install; and wind data leaking in from the wrong sensor channel on any station with a separate
  Anemometer Transport Kit.
- **Cross-repo heads-up posted**: eaglehunt-ops#180 (informational — the audit methodology may be
  worth reusing on HLF/dashboard, not a request, no reply expected).
- **Deploy gate, applies to all of #219–226**: `rtldavis.py` (and likely `dewpoint_service.py`) are
  baked into the Docker image, so none of it can deploy before Campaign B closes (~08-23) — design
  and merge to `dev` freely, hold the image cut for v2.0.14 (or v2.0.15+ for the two lowest-priority
  issues).
- Green gate at close, on merged `dev`: ruff clean, **305 passed**, mypy clean/52 files.
- Campaign B checked twice (session start and close), both times healthy and completely off this
  session's critical path — block 16→17 of 32, a scheduled 00:05 swap into arm A landed clean
  between the two checks. No code from this session touches the running station.
- ROADMAP checked: nothing here ships/closes/reprioritizes an existing P0–P3 line (the audit's
  findings are new work, not a resolution of a tracked item) — nothing to reconcile, tripwire still
  S96.

---
## [S90] — 2026-08-18 — NAS-LEASE adoption deferred to v2.0.14 (DEC-0099); the InfluxDB rollup answered as dashboard's build (DEC-0100)

- **Off-cycle start, by design.** BOOT's resume pointer had no date-gate reached yet (probe harvest
  waits on the 08-19 05:00 stop; the daily watch is cheap and unblocking). Session instead swept
  ops + dashboard + HLF for cross-repo messages — the routine `repo:weewx` check, run further than
  usual because the sweep surfaced a live thread nobody had caught yet.
- **DEC-0099 — OPS-DEC-0107 (NAS-LEASE) landed 2026-08-15 and HLF adopted (their DEC-0177, live
  since 08-16) while `BOOT.md` sat completely stale on both.** weewx has zero live levers today —
  the one committed-unbuilt lever (InfluxDB `post_interval` deferral, safe to ~30 min per DEC-0092)
  needs `influx.py` inside the container to see `LEASE_DIR`, which isn't mounted and can't be
  without a release-class recreate. **Deferred, not declined: v2.0.14 already recreates the
  container**, so that's the no-extra-cost moment to add the mount — bundled plan now in BOOT's
  v2.0.14 queue (mount `LEASE_DIR`; `influx.py` checks it and raises `post_interval` while held; the
  NAS image build becomes weewx's first HOLDER via acquire→flock→release; renewal in-place only,
  **never** `loop_json_writer.py`'s tmp+`os.replace` idiom, which the spec names as the exact way to
  strand a flock on an unlinked inode). Posted to ops#169, left open against weewx until the window
  lands the client.
- **Free correlation, no adoption needed:** read the live world-readable `heavy-io.log` this
  session — one real lease-held window exists so far (HLF's `daily-maintenance`, 2026-08-18
  00:10–06:10 EDT), containing both one RF-dead episode (02:41, 26.3 min) and one freeze
  (03:15–03:22, 420 s). n=1, far too small to test anything — logged as a lead in BACKLOG's standing
  watches, explicitly **not** revising DEC-0094's P=0.29 or the RF-stall P=0.32.
- **DEC-0100 — ops#175's mutual wait (weewx: "dashboard's call"; dashboard: "waiting on weewx to
  propose a shape") broke on an ops strawman; weewx answered.** Accept-and-monitor for InfluxDB
  agreed. On who builds the permanent daily rollup dashboard's all-time-record queries need: weewx
  declines, recommends dashboard build it as a native InfluxDB 2.x Task — `docs/INTERFACES.md`
  already draws the boundary ("our responsibility ends at writing the documented schema"), dashboard
  already runs Flux against this bucket and `influx.py` never has, and a Task changes neither write
  path. Posted to ops#175.
- **PR #215 merged (`b5c1be5`)** — both DECs, BACKLOG/BOOT synced to current reality, steady state
  restored. Green gate at close: ruff clean, 299 passed, mypy clean/51 files.
- **Campaign B watch, at close: block 16 of 32, arm C** (swapped 18:05:02, settled 84s — confirmed
  directly via `rx_experiment.state` + log, not derived). Soak run earlier the same session: 16
  pass / 2 expected-WARN (chatty stdout + ineffective USB hedge, both already-known), reception 75%
  5-window avg / 71% last window, 0 stalls, no STOP/lock. This was the session's only contact with
  the running square — the originally-planned S90 job list (probe harvest, closer campaign
  tracking) is untouched and carries to S91.
- ROADMAP checked: neither DEC touches a P0–P3 line item (both live in BACKLOG, not ROADMAP) —
  nothing to reconcile. Tripwire unchanged, still due by S96.

---

## [S89] — 2026-08-18 — The overnight "reception dip" was never reception (DEC-0097); the mechanism probe moves to the NAS (DEC-0098)

- **DEC-0097 — the reception-floor dip is RF-dead episodes, and BOOT's own record of it was
  wrong.** A watch carried four sessions ("n=4, window drifting later, needs the proper
  statistical test") fails on three premises. **The record:** PAUSE/RESUME lines pair one-to-one,
  so 08-18 was onset **02:55, five cycles**, not the logged "03:30, two" — corrected onsets
  02:15/02:15/03:25/**02:55** are not monotonic, and the drift was the stated reason for rejecting
  a fixed-clock artifact. The four nights are arms **A, B, C, D** — every gain × receive-window
  cell, so not an arm effect. **The measurement:** on per-minute `rxCheckPercent` (DEC-0069/S31 —
  *not* the monitor's 30-min mean; different instruments, the 50% floor does not transfer), tested
  on **31 pre-campaign nights the hypothesis was not derived from**, contrasting the window
  against its flanks *within one arm block* so gain/window/arm are constant: mean d = **−0.01 pts**
  (Wilcoxon p=0.60, permutation p=0.47). Deepest 30-min mean on campaign nights **68.4%** against
  DEC-0059's 73.3% baseline; **0 of 35 nights** under 50% while the monitor reported 20–45%.
  **The mechanism:** every episode reads one pathological value (3–22%), then minutes **absent**,
  then NULL, then normal 65–90% — `campaign_analyze.py`'s documented truncated-accumulation
  artifact, which cannot self-identify because `interval` stays 1. Those artifacts feed the laggy
  30-min mean and trip the floor. The null held-out result *is* the mechanism's confirmation:
  `partition()` already excludes them. **And night 1 was already classified** — DEC-0094 recorded
  08-15 02:00–02:22 as RF-dead three sessions before the watch was flagged untested.
  **What survives, on the right unit** (ledger rows re-clustered per DEC-0083's unit lesson):
  RF-dead episodes concentrate **00:00–04:00 — 8/19 vs 3.17 expected, P=0.0079**, stable at
  30/45/60-min clustering; stall-bearing rows only **7/9 vs 1.50, P=0.00009**, and **0/9** in
  DEC-0094's evening freeze window — different clocks, independent support for the two being
  separate phenomena. **7 of 7 ledger dates**, including three that **predate the square**.
  Stated against itself: ledger is 6.5 d, left-censored at ws.5; omnibus does **not** reject
  uniformity (X²=27.7, df=23, crit 35.2); DEC-0092's tenant maintenance (00:10→~03:00–05:10)
  overlaps and is not discriminated against. **No code changes** — DEC-0087 scoped the PAUSE to
  RF-dead episodes and that is exactly what fires it. Job 2 closes; blocker 2 gains a timing
  signature.
- **DEC-0098 — the mechanism probe runs on the NAS, because a laptop-side overnight probe is not a
  limitation but an infeasible design.** `ops/proc_probe.py` was built to BOOT job 6's "read-only
  from the laptop, no NAS write" scope and hardened inside it (per-batch ssh, a supervisor that
  relaunches on process death — verified by SIGKILL, rc=137 → auto-resume — idempotent `--resume`,
  gap-guarded deltas). None of that addresses the real failure mode: it required the owner's laptop
  awake **12+ hours**, and DEC-0097's second window (00:00–04:00) a laptop-side probe can never
  sample at all. `ops/proc_probe_nas.sh` now runs under `nohup` on the NAS (pid 28699, ends
  08-19 05:00) emitting the **same pipe-delimited stream** `proc_probe.py` parses; `--ingest`
  reuses `parse_line()`, and merging is idempotent. Footprint went **down** — ~2,700 ssh
  round-trips replaced by `/proc` reads plus an append. Costs recorded: a Class C write approved in
  chat, a bounded resident process on prod, and **cleanup owed**.
- **The probe measures cumulative counters, not instantaneous state** — the reason two prior
  attempts could not settle DEC-0068. `block_max` already showed a **4041 ms** uninterruptible
  block in a 4 h span containing no evening, so "main thread `S`, never `D`" was sampling coverage,
  not evidence. Measured before building, not assumed: no PSI (kernel 4.4.302+), `wchan` reads `0`,
  `/proc/<pid>/io` denied as non-root. A smoke test caught three real bugs pre-flight (a
  two-column row shift, both md2 fields collapsing to one value, `/wait_sum/` also matching
  `iowait_sum`).
- **New trap:** `nasctl cat /proc/<pid>/cmdline` returns **empty for a live process** — caught only
  by positive-controlling the method against weewxd's own known-live pid. Third instance of *a zero
  from a look-alike tool is a claim, not a result*.
- **Gain / receive-window hot-swap filed, not started (PR #212, [ops#179]).** Owner asked what
  prevents hot-swapping a gain instead of restarting the container every arm swap. **Only the
  feature.** Gain is a CLI flag on the Go binary carried in the `cmd` string, and `rtldavis.py` has
  **no concept of it at all** — `grep -i gain` returns five hits, four of which are the word
  "a*gain*st". The swap path already exists: `ProcManager.startup(cmd, …)` takes the command as a
  parameter, `shutdown()` kills and reaps, and the 150 s watchdog exercises that respawn cycle
  routinely (DEC-0081). The gap is only the trigger — config is read once in `__init__`. `-ex`
  rides the same string, so both axes of the square could swap with no container touch, retiring
  the 600 s settle window (~2.8% of campaign data) and the abort-on-unhealthy-swap failure class
  (DEC-0082, DEC-0087). Filed with its constraints attached: **not during campaign B**, the binary
  sets gain only at startup, it widens the vendored fork, and device re-open time after a
  deliberate SIGKILL is unmeasured.
- Campaign B watch: block 14 verified healthy at ~10:00 EDT (soak 16 pass / 2 expected-WARN);
  block 15 starting at close. Square through `08-23T00:05`, ~4.5 d left, no swap deferred.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179

## [S88] — 2026-08-18 — weewx 5.5.0 staged for v2.0.14; the schedule gains a stand-down state (DEC-0096)

- **weewx 5.4.0 → 5.5.0 merged to dev (PR #208)** — the deliberate bump behind dependabot #158,
  per the issue-#78 flow (the dependabot PR is the notification; #158 closed with a pointer).
  Rides the v2.0.14 image cut. Upstream 5.5.0 notably adds retry-on-database-locked — the
  DEC-0070 failure class. Corrected en route: #158's red `tests` check was an artifact of its
  only CI run predating the S73 test correction on `main` (the pre-S73 first-row assertion
  against a schedule that had legitimately launched), not a 5.5.0 problem — current `main` would
  pass it today.
- **DEC-0096 (PR #209): an empty SCHEDULE block is now the explicit between-campaigns stand-down
  state.** Campaign B's terminator (08-23T00:05) is the v2.0.14 window's opening moment, and
  `tests` is a required check on both branches — without this, every PR of the cut would have
  queued behind a red staleness guard, with nothing honest to regenerate the table to. `install`
  refuses the empty block loudly; six structural tests skip on emptiness; the staleness guard's
  classification moved to `_schedule_state()` with its stale branch positively controlled
  (DEC-0045) so a fully-elapsed real schedule still fails exactly as before. The live schedule is
  untouched; the post-square emptying PR must land FIRST in the window. 299/299.
- Watches: 08-18 swaps `B→D` 00:05:02 (settle ~196 s) and `D→A` 06:05:02 (~144 s) both healthy,
  block 14 of 32 in progress; reception-floor dip recurred 03:30–03:45 ×2 on arm D — watch n=4,
  window still drifting later (02:15 → 03:25 → 03:30). Soak 16 pass / 2 expected-WARN.
- Docs: CONSTANTS' release row corrected — `prod-baseline-20260811` (`main` = `1cc9605`) landed
  at S73, the "promotion pending" note was stale. ROADMAP checked: no v2.0.14 line to reconcile,
  scheduled pass S96.

---

## [S87] — 2026-08-17 — The soak was lying about a healthy station; retention settled as accept-and-monitor (DEC-0095)

- **`ops/soak_check.sh` measured every age against a clock captured before its own remote body —
  PR #206.** `now` was taken at the top of the ssh block, then ages were computed against it at the
  bottom, after `docker logs`, a full `weewx.log` window read and a `docker exec` sqlite loop. Every
  age was understated by exactly the block's runtime. That runtime was ~2 s historically (every
  recorded value 1–29 s, all inside the monitor's 30 s poll) and 15–100 s under load by 08-17, so
  the monitor's log mtime always landed *after* `now`, the age went negative, and the `-ge 0` guard
  reported a perfectly healthy watchdog as **`MONITOR LOG STALE … wedged`** — for ten days, on every
  run. The watchdog was in fact polling on the dot: 19:10:17 → :47 → 19:11:18 → :48 → 19:12:18, no
  gaps. **The quieter half mattered more:** the same stale clock fed `record_age_s`, the DEC-0036
  freeze detector, whose 180 s threshold silently became 180+runtime (measured 195–280 s) — least
  sensitive exactly when the box is loaded, which is when freezes happen (DEC-0088: median 240 s).
  Both ages now read the clock at the point of measurement, the runtime is reported rather than
  hidden, and the monitor verdict splits into its four real outcomes (dead / no log / clock skew /
  wedged). Also retires the reception check's hardcoded 80% floor, which read **one** 60 s window of
  21 packets — sd ~9.7 pts at this station's measured 73.3% baseline (DEC-0059) — and so warned on
  most healthy runs, 20 pts tighter than the monitor's own `WU_RF_MIN_PCT=60`; the soak now reports
  the monitor's five-window average and its `[OK]/[LOW]` verdict instead of keeping a second
  threshold beside it. New `tests/test_soak_check.py` drives the real script with `ssh` stubbed;
  every "no longer cries wolf" assertion is paired with a positive control that the check still
  fires, verified by running the suite against the pre-fix script (7 fail, all three teeth-controls
  pass).
- **DEC-0095 — retention is accept-and-monitor, not archive-then-prune, and the monitor executes.**
  Answers the weewx half of ops#175. Measured read-only 08-17: archive **33.61 MB = 0.89% of
  MemTotal 3.69 GiB**, 5.1 TB free disk, **1,392 rows/day at 275 B = 0.37 MB/day, ~7.3 yr to 1 GB**,
  InfluxDB engine 14 MB; `dbstat` puts 32.94 of 33.61 MB in the single `archive` table. HLF's
  DEC-0156/0174 **method** transfers and its **conclusion** does not — DEC-0174 justified retention
  on the working set at ~8.0 M hot rows against *this same 3.69 GiB box*, and we have 66× fewer
  rows. Three further grounds: the `archive` table is the deliverable rather than a regenerable
  diagnostic (a passively intercepted station cannot backfill); upstream already bounds long reads
  by aggregation (114 `archive_day_*` tables, ~0.1 MB); and the one cost this DB's history documents
  is CoW fragmentation, for which retention is the wrong lever (`chattr +C` queued, DEC-0092,
  confirmed unapplied). Because accept-and-monitor is worthless as prose (DEC-0040), the reversal
  condition ships as code: the soak reports the archive against **10% of MemTotal** (~386 MB, ~2.6 yr
  out) and crossing it reopens the DEC. The **InfluxDB half is deliberately left open against the
  dashboard** (DEC-0010) — weewx proposes no horizon for a shared bucket.
- **Campaign B watch: block 12 of 32**, `A→B` swap on time at 18:05:02, settle 136 s (n=7, still not
  a trend). STOP/lock absent, arm `B` live, square through `08-23T00:05`.
- **Recorded as a lead, not a finding:** at 19:16 EDT — inside DEC-0094's significant 18:00–21:00
  band — NAS loadavg was **9.05/11.39/8.75** on 4 cores, driven by ~220% CPU of `chrome-headless`
  (coffee-radar) plus ~14 MB/s sustained writes on `md2`. No process was in `D` state and weewxd's
  threads were all `S`, so tenant load is established but *blocking* is not — which is precisely
  blocker 1's open question. One instant is not a probe; sampling across a window is the next step.

## [S86] — 2026-08-17 — Watch-checkpoint discipline, LNA hardware history documented, scheduled ROADMAP reconciliation

- **Three daily-watch checkpoints through campaign B block 11, plus a dated hardware timeline in
  `CONSTANTS.md` — PR #203, merged.** `BOOT.md` now carries the night-3 finding: the reception-floor
  PAUSE pattern that hit ~02:15–02:45 on nights 1–2 shifted to ~03:25–04:20 on night 3 (4 cycles,
  not 2–3) — still n=3, still needs a proper test, but the shift argues against a pure tick-grid
  artifact. `CONSTANTS.md`'s Hardware/site section gained a dated timeline (station live 05-01,
  antenna 05-16, LNA ordered 05-27/activated ~06-01, anemometer replaced 06-16/17, LNA removed
  08-02) and dropped the stale "+ inline LNA" claim — the LNA has been out since 08-02, not
  present as the line previously implied. Prompted by an owner question re-examining whether the
  current elevated RF-dead episode rate is caused by the LNA removal: it isn't, directly — DEC-0083's
  onset (08-10 23:56) is 8 days after removal, and the intervening week was the quietest stretch in
  the whole 30-day record. Attribution among campaign B's high-gain arms / v2.0.12 / weather stays
  open, unchanged from DEC-0083.
- **ops#157 (VPN heads-up) closed** — the owner confirmed being back home off VPN, and NAS access
  was verified clean throughout the session (nasctl, ssh-backed calls, soak checks, no timeouts).
- **weewx-rtldavis#74 and #44 retroactively communicated** — both had been closed with zero
  comments (S52 and S43 respectively). Traced each to its actual fixing commit (`0b1ef85` for #74's
  calm-windDir log-level fix, `973235b` for #44's windchill/cloudbase fields, the latter's own
  commit message citing #44 directly) and added a comment naming it, rather than leaving the
  closure unexplained. Prompted by an owner ask to audit "any other issues we've closed" for the
  same gap, not just the one named.
- **`docs/ROADMAP.md`'s scheduled S86 reconciliation ran on time (tripwire: "by S86").** One stale
  item found and fixed: the freeze P0 item still stopped at DEC-0088's S80 rate correction and
  never picked up **DEC-0094 (S85)** — the hour-of-day split that refutes the nightly-maintenance
  hypothesis but finds the evening 18:00–21:00 window significant instead (P=0.0027). Everything
  else on ROADMAP verified current against DECISIONS.md/CHANGELOG.md/BOOT.md. Next tripwire: S96.
- **Board review confirmed nothing else is currently actionable for weewx** — checked the
  cross-project "Claude Code work" board (192 items, 9 not Done) directly rather than relying on
  `BOOT.md`'s own list. Everything weewx-relevant is either finished-and-queued for the v2.0.14
  deploy window (#144, #172, #158), explicitly not-owed (ops#169), or deliberately deferred
  (ops#173). **ops#175 (archive/InfluxDB retention policy) is the one real open item** — scoped
  for S87 on Opus (see `BOOT.md`'s job list for the reasoning).

## [S85] — 2026-08-16 — DEC-0093's gated half shipped (and its deploy plan was wrong); the NAS-LEASE spec reviewed; a new 02:15 watch

- **`current.json` cadence implemented — the dashboard answered dash#430 with 60 s and asked us to
  ship it.** `[LoopJsonWriter] current_interval` (default 60 s) throttles `current.json` only;
  `loop-data.txt` stays per-packet behind its hard 30 s liveness gate. First packet of a run always
  writes the snapshot; a failed write does not advance the timestamp; a backwards clock step forces
  one; `0` restores the S43–S84 behavior. **Measured by simulating a full day at 2.5625 s/packet:
  33,717 → 1,405 snapshot writes, 67,434 → 35,122 renames/day, 47.9% removed.** 8 new tests
  (**279** suite). Three existing tests were reading `current.json` to assert cache/TTL semantics
  and now read the live feed — which is what they always meant.
- **The deploy plan in DEC-0093 and BOOT was wrong, and checking caught it: `loop_json_writer.py`
  is MOUNTED, not baked.** `nasctl inspect` shows `<project root>/loop_json_writer.py` bind-mounted
  `ro` over the venv copy, and **the Dockerfile never `COPY`s it** — so "ships with the v2.0.14
  image cut" would have been **a silent no-op with a green checkmark** (DEC-0046's exact failure).
  Deploy is a file copy to the **project root** plus a restart; the copy in `weewx-data/bin/user/`
  is a **decoy**. `CONSTANTS.md`'s deploy-layer table did not list this file at all — now fixed,
  with `nasctl inspect` named as the authoritative per-file check.
- **Reviewed coffee-radar's NAS-LEASE spec (ops#169, for OPS-DEC-0107).** Seven findings, all
  adopted. The consequential one: the draft had Campaign B ending **08-22** and recorded a
  coffee-radar sweep as "HELD past 08-22" — the square actually runs to **08-23T00:05**, so acting
  on it would have dropped the box's heaviest foreign job into block 31/32, in the same evening
  window their own §8 ranks as most implicated. **That same bare date was also in coffee-radar's
  own `BOOT.md`/`BACKLOG.md`**; reviewing a document caught a live hazard in a neighbour's handoff.
  Also: `rx_experiment.lock` is ours, not HLF's; and §1's "CoW churn is unreachable by any
  tenant-side lever" was corrected to "unreachable by any *scheduling* lever — reducible by
  emitting fewer metadata operations," since our own cut is the counter-example.
- **Answered a question HLF's phase timeline made askable: is weewx a victim of their nightly
  window? Not detectably.** RF-stall episodes 4/15 in-window vs 2.9 expected (P=0.32), n=15 over
  31 days — the **second** independent failure mode to return a negative for that window after
  DEC-0094's freezes. Power caveat stated. Also flagged the limitation that bounds our value as a
  witness: **DEC-0067's gap taxonomy cannot distinguish "RF quiet" from "demodulator starved"**, so
  a weewx "no harm detected" is weak evidence the protocol must not over-trust.
- ⚠️ **NEW WATCH — the ~02:15–02:45 reception dip repeated on night two, on a different arm.**
  08-15: PAUSE 02:15/02:30/02:40 (arm A). 08-16: PAUSE 02:15/02:30 (arm B). All five auto-resumed.
  **A third metric nobody has tested by hour** — DEC-0094 tested freezes and S85 tested stall
  episodes, both negative; these are *reception-floor dips*. Recorded as a watch, not a finding:
  `02:15` is partly a 5-minute-tick artifact and two nights is two nights.
- **Campaign B clean through block 6** (`A`/`B`/`C`/`D` on 08-15, `D→B` and `B→C` on 08-16), every
  swap on time, none deferred. Settle series now n=6 — 82/139/198/137/197/79 s — confirming the
  S84 "not a trend" call: all fit `~20 s + k×60 s`, k = 1,2,3,2,3,1.
- **Cross-repo, all acknowledged:** ops#169 (footprint corrected, the hard 30 s floor declared for
  the spec, the nightly-window lead retracted, coffee-radar's ~19:00 job reported with limits),
  **ops#175 filed against us** (archive + InfluxDB retention — acknowledged with measured growth
  ~0.41 MB/day / ~6.4 yr to 1 GB, **design deferred to `BACKLOG.md`**), ops#173 (BOOT cap, updated
  figure), **ops#176 filed by us** (a `push-nas-guard` false positive whose printed remedy is to
  mint a Class C token for a local docs edit), ops#157 (VPN heads-up, ack'd).
- Docs/process: BOOT job 3 stopped quoting a cap figure that went stale on every edit and gives the
  measurement command instead; a guard-misfire rung 0 recorded (re-spell before minting); BACKLOG
  gained the NAS-LEASE adoption prerequisites, including that **our house `tmp`+`os.replace` idiom
  is forbidden for a lease file** (it strands the holder's `flock` on an unlinked inode).
- Gates at close: ruff clean, **279/279** pytest, mypy clean over 49 files, secret gate clean with
  its positive control at 54/54.

## [S84] — 2026-08-15 — The dataless-write proposal was already fixed in S43; the real amplification is `current.json`, which nothing reads (DEC-0093)

- **Asked (out of ops#169) whether `loop_json_writer.py` should skip dataless LOOP packets — it
  already does, one level up.** DEC-0024 Layer B (S43) stashes freq-hop packets and `continue`s
  (`rtldavis.py:1507-1517`), so `new_loop()` cannot fire on one; `PacketFactory.create()` does still
  *yield* them, which is what the reading saw, but `genLoopPackets` filters them first. The `~40%`
  figure was `66/166` — DEC-0024's own **pre-fix** 1.66×. **Verified live rather than from source**
  (DEC-0074): the monitor reads `WINDOW: 12–18/21 (57–86%)`, `RECEPTION: 72–74%` — the post-Layer-B
  signature; the inflation's signature is this metric pinning near 100%.
- **Measured what DEC-0092 estimated:** ~22,500 loop packets/day → **~45,000 renames/day**, refining
  its `50–85k` (whose upper bound was the pre-Layer-B rate). DEC-0092's last post-square queue item
  is answered and retired in place, in the house `Update (Sxx)` pattern.
- **`current.json` has no consumer anywhere.** The eh-proxy's only `/weewx-data` read is
  `loop-data.txt`; no runtime reference exists in the dashboard, in hyperlocal-forecast, or in this
  repo outside the writer and its tests; the dashboard's roadmap still carries Cold-load Fix B's
  consumer half **open at P0**. So half of all writes go to a file nothing reads — the whole 40% the
  proposal chased, but real. **Direction: decouple its cadence to 30–60 s (~47% of renames removed),
  gated on the dashboard confirming.** Not shipped; **no code changed** (PRINCIPLES §8, DEC-0014).
- **Recorded why content-based suppression is rejected, so it is not re-proposed.** The eh-proxy
  503s at `now - dateTime > 30` and the dashboard reads that 503 as its one proof the station is
  down, while `wind_speed` is set unconditionally including `0.0` when calm — a calm night would
  report a **healthy station as offline**. The "suppression is more honest" argument inverts
  DEC-0006/0053's two independent freshness axes (per-field TTL vs feed liveness).
- **Doc contradiction corrected:** INTERFACES §1 and the writer's docstring had claimed since S43
  that the dashboard fetches `current.json` at boot; it never did. INTERFACES §1 now also records
  the **30 s liveness gate** — DEC-0092 called loop-JSON "contractually fixed" without the number
  that makes it so. **Cross-repo reconciliation still owed** (weewx documented the whole feature as
  done; the dashboard holds the accurate half).
- **Link declined:** DEC-0068 measured the main thread `S`, never `D`, during a load-12 freeze, so
  less writer I/O is **not** evidence toward the freeze blocker (DEC-0067/0068).
- Docs only, plus a docstring in `loop_json_writer.py` (no behavior change).
- **Amended same day (S84b) — the NAS came back in reach and the square was verified after all.**
  `H -> A` at `00:05:01` (`arm A live and healthy` `00:06:23`), `A -> B` at `06:05:01` (healthy
  `06:07:20`); on arm **B**, no STOP, no PAUSE. **DEC-0087/0089 got their first live exercise and
  held:** one ~20-min blackout (02:00–02:22, reception `30→2→16→1→0%`) produced **three**
  pause/resume cycles as the 30-min mean lagged the recovery, and **pre-DEC-0087 the first trip
  would have been a sticky STOP that killed the block unattended.** Resumes 2 and 3 came from
  `recovered_since()`'s second path (`RECEPTION: 73% [OK]` at 02:31:43 / 02:41:44) — **DEC-0089's
  fix is what carried them**, since only one `RECEPTION RECOVERY` edge line exists. Whether the
  blackout was RF or a process freeze is **not established** (DEC-0067: both read identically on
  this metric) and it sits inside DEC-0092's nightly heavy-I/O window — logged as blocker 1's lead,
  not scored as an RF result. S84's "NAS unroutable" note was true when written and is now stale.
- **Later the same day (S84d, DEC-0094) — the hour-of-day freeze split ran, at zero prod cost, and
  refuted the lead it was meant to test.** DEC-0092 deferred it post-square as "a heavy sweep";
  that priced a *fresh* `freeze_baseline.py` run, but the script prints every individual event by
  design and those listings survive in session transcripts, so the split was arithmetic over
  already-collected data — no ssh, no archive query, no load on the square. **Nightly maintenance
  window (00:10–04:30): 9 of 40 freezes vs 7.2 expected, P=0.29 — it explains nothing.** The
  evening does: **18:00–21:00 = 12 vs 5.0 (P=0.0027)**, coffee-radar's ~19:00 window 7 vs 2.5
  (P=0.011), over 10 distinct dates — turning DEC-0068's "n=1, not a base rate" into **30% of
  freezes in 12.5% of the day**. Stated with its limits: found post hoc, and the omnibus X²=30.8
  (df=23, crit 35.2) does **not** reject uniformity, so it corroborates DEC-0068 rather than
  proving it. Used the **DEC-0088-corrected run only**, verified by a positive control (the
  documented 08-12 19:55 restart is absent from it, present in the pre-fix runs) and by parsed
  count matching claimed count. **Side result: the 08-15 02:00–02:22 blackout was RF-dead, not a
  freeze** — three `rtldavis process stalled` lines sit inside it, which is DEC-0067's own rule;
  S84b's open question closed by one grep. Blocker 1 stays open — mechanism still unproven.
- **Cross-repo brought current at close (S84e).** **ops#169** updated with both DECs: our 08-14
  footprint figure corrected (`~45k`, not `50–85k` — the upper bound was a pre-fix rate), **~47%
  declared removable unilaterally with no lease at all**, `loop-data.txt` declared a **hard 30 s
  floor** for the lease spec (a deferral past it is a consumer-visible outage, not a preference),
  the nightly-window freeze lead **retracted** from our side of that thread, and coffee-radar's
  ~19:00 job reported as correlating with 30% of our freezes — limits stated, no schedule change
  requested. **ops#173** (BOOT over cap) acknowledged with the measurement and the post-square plan,
  plus the general point that a repo running a live time-boxed experiment exceeds a static cap
  structurally, which is a different condition from neglect. **ops#157** (owner on VPN through
  ~08-16) acknowledged — it explains this session's NAS gap, and weewx re-derived that condition
  instead of reading the heads-up that already said it. **dash#430** filed, awaiting their answer.
- **S85: dash#430 answered 60 s, so DEC-0093's gated change is IMPLEMENTED (not yet deployed).**
  `[LoopJsonWriter] current_interval` (default **60 s**) throttles `current.json` only;
  `loop-data.txt` stays per-packet because its `dateTime` sits behind the 30 s proxy liveness gate.
  First packet of a run always writes the snapshot (a restart republishes immediately), a failed
  write does not advance the timestamp (one transient failure can't suppress it for an extra
  interval), a backwards clock step forces a write, and `current_interval = 0` restores the
  S43–S84 behavior. **Measured by simulating a full day at 2.5625 s/packet: 33,717 → 1,405
  snapshot writes, 67,434 → 35,122 renames/day, 47.9% removed** — matching DEC-0093's projection.
  8 new tests (23 in the file, **279** suite); three existing tests were reading `current.json` to
  assert cache/TTL semantics and now read the live feed, which is what they always meant.
- **The deploy plan was wrong and the check caught it: `loop_json_writer.py` is MOUNTED, not
  baked.** `nasctl inspect` shows `<project root>/loop_json_writer.py` bind-mounted `ro` over the
  venv copy, and **the Dockerfile never `COPY`s it** — so "ships with the v2.0.14 image cut", which
  both DEC-0093 and BOOT had said, **would have been a silent no-op with a green checkmark**
  (DEC-0046's exact failure). Deploy is a file copy to the **project root** plus a restart; the
  copy in `weewx-data/bin/user/` is a **decoy**. `CONSTANTS.md`'s deploy-layer table did not list
  this file at all — now fixed, with `nasctl inspect` named as the authoritative per-file check and
  the two other mounted modules added.
- Gates at close: ruff clean, **271/271** pytest (**279/279** after S85's tests), mypy clean over
  49 files, secret gate clean with
  its positive control at 54/54. Campaign B verified live at 10:39 EDT (arm B, reception 69–77%
  [OK], no STOP/PAUSE/lock). PR #158 deliberately still held for the v2.0.14 post-campaign cut.

---

## [S83] — 2026-08-14 — ops#169 answered: our yield is a near-no-op, the box has a nightly heavy window, and the filesystem was wrong (DEC-0092)

- **Answered coffee-radar's shared-NAS I/O lease proposal (ops#169), measured rather than
  estimated.** `binding` defaults to `archive`, so InfluxDB gets **1 record/60 s**; total weewx
  write bandwidth is order **tens of MB/day**. Our shape is metadata-heavy (~50–85k renames/day
  via `loop_json_writer.py`), not bandwidth-heavy — so downshifting frees almost nothing, and the
  counterpart accepted a near-no-op courtesy side as the honest answer rather than a refusal.
- **Drew the data-integrity line ops#169 asked us for.** InfluxDB deferral is safe — the *live*
  config was checked, not the shipped defaults: `[[Influx]]` sets only connection keys, so prod
  runs `stale=None` / `max_backlog=1e6` and a 30-min defer queues ~30 records against a million.
  The **SQLite archive write is the red line** (engine waits a hardcoded 120 s then restarts;
  `timeout=30` exists because a *reader* holding the lock 6 s once cost 5–10 min of prod), and
  loop-JSON is contractually fixed by INTERFACES §1.
- **Corrected a mechanism both sessions had adopted: `/volume1` and all 25 mounts under it are
  btrfs — only DSM's `/` is ext4.** There is no `jbd2` in either tenant's data path. Caught by
  reading `/proc/mounts` instead of inheriting the claim, *after* it was already in our draft.
  The strategic conclusion survives (`btrfs-transaction` is equally outside ioprio); write
  amplification is higher than the ext4 model predicts, and the mount is `relatime`, not
  `noatime`. Attribution independently confirmed impossible — `blkio/` holds only `reset_stats`,
  and cgroup v2's `io.*` postdates this 4.4.302+ kernel.
- **Found the box's real schedule, which outranks the protocol.** A sibling tenant's nightly
  maintenance runs **00:10 → ~03:00–05:10 every night** (6 nights verified, median ~4h20m), so
  **~72% of every 00:05 campaign block** sits under a heavy-I/O window nobody knew about; two more
  jobs fire at 00:05 itself, one of them our own `weewx-monitor` logrotate — the same minute as
  the swap's `harvest()`, which reads that log and its rotation. Task-id → owner mapping recorded
  in the gitignored local-infra doc; BOOT's copy is genericized (public repo).
- **Comparability is safe, and said so explicitly:** the square is a 4×4 Latin square run twice,
  so each arm takes the midnight slot exactly twice and a slot-level confound is absorbed by
  construction. The exposure is midnight *swap reliability* and *variance*, both uniform across
  arms. Job 1 gains a check-the-cluster-before-blaming-the-S82-state-machine caveat.
- **Blocker 1 gains a testable lead** (DEC-0067/0068): split freeze timestamps by hour-of-day
  against that nightly window. No prior analysis controlled for it because nobody knew it ran, and
  it is testable against rotated logs we already hold. Deferred post-square — `freeze_baseline.py`
  is itself a heavy sweep and would add load to the measurement it is explaining.
- **Coordination landed before any protocol constant was locked, via schedule disclosure rather
  than throttling:** the counterpart held its 12–20 h sweep past 08-22 and moved its 6-hourly job
  off :00 to :30 before block 1. Both verified here by process evidence, not relayed — the id=11
  output directory stamped 18:31 proves the new schedule *executed*, DEC-0074's principle applied
  to a neighbour.
- **Recorded but deliberately not acted on:** SQLite-on-CoW favors WAL, but the ~300% figure is
  single-writer and ours is the multi-process shape that bit us — **DEC-0071 stays closed**.
  `chattr +C` on the archive DB queued instead, with `noatime`, moving our logrotate off 00:05,
  and the freeze split. Also flagged for a design pass of its own — dataless freq-hop loop packets
  (DEC-0024) republish byte-identical loop-JSON under a refreshed timestamp.
- Gates: pre-commit ran ruff/mypy (no code files), tests, and the secret gate — plus a **positive
  control on `check_secrets.sh`**, which first appeared to show a seventh hole in the `_apppw`
  rule and did not: the payload used a key name outside `_key`. With the real `GMAIL_PASS` shape
  both quoted and unquoted forms tripped, confirming the DEC-0084 fix works. A *failing* positive
  control needs the same scrutiny as a passing one.

---

## [S82b] — 2026-08-14 — Owner's reframe used: #180 deployed pre-square, #172/#144 merged for v2.0.14 (DEC-0091)

- **"We haven't started our campaign yet"** — the owner's reframe of the S82 close: block 1 was
  still hours out, so pre-block-1 is the RIGHT window for instrument changes, not a violation of
  mid-campaign discipline. All three backlog items knocked out same day.
- **PR #182 — the #180 monitor trio, merged AND deployed before the square** (scp 12:24 EDT,
  respawned pid 7625, `Monitor started` 12:25:21 — startup line after file mtime, DEC-0074): the
  open episode now mirrors to `logs/monitor_episode.state` and restores at startup (a restart
  mid-episode used to silently lose the ledger row + RECOVERY edge); log rotation voids a pending
  reset verdict instead of faking "verified effective" off the zeroed counter; `do_reset`'s
  exception path emails (it fired live at 01:56:30 that morning as a silent 15 s timeout).
  #180 closed. The whole square now runs on one monitor version.
- **PR #183 — #172 + #144, merged to `dev`, deploys with v2.0.14 post-campaign**:
  `barometer_fetch_epoch` (last *successful* WeatherLink fetch, published outside the TTL
  machinery — a staleness signal must never be omitted for being old) and honest-null
  `pressure`/`altimeter` (they carried sea-level values mislabeled as station pressure — the
  archive columns go NULL from v2.0.14; hlf#302 heads-up posted on #144). INTERFACES §1 updated;
  both issues commented and left open until the deploy.
- **v2.0.14 queue set**: weewx 5.5.0 (#158) + #172 + #144 + the `:latest` move once the square
  proves v2.0.13. Remaining #144 sliver: the +0.03 inHg offset quantification (method in the
  issue, read-only, campaign-safe).
- Mechanical: #183 branched before #182 merged → branch protection refused the merge until
  `gh api .../pulls/183/update-branch` + CI rerun (now a BOOT gotcha). ROADMAP's "lockfile is
  post-campaign work" corrected (DEC-0090 shipped it pre-square).
- **weewx 5.5.0 pre-adoption review: GREEN** (same day, post-close) — source-diffed all 11
  runtime-chain files between v5.4.0/v5.5.0 rather than trusting the changelog: 7 byte-identical
  (incl. `accum.py` — the campaign metric's write path — `restx.py`, `units.py`, the logger);
  weedb's `timeout` read + pragmas-as-mapping **verbatim** (DEC-0070/0071 behaviors survive);
  `manager.py`'s new locked-DB retry layers benignly atop our 30 s timeout. Verdict + v2.0.14 cut
  checklist on PR #158 — the bump is now execution-only.
- **#144's offset third quantified: station-side, ~+0.04 inHg high** — 8 days of archive
  barometer vs four METAR references (+0.038…+0.049, conversion validated against reported-SLP
  anchors), agreeing with hlf#302's seven forecast models; stable daily, ±0.015 diurnal wobble.
  Knob identified: the WeatherLink console's configured elevation (~37 ft equivalent) — owner
  check filed as ops#168; hlf#302 answered in full. One authorized read-only archive query
  (mint path), no repo changes.
- **ops#167 filed**: lead-time heads-up to HLF that archive `pressure`/`altimeter` go NULL at
  the v2.0.14 deploy (it reads those columns; hlf#302 adjacent).
- 20 new tests across the two PRs; **271/271** on the merged tip; all gates green throughout.


## [S82] — 2026-08-14 — The state-machine audit: five apparatus fixes shipped (DEC-0090), monitor package filed

- **The audit BOOT ordered ran (user's Fable 5 pick)** over `ops/rx_experiment.sh`'s
  guard/tick/abort/pause/resume machine and `weewx_monitor.py`'s alerting/reset logic, hunting
  the DEC-0088/0089 edge-vs-level class. Every finding verified against live logs and the
  episode ledger before any fix was proposed; two clean checks recorded so they aren't re-derived.
- **Five `rx_experiment.sh` defects fixed (PR #179, merged + deployed 10:38, sha `4438a2a3…`):**
  resume aligned to the pause floor (the occupied [50,60) band could enter a pause it could never
  exit → needless ceiling abort); `recovered_since()` + the guard's floor mean read the rotated
  monitor log (rotates 00:05 — the exact swap minute); a due swap defers during an active pause
  instead of swapping into the episode's health-check abort (BASELINE exempt — property #5);
  the guard stands down after the BASELINE self-terminator (was armed forever between campaigns);
  tick/guard/abort serialize behind a lock (the 08-11 02:05:03 guard/tick interleave was on
  record, and a full-budget health_ok outlives the 5-min cron period).
- **`soak_check.sh`'s reset counter was dead since S67** — it grepped `RESET: triggering`,
  retired by DEC-0074's rename; the impossible "1 ineffective of 0 fired" on this morning's soak
  was the tell. Now counts `RESET: running`.
- **Monitor-side trio specced and deferred to #180 (tier:mid):** memory-only episode state (a
  restart mid-episode loses the ledger row + RECOVERY edge), midnight rotation zeroing
  `wu_bad_windows` and falsifying pending reset verdicts, and `do_reset`'s email-less exception
  path (timed out live at 01:56:30 this morning).
- **Ops lane:** #163 closed (MANIFEST carry settled — OPS-DEC-0101/ops#158 precedent), ops#165
  filed (tier-sweep needs an exemption for decision-blessed carries), MANIFEST's self-measurement
  de-drifted to ~1.1K.
- **Morning square watch:** overnight STOP refusals were S81's already-resolved blockade tail;
  both 01:55/01:59 stalls diagnosed RF-class (known DEC-0081/0083 phenomenon); reception 71%
  within 1 sd of baseline. Holding on H all session; arm A due `08-15T00:05` on the new code —
  its first live exercise.
- 9 new tests (one renamed to the new semantics); 39/39 `test_rx_experiment.py`, 251/251 full
  suite; ruff/mypy/secret gate clean, positive control caught both planted payloads.


## [S81] — 2026-08-14 — DEC-0087's first live pause/resume exercise found a bug in itself, fixed as DEC-0089

- **Arm A never swapped in overnight.** Session start (~08:15) found `current_arm()` still `H`
  and a STOP sentinel blocking every tick since `21:45:01` the night before — arm A's `00:05`
  slot never happened.
- **Reconstructed against the actual logs, not assumed.** Three short reception dips
  (2026-08-13 19:14–19:38) tripped DEC-0087's `PAUSE` at `19:40:05` — its first-ever live firing.
  Reception then read healthy continuously (`[OK]`, 65–81%) from `19:43` for almost two hours,
  but `recovered_since()` only checks for a `RECEPTION RECOVERY` log line — an ALERT→RECOVERY
  *edge* — and none fired again because reception never dropped low enough to re-trigger a fresh
  ALERT. The pause rode the full 120-minute ceiling into `ABORT: RF-dead pause exceeded 120min
  without recovery` at `21:45:01`.
- **DEC-0089 — the fix**: `recovered_since()` now also checks the monitor's ordinary periodic
  `RECEPTION: NN% ... [OK]`/`[LOW]` line (logged every ~5min regardless of ALERT state) as an
  additive level-signal fallback to the edge check — same lesson as DEC-0088, one session later:
  a just-shipped correction carried its own undiscovered blind spot. 4 new tests, including the
  exact incident fixture with its assertion flipped (the regression test). 30/30
  `test_rx_experiment.py`, 242/242 full suite.
- **Recovery**: schedule shifted +24h a third time (DEC-0082's unchanged mechanism) — arm A now
  due `2026-08-15T00:05`, square `08-15 → 08-23T00:05`. Fix + shift deployed together to the NAS
  (sha-verified) before clearing STOP, so no tick could land between a fixed-but-unshifted or
  shifted-but-unfixed state.
- **Post-clear log silence traced and confirmed as expected**, not a second incident: `due_arm()`
  returns the pilot block's trailing `H` row (never a literal `NONE`) until the square's first
  row arrives, matching `current_arm()`, so `tick`'s silent no-op runs for as long as nothing is
  due. New `BOOT.md` gotcha.
- Shipped as PR #177, merged to `dev` (`6079053`).
- **Next session scoped**: a dedicated audit of `rx_experiment.sh`'s full guard/pause/abort/resume
  state machine + `weewx_monitor.py`'s alerting/reset logic, hunting for other edge-vs-level
  signal mismatches — two sessions running with one each (DEC-0088, DEC-0089) is a pattern worth
  a deliberate pass. User's explicit choice: run it on **Claude Fable 5** (judgment/investigative
  work per AGENT-ECONOMY.md).

---
## [S80] — 2026-08-13 — freeze_baseline.py's ad hoc-restart blind spot found and fixed (DEC-0088)

- **Freeze-rate corroboration (job 3) surfaced a tool bug, not a trend.** The 48h window S79
  flagged had cooled to unremarkable on re-run, but 24h/36h had newly gone elevated (95.9th/94.0th
  pct) — until the freshest event (2026-08-13 10:24–10:27) turned out to line up almost exactly
  with this session's own tick log (`10:25:01 tick: swapping A -> H`), the S79 abort's self-heal
  restart, not a freeze.
- **Root cause**: `classify()`'s swap detection only recognized the fixed 0/6/12/18 schedule — no
  way to see a restart `rx_experiment.sh` triggers off it (an abort's baseline restore, a
  DEC-0087 pause escalation, a tick self-heal). Verified directly against the log, not just
  inferred: the 2026-08-12 "19:55 freeze" already on record **is** the `19:55:35 ABORT` →
  `19:55:36 RESTORING baseline snapshot` restart's own footprint.
- **Fix**: `classify()` now also cross-references every logged `tick: swapping`/`RESTORING
  baseline snapshot` line as ground truth, padded 3min back / 12min forward. RF-dead precedence
  unchanged and re-tested against the new path.
- **Corrected reading**: 7 of 47 previously-counted "freezes" reclassified as swap — rate
  1.54/day → 1.31/day, all four rolling windows (24h/36h/48h/72h) flip from elevated/85–95th pct
  to unremarkable (49–67th pct). Not a one-off: DEC-0087 guarantees more ad hoc restarts going
  forward, so the bug's main damage was still ahead of it.
- 5 new tests (ad hoc detection, pad boundaries, RF-dead precedence over the new path, a positive
  control encoding the exact 10:24 event that found this). 17/17 `test_freeze_baseline.py`,
  238/238 full suite, ruff clean, mypy clean.
- Shipped as PR #175, merged to `dev` (`8104c30`). BACKLOG.md's S79 freeze-rate watch item closed
  out with the correction (append-only, per convention). Campaign B untouched — no NAS/container
  write this session.

---

## [S79] — 2026-08-13 — Arm-A abort reconstructed and recovered; DEC-0087 pause/resume ships

- **Arm-A swap verified** (`00:05:02 swapping H -> A`, `00:08:24 arm A live and healthy`) — S78's
  open item. Ran clean 1h20m at 66–79% reception before aborting.
- **Stall burst (DEC-0083) plateau CONFIRMED** — fourth flat reading: 48h/72h still exactly
  record-max 6/6, 24h back to 1 (68th pct), no new episode since 08-12 01:36. Freeze rate's 48h
  window read elevated for the first time (92.5th pct) — one window, not yet a confirmed trend.
- **Arm-A aborted at 01:55:02** (`30-min mean reception 43% < 50% floor`), fully reconstructed: a
  clean ~11-min RF-dead episode (01:40–01:51, `RECEPTION ALERT` → `rtldavis process stalled` →
  `RECEPTION RECOVERY: 62% avg after 9min`), the lagging 30-min mean tripping 4 minutes after
  recovery. `rx_experiment.STOP` then sat uncleared 7.5+ hours, spanning the 06:05 slot.
- **PR #171 — schedule shifted +1 day** (DEC-0082's exact recovery mechanism, applied again):
  33 square rows, verbatim arm sequence, arm A's block 1 now at `2026-08-14T00:05`. 17/17
  `test_rx_experiment.py` unmodified.
- **DEC-0087 (PR #173) — RF-dead reception dips now PAUSE instead of hard-aborting.** Scoped to
  the guard's reception-floor check only (not freezes, not tick's own write/health-check aborts).
  A floor trip writes a non-sticky `PAUSE` marker — no config/container touched — and every guard
  tick checks for `weewx_monitor.py`'s own `RECEPTION RECOVERY` line (-> auto-resume) or a
  120-min ceiling with no recovery (-> escalate to the unchanged `trip_abort()`). Schedule slots
  stay fixed either way — a paused arm just gets fewer live minutes that block, not a moved clock
  boundary. 9 new tests. 224 → 233 tests.
- **PR #170 — BOOT/BACKLOG write-up merged.** All three PRs (#170, #171, #173) merged to `dev`
  same session; #171/#173 touch disjoint regions of `ops/rx_experiment.sh` and merged independently.
- **Deployed and verified**: `ops/rx_experiment.sh` scp'd to the NAS (sha-matched), `STOP` cleared
  (Class C, owner-approved). The very next tick self-healed `swapping A -> H` (the shifted schedule
  correctly overrode the stale live-state A), `arm H live and healthy` at 10:27:19. `soak_check.sh`:
  15 pass / 2 warn / 0 fail post-deploy, both warnings known/expected shapes.
- Green gate: ruff clean, 233 tests, mypy clean on 48 files. `BACKLOG.md` gets a new standing
  watch for the pause/resume incident-tracking half of the original ask, deliberately deferred
  until the mechanism has real data.

---

## [S78] — 2026-08-12 — Guard abort reconstructed and cleared: first freeze pair to gate the campaign

- **`rx_experiment.STOP` fired at 19:55 local** (`30-min mean reception 47% < 50% floor, arm H`).
  Reconstructed via `ops/freeze_baseline.py`: two back-to-back FREEZE events (19:46→19:50 240s,
  19:55→20:02 420s) — no stall line, correctly absent from `stall_baseline.py`'s episode list.
  **First known freeze pair severe enough to trip the campaign's own abort floor** (freezes were
  characterized as "gates nothing", DEC-0081/0083). Reception recovered to 67–84% within 10 min,
  healthy since.
- **STOP cleared** (owner-approved in chat, Class C), well ahead of the `2026-08-13T00:05` arm-A
  due time — no schedule shift needed this time, unlike DEC-0082. Landed in PR #168. Treated as a
  `BOOT.md`/`BACKLOG.md` finding, not a new DEC — refines an already-decided characterization
  rather than making a new design call.
- **Stall burst (DEC-0083): third flat reading (S76/S77/S78)** — 48h/72h still record-max 6/6 with
  no further growth, starting to lean plateau per S77's own threshold. 24h dropped to 1 episode
  (68th pct); acute rate quiet ~19h at check time.
- `ops/soak_check.sh`: 16 pass / 1 expected warn / 0 fail. Green gate: ruff clean, 224 tests, mypy
  clean on 46 files — no code touched this session, docs only.
- **Swap verification still open**: arm-A due `2026-08-13T00:05` had not yet occurred at session
  close — carried to S79.

---

## [S77] — 2026-08-12 — Freeze rate gets its own tool (DEC-0085); barometer's WeatherLink-passthrough provenance documented (DEC-0086)

- **DEC-0085 — `ops/freeze_baseline.py` ships**, completing DEC-0083's explicitly-flagged
  follow-up (BOOT/BACKLOG both warned the freeze number would decay without it). Reuses
  `stall_baseline`'s stall data and `campaign_analyze`'s DB constants rather than re-deriving
  either; `window_start()` extracted out of `stall_baseline.py` (+2 tests) so both tools share the
  same left-censoring boundary. Live run reproduces DEC-0083 almost exactly (21 RF-dead/12
  arm-swap/45 freeze exact, median 240s exact, rate 1.48 vs. 1.49/day). New: a rolling-window
  placement for the freeze side the original one-off never had — unremarkable across 24h–72h,
  moving independently of the same-day record-max stall reading. 210 → 224 tests (+12 in the new
  file, +2 for `window_start()`).
- **DEC-0086 — `barometer_inHg` is an unflagged, already-corrected WeatherLink passthrough.** The
  VP2+ ISS never transmits pressure over RF; `pressure_service.py` polls WeatherLink's cloud API
  and relays its already sea-level-corrected `bar_sea_level` as-is, with no `_qc` flag distinguishing
  it from RF-derived fields. Documented in `docs/INTERFACES.md` §1; cross-posted as a heads-up to
  `eaglehunt-weather-dashboard#377` and `eaglehunt-ops#162`.
- **eaglehunt-ops housekeeping:** #158 closed (duplicate of already-settled #153/#155 under
  OPS-DEC-0101), #160 closed (scope complete — see DEC-0085 above, plus the standing-watches sweep
  was already done per BACKLOG.md), #159 commented (weewx's open bullet answered by DEC-0083/0085).
- **`docs/CONVENTIONS.md`:** stopped hardcoding a model name in the commit-trailer convention
  (caught stale — said `Opus 4.8` while the session ran Sonnet 5).
- **Housekeeping:** 10 stale, already-merged feature branches deleted (local + remote,
  `s73`–`s76`-prefixed) — none touched `origin/dependabot/pip/weewx-5.5.0`, still deliberately open.

---

## [S76] — 2026-08-12 — Stall rate measured, not eyeballed (DEC-0083); secret gate's sixth hole closed (DEC-0084)

- **DEC-0083 — S75's "trending hot" survives measurement, but its evidence did not.** Over 30.5 d
  and 31 rotations the 48 h and 72 h windows ending now hold **6 episodes each, the record
  maximum** (98th pct); 24 h is 96th pct but off its peak of 5, so the burst may be easing.
  **The unit had to be fixed first**: a stall *line* is not an event — the 150 s watchdog re-raises
  every ~3 m 40 s, so 08-02 is **21 lines and one episode**. Clustering gives 15 episodes, stable
  at 30/45/60 min, and **reproduces DEC-0081's independently-derived boundaries** for the 08-10/11
  night exactly.
- **Three corrections to how S75 reached it.** Onset is **08-10 23:56**, not ws.5 — the v2.0.13
  container started 18:05 local on 08-11, so **5 of the 6 burst episodes predate it**; the ledger's
  19-hour field of view was mistaken for the phenomenon's onset. Not a simple LNA effect either:
  LNA-in 0.40/day → LNA-out 08-02→08-10 **0.13/day, the quietest stretch in the record** →
  08-10→now **2.43/day**. And "2→4 ledger rows" **compared two instruments** — row 3 is
  drought-only and `DATA DROUGHT` appears zero times in every pre-ws.5 log.
- **DEC-0081 amended: its LNA dates are wrong.** "08-02 and 08-06 were LNA-in" — the LNA came out
  **mid-ERR-0005, early 08-02** (S61: none existed yet; S62: "first honest no-LNA telemetry
  accruing"; S70: "out since 08-02"). **08-06 was LNA-OUT**; 08-02 only straddles. The clause's
  point survives on 08-02 alone.
- **New sanctioned readout `ops/stall_baseline.py`** (+7 tests, 203 → 210) — states its
  left-censored window and threshold sensitivity every run. Building it exposed a bias in its own
  first cut: anchoring "current" on the last stall guarantees the window contains it, so the check
  would read hot right after every episode. Fixed to anchor on now.
- **Secondary sweep (ops#160 job 3): freeze rate measured at 1.49/day, median 240 s** against the
  inherited "~once/day, ~3.5 min" — right order of magnitude, **~40 % understated**, refines rather
  than overturns. **A 60 % confounder was removed first**: the S37 backfill's `interval=15` rows
  read as 28 phantom 900 s freezes, caught only because individual events were printed rather than
  the summary rate. **Co-rejection watch re-verified 0 through 08-12 and positive-controlled**
  (stale at "through 08-01"); phantom-rainRate already instrumented in `soak_check.sh`.
- **DEC-0084 — secret gate hole class 6, found free by the routine pre-commit positive control.**
  `_assign` needs 8+ *consecutive* value chars and a Google app password breaks that run every 4;
  `_apppw` required **quotes**. So an **unquoted** app password was missed in every spelling —
  and unquoted is the **native form of `weewx.conf` (ConfigObj) and `monitor.env`**, the two files
  that must never be committed. Gitignored, so nothing leaked. **It survived S68 because that fix
  planted the quoted literal, went green, and never asked the neighbouring spelling.** Fix is
  key-anchored (an unanchored shape match would flag ordinary English prose); **one allow-list
  widening refused** — five of the six historical holes were allow-list defects, so
  `monitor.env.example`'s placeholder moved to `YOUR_GMAIL_APP_PASSWORD` instead. Harness holes
  27–29, **54 passed / 0 failed**. **The new detector then went red on the DEC entry documenting
  it** — the first draft wrote the literal shape into `DECISIONS-FULL.md`, and the gate caught it,
  exactly as `check_secrets.sh`'s own comment predicts. A decision log earns no exemption
  (DEC-0045); both spellings are now described rather than written.
- **ops#147 closed out from this repo's side** — weewx's §11 adoption named (DEC-0072 for item 1,
  DEC-0074-as-corrected for item 3); it was the one thing the thread was still waiting on here.
- Green gate: ruff clean, **210 tests**, mypy clean on 44 files. *A first mypy run reported
  "Success" on 42 files while silently skipping both new ones — `git ls-files` lists tracked files
  only. Staged first, then re-ran: 5 real errors.*

---

## [S75] — 2026-08-12 — Campaign B square recovered from an overnight stall; DEC-0080 verified clean

- **Discovered mid-session-start: the square never swapped to arm A.** A third same-day RF-dead
  episode (18:05, 08-11) tripped the sticky STOP six minutes after S74 verified the day's second
  episode "without re-tripping" — the STOP sat unnoticed through the entire scheduled 00:05
  A-arm swap, blocking every 5-minute tick for ~15h until this session's start.
- **Recovered via DEC-0082**: shifted the entire remaining square schedule +24h (not a
  partial-day restart, which `test_schedule_is_a_balanced_latin_square` rules out) — full 8/8
  per-arm balance preserved, 17/17 tests pass unmodified. Deployed to the NAS, sha-verified, STOP
  cleared. Arm A now due `2026-08-13T00:05`; square runs through `08-21T00:05`.
- **DEC-0080 dark-hours radiation verification: clean.** 495 archive rows across the 08-11→12
  dark window (21:00–05:30), zero non-zero radiation readings.
- **Stall rate: 2 → 4 episodes** in `episodes.log` since the ws.5 deploy (two new overnight,
  01:34–01:45 the longest yet at 647s) — eyeballed as "trending hot," which is itself the trigger
  for a properly baseline-measured follow-up (ops#160, S76).
- **`soak_check.sh`: 14 pass / 3 warn / 0 fail** — reception 67%, no-banner (cosmetic),
  USB-reset-ineffective (expected DEC-0081 signature).
- **Guard/classifier friction on the schedule deploy**: `scp` hit three independent layers before
  landing — the expected Class C confirm, `secret-read-guard.sh` re-blocking even with its own
  documented `command`-prefix escape hatch already applied (looks like a bug), and a bare
  classifier denial on an `rsync` substitution with no mint path. Owner ran the final `scp` by
  hand.
- **ops#160 filed**: S76 scoped to apply the "baseline-measured, not eyeballed" pattern (ops#159)
  to this repo's own standing watches, stall rate first.

---
## [S74] — 2026-08-11 — Day's second guard abort root-caused and cleared; square proceeds on schedule

- **09:55 guard abort root-caused**: reconstructed the exact 6-sample mean from `weewx_monitor.log`
  (70/30/70/71/20/16 → 46), matching `30-min mean reception 46% < 50% floor (arm H)` exactly. Traced
  to an RF-dead episode 09:33–10:04 (pre-ws.5): USB reset attempted and logged **ineffective**,
  recovery uncorrelated with the reset — the DEC-0081 signature, not a new failure mode. STOP
  cleared (owner-confirmed in chat, Class C mint); verified stable through a second live episode
  (17:52–17:59, also self-recovered, also non-mute) without re-tripping. Square proceeds on
  schedule, 08-12T00:05.
- **Monitor respawn and `dev`→`main` promotion confirmed** (both landed before this session's
  investigation, likely the concurrent session): pid 22206 (was 8810), `Monitor started` 15:29:02;
  PR #161 merged, `prod-baseline-20260811` tagged.
- **`ops/soak_check.sh` run: 14 pass / 2 warn / 1 FAIL** — repeated rtldavis stalls (2, both
  post-ws.5, both non-mute RF-class, both self-recovered <7 min). Frequency is a new, unexplained
  data point for DEC-0081's still-open characterization, not itself a regression.
- **Condensation floated as a fourth DEC-0081 candidate cause** (interference / no-LNA margin /
  site / condensation) — plausible for the one overnight episode, doesn't explain the two daytime
  ones. Unconfirmed either way.
- **Dependabot PR #158 (weewx 5.4.0→5.5.0) reconfirmed deliberately deferred** post-campaign; its
  `tests` check is also currently failing regardless of timing.
- DEC-0080 dark-hours (radiation=0) verification **still pending** — S74 found the correction live
  but dark hours hadn't happened yet at check time; carried to S75.

---
## [S73] — 2026-08-11 — GATE 2 passed; the stall mechanism captured (zombie child); DEC-0080 applied; `:latest` → v2.0.12

- **Pilot night: 2 of 5 arms, then a stall-abort — and the abort is the session's biggest win.**
  P496 ran clean (75.56 %, n=33), P449 ran (72.65 %, n=15) until a **USB-stall killed it**: the
  01:52 forensics pre-capture shows `rtldavis` a **zombie** (`Z`, `wchan=do_exit`, zero fds, no
  replacement) — the child died mid-block and the driver neither reaped nor respawned it, so both
  USB resets were structurally futile (a device reset cannot resurrect a dead consumer). That is a
  **third mechanism**, neither of DEC-0075's two hypotheses. Three capture sets banked incl. an
  *effective* 23:56 reset (during the HLF/coffee-radar load spike, loadavg ~25) for contrast;
  reset #2 also hit a new **15 s sudo timeout** failure mode. Guard abort at 02:05 (30-min mean
  39 % — dead air, not reception; per-minute archive stayed ~72 %), tick raced it at the same
  second (no lock — minor apparatus defect, post-campaign fix), sticky STOP converged it safely.
- **GATE 2 (owner, Fable-escalated): arms {372, 496} confirmed** — 496 ≥ 449 answers the only
  question the pilot had to answer (curve not peaking below 449); missing low arms feed no
  decision the square doesn't make itself. **STOP cleared 08:55, H hold resumed, square runs
  08-12T00:05 → 08-20T00:05 unchanged.**
- **DEC-0080 APPLIED** — the exact-code radiation zero into the live `weewx.conf` **and**
  `weewx.conf.rx-baseline`, activated by the H-swap's own restart (zero extra downtime). The
  both-files requirement was a hazard found at apply: `restore_baseline` copies the snapshot over
  the live conf at every abort/campaign-end, so a live-only apply would have been silently wiped
  — BOOT's original apply steps missed it. Third `CONSTANTS.md` deviations row added. Dark-hours
  = 0 verification due tonight (S74). Ops note filed: dashboard `eh-ui.js` floor filter now
  vestigial.
- **`:latest` moved to v2.0.12 on Docker Hub** (GATE 2 decision): config digest `9db5c1…`
  verified byte-identical across both tags via the registry API; manifest digests differ
  (S70c save→load push vs S73 daemon push — compression, not content).
- **A second budget bug found and fixed the same morning (S57's lesson, one term deeper):** the
  08:55 H re-swap was aborted at 08:58:14 as "no records" while the driver was alive and
  publishing — `health_ok`'s 180 s budget never modeled **RF acquisition** (measured ~127 s on
  this boot vs ~0 s on P449's). First archive record was due ~08:58:15; the budget missed a
  healthy swap by seconds, and would have coin-flipped every square swap. `HEALTH_TRIES` 36 → 60
  (~300 s vs the corrected ~245 s worst case: boot 25 + rf-acquire 130 + interval 60 + lag 30);
  the regression test now asserts the four-term arithmetic. The 02:11 P402 abort likely shared
  this mechanism beneath the guard race (S74 confirms). Third abort email of the day is this one.
  Also fixed in passing: `test_current_schedule_is_installable_today` went red the morning the
  campaign legitimately launched (first row in the past ≠ stale) — renamed
  `…is_not_fully_stale`, asserting the **self-terminator** hasn't passed instead.
- **The stall deep-read ran the same afternoon (owner pulled it forward) and re-diagnosed the
  class — DEC-0081.** Three read-only subagents (capture collation / night timeline / HLF +
  coffee-radar cross-correlation) + main-thread differential against the driver source: the
  device never re-enumerates, the driver's watchdog and respawns work, and the stalls are
  **RF-dead episodes** — resets are theater (~17 attempts, 0 fixes), ERR-0005's recreate-fix
  reads as episode-end coincidence, DEC-0065 vindicated. The first-draft remedy
  (auto-kill+start) was **rejected by its own differential** — restarts show the same
  evidence pattern as resets — and replaced with: reset demotion (`RESET_MAX_TRIES` 3→1),
  driver child-reaping (three stacked zombies captured; the one real process bug),
  `STALL DIAGNOSIS` / `DATA DROUGHT` self-classification, and the `episodes.log` ledger as
  the pre-registered LNA-verdict datum (owner reports for ~50–70 m/trees/walls sites).
- **v2.0.13 / ws.5 shipped same day, mid-H-hold, before the square's first block** (PR #159,
  merged tip `1530971`): NAS build `BUILD-EXIT=0`, container swap with identical
  mounts/devices/env + `BIAS_TEE=0`, ws.5 banner + DEC-0031 canary verified live, records in
  35 s, soak 15/2/0 after the ineffective-reset criterion reframe (FAIL→WARN — a criterion
  failing on now-expected behavior is the ops#147 item-6 anti-pattern). `:v2.0.13` on Hub;
  `:latest` holds at v2.0.12 until proven. Monitor deployed + sha-verified; respawn pends the
  owner's path-scoped-sudo kill (uid-1031 process — the day's one genuinely owner-run step).
  Tests 185 → 203 (+18: reap, diagnosis/drought, ledger; escalation test re-pinned to the
  single-hedge policy). CHANGES-FROM-UPSTREAM rows 12–13 (both upstreamable). Dependabot
  PR #158 (weewx 5.4.0→5.5.0) deliberately left open — no base-platform bump mid-campaign.
  ROADMAP campaign-B/v2.0.12/USB-reset rows reconciled (DEC-0057, same session).

---


## [S72] — 2026-08-10 — DEC-0080: the diode-floor fix is decided — StdCalibrate exact-code zero, config layer

- **DEC-0080 — solar radiation diode-floor correction: option A** (escalated session, per the S71
  handoff's ask). One exact-window `StdCalibrate` line (`0 if 1.75 < radiation < 1.77`,
  None-guarded) zeroes the `sr_raw=1` dark-current code; added to `weewx.conf.example` as the
  versioned, public artifact — the anti-regression mechanism the June dashboard-only fix never
  had. Option B (almanac elevation-gated service) declined: it also needs a `process_services`
  live-config edit so it escapes no config fragility, it would bake one station's calibration into
  the public image, and its dawn/dusk benefit is below the sensor's own resolution — design
  preserved in the handoff, can ride the #144 rebuild if ever wanted.
- **NAS apply deliberately deferred to post-GATE 2** (unattended pilot tonight, no dongle
  recovery, config-typo crash-loop precedent) — apply steps + verification (incl. the `sr_raw=2`
  check) in `BOOT.md`.
- **PR #155 merged** (S71 close). **ops#148 closed on the tracker** — S71's commit subject said
  closed, but the explicit `gh issue close` was missed (CONVENTIONS' `Closes #N` lesson, adjacent
  form); closed with a pointer at S72 open.
- S69 + S68c–d rolled to `CHANGELOG-ARCHIVE.md` verbatim (~3-session window). `MANIFEST.md`
  handoffs row de-counted (a literal "three" had gone stale). Green gates clean on pickup (ruff,
  185 tests, mypy 39 files).

*(S71, S70 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*

## [S71] — 2026-08-10 — ops#148/#7 closed; ERR-0005 backfilled; solar diode-floor traced and designed

- **ops#148 closed.** `MANIFEST.md`'s `CHANGES-FROM-UPSTREAM.md` row widened to name all 9
  uncovered files — it already documents each one's provenance (4 vendored forks, 5 original), so
  this was a one-line widen, not a new row. Verified against the sweep's own bare-filename matching.
- **DEC-0079 — opted into `.claude/transient-state` (ops#113).** Tracked file created (force-added
  past the local `.git/info/exclude`, same precedent as `settings.json`), convention documented in
  `CONVENTIONS.md`. Left empty — no current state meets the motivating shape that isn't already
  prominent in `BOOT.md`.
- **`BOOT.md` ordered backlog resequenced:** `#144` (console pressure / `pressure_service.py` field
  collision) then `ops#141` (HLF archive-directory mount) queued for after GATE 2, each flagged with
  why it's design work rather than mechanical execution.
- **ERR-0005 backfilled.** 7 records at `interval=15` inserted into the archive (backed up first:
  `weewx.sdb.bak-S71-preBackfill-20260810-124656`), daily summary rebuilt, matching InfluxDB points
  written flagged `backfill=1.0`. **Both machine history APIs failed first** — WU's `v2/pws/history/all`
  401'd, WeatherLink v2's `v2/historic/{id}` (same credentials `pressure_service.py` uses hourly)
  returned an empty `{}` with a 200 — neither carries historical-read entitlement on this account.
  Sourced from a manual WeatherLink/WU website read instead; recorded in `DATA_ERRATA.md` so a future
  backfill skips straight to that.
- **Solar radiation diode-floor bias — diagnosed, fix designed, not yet applied.** Owner recalled a
  prior fix; traced via the owner's own claude.ai search (this repo's git history and archive both
  start 2026-05-19, so nothing here predates it) to a June 2026 dashboard-only presentation-layer
  filter. Verified against the *current* dashboard: still correct for live numeric displays, but the
  24h chart panel (`eh-charts.js`) queries InfluxDB raw with no filter — regressed during the
  dashboard's July supercard refactor, the second time a per-path filter has been dropped on
  refactor. Decision: fix at the source here instead of patching the dashboard a third time. Two
  designs drafted and compared (`StdCalibrate` magnitude-match vs. a `weewx.almanac`-based
  elevation-gated service); full brief for the next session in
  [`docs/handoffs/S71-radiation-floor-design.md`](docs/handoffs/S71-radiation-floor-design.md).
- Green gate re-run clean throughout (185 tests).

---
## [S70] — 2026-08-10 — v2.0.12 promoted and built; campaign B GO, first launch night scrubbed on a dead VPN

- **Campaign B: GO.** Assessed against DEC-0066's hold: both gates closed on measurement
  (DEC-0069/0070), campaign A uncontaminated (DEC-0077) — the "instrument trusted" condition is
  met. The swap-night constraint is moot: the LNA has been out since 08-02, so the launch is a
  container swap + install, all remote.
- **Release v2.0.12 promoted** (PR #151): dev → main, `main` = `7b6fd42`. Image delta vs v2.0.11
  is four baked files (BIAS_TEE env, DEC-0062 redaction, driver stderr drain + ws.4 bump) —
  observability only, pre-registered as the one-image-for-B plan (DEC-0064).
- **The arm64 laptop can no longer build this image** — `docker build --platform linux/amd64`
  dies in tar with `Function not implemented` (ENOSYS under emulation), and the failure hid
  behind a `| tail` pipeline exit 0 until the log was read (the green-checkmark trap, again).
  Built **natively on the NAS** instead (v2.0.3 precedent): `9db5c1ddaac3`, verified by an
  explicit `BUILD-EXIT=0` marker. Hub push deferred (docker save → laptop → push from a home
  network); `:latest` waits for prod proof.
- **The 08-09 launch night was scrubbed at 00:58** — the VPN dropped end-to-end (ppp0 gone,
  route fell back to the foreign LAN's gateway) with the 00:35 first pilot row already passed.
  The runbook's postpone-24h contingency, exercised as designed: prod untouched, campaign A's
  script + STOP sentinel still in place, nothing half-deployed. Schedule regenerated +1 day
  (39 rows, S62's constant-offset method): **pilot 08-11T00:35, square 08-12 → 08-20T00:05**.
- No stall overnight (blocker 4 still waiting); prod healthy through the NAS build (v2.0.11,
  Up 4 days).
- **Deploy executed 08-10 morning, campaign B ARMED.** Campaign A archived (five artifacts →
  `.campaignA`, including the root-owned STOP sentinel the runbook's list omitted — a tick
  refuses while it exists); B's `rx_experiment.sh` deployed from merged tip `b7a07e1` and
  sha-verified (`6a99c949`); container swapped in one nohup'd batch (VPN-drop-safe after the
  previous night's lesson), `SWAP-EXIT=0`. Verified in the running system per DEC-0046: ws.4
  banner, `Bias-tee disabled (BIAS_TEE=0)` line, DEC-0062 redaction line, loop-JSON advancing,
  reception 70% → 57/59% through the swap dip → **70% [OK]** recovered. `install` clean at
  09:40: baseline snapshotted, **pilot 08-11T00:35, square 08-12 → 08-20T00:05**. Soak with the
  new expectations: **16 pass / 1 warn (settling reception) / 0 fail**.
- **DEC-0078 — image builds move to the NAS.** The laptop failure above is deterministic, so the
  NAS-native path is now the release mechanic, with Hub publication decoupled (`save` → laptop →
  `push`, only after prod proof — Hub lags prod until pushed, documented in CONSTANTS). CI
  builds noted as the structural fix, backlogged. `EXPECT_*` flipped to v2.0.12/ws.4 in the same
  deploy; ROADMAP P2 reconciled (DEC-0057): release item closed, campaign B item now LAUNCHED.
- **`:v2.0.12` pushed to Docker Hub at S70 close, digest-verified end to end:** the Hub
  manifest's config digest is the NAS build id (`9db5c1…`) — what the public pulls is provably
  what prod runs. One recorded blemish: the save→load→push path re-pushed the layers
  near-uncompressed (283 MB vs ~120 MB typical; same 8 layers, each ~2.2×) — content-identical,
  harmless, tightening deferred to DEC-0078's CI-build follow-up. `:latest` deliberately still
  v2.0.11 until the station proves the release (GATE 2). ops#152 closed on the measured green
  sweep.

---
## [S69] — 2026-08-09 — Tier files back under cap (ops#152)

- **BOOT.md 10,617 → 7,557 chars (cap 10,000); MANIFEST.md 4,055 → 3,936 (cap 4,000)** — the
  tier-sweep filing folded into a session close, as the filing prescribes. BOOT per STANDARD rule 1:
  the blocker-5 closure was told three times, the forensics deploy-and-verify story twice, and the
  footer re-told the whole body — each now once, reasoning left in DEC-0075/0077. Three gotchas
  deleted as second copies of canonical docs: the secret gate's "nothing to scan" (CONVENTIONS),
  "which layer wins in prod" (CONSTANTS), session-number authority (CLAUDE.md). MANIFEST per rule 9:
  teaching parentheticals compressed; no row deleted.
- **No stall capture yet** (blocker 4) — `logs/usb-forensics/` holds only the 08-09 smoketest and
  verify files, so the S70 job is unchanged: the event is the only thing left.
- S66 rolled to `CHANGELOG-ARCHIVE.md` verbatim (the ~3-session window).

---
## [S68c–d] — 2026-08-09 — Blocker 5 closed on measurement (DEC-0077); DEC-0074's probe corrected (#147)

- **DEC-0077 — reset gaps do NOT contaminate campaign A.** Blocker 5, answered by measurement rather
  than argument. Every rotated monitor log spanning campaign A (`.11`=07-29 … `.4`=08-05) grepped:
  **11 resets, all on 08-02** (00:11:23 → 01:27:20), seven of eight days empty — independently
  corroborating DEC-0067's "0 detections on every other day". The archive across the incident reads
  **00:04 = 72.73% normal → 80 rows absent → 01:24 NULL → 25 rows absent → 01:51 NULL → 01:52 back in
  range**: exactly the tool's documented **lock/outage** shape.
- **Why that settles it: classification is descriptive, exclusion is structural.** DEC-0069 drops the
  record either side of *any* gap plus every NULL, never consulting the class — so the reset-adjacent
  records were already excluded, and the 105 absent minutes contribute nothing because absent rows
  are not zeros. DEC-0074's framing (gaps "sorted into freeze/swap/lock") was the wrong thing to
  worry about. **The real exposure was present-but-low rows**, which nothing excludes because the
  tool refuses magnitude thresholds by design — and there are none.
- **Narrow amendment:** DEC-0069's taxonomy is complete for *shapes*, not *causes* — a USB reset is a
  fourth cause of the lock/outage shape. Treatment keys on shape, so no analyzer change.
- **Two bounded residuals, neither gating:** 01:52 (57.14%) survives the rule because it neighbours a
  NULL *row* rather than a gap — ≈0.04 pts on a 6 h block against a 2.0-pt bar; and 105 min vanished
  from one arm's block, costing precision rather than bias, since a receiver outage is not a property
  of the arm.
- **Correction to the record:** the log shows **11** resets, not nine. ERR-0005 and DEC-0065 both say
  "nine in 75 minutes" and call 01:27:17 "reset #10"; it is the 11th, span 76 min. Nothing downstream
  depended on it — DEC-0065's argument is about unbounded retry, which 11 strengthens.
- **DEC-0074's liveness probe corrected where it is documented (#147).** Its body, index row and the
  ROADMAP watchdog item all cited `/proc/<pid>` mtime, which S68b measured as access time. Amended in
  place rather than superseded: no decision changed, only its instrument. The lesson stands; the
  three checks that hold are a startup log line after the file mtime, `/proc/<pid>/stat` field 22 vs
  `/proc/uptime`, and new-pid-with-old-pid-gone.
- **Staleness sweep, again.** BOOT's blocker 4 still read "not yet deployed", its monitor row cited
  the pre-deploy sha, and the campaign-B paragraph still gated on blocker 5. All corrected, plus an
  internal contradiction BOOT had acquired (9/9 vs 11).
- **`Closes #N` does not work on this repo's flow.** #147 was still open while BOOT claimed it
  closed: GitHub auto-closes only on a merge to the **default branch, `main`**, which advances only
  at a prod-baseline release. `git log --grep` shows the pattern used on `dev` before, so this is not
  a one-off. Recorded in `docs/CONVENTIONS.md` §Git workflow — close explicitly, or say "addressed in
  #M" and leave it open on purpose; keep the trailer as a cross-reference, never the mechanism.
- **BOOT was a second copy of the runbook it points at.** It exceeded the DEC-0072 cap four times in
  one day and each overrun was paid for by shaving words — which DEC-0072 explicitly rejects. The
  cause was structural: six campaign-B launch steps sat directly under a line saying
  `docs/CAMPAIGN-B-RUNBOOK.md` governs the night. Verified absent from the runbook first, then
  **moved** there verbatim (not deleted) as a new "Release mechanics" section. BOOT 2516 → **~2332**,
  ~7% headroom rather than the 0.2% shaving bought.
- **Forensics reinstalled and the fix verified on hardware (S68e).** The `/proc`-mtime fix from
  #146 is now the deployed copy (`dc7912ae`, root-owned), and a live capture confirms it:
  `age=259633s` (3.0 days, matching container uptime) beside `proc-dir-mtime` labelled "ACCESS
  time, NOT start". The two fields visibly disagree in the artifact, with the right one marked.
  Verified rather than assumed, since the earlier smoke test is what found the defect at all.
  **#147 closed by hand**, #148 merged. Nothing pending deployment.
- **The session's recurring shape, worth naming:** three distinct staleness classes — the deploy
  state, DEC-0074's probe, the `Closes #N` trailer — all the same defect. *A claim that was true when
  written, with nothing that would fail when it stopped being true.*

---

## [S68b] — 2026-08-09 — Forensics deployed and verified live; the smoke test then found a defect in them

- **Deployed from the merged tip `ad7e5a4` and verified.** `usb_forensics.sh` + `usb_reset.sh` as
  **root:root 755** (ownership is load-bearing — `usb_reset.sh` refuses a helper it does not own),
  `weewx_monitor.py` as the service account, 644; monitor 3870 → **8810**, `Monitor started`,
  polling normally, ~3.5 min gap inside the esynoscheduler window.
- **The sudo half is owner-run and cannot be batched.** The `nas-admin` alias lands on an
  unprivileged account with no NOPASSWD, and an agent session has no TTY: `-t` fails to allocate one, `-tt` forces a pty and then
  hangs on a live `Password:`. Leading the remote script with `set -e` made the failed attempt a
  clean no-op — verified afterwards: prod shas unchanged, zero `.bak` files created.
- **Smoke-tested on the real box, which is the point.** Pid discovery by `comm` works; dongle
  confirmed `1-3` / `0bda:2838` / `devnum=5`; the two root-only sections correctly self-labelled
  `DEGRADED … UNREADABLE, not empty` rather than looking like a released handle.
- **And it caught a defect in what had just shipped.** The capture reported `rtldavis` as 17 seconds
  old; it had been up **2.88 days** (`/proc/<pid>/stat` field 22 vs `/proc/uptime`, corroborated by
  the container Up 3 days and unbroken `weewx.log` output). `/proc/<pid>` **mtime is access time**,
  and the script reads files under that directory moments earlier. In a stall capture it would have
  asserted a restart that never happened — a fabricated event in the one artifact built to settle a
  question whose hypothesis is deliberately unsettled. Fixed in **PR #146**; HZ=100 confirmed, not
  assumed (250 or 1000 both date `rtldavis` before the container that spawned it).
- **This undercuts DEC-0074's own probe — [#147](https://github.com/WeatheredScientist/weewx-rtldavis/issues/147).**
  Its documented liveness check is `nasctl ls /proc/<newpid>` vs the file mtime: the same unsound
  signal. The **lesson** stands — liveness needs process evidence — but the probe must become a
  startup line in the log after the file mtime (what actually carried both the S67 and S68
  verifications), field 22 vs `/proc/uptime`, and new-pid-plus-old-pid-gone.

---
## [S68] — 2026-08-08 — Reset forensics built and armed (DEC-0075); secret gate's fifth hole closed (DEC-0076)

- **DEC-0075 — the next stall photographs itself.** `ops/usb_forensics.sh` brackets every reset with
  the host USB tree and the dongle's `devnum`, the **container's** view of `/dev/bus/usb` via
  `/proc/<pid>/root`, and whether the stalled `rtldavis` still holds an fd on the device. Those last
  two are the decisive pair: a stale view or a surviving handle confirms the hypothesis, and both
  clean means the stall is **not a USB fault** and the reset treats the wrong thing entirely.
  Read host-side through `/proc` rather than via `docker exec`, because this fires *during* a stall
  and a wedged container can block an exec indefinitely — the capture would hang on the very event it
  records. Pre/post fire from inside `usb_reset.sh`, the only root context, needing **no new sudoers
  grant**; the monitor fires only the `+RESET_VERIFY_S` capture and **labels it DEGRADED**, so an
  unreadable fd section can never be misread as a released handle. **Capture-only — DEC-0065's
  escalation ladder is untouched.**
- **An escalation introduced and closed in the same change.** Executing a helper from `usb_reset.sh`
  runs it as root under the NOPASSWD grant, and mode 777 is common on this NAS — a helper writable by
  `weewx-monitor` would have turned that narrow grant into arbitrary root execution. The script now
  verifies the helper is root-owned and root-only-writable, refuses **loudly** otherwise while still
  resetting, and `do_reset()` logs its output on a zero exit so the refusal cannot go silent.
  Checked, not documented (DEC-0040), and positive-controlled by neutering the check.
- **Why it was built before the evidence:** no stall since the corrected reset code went live
  2026-08-07 19:28 — zero `RESET`/`stalled` lines across the 08-07 and 08-08 monitor logs, both greps
  positive-controlled against 1440/521-hit `WINDOW` counts. Nothing to read retroactively, and the
  event is ~1/day and unpredictable, so the apparatus has to exist first.
- **DEC-0076 — the secret gate missed `GMAIL_PASS`-shaped keys.** The key list held `password` and
  `passcode` but nothing for the `_PASS` abbreviation, so `GMAIL_PASS = "..."` was undetected in
  every spelling — and that is the exact variable `weewx_monitor.py` uses for its Gmail credential.
  **Nothing was ever leaked through it** (no `_PASS` literal in the tracked tree; none on any ref in
  the full history). Found by DEC-0045's routine positive control before an *unrelated* commit, not
  by an audit. Two detectors, each proven necessary by removing it and watching its payloads leak:
  bare `pass` (not `passwd`, which would flag README's `NOPASSWD:` sudoers line), and a literal
  matcher for the four-group app-password form that slips past the 8-consecutive-character value
  rule. `PASS` is listed separately because detection is case-insensitive and the allow-list
  deliberately is not — without it the gate flagged this repo's own source. Harness **41 → 51** cases.
- **ROADMAP reconciliation:** blocker 4 had **no P0 line at all** — DEC-0074 raised it at S67 and no
  item was opened, so the sequenced plan did not carry its own top blocker. Added.
- Tests **169 → 184**. `usb_reset.sh` now also documented in README's Security Note and Setup, since
  its escalation surface changed.

---

## [S67] — 2026-08-06 — Tier-file diet (ops#145, DEC-0072); watchdog found dead and its supervision designed (DEC-0073)

- **DEC-0073 — supervise the USB watchdog, make its absence loud, model its resets.** Design agreed,
  implementation is the open work and it now **gates campaign B**. Four parts: adopt
  `weewx_monitor.py:102-115`'s PID guard plus a 5-minute scheduled re-launch (the guard makes
  re-launch idempotent, so the scheduler carries no state); a heartbeat file so liveness is an mtime
  check rather than an inference; **`ops/soak_check.sh` asserts that heartbeat** — the structural
  half, since that script exists to ask "healthy, or just looks Up?" and had never asked it of the
  watchdog; and a rising reset rate reaching the alert path.
- **The campaign-B call that came with it.** `campaign_analyze.py`'s three-class gap taxonomy
  (freeze / arm swap / lock-outage) was validated over 07-29 → 08-05 — **a window in which the
  watchdog was dead** — so a USB-reset gap is a fourth class it has never seen and would, by shape,
  be absorbed into `freeze` and excluded *by accident*. That is DEC-0035's and DEC-0071's failure
  shape exactly. Agreed: **watchdog ON for B, analyzer taught the fourth class** so reset-adjacent
  minutes are excluded explicitly and auditably, rather than a measured result being quietly shaped
  by an intervention nobody modelled.
- Verified before deciding, not assumed: the dongle is still on USB `1-3` (`0bda:2838`, Realtek
  RTL2838) with `syno_vbus_reset` present — a silently wrong path would make every future reset a
  no-op that logs success — and the monitor's PID guard was read at source rather than remembered.
- **DEC-0073 (a)(b)(c) implemented.** `ops/usb_watchdog.sh` gains the PID guard, a heartbeat touched
  every tick, and env-overridable paths (the old hardcoded ones are much of why its behaviour was
  never tested). The loop now uses `read -t` so **the heartbeat ticks on a quiet log** — a bare
  `read` blocks until a line arrives, which would let `soak_check.sh` call a live watchdog dead.
  A closed `tail` pipe is distinguished from an idle one so the script exits and lets the scheduler
  restart it, rather than spinning.
- **New `tests/test_usb_watchdog.sh` — 8 tests, and they have teeth.** They cover the *supervision*,
  which is what actually failed: heartbeat on a quiet log, pidfile contents, stall detection, the
  300 s cooldown, non-matching lines triggering nothing, the PID guard refusing a second instance,
  and a **stale pidfile being reclaimed** (if that were fatal, one `kill -9` would keep the watchdog
  dead forever — the exact permanence this DEC exists to prevent). Positive-controlled: reverting
  the `read -t` to a bare `read` turns the heartbeat test red, and restoring it turns it green.
- **`ops/soak_check.sh` asserts the heartbeat** (2× the 60 s tick). Confirmed against prod, where it
  correctly reports `USB WATCHDOG NOT RUNNING` — production is its own positive control here.
- **DEC-0074 supersedes DEC-0073 the same session, before anything was deployed.** Asked to deploy
  the watchdog, I read `weewx_monitor.py` first and found it already **is** the watchdog —
  `reset_dongle()` (l.342), `watchdog_stall()` with escalation (l.354), wired at l.692 — alive as
  pid 5015, and it had handled all three of the 08-06 stalls within seconds. **DEC-0073's claim that
  those stalls "went unhandled" was false.** The evidence for the standalone script being dead was
  sound; what was never checked was whether anything *else* did the job. Three sources were
  consulted — the watchdog's log, `weewx.log`, the process table — and all three are silent about
  the monitor, whose own log holds the answer in plain text. DEC-0031's lesson turned on its author:
  *"this component is dead" and "this capability is missing" are different claims.*
- **`ops/usb_watchdog.sh` and its tests deleted, not deployed.** Deploying would have added a second
  uncoordinated resetter to the same dongle, unshared cooldown, beside a monitor whose source
  records nine resets in 75 minutes on 08-02. **No NAS change was made, and none was needed.**
- **The `soak_check.sh` criterion survives, repointed at the monitor** — live pid plus a log younger
  than 300 s, since its poll is 30 s and a live pid with a stale log means *wedged*, not dead.
- **The real defect, which DEC-0073 walked past:** all three resets on 08-06 **failed** —
  `RESET ineffective (1/3)` each time, bad windows climbing **8 → 10 → 15**. The monitor works and is
  reporting that the remedy doesn't. New `USB RESETS INEFFECTIVE` criterion. Open and unexplained.
- **Bigger consequence for campaign B:** reset gaps are not a new class B would introduce — the
  monitor fired **nine resets on 08-02, inside the 07-29 → 08-05 window `campaign_analyze.py`'s
  taxonomy was validated against**. So reset-adjacent gaps are already inside campaign A's recomputed
  figures. That makes the fourth-gap-class question one about a result DEC-0069 already published.
- **`weewx_monitor.py` was never in `MANIFEST.md` — the hole that caused DEC-0073.** It is tracked
  in this repo, at the root, 38 KB, the largest operational file here, and it appeared zero times in
  the index. DEC-0072's class row scopes to `ops/*` + `scripts/*`, which excludes the repo root, so
  the diet did not just miss it — it codified the omission behind a rule that reads as if it covers
  the harness. Since the session-start read is BOOT + CONSTANTS + MANIFEST, nothing in the load path
  named the file that **is** the watchdog; the index shaped where I looked and had a hole exactly
  where the answer was. Now has its own row, whose "load when" is *any "what handles X at runtime?"
  question — read this BEFORE concluding a capability is missing*. Preamble gains the rule that was
  missing: **a file in no class gets its own row.**
- **Reset log message fixed structurally, not textually** (+4 tests, positive-controlled).
  `USB_RESET_SCRIPT` and `USB_RESET_ACTION` are now named once and used for both the subprocess call
  and every log line about it, so the message cannot drift from the action again. Correcting the
  string alone would have left the same trap armed. `tests/test_reset_log_matches_action.py` asserts
  no `log()`/`send_email()` call names `syno_vbus_reset`, that the call site uses the constant rather
  than a duplicated literal path, and that mechanism log lines derive from the constants —
  reintroducing the exact historical line turns two of them red.
- **The reset log line named an operation that never happened.** `reset_dongle()` logged
  `RESET: triggering syno_vbus_reset` but shells out to `usb_reset.sh`, which is a driver
  **unbind/rebind, not a power cycle**. The retired `usb_watchdog.sh` really did write
  `syno_vbus_reset`; when the logic moved into the monitor the action changed and the message did
  not. Every reset line in every log for months has named the wrong operation. Evidence, the
  leading hypothesis for why the resets fail, and the decisive test are in `BACKLOG.md`.
- **Monitor deploy deferred, and recorded rather than remembered.** The corrected log message is on
  `dev` but the NAS still runs the pre-fix copy, so prod logs keep printing the line that isn't true.
  The Class C token mint was refused twice, and since the change is log text with no behaviour, rung
  2 of the ladder applied — defer, don't hand over a paste-me command. A blocking note now sits at
  the top of `BACKLOG.md`'s reset section, because from the repo side that fix looks *done*: merged,
  tested, closed. The next session's first act would otherwise be reading the exact lines it fixed.
- **Lessons filed cross-repo as [ops#147](https://github.com/WeatheredScientist/eaglehunt-ops/issues/147)**
  (`repo:` all four, `tier:frontier`). Eight items on one through-line — *every failure this session
  was a green-looking signal resting on the wrong evidence* — so it continues OPS-DEC-0040 and
  DEC-0035 rather than opening a new concern. The two with leverage: **the index directs attention,
  so a hole in it is invisible** (STANDARD rule 9 as written lets a diet codify an omission — a class
  row scoped to `ops/*` reads as "all the operational scripts" while excluding the repo root, which
  is exactly how `weewx_monitor.py` stayed unindexed), and **a file match proves the FILE, never the
  PROCESS**. Both are better served by a mechanical check than a written rule, per OPS-DEC-0040's own
  argument; `checks/tier-sweep.sh` already reads each repo's pushed files and could enumerate
  operational artifacts covered by no row.
- **`weewx_monitor.py` now has its own MANIFEST row**, and the preamble states the rule that was
  missing: *a file in no class gets its own row.* It is the largest operational file in the repo and
  had never been indexed — the direct cause of the DEC-0073 error, since the session-start read path
  contained no pointer to the thing that answers "what handles this at runtime?".
- **`docs/ROADMAP.md` line corrected (DEC-0057, same session):** the watchdog-deploy item cited
  *"matches the repo tip byte-for-byte, with zero resets or escalations since"* as proof it was live.
  That is the exact wrong-evidence pattern DEC-0074 corrects, sitting in the roadmap as a worked
  example. The deployment was real; the reasoning was not.
- Also noticed: `weewx.log` rotates at midnight, so the DEC-0031 driver canary reads `UNVERIFIED`
  after rotation until the next restart logs a banner — the same silent-window class. The reset
  counters were made rotation-aware (they read `.log` and `.log.1`); the canary was not, and wants a
  follow-up.

- **`BOOT.md` 3734 → 2161 tok (cap 2500), `MANIFEST.md` 1948 → 970 tok (cap 1000)** — verified with
  `checks/tier-sweep.sh` itself against fixtures, not by hand arithmetic. Both green, exit 0.
- **`MANIFEST.md` switched to class rows (STANDARD rule 9).** `ops/*` + `scripts/*` collapsed from
  five per-artifact rows to one naming the convention — *the script's header comment is its manual*.
  The convention was **verified before relying on it**: the docstrings already carry more than the
  rows that duplicated them. Coverage went **up**, because 6 of the 11 harness scripts had no row.
- **Four facts that existed only in the index now live in the scripts** — `campaign_analyze.py`
  documents that campaign A needs `--since`; `rx_experiment.sh` states campaign B is loaded and that
  `install` refuses a stale schedule; `soak_check.sh` states `EXPECT_IMAGE` must track the deploy.
  Content moved, not deleted.
- **`BOOT.md`**: standing watches and the campaign-A LNA findings rehomed to `BACKLOG.md`; the
  DEC-0069/0070/0071 write-ups cut to one-liners with pointers, since the full bodies are already in
  `DECISIONS-FULL.md` (STANDARD rule 5 — a second copy is a defect).
- **Fixed a stale launch pointer.** BOOT told the next session to rebuild `:v2.0.12` from
  `bdc4f9f` — 13 commits stale, predating DEC-0069/0070/0071, so the image would have silently
  lacked `campaign_analyze.py` and `freeze_watch.sh`. Now: take the tip from `git rev-parse`.
- **Found:** `ops/soak_check.sh`'s `EXPECT_IMAGE` defaults to `v2.0.12` while prod runs `v2.0.11`, so
  a soak run today goes red on a healthy station. Noted in the script and in the launch sequence.
- **Found:** `~/.claude/hooks/secret-read-guard.sh` matches by basename and so blocks reads of this
  repo's *clean* `ops/wxcheck.sh` (it uses `${WU_API_KEY}`, no literals). Workaround `readconf`
  documented in BOOT; the guard is ops-owned, so not changed here.
- HLF confirmed recovered — container recreated with hyperlocal-forecast PR #286 merged; ops#141
  relabelled `repo:hlf`, nothing further owed by this repo.
- **`ops/soak_check.sh` expectations reset to what prod actually runs.** `EXPECT_IMAGE`
  `:v2.0.12` → `:v2.0.11` and `EXPECT_DRIVER` `0.20+ws.4` → `0.20+ws.3`. Both were bumped together
  at S62 (`e21c03e`) in anticipation of a `:v2.0.12` release that never deployed, so for five
  sessions the soak check would have reported two red criteria against a correct deployment —
  including the DEC-0031 driver canary, the one check whose whole job is to notice a wrong image.
  Nobody ran it, which is the only reason it went unnoticed. `CONSTANTS.md`'s driver-banner row
  carried the same anticipatory value and now distinguishes prod from the repo.
- **Running it surfaced a real prod finding (new blocker 4).** Three `rtldavis process stalled`
  events on 08-06 (09:53 / 10:10 / 10:32 EDT) that the USB watchdog did not log — its log has been
  silent since 2026-05-22 and there is no watchdog pidfile, though its `STALL_PATTERN` does match
  those lines. `BOOT.md`'s "watchdog deployed and live" had been asserted from **file identity**,
  not process liveness — DEC-0031's shape, and corrected in place. Reception recovered to 81%;
  nothing is degraded now, but this wants verifying before an unattended campaign B.
- The 6 tracebacks the soak check counts are the DEC-0071 crash loop (07:18–07:24 EDT), already
  known and resolved — `weewx.log` persists across restarts, so they stay in the window.
- **Blocker 4 resolved to a fact: the USB watchdog has not run since 2026-05-22.** It logs
  `Watchdog started` unconditionally before its `tail -F` loop, and the complete 845-byte log holds
  exactly one such line, timestamped the same minute the script was deployed — hand-started once
  from a shell and never supervised (no crontab entry, no pidfile). NAS uptime of 29.6 days means it
  died at the 2026-07-08 boot at the latest. **The script is not at fault** — on 05-22 it caught 3
  stalls, fired 2 resets and correctly skipped one for cooldown, and its NAS copy is byte-identical
  to the repo. Only supervision is missing. Evidence in `BACKLOG.md`; fix needs a design call plus a
  Class C action, and is now a pre-campaign-B gate.
- **The lesson, added to BOOT's gotchas: a sha match proves the FILE, never the PROCESS.** The claim
  that hid this for ~2.5 months was *"deployed and live — NAS copy matches repo tip byte-for-byte,
  zero resets since."* Both sub-claims were true and re-verified. The conclusion was still wrong:
  zero resets because nothing was listening. A watchdog that isn't running emits exactly the same
  log as one with nothing to do, so its failure mode is silent by construction.
---
## [S66] — 2026-08-05 — Both campaign-B gates handled: metric goes freeze-aware (DEC-0069), DB lock bounded (DEC-0070)

- **New `ops/campaign_analyze.py` + 14 tests** — reads per-minute `rxCheckPercent` from the archive
  DB, excludes freeze artifacts structurally, reports per-arm means with the *uncleaned* figure
  alongside so the size of the correction is visible rather than asserted. `ops/rx_experiment.sh`
  is deliberately untouched: the unattended, prod-config-writing apparatus was not modified to close
  a reporting gate.
- **The gate was mostly a resolution problem, not a freeze problem.** `harvest()` scraped the
  monitor's *5-minute* `RECEPTION:` aggregate, where one frozen minute drags the whole bucket
  (measured 16 % and 27 % against a ~72 % neighbourhood) and destroys four good minutes — that is
  where BOOT's ~0.8-point estimate came from, and it was correct *for that metric*. The same
  measurement is stored **per minute** in the archive. Net effect on a pooled arm mean: **±0.03
  points** against a 2.0-point adoption bar.
- **Measured the freeze signature** over 10 988 records / 33 gaps: three non-overlapping classes
  (freeze / arm swap / lock-outage). **The contaminated record is the one adjacent to the gap; the
  freeze minutes are simply absent rows** — BOOT had assumed they scored as zeros, which is what
  made the estimate ~60× too large. Retro-found one freeze nobody had logged (07-29 22:12).
- **Corrects DEC-0067 in both directions.** Its predicted post-freeze "up" is real — 2026-07-29
  03:10 reads `rxCheckPercent = 200.0` — but conditional, ~1 in 8 days. An initial two-freeze
  reading here concluded there was no "up" at all; the 8-day scan overturned that.
- **Campaign A recomputed:** A 74.81 / C 74.37 / D 74.17 / B 73.87, spread **0.94 pts**, no arm near
  adoption. The ~1.9-pt offset from the previously-recorded 72.4 % matches `weewx_monitor.py`'s own
  "~1–2 pts optimistic" note — the two metrics validate each other, and A-vs-B must be read on the
  same one. *This unsealed A's arm winner ahead of B; see DEC-0069's sealing note.*
- **Two build-time defects caught, both of which would have printed confident wrong numbers:** a bare
  run pooled campaign A's aborted 07-29 attempt with the campaign proper (unbalanced square, tidy
  table, no indication) — now detected mechanically; and deriving the query bound locally dragged the
  entire archive over ssh — now bounded NAS-side.
- **ROADMAP:** metric gate closed; the `database is locked` defect restated as campaign B's **sole**
  remaining gate. The by-S66 *full* reconciliation tripwire fired and is flagged as still owed.
- **DB lock bounded (DEC-0070) — it was two defaults, not a bug.** `journal_mode=delete` (a reader's
  SHARED lock blocks the writer) plus weedb's **5 s** SQLite timeout (`weedb/sqlite.py:136`, and the
  live config set none). Six seconds of reader therefore cost a CRITICAL + weewx's hardcoded 120 s
  wait + restart ≈ **5–10 min outage**. Shipped **`timeout = 30`** to the live `weewx.conf`; verified
  in the running system (resolved `database_dict` carries it) and restart healthy at **106 s**.
  Outages now capped at ~30 s. New behaviour to expect: weewx *blocks* rather than erroring, and such
  a stall is indistinguishable from a DEC-0067 freeze to `freeze_watch.sh` — excluded correctly by
  `campaign_analyze.py`, not a bug to chase.
- **WAL is the real fix and is blocked cross-repo — filed ops#141.** `hyperlocal-forecast-api` binds
  the archive DB as a single *file*, so WAL's `-wal`/`-shm` siblings can never appear beside it. An
  initial reading that the mount would also need to become *writable* was **tested and disproved** on
  the container's own SQLite 3.46.1: read-only directory mounts work with `-shm` present or absent;
  only the single-file case fails, and it fails as `no such table`, not as stale data. So `RW=false`
  stays and no HLF code changes.
- **`CONSTANTS.md` gains a live-config deviations table.** `weewx.conf` is the mounted layer and is
  never committed, so `timeout = 30` exists only on the NAS with no CI and no diff — a stock
  container recreate would silently revert it.
- **Guard finding (belongs to ops):** the NAS mutation that wrote live prod config **did not trip the
  Class C guard** — `ssh <nas> "python3 -" < script` hides the mutation in stdin while the guard
  matches the command string, and that is the batching shape CONVENTIONS recommends. Meanwhile the
  *read* guard fired three times on `grep`/`tail` against files carrying no secrets. Owner-authorized
  in chat, so nothing improper — but the mechanism didn't enforce it.
- **Corrects DEC-0067's reader list:** it named "the dashboard" as an archive-DB reader. Scanning
  every container that mounts a weewx path finds only `hyperlocal-forecast-api`, `eh-proxy` (parent
  dir, read-only), and weewx itself.
- **WAL tried and ROLLED BACK (DEC-0071) — with a self-inflicted ~6 min prod outage.** HLF shipped
  the directory mount (ops#141), WAL went live 06:56 EDT, and hyperlocal-forecast **froze on a stale
  snapshot within minutes**. Two blockers, both missed: a Docker `:ro` bind makes the **files**
  read-only, and DEC-0070's own test only chmod'd the *directory*, so it never reproduced that —
  structurally blind, DEC-0035's lesson recurring; and SQLite creates `weewx.sdb-wal` mode **0555**,
  so even a read-write mount leaves a non-root reader unable to write it.
- **Rolling back was the hard part.** `PRAGMA journal_mode=DELETE` needs an exclusive lock that
  weewx's persistent connection denies, and with the container stopped there's no `docker exec`
  either. Resolved by letting weewx apply it: `[[[pragmas]]] journal_mode = DELETE`, kept in place so
  the mode is re-pinned on every start. **That pragma was first written as a scalar** — weedb wants a
  mapping, so it raised `TypeError: string indices must be integers` and crash-looped weewxd
  (CRITICALs 07:18:58, 07:20:22) until the subsection form landed at 07:24.
- **Process failures worth naming:** the first rollback attempt opened with a `SELECT COUNT(*)` that
  had *already* timed out earlier the same session, and the config shape was assumed from the field
  name rather than checked against the consumer whose source had been read an hour before. Two of
  three failures repeated lessons already written down in this repo.
- **Net:** WAL is not viable as scoped; `timeout = 30` is the fix, not an interim, and delivers most
  of WAL's practical benefit. weewx healthy and current. **hyperlocal-forecast is still stale and
  needs a container restart by an HLF session** — reported on ops#141, relabelled `repo:hlf`.
- **Full ROADMAP reconciliation run (the by-S66 tripwire, honoured).** All 8 open items diffed
  against DECISIONS/CHANGELOG/BOOT. Four were stale: the tiering migration sat unchecked *while its
  own body read "Executed S60"*; the v2.0.12 row said "BUILDING 2026-08-02" for four sessions when
  that build no longer exists; campaign B's gates were listed open after DEC-0069/0070/0071 cleared
  them; and the DB-lock row still said "flip WAL once ops#141 lands" **after DEC-0071 abandoned
  WAL** — a same-session DEC-0057 update missed the day before, which is precisely what the full
  pass exists to catch. Also fixed: the P2 heading still announced "CAMPAIGN A RUNNING", and the
  archive-DB reader list still named the dashboard. Next check due **by S76**.
- **Branch hygiene:** nine merged S62–S66 feature branches deleted (local + remote), restoring the
  `dev` + `main` steady state CONSTANTS.md specifies. Every one verified contained in `dev` first;
  `main` deliberately untouched. BOOT.md's "stale branch still exists, harmless" row retired with it.
---
## [S65] — 2026-08-04 — Freeze-watcher fixed (parallel reads, dedup bug, local notification); two freezes caught, one tied to coffee-radar's scheduled run

- **The watcher's second-sample bug is fixed.** S64's second `S`-vs-`D` sample landed ~7 min late
  because it read all 12 thread states sequentially, one `nasctl` round-trip at a time (no SSH
  connection multiplexing on this box). Now fanned out in parallel (background + `wait`, single
  retry for stragglers): a full 12-thread sample takes ~1-2 s.
- **Found and fixed a second bug the same night: the watcher didn't dedup an ongoing freeze.**
  Tonight's run "caught" three stalls in a row, all reporting the identical frozen `weewx.log` size
  — it was one continuous ~4 min freeze (longer than the usual ~3.5 min), captured three times,
  which burned `MAX_CATCH=3` on a single event and exited the watcher 8+ hours early. It now waits
  for the log to actually regrow before re-arming detection.
- **Native macOS notification wired in** (`osascript`, confirmed deliverable live) on each genuine
  catch and on exit. The watcher is a detached `nohup`+`caffeinate` process; it now needs no open
  Claude session or cloud connectivity to reach the owner.
- **Freeze #1 (17:48:59–17:52:37 EDT, ~4 min):** every thread read `S` throughout except three
  isolated moments where a single `rtldavis` worker thread went `R`; `weewxd`'s main thread and all
  four REST-uploader threads stayed `S` the entire time. Still no `D`. **Coffee-radar was not
  running and loadavg was normal (0.3–0.7)** — no shared-NAS signature on this one.
- **Freeze #2 (19:13:43–19:15:41 EDT, ~2 min): loadavg spiked to 12.39, and coffee-radar was
  confirmed running the entire time** — checked at the owner's request, since this NAS also runs
  hyperlocal-forecast and coffee-radar. `nasctl inspect` showed image `coffee-radar` on a
  Docker-auto-named container (`dreamy_merkle` — its scheduled command never passes `--name`, which
  is why every earlier `docker ps` name-string check missed it), started **19:00:16 EDT**, 13m27s
  before detection. That start time lines up almost exactly with coffee-radar's documented 19:00
  daily run — its schedule is **local time (EDT), not UTC**, a unit mismatch in this session's own
  earlier comparison. `pid=30506 (rtldavis)` read `R` in *both* 20s-apart samples this time
  (continuously runnable, not a single blip) — more consistent with CPU contention than the brief
  ticks seen elsewhere. `weewxd`'s main thread still read `S` throughout, never `D`.
- **Net read: coffee-radar likely contributes to some freezes, not all.** Freeze #1, the same
  night, shows the identical symptom with neither coffee-radar running nor elevated load — so it
  isn't the sole cause. A general NAS-wide stall stays ruled out (S63/DEC-0067); this is narrower.
  Re-checking the 4 historical freeze timestamps against coffee-radar's now-corrected local-time
  schedule still shows no clean match, but that comparison is weaker evidence than tonight's direct
  `docker ps`/`inspect` observation, and DSM's own coffee-radar run history (if it logs one) hasn't
  been checked yet. `nasctl ps` is captured on every future catch, at no extra cost.
- **The overnight run finished at its 15h deadline with exactly one catch** — the coffee-radar one
  above; no third freeze materialized. `docs/ROADMAP.md`'s P0 freeze item updated to match.
- **DEC-0068 accepted**, capturing this finding as the settled (if partial) record: coffee-radar is
  a confirmed contributor to some freezes, not a full explanation. n=1 correlated of 3 total
  detailed captures — not a base rate. Full body: `docs/DECISIONS-FULL.md`.
- **`ops/freeze_watch.sh` committed** — third time this watcher was rebuilt from session-transcript
  archaeology (S63, S64, S65); no reason for a fourth. Also fixed a real bug found while writing
  this up: its coffee-radar-presence check grepped container *names* via `nasctl ps`, but a one-shot
  container run without `--name` (coffee-radar's own scheduled command) never gets one, so the check
  could never have matched — now greps the whole `nasctl ps` line, catching the `IMAGE` column too.
  `MANIFEST.md` gains a row.
- **Priority shifts off freeze-chasing.** Root cause isn't fully explained, but campaign B doesn't
  need it to be — its two real remaining gates (make the metric freeze-aware, fix the DB lock) are
  unchanged by this finding and are next.

---
## [S64] — 2026-08-04 — First live D-vs-S capture of a freeze, plus two closed trackers

- **CI: bumped pinned GitHub Actions off Node 20** (#121, closes weewx-rtldavis#117).
  `actions/checkout` v4→v7, `actions/setup-python` v5→v7, `peter-evans/dockerhub-description`
  v4→v5 — Node 20 runners are removed this Fall and every CI run already warned. Breaking-changes
  for each action were checked against how these specific workflows use them; none apply.
- **ops#114 closed.** It tracked campaign A toward an expected 08-06 self-close, but campaign A
  actually ended 4 days early via its own abort tripwire (2026-08-02, confirmed correct in S62) —
  there was never going to be a completion email to wait for.
- **First live thread-state capture of a process freeze (DEC-0067's open question).** An overnight
  read-only watcher (poll `weewx.log` size, `nasctl cat /proc/<tid>/stat` on the container's thread
  IDs) ran 15 h (17:32→08:32) and caught the 08-03 23:23:03→23:27:25 freeze (262 s, zero driver
  stall exceptions that day — the process-freeze signature, not RF loss). All 12 named threads read
  `S` (sleeping), none `D` (uninterruptible I/O), about 2 min into the freeze — independently
  confirmed against the raw log (exactly one gap ≥60 s all night, matching the watcher's count).
  **Leans away from the leading I/O-blocking hypothesis but isn't conclusive**: the design's second
  sample, meant to confirm the state persists, took ~7 min instead of the intended 20 s (12
  sequential `nasctl` round-trips) and landed after the freeze had already recovered. One clean
  sample, not two. Detail: [docs/ROADMAP.md](docs/ROADMAP.md) P0 freeze item.

---
## [S63] — 2026-08-03 — The recurring "reception dropouts" are process freezes, and the driver already knew

Diagnostic session, no production change. Nothing was deployed; campaign B stays held.

- **DEC-0067 — they are not reception dropouts.** `get_stderr()` is bounded at 10 s, so a *running*
  main thread that hears no RF raises `rtldavis process stalled` at 150 s. Across the silent
  208–218 s gaps it **never fired** — the main thread was not executing. **The receiver was fine;
  the weewx process freezes**, ~3.5 min, roughly once a day. The discriminator was already deployed
  and already correct; what was missing was reading its *silence* as data.
- **Measured, not asserted:** genuine RF loss is confined **entirely to ERR-0005** — 21 driver
  detections on 08-02, **0** on 07-30, 07-31, 08-01 and 08-03. So ERR-0005 is a single incident, not
  the head of a pattern. Its own root cause is still unestablished.
- **The standing watch is answered and closed.** A freeze on **07-30 with the LNA still installed**
  proves the dropouts are **not** new to the no-LNA regime. Removing the LNA did not cause them.
- **The instrument was the problem, not the weather.** The monitor counts *published output*, so a
  frozen process and a deaf receiver both read `WINDOW: 0/21 (0%)`. Every "unexplained dropout" was
  scored by a metric that cannot make the distinction the watch existed to make.
- **A freeze also misdates what it recovers.** Packets are stamped at *parse* time, so a backlog
  collapses onto the resume instant: the frozen minutes have no records at all and the next record
  absorbs ~3.5 min of packets — distorting the very counters campaign B measures, down then up.
- **Campaign B's gate is reframed, not lifted.** The recurring class is explained in kind and
  bounded (~0.4 % of wall-clock); the launch condition becomes mechanical — detect and exclude
  freeze windows — instead of "wait until the instrument is trusted".
- **`database is locked` is recurrent and pre-dates the LNA** (08-01 15:08, 08-02 19:45). The 10-min
  outage decomposes as ~106 s hung threads + **120 s of weewx's own hardcoded wait** + ~5 min
  restart; the identical lock on 08-01 cost 4 min because threads exited in 0.26 s. **The archive DB
  is not in WAL mode** — the first thing to try.
- **Ruled out with evidence:** NAS-wide stall (influxdb's timer fired mid-freeze, sub-ms on
  schedule), the S37 stdout wedge (live config has **no console handler**), CPU-quota throttling
  (DSM 4.4 exposes no `cfs_quota_us`), `pressure_service` (82 fetches, worst 8.99 s), the monitor's
  6-hourly read, and the HH:04 gap cluster (campaign-A swaps).
- **Still open: why it freezes.** All threads stop together and nothing is logged — consistent with
  a thread blocking on the bind-mounted log volume while holding the logging lock (box runs at
  **18.6 % cumulative iowait**). Unproven; the `D`-vs-`S` capture did not land before session end.
- Also corrected S62's stale handoff: the branch had merged and the watchdog had been deployed
  between sessions, so BOOT.md was telling S63 to redo both.

---
## [S62] — 2026-08-02 — A 105-minute receiver outage (ERR-0005), the follow-ups it earned, and campaign B moved up 4 days

Incident session. Prod went deaf at 00:05 and came back at 01:50; the rest of the day was spent on
what that exposed.

- **ERR-0005 — the outage.** Not one gap but **two**, separated by brief islands of reception:
  00:05:05→00:07:26, an ~56 s island at **71%**, then **00:08:22→01:23:56** (1 h 15 m), a ~36 s
  island, then 01:24:32→01:50:13. ~102 one-minute archive records missing. No correction applied —
  an honest gap, nothing to null. **WeatherLink Live backfill approved, not yet applied** (~7
  records at `interval = 15`, ERR-0003's path).
- **What actually fixed it: a full container recreate.** The LNA was already physically out and
  reception stayed at zero; `kill`→`rm`→`run` at 01:48 restored it. Nine USB resets and ~18 driver
  respawns had done nothing. **Root cause of the original fault remains unestablished** — 12 h of
  clean running since says the recreate cleared it, not what it was.
- **The watchdog made it worse, and now escalates instead (DEC-0065).** Measured: 9 resets, 0
  effective, 17 emails in 80 minutes, and not one distinguishing the 9th attempt from the 1st;
  reset #10 preceded a strictly worse failure mode by 46 s. **Detection was never the deficiency**
  — RECEPTION ALERT fired correctly 8 minutes in. Now: each reset is judged by whether reception
  recovered, 3 ineffective ones stop the loop and escalate **once** with a `docker inspect`-derived
  recreate command (secret env values redacted), and `rtldavis process is not running` never
  triggers a reset at all. Escalation lands ~18 min in — for ERR-0005, ~00:29 instead of 01:27.
  **Auto-recreate deliberately not built:** n=1 and unexplained, against the owner's own
  "proven fix" bar. 14 tests, including a replay of the incident's shape.
- **The driver threw away the evidence.** `logerr("err: %s" % self._mgr.get_stderr())` formatted a
  *generator's repr* — and iterating it would not have helped, since that generator is gated on
  `running()` and yields nothing once the process is dead. New `drain_stderr()`; 6 tests pin both
  layers. Driver → **`0.20+ws.4`**.
- **The DEC-0031 canary had silently stopped checking.** `ops/soak_check.sh` grepped a hardcoded
  `0.20+ws.1` and degraded to a soft `note` on mismatch, so from **v2.0.10 onward** it verified
  nothing and "wrong version" was indistinguishable from "banner not in window". Now reports the
  version actually announced, three distinct states, mismatch is a **FAIL**.
- **Abort near-miss investigated and cleared.** The campaign-A abort at 00:08:21 looked like a
  DEC-0061 repeat (loop data flowing at 71%) but was **correct**: `health_ok()` waits for an
  *archive* record, last was 00:04:20 and next 01:24:24. RapidFire publications are not archive
  records. Campaign B is not gated on it.
- **Campaign B prepared to launch 08-03, then HELD (DEC-0066).** Schedule shifted −4 days (pure
  constant offset; Latin square preserved by construction), v2.0.12 built and all four `BIAS_TEE`
  branches verified, apparatus green. Held after **two further outages the same day**: a 3-minute
  dropout at 13:47 (**unexplained** — no engine shutdown, no DB error, driver never faulted) and a
  10-minute outage at 19:45. The decisive argument is not abort risk but **instrument trust**: B
  measures reception, and a receiver intermittently losing 50–100% of packets for unexplained
  reasons yields noise shaped like a result. **Design unchanged; only timing.** ⚠️ The schedule
  literals now sit in the **past** — regenerate before any `install`, or `due_arm()` jumps straight
  into the middle of the square.
- **`database is locked` is a thread now, not a one-off.** It caused the 19:45 outage on its own,
  with no restart churn in front of it — this session first called those errors "downstream noise"
  and was **wrong**. The lock is momentary; what made it a 10-minute outage is that
  **OgoxeUploader, Influx and OWM all refused to shut down**, holding the teardown ~100 s with the
  driver killed. Any future DB hiccup does the same.
- **First honest no-LNA telemetry accruing:** n=1106 windows at gain 372, mean **72.0%**, **no
  hour-07 notch** (S58 measured ~2 pts LNA-in). Campaign A pooled 72.4% — but A pools the gain-207
  arms and is biased low, so this is **not** parity and **not** adoption evidence.
- **Versioning documented** after the owner asked what `ws` stands for — an expansion that appeared
  **nowhere in the repo**. New README §Versioning: image version vs driver version, `ws` =
  WeatheredScientist, per-file counters, and why we never renumber into upstream's space. Also
  fixed a README that still advertised **v2.0.9** as current, three releases stale.

---
## [S61] — 2026-08-01 — Campaign B designed end to end (DEC-0064): owner-gated swap night, overnight pilot, no-LNA square

Design session (owner-escalated). Nothing deployed; everything staged for the 08-06/08-07 window.

- **DEC-0064 — campaign B pre-registered end to end**, so the swap night is execution, not
  derivation. Swap sequence is **owner-gated**: nothing touches the container or bias tee until an
  in-chat GO with the owner physically at the dongle — the antenna-disconnected window is the
  20–40 s SMA swap. Checklist: **`docs/CAMPAIGN-B-RUNBOOK.md`** (new, + MANIFEST row).
- **`ops/rx_experiment.sh` rewritten for campaign B:** overnight pilot 08-07 00:35–04:20 (gain-only,
  45 min/arm, HIGH→LOW 496/449/402/372/328 — pre-registered as arm-selection input only; an abort
  = the cliff found with high arms already harvested), **H hold** (arm-A settings under their own
  harvest tag, Friday daylong baseline window), square 08-08→08-16 at gain **{372, 496}** × ex
  {0, 50} (372 = cross-campaign anchor; `-fc/-ppm 0` unchanged from A to keep the LNA contrast
  clean), abort floor 55→**50%**. Tests extended to 13 (pilot structure, hold placement, square
  balance); **full DRY_RUN pass** exercised every phase incl. guard trip/settle and sticky STOP.
- **v2.0.12 prepped:** `entrypoint.sh` gains a `BIAS_TEE` env (default 1 — published image
  unchanged for existing users; the off branch drives `rtl_biast -b 0` explicitly), Dockerfile +
  `soak_check.sh` bumped. Carries DEC-0062's deferred redaction; landing *between* campaigns means
  B runs uniformly on one image. Build+push Thu 08-06; deploy on the swap night with
  `-e BIAS_TEE=0`.
- **Archive forensics replaced the assumed no-LNA baseline.** A cold-backup copy of the archive
  shows two flat `rxCheckPercent` plateaus — Jun 2–18 **67.45** (sd 3.22, gain 207) and Jul 5–27
  **74.83** (sd 4.13, gain 372) — with the transition hidden in the metric-dark gap. Owner
  confirmed **the LNA was IN during June**: S29's "pre-LNA baseline" label was wrong, honest no-LNA
  telemetry does not exist, and Friday's pilot is the first real measurement. Bonus: both plateaus
  being LNA-in makes their contrast a same-hardware gain comparison — **207→372 = +7.4 pts**,
  retroactively corroborating DEC-0017 in 372's favor (uncontrolled, directional only).
- **Campaign A untouched and healthy** — block 12 (arm B) live at 18:07, 12 swaps clean, zero
  aborts; co-rejection watch still 0 hits. Partial results deliberately not read.
- [ops#126](https://github.com/WeatheredScientist/eaglehunt-ops/issues/126) closed — the citation
  fix had already landed in S59; only the tracker was stale.
- Overdue CHANGELOG roll executed: S54–S58 moved verbatim to `CHANGELOG-ARCHIVE.md` (the live file
  had grown to 7 sessions against the ~3 guideline).

---
## [S60] — 2026-08-01 — DEC-0063 executed: session-start context cut 72% (~25.5K → ~7.2K tokens)

- **Migrated to the ops session-context tiering standard.** `BOOT.md` + `CONSTANTS.md` +
  `MANIFEST.md` are now the entire session-start read; `ARCHIVE/` is never in the load path.
  Measured: always-load went **91,806 B (~25.5K tok) across six files → 25,819 B (~7.2K) across
  four** — a **72% cut**, at the optimistic end of DEC-0063's ~19K estimate. `BOOT.md` landed at
  **2,493 tokens against its ~2,500 cap**.
- **`docs/STATUS.md` is retired.** It did not fit in `BOOT.md` and forcing it would have blown the
  cap, so its content distributed by kind: live bench state → `BOOT.md`; open threads and
  housekeeping → `BACKLOG.md` verbatim; the four upstream threads → a new
  `docs/UPSTREAM-THREADS.md`. Resolved items collapsed to one-line pointers. Deleted rather than
  archived — git history preserves it, and a second copy is what rule 5 exists to prevent.
- **The hook was verified before the delete, not after.** STANDARD §5's hazard is that a `BOOT.md`
  matching no marker shape goes *silently* quiet — the DEC-0106 shape, not wrong output but no
  output. `resume_pointer_for()` was run while `docs/STATUS.md` still existed (returned source
  `BOOT.md`), and again afterward. Both passed.
- **The shared archiver matched a different set of files than ops#130 predicted.** It matches
  *date-stamped* names, so it found three unlisted pre-governance root artifacts and did **not**
  match the three `docs/handoffs/S3x-*.md` files ops#130 named — those are session-numbered. The
  root three were unreferenced and got archived; the handoffs are cited by path from two live docs
  and stayed put with `MANIFEST.md` rows. Moving them would have broken three live citations to
  satisfy a rule about a load path they were never in.
- **A third copy of the broken validation-gate list turned up in `AGENTS.md`**, still naming
  `ruff-format` — the command DEC-0027 exists to reject. S59b fixed `CLAUDE.md`'s copy; S43 fixed
  `.pre-commit-config.yaml`'s. Three copies, three independent drifts. All now point at the single
  list in `docs/CONVENTIONS.md`. `CLAUDE.md`'s duplicated infra table went the same way — it had
  already gone stale on the reception baseline and on the driver-vs-config layer table.
- **A second public-repo divergence: `ARCHIVE/` stays uncommitted.** STANDARD rule 3 has retired
  material live in the repo under `ARCHIVE/`. Here it can't: the directory was already gitignored,
  its three files had **never been tracked**, and a scan found **IP- and credential-shaped strings
  in two of them** — pre-governance conversation dumps written before this repo had any secret
  hygiene. Committing them would violate DEC-0012. `MANIFEST.md` now says this at the top of its
  `ARCHIVE/` section, because the alternative is a manifest pointing a fresh cloner at files their
  clone does not contain — the same dead-end-for-external-contributors problem DEC-0063 already
  called out once. **For a public repo, git history is the archive.** Nothing was lost; retired
  repo content is reachable with `git log --follow`.
- **Both divergences share one root cause**, worth stating for ops: the standard's two
  "preserve-or-share by pointing at a file" mechanisms — `ops/CONSTANTS.md` and `ARCHIVE/` — each
  assume every reader has access that the public member's readers do not.
- **`docs/ASSESSMENT.md` deliberately left alone.** It still describes STATUS.md as the source of
  truth, and it is a *dated audit artifact* — rewriting it to match today would destroy the record
  of what was true then. Flagged in its `MANIFEST.md` row instead.
- Gates: pytest **125 passed**, mypy clean on 33 files, secret gate positive-controlled. Hook
  resume-pointer verified live.

---
## [S59b] — 2026-08-01 — the documented validation gates now actually run

- **Three of the four commands under CONVENTIONS §"Python / validation" failed when followed
  literally, and one of them damaged the tree.** Found while running the S59 closeout green gate —
  the gate list had never been executed verbatim.
- **`ruff format` was listed as a required gate, and DEC-0027 exists specifically to reject it.**
  Running it as documented reformats **30 of 33 files**, against the deliberate column alignment
  that decision protects. The identical contradiction reached `.pre-commit-config.yaml` and was
  removed there at S43 — *this line was the surviving copy*, still instructing the reader to run it
  for two years of sessions. Now marked do-not-run with the reason attached.
- **The interpreter guidance pointed at two dead ends.** The doc said "on the macOS dev box the
  interpreter is `python3` — there is no bare `python`." Both halves are wrong: a bare `python`
  does exist (pyenv shim, 3.12.12), and **neither it nor `python3` (Homebrew 3.14) carries pytest,
  mypy or ruff at all**. `python3 -m pytest` returns `No module named pytest`. `.venv/bin/python`
  is the only interpreter on this box with the tooling; all three commands now spell it out.
- **mypy needed arguments the doc never supplied.** This repo has no mypy config of any kind (no
  `pyproject.toml`, no `mypy.ini`, no `setup.cfg` — only `ruff.toml`), so a bare `python -m mypy`
  exits `Missing target module, package, files, or command`. Documented with the flags
  `.pre-commit-config.yaml` actually passes plus an explicit file list, which reproduces CI locally.
- **Secret-gate note sharpened on the same parenthetical.** It said the gate "passes cleanly with no
  staged files rather than erroring" — true, and a trap: a clean pass (silent, exit 0) and
  `SECRET-SCAN: nothing to scan` (exit 0, scanned *nothing*) are indistinguishable by exit code.
  Now says to stage first and positive-control any clean result (DEC-0039/DEC-0045).
- Every command verified as written before committing: `ruff check` passes, pytest **125 passed**,
  mypy clean on 33 files with `.mypy_cache` cleared, and `ruff format --check` confirms the
  30-of-33 figure rather than it being inferred.
- **The lesson, which is the reusable part:** a documented command that nobody runs verbatim decays
  exactly like a doc's prose claims do (dash DEC-0104), except it fails *loudly* the first time
  someone follows it — or, in `ruff format`'s case, succeeds destructively. Worth running a doc's
  own gate list literally when touching it.

---
## [S59] — 2026-08-01 — #74 watch closed on evidence; ops#126 citation fixed; ops#130 answered ADOPT (DEC-0063)

- **Issue #74's calm-windDir watch is CLOSED.** The v2.0.9 fix is confirmed on air: **zero**
  `windDir expired` WARNINGs across five consecutive days (07-28 … 08-01) against a prior base rate
  of ~1/hr. Checked with a **positive control** — the same grep returns **21 hits** in the 07-27 log,
  so the pattern still matches and the zero is real, not a false zero from the `nasctl grep`
  multi-word gotcha. STATUS's standing-watch list and ROADMAP's P1 watch line both updated (DEC-0057
  step 5). **No DEC for this item specifically** — closing a watch against a criterion agreed when
  the watch was opened is not a new design call. (DEC-0063 below is this session's one DEC, and it
  is about ops#130.)
- **[ops#126](https://github.com/WeatheredScientist/eaglehunt-ops/issues/126) fixed** — after
  eaglehunt-ops suffixed three re-issued decision IDs, one citation here resolved to the wrong
  decision. `DECISIONS-FULL.md` (DEC-0052 body) now reads `locked OPS-DEC-0019b`, the
  CLOSEOUT-TEMPLATE lock. Independently re-verified that this repo's other three `OPS-DEC-0019`
  references (CHANGELOG-ARCHIVE, S45/S46) all mean the **first** use — the env-twin rollout — and
  correctly stay bare. No `OPS-DEC-0020`/`0021` citations exist here.
- **Campaign A untouched and healthy** — 10 of 32 blocks harvested, block 11 (arm A) live, 11/11
  swaps healthy, zero aborts, completes ~08-07 00:05. Partial results deliberately not read.
- **One unscheduled restart logged, not chased.** `weewxd CRITICAL Database OperationalError
  exception: database is locked` at 15:08:22 on 08-01; weewx waited its built-in 2 minutes,
  re-initialized cleanly at 15:10:22, and resumed publishing (verified 15:43). First of the live
  campaign. Recorded because the campaign's settle rule drops samples after a *swap*, not after an
  unscheduled restart, so block 11 carries a small unmasked transient.
- Also corrected in passing: STATUS.md's header still said "Current session: S57" two sessions on,
  and its handoff heading said "S57 done → S58". Both reconciled. Documented that
  `ops/rx_experiment.sh status` is **not** a `nasctl` verb, and that `rx_experiment.log` was never
  rotated — it still carries the aborted 07-29 run, which inflates a naive swap count by 2 blocks.
- **[ops#130](https://github.com/WeatheredScientist/eaglehunt-ops/issues/130) answered: ADOPT the
  session-context tiering standard (DEC-0063)** — against that issue's own recommendation to defer.
  ops filed it saying "the case here is genuinely weak," on the basis that this repo is the leanest
  in the forum at ~21K and migration buys "maybe 6–8K tokens." Checking the premise rather than the
  offer: the tree is at **~25.5K, not ~21K** (ops measured a tree two session-closes stale); the
  saving is **~19K, not 6–8K** (`CHANGELOG.md` + the `DECISIONS.md` index leaving always-load is
  ~12.2K by itself — more than ops's quoted total, an internal inconsistency in the issue); and
  decisively, Tier-1 measured at four consecutive merge points grows **~1.1K tokens per session
  close**, structurally, because DEC-0052's closeout steps 2 and 3 append to STATUS and CHANGELOG
  every time. "Leanest in the forum" is a statement about a moment, not a trajectory. Both siblings
  have already migrated; this repo was the last of the trio.
- **A spec gap found and NOT resolved unilaterally.** STANDARD.md §3 has the trio load
  `ops/CONSTANTS.md` at session start, and separately says this repo may point at ops but never
  quote it. Those clauses conflict here: **ops is private and this repo is public**, so a
  `CLAUDE.md` telling its reader to load `ops/CONSTANTS.md` is a dead end for every external
  contributor — the population this repo has and the other three do not. This repo's `CONSTANTS.md`
  will be self-sufficient for anyone who can clone it (closer to coffeeradar's DEC-0017 posture),
  with any ops reference marked an owner-only supplement. Filed back to ops rather than edited into
  their file — read-only across the boundary.
- **The migration itself is a work order for S60, not done here.** STANDARD §7 wants migration at a
  session end with full state in context, which this was; it was still wrong to start, because the
  session stood at **~157K absolute context** against AGENT-ECONOMY §7's ~200K ceiling and the
  mechanical work is ~40K more. A half-applied migration leaves two contradictory entrypoints and a
  hook choosing between them by fallback order. Decision taken where the state was; execution
  written down as seven numbered steps in STATUS.md.
- Gates: pytest **125 passed**, mypy clean on 33 files (`.mypy_cache` cleared first, per CONVENTIONS).

---

## [S58] — 2026-08-01 — campaign A tracking clean (9/32 blocks); a site RF notch characterized, DEC-0059's diurnal claim amended

- **Campaign A healthy, no intervention.** 9 of 32 blocks harvested, 9/9 swaps healthy, zero aborts;
  prod untouched apart from the arms cycling in the mounted `weewx.conf`. **Both main effects are
  flat**: gain 207 vs 372 = **−0.1 pts (±0.36 SE)**, ex 50 vs ex 0 = **−0.1 (±0.36)**, against
  DEC-0059's ≥2.0-point adoption bar. The apparent −1.2 pt gain effect visible on day 1 dissolved as
  blocks accumulated — which is precisely why the design pre-registers 8 blocks/arm instead of
  letting anyone read day 1.
- **Site RF notch characterized** (BACKLOG §Durable RF findings). Reception dips ~2 pts at **hour 07
  and hour 19**, reproducibly, and **predates the campaign** — so it belongs to the site, not to any
  arm. Corroborated by two independent metrics (the monitor's 26% sample and the archive's
  `rxCheckPercent` min of **4.9%** in the same minute). Three candidate explanations were tested
  against the station's own weather archive and **falsified**: dew (the dewiest hours have the
  *best* reception), solar noise (radiation peaks midday where reception is fine), and wind (the
  deepest notch fell on a zero-wind morning).
- **`freqError` thermal drift measured on our own hardware** — ~2400–2600 at 65–69 °F falling to
  ~900–1200 at 77–84 °F. Real and cleanly temperature-linked, but **not** the notch's mechanism:
  hour 06 pairs the highest freqError with excellent reception, so the AFC is absorbing it.
- **DEC-0059 amended**: its "no detectable diurnal cycle" holds at 6-hour resolution and fails at
  hourly. The notch is small enough to sit inside the quoted 70–75 band, which is how it was missed,
  but it repeats daily. No effect on campaign validity — the Latin square balances any time-of-day
  term across all four arms.

---
## [S57b] — 2026-07-29 — campaign A aborted after 80 min; two defects fixed (DEC-0061), schedule regenerated, re-armed

- **Campaign A aborted 12:13 EDT in its third block.** The safety model worked: baseline snapshot
  restored, sticky STOP sentinel set, prod left healthy on `gain 372` — verified. The one thing it
  failed to do was tell anyone.
- **Defect 1 — the health check was too small by construction.** `health_ok` allowed ~90s for a new
  archive record after a restart, but a restart needs boot (~25s) + up to a full 60s archive
  interval + ~30s write lag ≈ **115s worst case**. Measured on the failure: `weewxd` init 12:11:46,
  first record 12:13:30, abort fired 12:13:27 — **three seconds early**. Arm B had won the same coin
  flip 80 minutes before. Now `HEALTH_TRIES=36` (~180s), and the test asserts the *arithmetic*
  rather than the literal, so lowering it fails with the reason attached.
- **Defect 2 — every alert this script could send was inert.** `send_mail` sourced `monitor.env`
  without exporting, so its `python3` child saw nothing and died on `KeyError: 'ALERT_FROM'`. True
  since the file was written; never disproved because no alert had ever fired. Extracted
  `load_env()` (`set -a`/`set +a`), tested against a real child process, mutation-verified. Confirmed
  live against the real `monitor.env` after deploy (booleans only, never values) — all `True`.
- **Schedule regenerated for a 2026-07-30 start** (completes 08-07). The 07-29 run lost `A@00:05`,
  took a partial `B@06:05` and lost `C@12:05` — three damaged Latin-square cells, the exact
  time-of-day confound the design exists to remove. ~10h of delay bought a valid experiment.
- **Re-armed:** fixed script deployed (sha `88c1aeaf…`, byte-verified against the merged `dev` tip),
  stale state reset to `NONE` (otherwise the first tick would have harvested a baseline-config period
  and recorded it as arm-B data), STOP cleared, the aborted run's 88 samples rotated aside. Campaign
  starts itself at 00:05.
- Also corrected a comment promising a `schedule --generate <date>` mode that **has never existed**;
  the dev-side recipe that actually produces the table is recorded in its place.
- Gates: pytest **123 passed** (was 120), mypy clean. See DEC-0061.
- **Credential redacted from a startup log line (DEC-0062).** `pressure_service.py` logged
  `api_key[:8]` at INFO on every restart, into `weewx.log` and its 30 rotations. The point isn't the
  8 characters — it's that **DEC-0047's read-guard covers configs, not logs**, so the most routine
  operation in this repo (tail the log to confirm a restart was clean) walks past the guard into an
  agent transcript. It did, twice, on 2026-07-29. Now logs `present`/`MISSING` with the flags
  resolved into locals *before* the call, so no credential attribute appears in a log argument at
  all — guarded by an AST test with a positive control. **The file is BAKED (`Dockerfile:117`), not
  mounted as first assumed** — an `scp` would have been a silent no-op (DEC-0031), caught only by
  actually asking DEC-0046's "which layer wins in prod?". **Deploy deliberately deferred to the next
  image release:** rebuilding restarts prod, and swapping the image under a running 8-day factorial
  would confound its arms. pytest **125 passed**, mypy clean on 33 files.

---
## [S57] — 2026-07-29 — Phase 0 confirms FreqError telemetry (DEC-0060); RX campaign A deployed and running

- **Phase 0 answered:** `FreqError` telemetry exists in the deployed driver — confirmed within 13s
  of a restart (`Hop: {ChannelIdx:0 ChannelFreq:902419338 FreqError:0 Transmitter:0}`). Getting
  there took a real correction: the first attempt (`debug_rtld=2` alone, ~19:11 EDT 07-28) produced
  zero evidence for ~7h because the live `[Logging][[[user]]]` logger was at `INFO`, independent of
  `debug_rtld` — `dbg_rtld()` calls `log.debug()`, silently dropped regardless of verbosity. Fixed
  with a scoped `[[[user.rtldavis]]]` DEBUG logger entry (DEC-0060), not the broader `[[[user]]]`.
  Both changes fully reverted once confirmed (09:34 EDT 07-29). Honest tally: elevated-debug window
  ran ~14.5h against a planned 3h (a session gap), `weewx.log` grew to ~8.8 MB vs. a normal
  ~4 MB/day — non-critical, but a real DEC-0041 bloat instance. `ppm`/`fc` measurement-by-value
  deliberately deferred, not blocking the campaign.
- **`ops/rx_experiment.sh` deployed and running.** Scp'd to the NAS project root (sha-verified),
  `install` run (baseline snapshotted). Owner created the two DSM Task Scheduler entries (`tick`,
  `guard`, 5 min, root); first automatic tick swapped to arm B (gain 207, `-ex 0`) at 10:52:37 EDT.
  Campaign A runs unattended for 8 days, self-terminating to baseline (~2026-08-06 expected).
- **DEC-0059 status updated** (deployed/running, was design-only) and **DEC-0060 added** (the
  logger-level gotcha, so it isn't re-derived next time debug output is needed). ROADMAP.md P2
  section reconciled: Phase 0 checked off, campaign A marked running, the "rebuild for FreqError
  telemetry" item closed as moot (the current binary already has it).
- **Cross-repo:** [ops#112](https://github.com/WeatheredScientist/eaglehunt-ops/issues/112) closed
  with the full finding; [ops#114](https://github.com/WeatheredScientist/eaglehunt-ops/issues/114)
  tracks the running campaign; [ops#113](https://github.com/WeatheredScientist/eaglehunt-ops/issues/113)
  (the transient-state tracking proposal, filed this session) was independently built and closed by
  ops the same day — worth adopting `.claude/transient-state` here for future transient prod state.

---
## [S56d] — 2026-07-28 — S56 closeout

- Handoff rewritten so S57 opens on the three RX items in order (Phase 0 → deploy → regenerate the
  schedule if the start date slipped), with the standing watches demoted below them.
- Docs diet (DEC-0030): `[S53]` rolled verbatim to `CHANGELOG-ARCHIVE.md`; entries here now run
  S54–S56, and the S56 entries were **reordered newest-first** — they had landed S56, S56c, S56b,
  contradicting this file's own "most recent first" rule.

---

## [S56c] — 2026-07-28 — the RX experiment gets an apparatus (DEC-0059); 7 dead sweep scripts deleted

Design + tooling only — **nothing deployed, prod untouched** (still v2.0.11, gain 372).

- **`-ex N` ≡ `receiveWindow 300+N`** — upstream sums them and `receiveWindow` appears nowhere else,
  so the window axis is a mounted-config knob and **no arm of the experiment needs an image
  rebuild**. The `rw250/rw350/rw400` images were redundant, not just misnamed (DEC-0048). Read from
  upstream master; the deployed binary is older and unverified directly — caveat recorded.
- **Measured baseline replaces "~67–70%"**: 447 samples → **73.3%, sd 4.67**, autocorrelation ~0,
  no diurnal cycle. So 24 h/arm resolves 1.1 pts and DEC-0017's "1–2 weeks" was ~7× overkill.
- **`ops/rx_experiment.sh`** — Latin-square scheduler with literal-only arms, atomic verified writes,
  byte-exact whole-file revert, sticky STOP sentinel, self-termination to the production baseline,
  and a mailer independent of `weewx_monitor.py`. Verified end-to-end against fixtures.
- **`tests/test_rx_experiment.py`** (8 tests) — drives the real shell functions; includes a DEC-0045
  positive control proving the old global-regex approach corrupts the same fixture, and a machine
  check that the Latin square is balanced (mutation-tested: it goes red on a one-row typo).
- **Deleted all 7 pre-governance sweep scripts.** `gain_sweep.sh` and `fc_sweep.sh` counted
  `RAW_DATAPACKET_MATCH`, which prod no longer logs — they would have reported 0.0% for every arm
  and looked like they worked. `gain_sweep.sh` also used a 2.5 s denominator against our 2.8125 s
  ISS. The one durable finding living only in `fc_sweep.sh`'s header was moved to BACKLOG first.
- **DEC-0008's `set_gain.sh` exemplar superseded** — the kill/start codification moves to
  `restart_container()`; the rule itself is unchanged.
- Secret gate caught the test fixture's credential-shaped line; fixed the fixture, **not** the
  allow-list (DEC-0045).

---

## [S56b] — 2026-07-28 — ROADMAP.md split to P0–P3; long-term direction moves to BACKLOG.md (DEC-0058)

Same session, second act. Docs-only, nothing deployed.

- **STATION_NAME check:** before doing any work, live-verified the NAS `monitor.env` —
  `STATION_NAME="Eagle Hunt PWS"` was already set (since S31). BACKLOG.md's note was stale (dated
  "observed S27," pre-fix); corrected, no NAS mutation needed.
- **DEC-0058:** `docs/ROADMAP.md` trimmed to P0–P3 only (the actively-sequenced plan). P4 +
  "Longer horizon" (credential hygiene, multi-source adaptability, the template harvest, ops#110)
  moved to a new "Long-term direction" section in `BACKLOG.md` rather than a fourth document.
  `CLAUDE.md`'s doc-map annotated with the split.
- While editing `BACKLOG.md`, found and pruned a second stale copy of the already-resolved (S48)
  May rain-total item — same fact CHANGELOG `[S56]`'s ROADMAP pass had already corrected once, in
  the other file.
- **Self-caught bug:** the DEC-0057 append (`[S56]`, above) had matched an `old_string` that didn't
  include the file's true last line, stranding an orphaned original fragment (`*silently*.`) after
  everything inserted, and papering over it with an invented duplicate sentence. Fixed before
  appending DEC-0058: restored the original DEC-0056 closing line, removed the invented text.

---

## [S56] — 2026-07-28 — ROADMAP.md reconciled and restructured; DEC-0057 adds it to the closeout ritual

Docs-only, nothing deployed. Prompted by a routine status check that turned into an audit.

- Confirmed prod healthy on v2.0.11: co-rejecting grep 0 hits (positive-control-verified against a
  known-present pattern), ops#105 confirmed CLOSED. Found ops#110 newly opened (winter 2027
  sky-state instrumentation — IR sky sensor alongside the lightning detector; planning horizon
  only).
- **ROADMAP.md reconciliation pass:** found and fixed 5 items shown open that had already shipped —
  the `cleanup_backlog.md` fold-in (done S27), remote-URL-casing + stale-branch cleanup, P1.5's
  "deploy pending" (shipped v2.0.4, S34), the May rain-total reconciliation (done S48), and the
  README public-onboarding refresh.
- **Fuller restructure:** folded the old P1 ("false-rain fix") and P1.5 ("Sensor-QC hardening")
  sections into one continuous data-integrity arc that now actually covers what shipped since —
  v2.0.4 through v2.0.11 (sensor-QC filter, reception-metric fix, frame-level co-rejection, signed
  temp decode, cap-16 tuning) — previously unrepresented on the page entirely. Collapsed P0.5's
  mostly-done checklist to a pointer. Added the ops#110 item under Longer Horizon.
- **DEC-0057:** ROADMAP.md joins the closeout ritual as step 5 — same-session update whenever a DEC
  ships/closes/reprioritizes a line item — plus a "Keeping this current" tripwire inside
  ROADMAP.md itself (next full check due **by S66**). CLAUDE.md's closeout steps renumbered
  (5→6 model-tier restore, 6→7 commit+push).

---

## [S55c] — 2026-07-28 — v2.0.11 shipped: cap 16 live in prod; ops#105 audit closed from this side

Third act of the day, owner-approved after the ops relay flagged the gap: DEC-0056's cap was merged
but inert (the driver is baked, DEC-0031 — v2.0.10 was built before PR #93). Released same-day so
R2 actually protects the station.

- **Release:** `DRIVER_VERSION` → **0.20+ws.3**, Dockerfile header → v2.0.11 (one PR this time,
  #95); promoted via #96 (merge `a4628769`); NAS build from the md5-verified tree (the build
  script's tree gate caught my own stale ws.2 assertion from the v2.0.10 template and refused to
  build until corrected — the check working as designed, on its author); pushed `:v2.0.11` +
  `:latest` (digest `sha256:b8f35f36…`); prod recreated 11:00 EDT; live-verified banner
  `0.20+ws.3`, sensor_qc active, records publishing, soak 13/2/0 (restart-window WARNs). Tagged
  **`prod-baseline-20260728b`**;
  [GitHub release v2.0.11](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.11).
  **Rollback: `:v2.0.10`.** Fifth consecutive clean recreate; no stall.
- **Monitor tripwire live end-to-end:** owner killed the old monitor 10:28, scheduler respawned it
  on the reframed code (sha-verified), startup email received, `--test-alert` fired through the
  new wording and received.
- **Prod moved v2.0.9 → v2.0.10 → v2.0.11 in one day** (R1 then R2), each with its own baseline
  tag and retained rollback.
- **ops#105: both code items (R1 + R2) now released, deployed, live-verified** — audit umbrella
  closeable from this repo's side
  ([completion note](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5105845282)).
- Docs: CONVENTIONS/CLAUDE quick-ref → v2.0.11 / `prod-baseline-20260728b` / rollback `:v2.0.10`;
  soak `EXPECT_IMAGE` default → `:v2.0.11`.

---

## [S55b] — 2026-07-28 — R2 decided and coded: `MAX_PLAUSIBLE_TIPS` 60 → 16 (DEC-0056), rejection email reframed as the tripwire

Same session, second act: the owner opened the R2 design discussion, an **evidence pass over the
full 70-day archive** settled it, and the owner approved the package (PR #93).

- **The evidence** (pre-correction backup, 95,901 minutes, 490 wet): worst real minute **7 tips**;
  worst real 3-min window **exactly 16** (2026-06-14 storm — still passes, the check is
  `delta > max_tips`); reception during rain never below 50%; in-service gaps near rain: two
  1-minute events ever; rain-counter rejections at cap 60 in the 30-day logs: **zero** (all five
  "implausible" hits are SensorQC wind/humidity). Physics: at the bucket's ~4 s/tip ceiling a
  genuine delta can exceed 16 only across a >64 s gap — longer than any gap observed during rain.
  **Reframing:** weewx `[StdQC]` (0.3 in/min) already discarded anything over 30 tips, so
  "60 → 16" really exposes only the never-occupied 17–30 band.
- **The worry that shaped the package** (owner: don't lose an intense storm to an over-tight
  filter): the change ships with the failure mode converted from silent-permanent to
  loud-bounded-recoverable — `weewx_monitor.py`'s existing DEC-0021 glitch email is reframed as
  the **DEC-0056 tripwire** (prompts the WeatherLink cross-check; a rejection on a wet day is the
  predefined revisit trigger), a **recovery playbook** is written into DEC-0056 (console
  reconciliation via the ERR process), and a **driver↔monitor marker contract test** pins the
  alert to the driver's exact wording. Confirm-on-reject documented as the designed escalation if
  the tripwire ever fires on real rain.
- Tests 111 → **112**: boundary 16-passes/17-rejects, the 06-14 evidence vectors, cap-60-era
  cases retuned as documented rejects; cap and marker assertions both **mutation-tested red**.
- **Deployment split:** the monitor (mounted layer) deployed NAS-side same session — scp'd from
  the merged tip, sha-verified `383f5baa…`, restarted via the scheduler respawn. The driver cap
  (baked layer, DEC-0031) **rides `dev` until the next image cut (v2.0.11)** — prod's running
  driver keeps cap 60 until then; a hardening, not a live bug, so it forces no deploy.
- R2 closed out on [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105).

---

## [S55] — 2026-07-28 — v2.0.10 shipped: the signed temperature decode is live in prod; upstream PR #23 opened

**The R1 release (DEC-0055), executed end-to-end** — prod ran the unsigned decode until 09:28 EDT.

- **Version bump first** ([#88](https://github.com/WeatheredScientist/weewx-rtldavis/pull/88)):
  `DRIVER_VERSION` 0.20+ws.1 → **0.20+ws.2** — the banner is the live-verify marker (DEC-0046), so
  a driver release must be distinguishable in the running log — plus the missing 2026-07-28
  DEC-0055 entry in the driver's header change list, README, and the CHANGES-FROM-UPSTREAM version
  table (`influx.py` stays ws.1, untouched). Dockerfile header → v2.0.10
  ([#90](https://github.com/WeatheredScientist/weewx-rtldavis/pull/90); every release since v2.0.6
  bumps it). Promoted dev → main (PRs #89 + #91, merge `2d3bc09a`), CI green throughout.
- **Built on the NAS from the verified tree** (S52 pattern: staged tarball → fresh
  `build-v2.0.10/`, with `rtldavis.py` md5-checked against `git show` before the build could
  start); pushed `:v2.0.10` + `:latest`, digest `sha256:ee3027e1…`. weewx stays pinned 5.4.0
  (#78) — no silent drift this rebuild.
- **Prod recreated** from the re-captured live inspect config (kill→rm→3 s→run; no mounted-layer
  changes this release — `loop_json_writer.py`/`influx.py` untouched since v2.0.9).
  **Live-verified (DEC-0046):** banner `0.20+ws.2`, `sensor_qc True`, records arriving, outTemp
  74.1 °F sane, soak **13 PASS / 2 WARN / 0 FAIL** (both WARNs restart artifacts). No startup
  stall — 4th consecutive clean recreate. Tagged **`prod-baseline-20260728`**;
  [GitHub release v2.0.10](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.10).
  **Rollback: `:v2.0.9`** on the NAS and Docker Hub.
- **Upstream [lheijst#23](https://github.com/lheijst/weewx-rtldavis/pull/23) opened**
  (owner-reviewed verbatim), companion to #22. Found while drafting: **upstream #19 (LloydR) had
  already diagnosed the sign bug** — its 16-bit-signed ÷16 form carries the `pkt[4]` flag nibble
  into the value (a constant +0.05 °F on digital frames) and lacks `0xFF8`; #23 credits the
  diagnosis and offers the masked 12-bit form as an alternative, non-stepping per #22's precedent.
- **R1 closed out on [ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5104787452)**;
  **R2 untouched** (owner holds it for design discussion).
- Housekeeping: two stale `.claude/worktrees/` (+ their `claude/*` snapshot branches, 0 unique
  commits) removed; four merged `s54-*` branches deleted local + origin — the repo is back to
  exactly `dev` + `main`. Session-start watches: co-rejection 0 hits (positive-control-verified),
  #74 calm-windDir silent 10.6 h post-v2.0.9 (last WARNING 21:59, 19 min before that deploy),
  humidity largest step 0.7 pts in 240 new samples, soak 10/5/0 pre-release.
  `ops/soak_check.sh` `EXPECT_IMAGE` default → `:v2.0.10` (STATUS's standing instruction). No new
  DEC — the session executed DEC-0031/0038/0046/0055 as designed.

---

## [S54] — 2026-07-28 — R1 landed: outside-temperature decode is now signed two's complement (DEC-0055); not yet released

Owner approved **R1** from the S53 ops#105 audit; **R2** (`MAX_PLAUSIBLE_TIPS` 60 → 16) held for
further discussion and is untouched.

- **`rtldavis.py`** — the 12-bit digital temperature field is decoded as **two's complement**
  (`(temp_raw - 0x1000) / 10.0` when bit 11 is set), and `0xFF8` joins `0xFFC` as a no-sensor
  sentinel. Unsigned, a −5 °F reading decoded to 404.6 °F (207 °C), tripped the −40…65 °C SensorQC
  bounds, and — since v2.0.9 — **co-rejected the entire frame** (DEC-0054), so an ordinary cold
  snap would have nulled wind + payload every ~30–60 s and saturated the corruption alarm we are
  currently watching. Analog/thermistor branch untouched.
- **Deliberate one-LSB deviation from weewx-meteostick** (DEC-0055): its
  `-(temp_raw ^ 0xFFF)` is *one's* complement — 0.1 °F warm on every negative, maps `0xFFF` and
  `0x000` both to 0.0 °F, and flips the truncation bias at zero. Its two real contributions (the
  field is signed; the `0xFF8` sentinel) are adopted.
- **`tests/test_temp_twos_complement.py`** — 10 new tests: −40 °F frame, the `0xFFF` case that
  distinguishes this from meteostick, both sentinels, a DEC-0054 **co-rejection non-fire** sweep
  (−0.1…−39.9 °F), plus two positive controls (frame-builder round-trip; proof the bounds gate
  really fires on the old unsigned decode). All three plausible regressions **mutation-tested red**.
  Also fixed a real cross-module test-isolation trap: these suites share `sys.modules` and replace
  `weewx.wxformulas` wholesale, so the stub is now additive and resolved through `rtldavis.weewx`
  (the object the driver actually dereferences) rather than `sys.modules['weewx']`.
- **`CHANGES-FROM-UPSTREAM.md`** — two DEC-0034 fork-inventory gaps closed. DEC-0054 (frame-level
  co-rejection, shipped in v2.0.9 at S52) had never been recorded there and is now behavior
  change **11**. The `rtldavis.py` delta was **recounted against the real upstream baseline** —
  fetched from the same `weewx-contrib` `src.tgz` the Dockerfile builds from, which this repo does
  not vendor: **+477 / −88** (1422 → 1811 lines), replacing S37's **+263 / −51**. That figure was
  one commit stale the day it was written (it is the exact count at `cd49214`, and the S37 commit
  recording it also added the fork-identity header). The reproduce recipe now ships next to the
  number, so the next recount is a paste rather than an archaeology session.
- **Upstreaming table** — gained the temp-sign candidate (the prose already claimed 10 was part of
  the intended contribution), and two **stale statuses corrected**: it still read *"draft comment …
  not posted"* and *"not yet offered"* for work that has been live upstream since S38 —
  [lheijst#22](https://github.com/lheijst/weewx-rtldavis/pull/22) and
  [david-lutz#1](https://github.com/david-lutz/weewx-influx2/pull/1) are both OPEN, and the issue #15
  comment was posted 2026-07-13. The table was written at S37 and never re-read after the PRs landed.
- **Stray `0` file removed** from the repo root ([#86](https://github.com/WeatheredScientist/weewx-rtldavis/pull/86)) —
  a zero-byte artifact committed by accident in `5e3c3dd` (S41) alongside `ops/soak_check.sh`, a
  script dense with redirects; a stray `2>0` for `2>&1` is the likely mechanism. It landed as
  `0 | 0` and was never referenced: nothing redirects to it, the `Dockerfile` `COPY`s only named
  files (no root glob, so it never entered the image), and there is no packaging manifest to sweep
  it up. Tracked files 82 → 81.
- Gates: pytest **111 passed**, `ruff check` clean (0.5.7, DEC-0027), `mypy --ignore-missing-imports
  --no-strict-optional .` clean on 33 files.
- **Not released.** The driver is baked (DEC-0031) → needs an image rebuild + deliberate release,
  deadline **before first frost**. A companion upstream PR belongs alongside lheijst#22.

---

## [S53] — 2026-07-27/28 — ops#105 cross-observable QC audit delivered; archive swept CLEAN; temp sign bug found (no code)

The owner-directed audit ([ops#105](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105),
carry-forward of ops#103's "where else could this slip through") delivered as an
[issue comment](https://github.com/WeatheredScientist/eaglehunt-ops/issues/105#issuecomment-5099627052).
Every encoding verified against `rtldavis.py` source (ops#103's *inferred* entries confirmed; its
"rain closed since 07-12" claim corrected — counter deltas ≤ 30 tips = 0.30 in still clear both
`MAX_PLAUSIBLE_TIPS = 60` and the 0.3 in StdQC cap, and a phantom is never reversed).

- **Historical-signature sweep (full archive 2026-05-19 → 07-27, 95,901 rows, pre-correction
  backup): CLEAN.** 13 gust-spike candidates all adjudicated genuine (storm outflow / breeze
  context) except ERR-0004 itself; temp spike-and-return zero ever; humidity spikes all
  pre-SensorQC (known DEC-0029 class); night radiation/UV zero; isolated rain zero. All 5
  rejection events in 31 days of logs cross-checked — sibling fields clean in the archive. **No
  new ERR entries.** Corroboration: ~722 dup frames/day × 1/65536 CRC-pass ≈ 1 in-bounds escape
  per ~90 days — matches the 1 observed in ~4 months.
- **NEW finding (R1, needs-design, pre-winter):** the temp decode is **unsigned**; Davis is two's
  complement (verified vs weewx-meteostick, which also handles a second `0xFF8` sentinel both our
  fork and upstream lack). First sub-0 °F morning → every temp frame decodes ~+400 °F →
  bounds-trips → **DEC-0054 co-rejects the whole frame** (wind + payload nulled, ERROR-pair log
  spam) for the duration of real cold weather. Inherited upstream bug, never fired only because
  the station hasn't seen winter.
- **Recommendations R1–R5** (temp sign fix; `MAX_PLAUSIBLE_TIPS` 60 → 16; wind residual
  accepted driver-side / spike guard is dashboard's; radiation night-ceiling noted-not-built;
  extra-station zero-QC docs note) — all awaiting design agreement, no code this session.
- **v2.0.9 first-days watch:** co-rejection 0 hits (first post-deploy hour); #74 WARNINGs present
  up to the 22:18 recreate, silent after (needs a full-day re-check); soak 15/0/0, reception 81 %;
  no stalls; humidity watch through 07-27 23:14 still unfired; no Dependabot PRs yet.

---

## [S52] — 2026-07-27 — ERR-0004 phantom 39 mph gust: corrected in both stores, frame-level co-rejection shipped as v2.0.9 (DEC-0054)

**The incident (ERR-0004):** at 14:55:50 EDT, during an rxCheckPercent collapse to 13.2%, one
multi-bit-corrupt-but-CRC-valid frame (DEC-0033 class) carried humidity decoding to 144.9% — rejected
by SensorQC bounds — *and* a wind byte decoding to 39 mph from dead calm, which passed (in-spec, and
+16.5 m/s sat under the 20 m/s delta cap). It became the archive interval's gust max and went out to
all ten external sinks. Owner spotted it on the dashboard hours later; dashboard S149 and an
eaglehunt-ops session had already filed [#76](https://github.com/WeatheredScientist/weewx-rtldavis/issues/76)
+ ops#103 with the diagnosis — independently re-verified here (log + code) before acting; every
claim held. Coordinated in real time on #76 (3 comments: pickup → correction landed → release).

- **Correction applied live, both stores, same session (DEC-0025/0032/0037):** archive row
  1785178560 → windSpeed/windDir/windGust/windGustDir/ET/appTemp/windrun all NULL (wview-extended
  schema carries the derived fields in-row), guarded UPDATE + `rebuild-daily`; InfluxDB point
  rewritten minus 7 wind-affected fields with sparse `windGust_qc=1`/`windSpeed_qc=1` (DEC-0099
  contract). Verified via the public /query proxy: day-max gust now a genuine 12 mph. Dashboard's
  ops#104 verification unblocked the same hour. Backup: `weewx.sdb.bak-err0004-20260727`.
- **DEC-0054 — frame-level co-rejection (v2.0.9):** a bounds failure on ANY field now nulls every
  weather field of that frame and skips the rain counter *without* resyncing its baseline; delta
  trips never co-reject. Zero free parameters — explicitly not the parked DEC-0044 coupling filter.
  6 new tests incl. a verbatim replay of the corrupt frame; the old test asserting same-frame
  humidity *survives* a wind bounds failure was inverted (it encoded exactly this gap).
- **Issue #74 closed (bundled):** calm-windDir TTL expiry logs DEBUG when windSpeed is 0.0 (calm is
  Davis semantics, not a fault); WARNING kept for expiry with wind, and an expired windSpeed counts
  as a dropout. Recovery line downgraded symmetrically. 4 tests.
- **BACKLOG pruned:** DEC-0024 bullet (shipped v2.0.8) and RAW_* log bloat (resolved; live log has
  zero RAW_ lines) marked done.
- **v2.0.9 released:** PR #77 → dev (CI green), image built on the NAS from a fresh checkout, pushed
  to Docker Hub `:v2.0.9` + `:latest` (digest `sha256:5eb38850`), prod container recreated from the
  live inspect config (kill→rm→3s→run), `loop_json_writer.py` hot-swapped (`.bak-pre-v2.0.9`),
  live-verified: driver banner `0.20+ws.1`, `sensor_qc True`, records publishing, `current.json`
  writing (calm windDir correctly omitted), soak 14 PASS / 1 WARN (restart-empty reception window) /
  0 FAIL, no startup stall. Rollback: `:v2.0.8` remains on the NAS and Docker Hub.
- **Found in passing: the Dockerfile installed weewx UNPINNED** — this rebuild silently moved prod
  weewx 5.3.1 → 5.4.0 (came up clean, daily summaries fine; 5.4.0's changelog is reporting/tooling
  only — `weectl rest`, skin fixes — nothing touching the driver API, restx, schema, or QC paths).
  Same silent-drift class as S46's unpinned-ruff CI break. **Closed same session (#78):**
  `requirements.txt` pins `weewx==5.4.0` (matching what is verified-live), the Dockerfile installs
  from it, and `.github/dependabot.yml` turns future weewx releases into review PRs — notification
  and deliberate bump, never a blind update. No rebuild needed: the pin equals the running version.

---

## [S51] — 2026-07-26 — Watch items all run: DEC-0053 TTL watch resolved benign, humidity spike still unfired; issue #74 filed

No code changed. All four S50-handoff watch items executed against prod:

**DEC-0053 TTL-expiry watch — fired 10× in its first full day, both patterns benign, watch RESOLVED.**
(a) One real event: `dewpoint_F`/`outHumidity`/`heatindex_F` all expired at 20:09:44 after a genuine
~13-min humidity-packet reception dropout (19:59–20:12 EDT) — the bound doing exactly its job (the
~611 s of tolerated absence is the two caches stacking: DewpointCacher carries the value ≤300 s, then
the writer's own 300 s TTL runs). (b) Seven `windDir` expiries at ~301 s during calm stretches — the
driver *deliberately* sets `wind_dir = None` on calm readings (`rtldavis.py` ~1356), so any ≥5-min
calm expires the cache. Healthy sensor, semantically correct omission, misleading "sensor may be
failing" text. Filed [#74](https://github.com/WeatheredScientist/weewx-rtldavis/issues/74)
(tier:mid): proposed calm-aware downgrade to DEBUG, needs design agreement first (PRINCIPLES §8).
Explicitly NOT a bump-the-TTL case — a longer TTL would serve a stale direction during calm.

**Humidity-spike watch — still unfired.** 2,755 raw samples decoded covering 2026-07-24 00:04 →
2026-07-26 20:42; largest single step −8.7 RH pts, and that across a 4-min reception gap. Nothing
near the 16–37 pt DEC-0044 single-step signature. No SensorQC rejections in today's log at all.

**Soak check: 14 PASS / 1 WARN / 0 FAIL** (WARN = the known 67% reception baseline). Phantom-rainRate
prediction (DEC-0049): 0 qualifying rows in 1,214. No driver stalls in today's log — the S41
startup-race class is now clean across three consecutive restarts (S43, S47, S48).

---

## [S50] — 2026-07-26 — STATUS resume pointer fixed (micro-session)

One docs commit (PR #73): STATUS.md's `▶ Resume here` line still read "S48 → S49" after S49 had
shipped and closed. No other work.

---

## [S49] — 2026-07-26 — Issue #67 closed: mypy is now a real CI gate

Triaged and fixed the 19 pre-existing mypy errors S48 flagged (`--all-files` run while adding the
pytest hook) but didn't diagnose. Reproduced locally via `pre-commit run mypy --all-files`.

**Two genuine bugs, both in `ops/recover_sweep_results.py`:** the `results` list's `NO_DATA` row
appended an `int 0` for the pct column where every real-data row appends a `float`
(`round(mean_pct, 1)`) — now `0.0`. Separately, the summary loop reused the module-level names `ts`
(a `datetime` from the log-parsing loop) and `pct` (an `int` from the same) for unrelated `str`/
`float` values unpacked from `results` tuples — silent shadowing, not a crash, but genuinely
confusing and exactly the kind of thing mypy is right to flag. Renamed to `_ts` (unused) and
`row_pct`. `results` also gained an explicit type annotation
(`list[tuple[int, int, str, int, int, float, int | str]]`) documenting that its last column is
intentionally either a window count or the `"NO_DATA"` sentinel string — a deliberate design choice,
not something to unify.

**One missing stub, not a bug:** `pressure_service.py` needs `types-requests`. Added to
`.pre-commit-config.yaml`'s mypy hook `additional_dependencies` and to CI's `pip install` step.

**13 py2/py3-compat false positives (`influx.py` 9, `wcloud.py` 4), plus one real
shadowing bug in `influx.py` (3 cascading errors):** the `try: import X / except ImportError: import Y as X` compat shims
mypy statically flags on the branch that never executes under Python 3.14 — suppressed per-line with
`# type: ignore[no-redef]` / `[attr-defined]`, never a blanket per-file ignore, per the issue's own
suggested triage. Separately, `influx.py`'s manual test harness (`if __name__ == "__main__":`) had
`queue = queue.Queue()`, shadowing the `queue` module import with a same-named local — the two
`Module has no attribute "put"` errors were downstream of this one root cause, not independent bugs.
Renamed to `q: queue.Queue = queue.Queue()`.

Verified clean: `pre-commit run mypy --all-files` 19 → 0 errors, ruff clean, pytest 91/91. Removed
`.github/workflows/ci.yml:81`'s `|| true` — mypy failures now actually block CI, mirroring what
#55/DEC-0015 did for pytest via pre-commit at S48. No DEC entry — this closes an enforcement gap,
not a new design decision, same class as #55.

---

## [S48b] — 2026-07-25 — Provenance audit (DEC-0053): loop-JSON cache bounded; #48 and #45 closed

**Issue #48 — closed, DEC-0042 upheld.** A dashboard-side reconciliation found WeatherLink's
install-to-date total only balances if the console *excludes* the 2.56″ of phantom rain we corrected,
and asked whether that undercuts DEC-0042's ISS-side mechanism. It does not — the premise conflates
two classes this repo's data model already separates into independent flags: the 2.56″ is `rain_qc`
(3 points, the **counter**, owned by DEC-0021/0033/0035), while DEC-0042 governs `rainRate_qc`
(33 points, `rain = 0.0` in every one, contributing 0″ to any total). Both classes independently
*require* the console's absence — ERR-0001 was our own wraparound handler adding 128 to a logged
`rain_count=-64` and ERR-0002 a bit-7 flip passing CRC (both downstream of the shared broadcast), and
DEC-0042's mechanism predicts no tip at all. Per INTERFACES §4 the console is our ground truth for
"did the bucket actually tip," and it says no — confirmatory, not contradictory. The reconciliation is
real value as **independent validation that the correction was right** (residual 0.01″), now recorded
in `DATA_ERRATA.md`. DEC-0042 gained a "Challenged and upheld" note so it isn't re-derived.

**Issue #45 — closed as DEC-0053.** Audited every artifact a consumer reads for whether the
assumptions it was produced under travel with it. One real bug, two documented gaps:

- **Fixed:** `loop_json_writer.py`'s cache was **unbounded** — it updated only on non-None values,
  never expired them, and stamped every write with the *current* packet's `dateTime`. A dead or
  SensorQC-rejected sensor emitted its last value forever, indistinguishable from a live reading, on
  the surface the dashboard reads. Same failure `dewpoint_service.py` fixed for the archive path at
  S33/DEC-0022 — learned in one artifact, never propagated to its sibling. Now bounded per-field:
  300 s default (matching DewpointCacher), **2 × `[DavisPressure] fetch_interval`** for
  `barometer_inHg`, since a flat 300 s would have blanked the hourly-fetched barometer for 55 min of
  every hour and regressed Cold-load Fix B. Expired fields are omitted, not frozen, and logged at
  WARNING. 6 new tests + a mutation check confirming they go red against the old cache (91 total).
- **Documented, not fixed:** InfluxDB carries no station identity — and the "one-line" `tags =` fix is
  a trap, since it forks the series key (interface break, needs dashboard coordination). The SQLite
  archive carries no correction flag, so the system of record is less provenanced than the derived
  store. Both in BACKLOG with the reasoning.

`INTERFACES.md` §1 updated — the staleness bound is part of the contract, and a missing field now
explicitly means "no current value," never "value unchanged."

**Deployed and verified in prod** (PR #69 merged, then hot-swapped — `loop_json_writer.py` is MOUNTED
per DEC-0046, so the merge alone would have been inert). Pre-flight drift check confirmed the live
file was byte-identical to the repo's pre-change version; scp'd with md5 matched both ways, pyc
cleared, container restarted (`kill` → `start`, DEC-0008). Live log: `cache TTL 300 s,
barometer_inHg 7200 s` — the barometer TTL correctly derived from the live `fetch_interval = 3600`.
Watched 453 s, past the default TTL: zero expiry warnings, all fields still served, values updating.
Rollback is `loop_json_writer.py.bak-pre-ttl-S48` + restart. No image rebuild; `:v2.0.8` unaffected.

---

## [S48] — 2026-07-25 — pytest hard-gated at commit time; closes issue #55

Investigated [#55](https://github.com/WeatheredScientist/weewx-rtldavis/issues/55) ("closeout
doesn't hard-gate on a green test suite"), filed 2026-07-16 before this repo's closeout skeleton
existed. Found the practical exposure already narrow: `dev` is a protected branch requiring the
`tests`/`lint`/`secret-scan` CI checks before any merge (verified directly this session via PR #65),
so a broken-test commit has no path onto `dev` regardless of whether an agent remembers to run
pytest locally. The one real remaining gap: pytest wasn't part of `.pre-commit-config.yaml` — only
ruff/mypy/secret-scan ran at commit time, which is what DEC-0015 originally intended but never fully
wired up. Added a `local` pytest hook (isolated pre-commit env, `additional_dependencies: [pytest]`,
`always_run: true`) — the suite is all-stdlib so it needs nothing from this repo's `.venv`. Verified
it fires on every commit and passes in isolation. Commented on and closed #55, citing the branch-
protection/CI structure as the actual hard gate, with this as the immediate-local-signal bonus.

(Caught, not fixed, as out of scope: running `pre-commit run --all-files` surfaced 19 pre-existing
mypy errors and trailing-whitespace fixes across `influx.py`/`ogoxeUploader.py`/`weewx.conf.example`
that normal per-commit runs never touch, since pre-commit only checks each commit's own diff.
Reverted those incidental changes — not this session's task.)

---

## [S47] — 2026-07-25 — Backlog + branch cleanup: loopdata.py / reception_service.py removed, rw350/400-test images deleted, stale worktree removed

Cleared four long-parked, "not urgent" backlog items in one session.

**`loopdata.py` (DEC-0005, open since S16).** `user.loopdata.LoopData` was confirmed still absent
from every active `[Engine][Services]` list. Removed the `[LoopData]` config section from the live
`weewx.conf` (backed up first as `weewx.conf.bak-pre-loopdata-cleanup-S47`; a small Python script
found the section by its top-level header and asserted on expected content before writing, rather
than a line-count sed). Recreated `weewx-rtldavis-v2` (`kill` → `rm` → 3 s settle → `run`,
reconstructed from `docker inspect`) without the `loopdata.py` bind mount. Verified live: container
`running`, 6 mounts (down from 7), `weewx.log` publishing archive records and RESTful uploads within
seconds, no `CRITICAL`/stall. `loopdata.py` renamed aside on the NAS to `loopdata.py.removed-S47`
rather than deleted, for rollback.

**`ops/reception_service.py` (found S43).** Confirmed unimported anywhere in the test suite (one
stale comment reference in `tests/test_reception_layer_b.py`, fixed), never `COPY`'d into the
Dockerfile, and its `ReceptionMonitor` service never listed in `weewx.conf`. Deleted from the repo;
the NAS copy renamed aside to `reception_service.py.removed-S47`.

**`rw350-test` / `rw400-test` Docker images (DEC-0048's last piece).** `rw250-test` was retired at
DEC-0048 (S41); the other two ad-hoc `receiveWindow`-sweep tags were left. Confirmed neither backs
any running container (`docker ps -a` showed only `weewx-rtldavis-v2` on `:v2.0.8`) and deleted both
from the NAS. DEC-0048 is now fully closed.

**Stale worktree.** `.claude/worktrees/s46-closeout-amendment` (branch
`worktree-s46-closeout-amendment`, merged via PR #64) removed — same pattern as the 8 worktrees
cleaned up at S41.

No driver/source code changed, no image rebuild, `:v2.0.8` unchanged. Docs updated: BACKLOG.md,
ROADMAP.md, docs/ARCHITECTURE.md, docs/DECISIONS-FULL.md (DEC-0005), docs/STATUS.md.

## [S46] — 2026-07-24 — Humidity-spike watch checked directly (still unfired); OPS-DEC-0019 rollout closed cross-repo; dev housekeeping

Ran the DEC-0044 humidity-spike check directly against the live NAS logs rather than deferring it:
fetched every `log_humidity_raw` packet captured since the capture went live (2026-07-13 15:27, S41)
through the current log — 11 days, 8,852 raw packets, ~3x the largest prior sample (S43's 2,056).
Decoded per the driver's own formula (`rtldavis.py:1543-1550`) and searched for a single-step raw jump
of 16-37 %RH (the DEC-0044 signature). **Zero matches.** Largest swing: -9.86 %/min (2026-07-17
13:16→13:17, 60.5%→51.3%) — larger than S43/S44's reported 7.5 %/min purely from sample size, still
ordinary midday humidity movement, clustered in the predicted 11:00-16:00 window. Watch remains open,
unfired.

Closed [eaglehunt-ops#37](https://github.com/WeatheredScientist/eaglehunt-ops/issues/37) (OPS-DEC-0019
env-twin rollout): confirmed all three Eagle Hunt repos had merged their portion (weewx-rtldavis#59 in
S45, hyperlocal-forecast#135, eaglehunt-weather-dashboard#102+#112) — commented and closed.

Housekeeping: local `dev` was 2 commits behind `origin/dev` (PR #61, `ops-53-settings-consolidation`)
— pulled forward; removed the resulting stale merged worktree
(`.claude/worktrees/ops-53-settings-consolidation`) and its local branch. Checked eaglehunt-ops' open
issues and both sibling repos for anything owed here: nothing tagged `repo:weewx`, nothing outstanding.

Opening this closeout as PR #62 surfaced a real CI break: the lint job's unpinned `pip install ruff`
had drifted to 0.16.0, whose new default rules flagged 295 pre-existing hits (139 in `rtldavis.py`,
the driver protected from reformatting churn by DEC-0014/DEC-0027) — `lint` is a required check on
`dev`, so this was silently blocking every PR. Fixed via PR #63 (pinned `ruff==0.5.7`, matching the
`.pre-commit-config.yaml` pin DEC-0027 already settled on; no source files touched). Merge order:
#63 merged first, then #62's branch was updated onto it so its own lint check went green. Both
merged 2026-07-24. The CI workflow file changed; no source/driver code did.

---

## [S45] — 2026-07-20 — PR #59 merged: OPS-DEC-0019 env-twin permission rules (cross-repo)

`.claude/settings.json` gained two ask-rule entries: `Bash(env * git merge * main)` and
`Bash(env * git merge * dev)`. Env-wrapping (`env -u GH_TOKEN git merge …`) defeats ask-rule
pattern matching, since `env` isn't stripped before the match runs — the existing `git merge * main`/
`git merge * dev` rules never fired for an env-wrapped call, which fell through to the auto-mode
classifier instead of resolving by rule. `git push` already carried its env-wrapped twin; this fills
in the same gap for the two protected-branch merge rules. Mechanical, no code touched, part of the
cross-repo OPS-DEC-0019 rollout (`eaglehunt-ops#37`) landing the same fix in all three Eagle Hunt
repos. CI green (lint/secret-scan/tests). The branch and commit were already staged when this session
started; this session's contribution was flipping draft PR #59 to ready and merging it to `dev`.

Humidity-spike watch and the DEC-0049 rainRate prediction: unchanged, still unfired (see [S44]).

---

## [S44] — 2026-07-19 — Soak-check phantom-rain false positive fixed; shared closeout skeleton adopted (DEC-0052)

`ops/soak_check.sh` on the still-running v2.0.8 (up 98h) flagged 49 archive rows as a possible
DEC-0049-predicted phantom-rainRate event. Cross-checked against the full 2026-07-18 archive: it
wasn't one — 3 real bucket tips that day, a falling barometer (29.93→29.78 in) and rising gusts (to
8 mph) confirm a real storm, and every flagged row is the ISS's own rain-rate message decaying after
a real tip (one decay tail ran 38 minutes, past the light-rain formula's nominal ~1022s ceiling).
**Fixed:** the detector now excludes any row with a real tip in the preceding hour. Re-verified
live: 49 → 0 false positives, all other soak checks unchanged. The DEC-0049 prediction itself (a real
condensation event, tip counter not advancing) remains unfired.

**DEC-0052:** adopted eaglehunt-ops' locked closeout skeleton (OPS-DEC-0016), adapted. `CLAUDE.md`'s
closeout ritual — previously split across two paragraphs ("Session ritual — End" and a separate
"Docs-diet ritual at close") — is now one 6-step numbered list; the docs-diet ritual and this repo's
stricter local commit/push rule are kept as addenda, per the template's own pattern. The only
genuinely new content is step 5, a model-tier restore check — the third repo (after
hyperlocal-forecast, coffeeradar) to independently land on that same assessment. Closes
weewx-rtldavis#56; outcome reported to eaglehunt-ops#22.

Both changes landed via PR #57 (`s44-ops-closeout-and-rain-fix` → `dev`), checks green
(lint/secret-scan/tests).

Humidity-spike watch: still negative, 894 samples this container lifetime, largest jump ~7.5 %RH/min
— same magnitude as S43, no qualifying spike.

---

## [S43] — 2026-07-15 — v2.0.8 shipped, deployed and verified: Cold-load Fix B/DEC-0051, Reception Layer B/DEC-0024, duplicate-frame counter/DEC-0035

> **Soak check (v2.0.7, up 49h): green.** 11/15 pass, 4 expected startup-only warnings, 0 failures —
> archive current, stdout quiet, no tracebacks, no stalls, 100% reception, 45,190 records published, 0
> phantom-rain rows in 2,987 archive rows. **Humidity-spike check: no qualifying spike yet.** Decoded
> the full `humidity_raw=` series since the capture went live (2,056 samples, ~50h, including the
> rotated `weewx.log.2026-07-13`/`.2026-07-14` the live log had already rolled past) per the driver's
> real decode formula. Largest jump: 7.5 %RH/min, clustered in the predicted 11:00–16:00 window but
> well under the 16-37% DEC-0044 signature. Capture instrument confirmed working correctly.
>
> **Three backlog items shipped in code:**
>
> 1. **Cold-load Fix B + windchill (DEC-0051, closes issue #44).** `loop_json_writer.py` now writes an
>    identical snapshot to a second path (`current.json`, default `/opt/weewx-data/current.json`) on
>    every LOOP packet, atomic tmp+rename same as `loop-data.txt`; `windchill` added to `_FIELDS`
>    (`windchill_F`). `docs/INTERFACES.md` updated. **Deploy: mounted file — hot-swap (scp + clear-pyc
>    + restart), no image rebuild** (verified against `docs/ARCHITECTURE.md`'s mount table).
> 2. **Reception Layer B (DEC-0024 — now fully resolved).** The driver published channel-hop
>    (`freqError{n}`) packets as their own dataless loop packets, which every uploader (WU RapidFire
>    etc.) then published as if they were full weather updates — the ~1.6x overcount measured at S21.
>    Considered and rejected: dropping the packet outright (freqError is repurposed onto real archive
>    schema columns — `consBatteryVoltage`/`hail`/`hailRate`/`heatingTemp`/`heatingVoltage` — and
>    `ops/reception_service.py` logs non-zero freqErrors, so silently breaks both); tagging it dataless
>    and filtering in every consumer (broader blast radius for no benefit). **Chosen:** cache the
>    channel-hop packet's freqError fields and merge them onto the *next* real DATA packet instead of
>    ever yielding a standalone one (`_cache_pending_freq_fields` / `_merge_pending_freq_fields`, each
>    cached value rides exactly once). Side effect: also fixes `weewx_monitor.py`'s live `WINDOW:`
>    reception metric, which counted channel-hop packets as real readings via its epoch-dedup (S22)
>    never fully catching them (S31 confirmed it still pinned near 100%) — verified live post-deploy,
>    see below.
> 3. **Duplicate-frame counter (DEC-0035's own proposed instrument).** `genLoopPackets`'s stderr scan
>    now counts Go's `"duplicate packet:"` dedup line unconditionally (no `debug_rtld` gate) into
>    `self.stats['dup_count']`; `_update_summaries()` logs one INFO line per archive period (including
>    `N=0`, so a quiet period is distinguishable from the instrument not running); `_reset_stats()`
>    zeroes it for the next period — the same pattern already used for `pct_good_all`.
>
> Items 2+3 both touch the baked driver (`rtldavis.py`) — bundled for **one** image rebuild rather than
> two. +13 offline tests (`test_loop_json_writer.py`, `test_reception_layer_b.py`,
> `test_duplicate_frame_counter.py`); suite 72 → 85. **DEC-0051 added; DEC-0024 and DEC-0035 updated**
> with S43 sub-sections in `DECISIONS-FULL.md`.
>
> **Caught mid-commit: local pre-commit's `ruff-format` hook had silently contradicted DEC-0027 since
> S31.** CI dropped `ruff format` deliberately (it flattens `rtldavis.py`'s column alignment and
> reformats the baked driver — No-Rewrite); local `.pre-commit-config.yaml` still carried it. Never
> fired because pre-commit itself was never installed until S42 (DEC-0050) — its first real run
> attempted to mass-reformat `rtldavis.py` (3,213-line diff) on this session's commit. Caught (a second
> hook also blocked the same commit), reverted, `ruff-format` removed from the config. Checked both
> siblings for the same pattern: the dashboard already avoids it deliberately; `hyperlocal-forecast`
> carries it too but with no equivalent DEC and no known baked file, so no finding filed there.
>
> **Deployed and verified, same session.** PR #49 (the three items) and PR #50 (the `v2.0.8` version
> bump — Dockerfile header + README) merged to `dev`. Image built on the NAS in a fresh `build-v2.0.8/`
> checkout (`docker build`, zero errors in the build log), pushed to Docker Hub as `:v2.0.8` + `:latest`
> (digest `sha256:2c05493a...`). `loop_json_writer.py` hot-swapped into place (old copy preserved as
> `.bak-pre-v2.0.8`); production container recreated (`docker kill` → `rm` → `run`, DEC-0008 — replicated
> the *actual running container's* `docker inspect` config, not the NAS's own stale `docker-compose.yml`,
> which still said `:v2.0.4`). **Live-verified, not image-checked (DEC-0046 discipline):** driver banner
> `0.20+ws.1`; `current.json` writing real data including `windchill_F`; `duplicate frames this period: N`
> logging every archive period; **Wunderground-RF published-record count now matches unique record
> epochs exactly (53/53 over a 3-min window)** — the ~1.6x overcount DEC-0024 documented is gone;
> `soak_check.sh` 14/15 pass, 0 failures (1 warning: 71% reception, ordinary RF variance, not a
> regression). **`weewx_monitor.py`'s live `WINDOW:` metric confirmed fixed too:** post-deploy it reads
> `WINDOW: 14-17/21 (67-81%)`, `RECEPTION: 73-77% avg` — matching the driver's own trusted
> `rxCheckPercent` range (59-95%, median 75%, S31) for the first time, instead of the pre-fix pinned-
> near-100% pattern S31 documented. (Correction: `ops/reception_service.py` — a *different*,
> WeeWX-internal `ReceptionMonitor` service — turned out not to be wired into this station's
> `weewx.conf` at all, and per `git log` has sat untouched since S16; likely vestigial, like
> `loopdata.py`. It is not what generates the reception emails; `weewx_monitor.py` is.)
>
> **PR #51 promoted `dev` → `main`** (CI green on both source commits); tagged `prod-baseline-20260715`
> + `v2.0.8`; GitHub Release published. `docs/CONVENTIONS.md` and `CLAUDE.md` had stale `:v2.0.4`/`:v2.0.5`
> drift notes left over from S38 that were never corrected when S41 actually caught prod up — fixed now
> alongside this release. `ops/soak_check.sh`'s own `EXPECT_IMAGE` default bumped to `:v2.0.8`.

---

## [S42] — 2026-07-14 — the cross-repo round: DEC-0040's triggers fired, the identifiers were live on public dev, and pre-commit had never run (DEC-0050)

> **This was the scheduled `[Fable]` cross-repo coordination round** (dash S74 = this repo's S42),
> and this repo's share of it landed in one PR.
>
> **The identifier scrub was not hypothetical.** `ops/soak_check.sh` carried the real NAS
> user/IP/port as tracked shell defaults — **on `dev`, on a PUBLIC repo**, since S41. Our own
> `test_check_secrets.sh` tree check flags it (40/41 → the "1 FAILED" was this), but that check
> runs only where the gitignored `.identifiers` file exists — **CI is structurally identifier-blind
> by design**, so the only enforcement point was local pre-commit. And the hole under the hole:
> **pre-commit was configured but never installed** — `.git/hooks/pre-commit` did not exist, here
> or in either sibling repo. The load-bearing local gate for a public repo had never once executed.
> A configured control that nothing runs is prose (DEC-0040, one level down). Fixed: defaults are
> now placeholders that fail fast; real facts live in `~/.claude/nas.env` (also honored by the new
> eaglehunt-ops checks) / gitignored `docs/LOCAL_INFRA.md`; suite 41/41 with a clean tree; soak
> re-proven green end-to-end via `nas.env` and red on the placeholder path; pre-commit actually
> installed (owner-run). Per DEC-0028's precedent (identifiers, not credentials; LAN IP): fix
> forward, **no history rewrite**.
>
> **DEC-0050 — the station gets a master for its IDENTITY (and only that).** DEC-0040's own revisit
> triggers fired (five shared `~/.claude/` executables versioned nowhere; the same gate fix
> re-derived four times; the dashboard's DEC-0106 as the predicted casualty — 6.7 km of coordinate
> drift, a week of forecasts for the wrong town). The private **`eaglehunt-ops`** repo now holds:
> canonical `station-identity.env`, the drift check (**first run: 8/9 representations within 19 m —
> and the 9th finding was real**, see below), the NAS runtime contract, and the `~/.claude/` guards
> under version control with their tests (live copies = deployments via owner-run `install.sh`).
> Scope fenced by the S38 §Etiquette litmus test; deletion clause attached.
>
> **The identity check's first run caught a live outage in a sibling:** HLF's
> `/api/v1/forecast` hangs indefinitely for **every** coordinate pair (health/current fine,
> container "Up 8 hours" — *"Up" is not health*, our own DEC-0036 lesson, now on an API surface).
> Per §Etiquette: **filed in HLF's tracker with the evidence, not fixed from here.**
>
> **Also filed here (cross-repo asks from the dashboard's S73):** the loop writer emitting
> `cloudbase` (+`windchill`) — folds into the existing Cold-load Fix B thread; and a provenance
> audit (does the artifact a consumer READS carry the assumptions it was captured under — their
> DEC-0104/0106 twins of our DEC-0040/0045/0047 family). The dashboard's stale claim that our
> secret gate was "neutered" was **re-measured and retired** — 40/41 planted payloads pass; the
> one failure was the tree check doing its job on the identifiers above.
>
> **Read-guard field data (their `~/.claude/` DEC-0047 guard, now versioned in eaglehunt-ops):**
> S73/S74 logged five false positives — all token×verb string matches with no data flow (a commit
> MESSAGE containing "proxy.env" + the word "more"; the sanctioned `readconf` invoked by full path;
> a `.env` name inside an `echo` literal). Two mechanical fixes ride the eaglehunt-ops migration
> (readconf at a path boundary; a lone `git commit` exempted after heredoc-body stripping — chains
> and substitutions still block), proven 46/46 both directions. The wider class is documented as
> accepted: a false block costs a retype; a false allow costs a rotation.

---

## [S41] — 2026-07-13 — v2.0.7 shipped, and the config fix that would have missed prod entirely

> **v2.0.7 is on Docker Hub, prod runs it, and the raw-humidity capture is finally live.**
>
> The headline was meant to be routine: take S39's `[[root]]` logger fix (DEC-0043), which had been
> sitting merged-but-unreleased on `dev`, and ship it. That happened — `:v2.0.7` + `:latest`
> (digest `sha256:31cad4d2`), GitHub release, `main` == prod, `prod-baseline-20260713b` tagged.
>
> **The finding is what the deploy nearly missed.** The `[[root]]` fix lives in the image's *baked*
> config, protected by a Dockerfile build-time assertion so an image cannot be built without it. But prod
> bind-mounts `weewx-data/` over `/opt/weewx-data` — the mount covers the whole directory, so the live
> `weewx.conf` **shadows the baked config completely**. Deploying `:v2.0.7` and stopping there would have
> been, in prod, **a no-op with a green checkmark**: correct image, passing assertion, accurate release
> notes, and a station still emitting syslog tracebacks and still silently dropping every startup
> diagnostic. **DEC-0046.**

### Shipped — v2.0.7

- **Docker Hub:** `:v2.0.7` and `:latest`, both at digest `sha256:31cad4d2826b…`. Built on the NAS from
  `git archive v2.0.7` — the image is built from *exactly* the tagged tree (DEC-0038).
- **GitHub release** [v2.0.7](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.7);
  `dev` → `main` (PR #38, after PR #37's version bump); `main` and `dev` are identical trees.
- **Prod recreated on `:v2.0.7`** at 15:27 EDT. `docker kill`, never `stop` (DEC-0008); no `rtldavis.py`
  mount (DEC-0031). Rollback available: `:v2.0.6` (`e23cabd53591`) is still on the NAS.
- **`prod-baseline-20260713b`** tagged — the second baseline of the day (the first, `-20260713`, was
  v2.0.6). Not force-moved; the old tag still means what it meant. DEC-0011's *`main` = production truth*
  invariant holds.

### Found — DEC-0046: the baked config never reaches prod

- Caught by a **pre-flight `grep` of the live config**, which found **zero** `[[root]]` blocks while the
  image's baked config carried it and asserted it.
- **The exact mirror of DEC-0031.** There, the *driver* is baked and the bind-mount is the no-op, so an
  `scp` is silently ignored. Here, the *config* is mounted and the image is the no-op, so a rebuild is
  silently ignored. Inverses — which is precisely what makes the pair easy to get backwards. **Neither
  errors. Both accept the instruction and discard it.**
- Fixed in the same window: the live `weewx.conf` gained the `[[root]]` block (backed up first to
  `weewx.conf.bak-pre-v2.0.7`). Prod's version routes to `handlers = rotate,` — **file only, no console**,
  deliberately differing from the baked config, because prod declares no console handler and adding one
  would re-arm the DEC-0036 freeze hazard that DEC-0041 disarmed. **The fix must match; the text need not.**
- **The fifth member of the family**: an interface that accepts an instruction and silently discards it
  (DEC-0031's bind-mount, DEC-0036's `max-size`, DEC-0040's prose, DEC-0045's test that certified the
  hole). The build assertion was not wrong — **it was answering a question nobody was asking in prod.**

### Verified in prod — behaviorally, not by inspecting the artifact

- **`weewx.log` now contains `weewxd INFO Initializing weewxd version 5.4.0`**, plus the command line, the
  Python version, the platform and `WEEWX_ROOT` — **lines that had never once appeared in that file.** This
  is the S39 acceptance criterion, and it reads the running system. An image check would have said PASS.
- **Zero `--- Logging error ---` blocks** on stdout (was ~15 tracebacks / ~515 lines per start).
- `driver version is 0.20+ws.1 (patched by WeatheredScientist -- not stock upstream)`, `sensor_qc True`,
  **`log_humidity_raw True`**, 0 tracebacks, `RestartCount: 0`, and Wunderground (rapidfire + PWS), Influx
  and Windy all publishing.

### Armed — the raw-humidity capture is now live (DEC-0044)

`log_humidity_raw` had been sitting in the live config since S39 but weewx reads its config **only at
startup**, so it took this restart to activate. It is now running. **The next midday humidity spike logs
its raw `pkt[3]`/`pkt[4]`** and settles the nibble question deterministically — no averaging, no free
parameter. Spikes run ~2–3/week, clustered 11:00–16:00. The inversion method is in DEC-0044; do not
re-derive it.

### Security — DEC-0047: the secret gate guards commits, not reads

> **The transcript is an egress path, and nobody had modeled it as one.**

- **The gap.** Every secret control in this repo is a **commit-time** control — DEC-0012,
  `check_secrets.sh`, the CI secret-scan, the 41-payload proof suite. Four hardenings across S26 → S40, all
  of them guarding the **write** path to GitHub. **None says anything about reading.** Whatever a tool
  prints lands in `~/.claude/projects/*.jsonl` in plaintext and is transmitted to the model provider. The
  `.gitignore` entry feeds the blind spot: the live config is *deliberately* excluded from the repo, which
  makes it feel handled. **"Not in the repo" is not "not in the transcript."** DEC-0040 said *prose does not
  execute*; this is worse — **there was no prose.** No rule was broken because no rule existed.
- **What surfaced it:** a `sed -n "/^[Logging]/,+44p"` on the live config during this deploy. A fixed
  **line-count** window on a sectioned file: `[Logging]` is ~22 lines, so it ran off the end and printed the
  following sections into the transcript. **A line-count window on a sectioned config is a loaded gun —
  sections move, the window does not.**
- **Three mechanical controls, in `~/.claude/`** (global — DEC-0040's "no master repo"):
  `hooks/secret-read-guard.sh` (PreToolUse on Bash/Read/Grep; blocks *secret path* × *emitting verb*, sees
  through `ssh "…"`, **leaves editing alone** so the DEC-0046 release workflow still works — a guard that
  blocks the work gets switched off; matches **per-token**, so `cat weewx.conf.example && cat weewx.conf`
  cannot launder the live config through the `.example` carve-out);
  `bin/readconf` (**section-scoped — it structurally cannot take a line window**; values become stable
  `sha256` fingerprints while `handlers = rotate,` and `level = INFO` stay readable, because a DEC-0046
  deploy has to verify exactly those); and `bin/scan-transcripts` (the detection half).
- **Proven, not merely green.** The guard's suite asserts **both directions** (38/38 — the leaking command
  blocks; `cat weewx.conf.example`, `sed -i`, `cp`, `readconf` all still pass), and a **mutation test**
  turns it **red — 18 failures.** The scanner **self-tests before every run** and refuses to report "0" if
  the harvest returned nothing. **Verified live:** re-running the original command is now blocked by the
  hook.
- **A scanner that cries wolf is its own failure mode.** The first pass reported a real password sitting in
  `weewx.conf.example` on public `main` since S16 — which would have been a live exposure and a fifth gate
  hole. It was the example's own placeholder string. The evidence looked internally weird (the same
  "password" appeared as three different keys), and re-checking it is the only reason a five-alarm claim was
  not filed. DEC-0039: *a green exit code is not evidence.* DEC-0045: *a passing test is not evidence
  either.* **S41: a scan that finds nothing is not evidence unless you have proved the scanner can see.**
- **A full scan of all refs confirms no real credential has ever been committed to any of the three repos.**

### Housekeeping — the cleanup that found its own backlog item was stale

- **DEC-0049 — the ISS hardware is new and inspected, so the phantom rainRate is not a broken part.**
  DEC-0042 closed with *"next step is physical: inspect the bucket, the reed switch and its wiring."*
  **That action is now closed and it came back clean.** The owner reports the ISS hardware is **new**, was
  **recently inspected**, and has **no faults** — the one component that did fail, the **anemometer**, was
  **replaced ~16–17 June 2026**. A clean inspection does not falsify DEC-0042, it **sharpens** it: the two
  readings were always *defective part* or *working part reacting to the environment*, and **the first is
  now excluded.** Condensation bridging a **healthy** reed switch produces exactly the measured signature
  (94 % RH, 1.7 °F dewpoint spread, 0 mph wind, tip counter never advancing). **There is nothing to swap and
  no part to order** — anyone reading DEC-0042's "next step is physical" without DEC-0049 would order one
  for no reason. The anemometer date is also a **dating anchor**: wind data either side of mid-June comes
  from different physical hardware.

- **DEC-0048 — reception testing is a designed experiment, not a pile of image tags.** `rw250-test` is
  retired. It was a **misnomer within a day of being built** (`receiveWindow` ships at the upstream
  default), and it was **never published to Docker Hub** — verified against the live tag list, so the
  confusion was only ever ours. The deeper point: that sweep was never a controlled experiment, which is
  also **why DEC-0017 has sat open since S16** — gain is held at 372 pending an "averaged re-test" that
  never happened because no method was ever agreed. A proper RX test is **deferred, not abandoned**: when it
  runs it gets a hypothesis, a control arm, an averaged window, and a pre-registered metric — and it settles
  **gain 372-vs-207 and `receiveWindow` in the same run**, since they share the same apparatus and the same
  confound. Until then **neither parameter gets tuned by feel.**

- **Branch cleanup — and the backlog item was stale.** STATUS had been asking us to delete
  `feature/rain-spike-filter` and `s32-reconcile-main`; **neither still existed.** What *did* exist was **8
  merged `worktree-*` branches**, each verified at **0 unmerged commits** before deletion. The remote is now
  exactly **`dev` and `main`**. All three Eagle Hunt repos have **zero** open PRs, and the dashboard's
  long-flagged stranded draft PR is gone too.

## [S40] — 2026-07-13 — a comment is not an exemption: the gate's proof had certified the hole

> **The secret gate let commented-out credentials into a PUBLIC repo — and its own test said that was
> correct.**
>
> Carried over from the close of S39, where it was spotted and deliberately left as the owner's call.
> `scripts/check_secrets.sh` had an `ALLOW (1)`: *if the whole line is a comment, allow it.* So
> `# api_key = <a real credential>` shipped clean. `git push` does not strip comments, and neither does
> anyone reading the file on GitHub.
>
> **The part that made this a DEC and not a bug fix:** the rule was not a blind spot the test missed —
> **the test asserted it.** Two commented credentials sat in `test_check_secrets.sh` under *"must PASS"*,
> and they were part of DEC-0039's celebrated *"28/28 planted payloads, proven"*. DEC-0039's thesis is
> *"a green exit code is not evidence."* S40's correction: **a passing test is not evidence either, if
> the assertion is wrong.** The proof had certified the hole.

### Fixed — DEC-0045: comments are scanned exactly like code

- **`ALLOW (1)` deleted.** No comment rule at all. A comment earns no exemption; only its **value** can.
  `# api_key = YOUR_API_KEY_HERE`, `# token = "${INFLUX_TOKEN}"` and the `influx.py` docstring style still
  pass — via the placeholder / interpolation / prose rules, which test the value. Commenting a line out no
  longer changes the verdict **in either direction**.
- **No new exemptions.** The gate's own header had illustrated three past bugs with six real-looking
  credential literals, which the fix now flags. The tempting move — exempt `check_secrets.sh` by path, as
  the test file already is — was **rejected**: that is a 130-line blind spot in the one file that most
  needs scanning. The literals **moved into `test_check_secrets.sh`, where they execute as payloads**, and
  the header now points at them. DEC-0040 applied to the gate itself: *prose does not execute.* The gate
  scans 100 % of tracked files, including its own source.

### Evidence — because a green run proves nothing on its own (DEC-0039)

- **Blast radius measured before deciding:** deleting `ALLOW (1)` produced **6 hits across the entire
  tracked tree, all of them inside the gate's own header comments.** Every legitimate comment elsewhere
  (README's `YOUR_*` blocks, `influx.py`'s docstring, the handoff docs) already passed on its *value*. The
  exemption was doing **no legitimate work in this repo** — it was close to pure hole.
- **Planted-payload suite: 41 passed, 0 failed** (was 28). Seven new BAD payloads cover every comment
  marker form (`#`, `//`, `/* */`, ` *`, indented, no-spaces) plus a commented constructor line; six new
  GOOD payloads are the same placeholder/prose/empty values wearing a comment marker.
- **Mutation test:** re-adding `ALLOW (1)` turns the suite **red — 7 LEAKED**. The fix is load-bearing and
  the test can actually fail.
- **Full-history scan: 0.** Every blob that ever existed in this repo (**333 unique, all refs**) was
  scanned for a commented credential. None. **The hole was never exploited** — nothing needs revoking, and
  no history rewrite is warranted. Positive-controlled: the same scan with the gate's own files re-included
  finds the 11 known header examples, so the scanner demonstrably sees things. (The first version of that
  scan reported a false "0" because `git` was silently not running inside the loop and `2>/dev/null` ate
  the error — caught only *because* the positive control was run. Same lesson, third time in one session.)
- **The gate blocked this session's own ADR** on first draft (4 hits — it quoted the payloads verbatim).
  The literals were removed rather than exempted.

### Also

- **PR #34 merged** — S39's work (DEC-0043 root logger, DEC-0044 nibble theory) landed on `dev`. It had
  been sitting open and green since S39; the session-start hook flagged it.
- 72 pytest tests still green. **Prod untouched** — still `:v2.0.6`, `RestartCount: 0`. This session
  changed no runtime code, only the commit-time gate and its docs.

---

## [S39] — 2026-07-13 — the root logger nobody overrode, and a theory that did not survive its own test

> **Two findings, one shipped fix, and one filter deliberately NOT built.**
>
> A routine post-deploy health check on `:v2.0.6` found prod emitting **15 logging-error tracebacks
> (~515 lines) to stderr on every container start**. Root cause: weewx's own defaults point the **ROOT
> logger** at a syslog handler on `/dev/log` — a socket that does not exist in a container. Our
> `logging.additions` had always overridden the `weewx` and `user` loggers, but `weewxd` and
> `weeutil.*` are in **neither** namespace, so they fall through to root and blow up there.
>
> The louder half is cosmetic (bounded burst; steady state is still 0 lines/90 s, so DEC-0041 holds).
> **The quieter half is not:** `weewx.log` has *never* contained a single `weewxd` or `weeutil` line —
> no version banner, no config path, no group list. Those records were not noisy, they were **lost**,
> and the failure announced itself only on a stream nobody reads. Fixed with a `[[root]]` override plus
> a build-time assertion, and verified A/B inside the real container: with the fix, `weewxd INFO
> Starting up weewx version 5.4.0` lands in the file for the first time. **DEC-0043.** Ships in v2.0.7.

**The coupling filter was on the S39 plan. It is not being built, and that is the bigger result.**

The inherited task was a "cross-sensor consistency filter" from dashboard S69: *a humidity move
>6 %/min with temperature essentially flat is physically impossible*, reported 3-for-3 with 0 false
positives. Underneath it sat an unproven mechanism — the **nibble theory**: the ISS message-type nibble
(`pkt[0] >> 4`) takes a bit flip, so **another sensor's payload is decoded as humidity**. S69 proposed a
falsifiable arithmetic test and never finished it. S39 finished it. **DEC-0044.**

- **The theory's arithmetic contradicts its own story.** Humidity is `0xA` = `1010`. Its single-bit
  neighbours are `0x2` (supercap), `0x8` (temp), `0xB` (undefined), `0xE` (rain). **Solar is 2 bits
  away; UV is 3.** So "a misdecoded solar/UV payload — that's why it's always midday" is not reachable
  by a single bit flip, and midday was the theory's headline evidence.
- **Every testable variant fails.** UV: implied ≈ 2× actual on *every* spike. Temperature: implied
  200–400 °F. Supercap: fails where testable.
- **The solar "match" was fitted noise.** Recovering a raw reading from a 1-minute average needs
  `raw = n·spike − (n−1)·baseline` with `n` unknown; letting `n` float over {1,2,3} scored 12/28, but
  the winning `n` came out uniformly **{1:4, 2:4, 3:4}** — a meaningless parameter. Against **2000
  shuffled pairings**: true 43 % vs chance 35 %, **p = 0.248**.
- **This is structural.** The free parameter exists *because* the archive averages, and it is precisely
  what manufactures false matches. **No analysis of 1-minute data can settle this** — and InfluxDB
  stores the same 1-minute records (checked: bucket `weewx`, retention infinite).
- **The filter's own premise is weak too.** "Temperature essentially flat" describes **90 % of all
  minutes** (66,743 of 74,538 at |ΔT| ≤ 0.1 °F), so the flatness test discriminates almost nothing. And
  every spike visible in the archive implies a *raw* glitch of 16–37 %RH — **already rejected by
  DEC-0029's existing 10 %RH-per-reading cap**. The filter would have targeted a residual we never
  showed exists.
- **The cited false-positive test was not evidence.** The 2026-05-23 "gust front" shows a maximum
  humidity move of **1.0 %/min** in our archive (90 %RH, 50 °F, wind ≤ 2.5 mph — a calm, saturated
  day). Any threshold spares it.

**So: instrument, don't filter.** The decisive instrument was already in the code — **`log_humidity_raw`**,
an upstream option (Luc Heijst's) nobody had switched on. It logs `(pkt[4] << 8) + pkt[3]`: **both raw
payload bytes**. With a real `pkt[4]` there is no averaging and no free parameter, and the inversion
becomes deterministic. Armed in the live `weewx.conf` (INFO → file handler only; prod declares no
console handler, so it adds nothing to stdout and carries no DEC-0036 risk). It activates on the next
restart, and the next midday spike settles the question.

**Also:** `iss_channel = 5` with every other channel `0` — there is exactly **one** transmitter, so
"bleed from another *transmitter*" was never possible. A type-level misroute inside the ISS's own
packets is the only mechanism the hardware permits.

**Tests:** 67 → **72**. The five new ones assert the `[[root]]` override in both shipped configs and the
Dockerfile's build-time assertion; deleting the `[[root]]` block fails three of them (planted-payload
check, per DEC-0039).

---

## [S38] — 2026-07-13 — v2.0.5 → **v2.0.6** SHIPPED; the gates now execute instead of asking nicely

> **v2.0.5 was an incomplete fix, and v2.0.6 finishes it (DEC-0041).** v2.0.5 moved the console log
> handler to `WARNING` and I claimed that made weewx's stdout nearly silent. **It did not.**
> `report_services = weewx.engine.StdPrint` `print()`s **every LOOP packet straight to stdout**,
> bypassing the logging module entirely — no log level touches it. It was writing **~25 MB/day** into
> the very pipe that froze prod for 7h18m, and because it is a **weewx stock default** it was in the
> baked image *and* our `weewx.conf.example`, so **every downstream user had it too**.
>
> Found by finally checking the thing nobody had checked — the actual `log.db` sizes (needs root):
> `weewx-rtldavis-v2` had accrued **15 MB in 14 hours**. The mitigation had been *reasoned about from
> the architecture* instead of *measured at the source*. One `sudo du` would have caught it.
>
> **Fixed everywhere:** prod (`report_services =`, restarted — stdout growth now **0 lines/60 s**,
> was ~36); the baked image config, **with a build-time assertion that fails the build if the edit
> no-ops**; and `weewx.conf.example`. Shipped as **v2.0.6**. Also removed `/weewx`, a container **dead
> since 2026-05-04** still holding the **largest `log.db` on the box (47 MB)** — dead containers keep
> their log store forever.

**The headline: `v2.0.5` and `latest` are on Docker Hub.** Downstream users had been getting the
**stock driver** (DEC-0031) *and* the **console-handler freeze hazard** (DEC-0036) on every `docker
pull` since 2026-07-08. That stopped at 12:55 today. It is the only item in this session that had an
ongoing external cost, and it is closed.

**Why v2.0.5 and not v2.0.4 (DEC-0038).** The `v2.0.4` image on the NAS was built at **15:44 on
07-12 — eight hours before the freeze that produced DEC-0036**, so it never contained the fix the
release was being cut for. A rebuild was mandatory either way. Republishing different content under
`v2.0.4` would have made one tag name two different images, which is the *same* lie as DEC-0031 and
DEC-0034 — the artifact asserting one thing and being another. `v2.0.4` was never on Hub, so nothing
public breaks. Prod deliberately stayed on `:v2.0.4` **at that point in the session** — the delta was
behaviorally nil here (prod's `weewx.conf` has no console handler at all — the config drift that spared
us), and redeploying prod unattended, hours after a seven-hour outage, to fix something that did not
affect prod, was the wrong trade. *(Resolved later the same day: once v2.0.6 existed and the owner was
present, prod was deployed to `:v2.0.6` in an attended window and `prod-baseline-20260713` was tagged —
see below.)*

**S37 never landed, and that is its own lesson.** All of S37 — three ADRs, the fork-identity audit, the
duplicate-frame confirmation — was sitting in **draft PR #23** and had never merged to `dev`. CI green,
branch pushed, nothing shipped. Found and merged at the top of this session. It is the direct
motivation for the session-start hook below.

**The secret gate, hardened and PROVEN (DEC-0039).** The bug class, stated once: *an allow term that
can match anywhere on the line is not an allow-list, it is an escape hatch — the secret sits on the
left and the excuse on the right.* `token = REAL  # falls back to os.environ` passed the old gate
clean. Every allow term is now **anchored** or **positioned against the key the detector matched**, and
the `grep -n` prefix bug is fixed at the root (bash parameter expansion; the allow-list runs on raw
lines) rather than compensated for with `^[0-9]+:` anchors. Ships with
`scripts/test_check_secrets.sh`: **13 planted payloads that must be caught, 14 good lines that must
pass, plus a clean-tree check — 28/28.** It runs in CI *before* the scan. It earned its keep
immediately by catching a hole in **the fix being written to close the previous hole**, and then by
catching the ADR that described it. CI also now runs the **67 unit tests**, which it never did.

**The cross-repo question, answered (DEC-0040): the gap is an ENFORCEMENT gap, not a documentation
gap.** All three options on the table (shared ops repo / vendored fragment / status quo) distribute
*documentation* — and in the worst incident **the rule was already written down**. "`docker logs`
always with `--tail N`" was in `CLAUDE.md` *and* `CONVENTIONS.md` before the freeze; it was followed
for thirty-odd sessions and broken once, and once cost seven hours. **Prose does not execute.**
Decision: **no master repo.** Build a shared enforcement layer instead —
- `~/.claude/hooks/docker-guard.sh` (`PreToolUse`): blocks bare `docker logs` and `docker stop`.
  **19/19 tests**, including a `docker logs` hidden inside `ssh nas "..."` that beat the first draft.
  Verified live.
- `~/.claude/hooks/eaglehunt-status.sh` (`SessionStart`): reports draft PRs, stranded branches and
  uncommitted work **across all three repos**. **On its first run it found a live stranded draft PR in
  the dashboard (#22)** that nobody knew about.
- Branch protection: **`enforce_admins: true`** on `main` and `dev` (checks: `secret-scan`, `lint`,
  `tests`). The S36 bypass is now mechanically impossible, for everyone.

**The Synology `db` log driver cannot be capped — proven, not assumed.** A container run with
`--log-opt max-size=1m` emitted 200,000 lines and **kept all 200,000**. `db` is a proprietary Synology
driver with no published options; the cap is *unsupported*, not undocumented. The daemon accepts the
option and discards it — **the third time in one session** that "the configuration was accepted" did
not mean "the configuration does anything" (cf. the green secret gate, the silent compose clobber).
Also demonstrated, rather than inferred, the DEC-0036 mechanism: retrieving that log **hung for over
three minutes**, and that was a `--tail`-bounded read. Prod was never at risk.

**Provenance, outward half — SENT.** After three sessions of "the fork hasn't given anything back," it
has. Both upstreams forked separately (our distribution repo correctly stays a normal repo, not a GitHub
fork), both PRs **open**:
- **[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22)** — the rain-counter
  wraparound. Proven against LloydR's own numbers from issue #15: `115 → 49 → 115` now yields
  missing/missing instead of a phantom 1.28″, while genuine wraparounds still work (`127 → 0` = 1 tip).
- **[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1)** — five fixes, led
  by a **silent TLS-verification bypass** (`ssl._create_unverified_context()` applied unconditionally to
  every https endpoint, so every user posting to InfluxDB Cloud has certificate verification off and
  their token on an unauthenticated connection). That repo's first-ever PR.
- **[The issue-#15 comment is POSTED](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128)**
  (owner-approved, 2026-07-13) — **the first comment on that thread since 2022-11-14.** It explains the
  duplicate-frame mechanism, the wraparound bug, and that the phantom **rainRate is ISS-side, not a driver
  bug** (DEC-0042) — which the three people there had been hunting in software for four years.

**DEC-0042 — the phantom rainRate is ISS-side, and the rainRate thread is CLOSED.** Reconstructed from a
2026-05-29 DB backup that happened to predate our own S36 correction: no real rain that day at all; the
rate held **03:22–03:37 UTC, sharp on and sharp off** — exactly the ISS's ~15-min timeout; the implied tip
interval stayed in a tight **8.5–10.0 s** band; and **the tip counter never advanced** (`rain = 0.0000` in
all sixteen records). Decisive: reaching those raw values from the `0x3FF` "no rain" sentinel needs **~6
bit-flips in every packet for sixteen consecutive minutes** — RF corruption gives *one* bad packet, not a
coherent stream. **The ISS sent them.** Conditions both events: overnight, 94 % RH, 1.7 °F dewpoint
spread, 0 mph wind. **Condensation trips the reed switch enough to start the rate timer, never enough
water to tip the bucket.** So DEC-0033/0035 are now explicitly *bounded* — they explain the rain
**counter**, and no decode-layer filter will ever touch the rate. **The next step is physical, not
software.** Method lesson kept in the ADR: this was only answerable because a backup predated our own
correction — **snapshot the affected rows BEFORE a retrospective correction, not after.**

**Prod finished the session on `:v2.0.6`, and `main` == prod again.** Recreated 11:09 EDT; verified
`driver version is 0.20+ws.1 (fork of lheijst 0.20)`, `sensor_qc True`, `influx service version 0.20+ws.1`,
stdout **silent**, every uploader publishing, `RestartCount: 0`. `prod-baseline-20260713` tagged, which
restores DEC-0011's *`main` = production truth* invariant that S38 deliberately broke for a few hours.
Prod's bind-mounted `influx.py` also caught up with the repo (it had drifted — DEC-0031's class again:
the running copy still had `VERSION = "0.20"`, the unconditional `_create_unverified_context()`, and
per-record `loginf` spam; not a live exposure, since the endpoint is plain http).

---

## [S37] — 2026-07-12→13 — A 7-hour prod freeze, the CRC question answered, and the fork finally admits it is one

Three unrelated things collided. In order of how much they matter.

### The outage: weewx froze for 7h18m (DEC-0036, ERR-0003)

At 23:53:45 weewx stopped doing anything and stayed that way until 07:12. **It did not crash** — both
processes alive, container reporting `Up`, and **no error or traceback ever written, because the thing
that was stuck was the logging.** `weewx_monitor.py` emailed at 00:15 (22 min in — the monitor worked);
the owner was asleep.

- **Established:** weewx's main thread blocked in `pipe_wait`; the Docker daemon's path for *that one
  container* was wedged (`logs`/`exec`/`kill` all hung, other three containers healthy); a **bare
  `docker logs` with no `--tail`** had been hung since the previous day against Synology's SQLite
  `log.db`. Only `synopkg restart ContainerManager` cleared it.
- **NOT established, and the first answer was wrong.** The initial diagnosis — "the INFO console handler
  filled the stdout pipe" — is **false for this station**: the live `weewx.conf` has *no console handler
  at all*. `pipe_wait` covers a blocked pipe **read or write**, and it was read as a write without
  checking. **Mechanism recorded as OPEN.** No causal story was invented to close the ticket.
- **But the console-handler finding is real for the image we publish.** `logging.additions` (baked in by
  the Dockerfile) *does* set the console handler to INFO. Prod escaped only because **the live config has
  drifted from the repo**. Every downstream user has the hazard we did not — the same shape as DEC-0031.
  Fixed to `WARNING`; it reaches users only when v2.0.4 is pushed.
- **Recovery + backfill (ERR-0003):** ~438 one-minute records were **never captured** (nothing was
  cached; the restart discarded nothing). Backfilled 29 records from the co-located WeatherLink Live
  console via the WU history API — same ISS, **different receiver, 15-min cadence** — into both stores,
  flagged in-band `backfill = 1`. The window was dry and dead calm, so the loss is small.

### The CRC question is answered — and the test that answered it first was broken (DEC-0035)

The S36 Lloyd test reported **0 suspicious pairs** over 1,863 frames, with gaps perfectly quantized at
the 2.8 s ISS period. It looked like a decisive null. **It was an artifact — the instrument was blind to
the thing it was built to detect**, twice over: it parsed the driver's `data:` lines, which are emitted
*after* `main.go` has already dropped every duplicate; and its stated premise ("we see spurious frames
even when they fail CRC") is false, because `protocol.go` L218 bails on CRC failure *inside the Go
binary*.

Counting Go's own `duplicate packet:` lines instead: **61 frames arriving 1.4–10 ms (median 2.0 ms) after
a byte-identical frame — ~722/day.** A Davis ISS transmits every 2.8 s and cannot transmit twice 2 ms
apart. **The receiver manufactured them.** DEC-0033 is confirmed on our hardware (LloydR's gap was
262 µs; ours ~2 ms). The 712 duplicates at 2.8 s are just the transmitter repeating an unchanged payload.

This **meets the owner's precondition for the upstream post** (he wanted local confirmation first). The
post is still **not sent** — what remains is prose, in his voice, on his explicit go.

### The fork admits it is a fork (DEC-0034)

We shipped four GPLv3 files with our patches on top and said so **nowhere**, while `rtldavis.py` reported
`DRIVER_VERSION = '0.20'` — stock upstream — carrying +263/−51 lines. Every other link in the chain had
done this properly: Luc documents his merge in the header, and Vince Skahan added a dated
`# 20-12-2025 patched by...` block to the very same file. We inherited the convention and skipped it.

- **GPLv3 §5(a) modification notices** on `rtldavis.py`, `influx.py`, `ogoxeUploader.py`, and `wcloud.py`
  (whose only change is an SPDX line — recorded honestly).
- **Versioned honestly:** `0.20` → **`0.20+ws.1`** (PEP 440 local version) in the driver and the influx
  uploader. The driver now logs `(fork of lheijst 0.20 … not stock upstream)`, which also replaces the
  ad-hoc `RTLDAVIS_DRIVER_MARKER` canary — stock upstream cannot print that line.
- **`CHANGES-FROM-UPSTREAM.md`** — the full inventory, built by diffing against the real upstream
  sources, not from memory. It turned up **more than expected**: `influx.py` carries **five** patches, not
  the one we thought — including `e.read.decode()` (missing parens: the HTTP error handler raises
  `AttributeError` instead of reporting the error) and an unconditional `ssl._create_unverified_context()`
  on https. `rtldavis.py` holds **four** real upstream bugs beyond the rain filter, including a windDir
  branch that never populates wind data and a `NameError` crash path.
- **README rewritten** — it read as though we ship Luc's driver. We don't.

### Also

- **ERR-0001 amendment / DEC-0037** — the phantom-rain correction never propagated to the *derived*
  fields. The dashboard's S70 handoff caught `dayRain_in` still at **1.84″** against a corrected 0.56″;
  auditing found **`rain24_in` (1.84″) and `hourRain_in` (1.28″ — entirely phantom) were wrong too.** All
  three recomputed from the corrected SQLite series and rewritten in InfluxDB (5,394 points, in place,
  idempotent). New rule: *a retrospective correction must propagate to every field derived from it.*
- **Debug state reverted** (`debug_rtld` → 1, `user` logger → INFO). `qc-capture` on the NAS is gone.
- **Cross-project handoff** written for the dashboard + HLF (advisory; **no changes made in their
  repos**), carrying the owner's open architectural question about harmonizing shared NAS-level assets.

*Two confident, internally-consistent, wrong conclusions were reached and retracted in this session — the
"decisive null" and the console handler. Both collapsed the moment the actual artifact was inspected.
Recorded because the pattern matters more than either error.*

---

## [S36] — 2026-07-12 — v2.0.4 SHIPPED: SensorQC live; the driver-clobber found and killed; rain errata closed

The deploy that three sessions had staged and never shipped. Triggered by a handoff from dashboard
session S69, which had walked into this repo's territory, changed the live station, and found that the
bug it was chasing was already fixed here and never deployed. **Prod is v2.0.4; the bad data flowing to
WU/CWOP → NOAA MADIS (where it is immutable) has stopped.**

- **The handoff's recommended deploy path was wrong, and finding out why was the session.** It advised
  hot-fixing the driver by `scp`-ing to the bind-mounted `weewx-data/bin/user/rtldavis.py`. That path is
  **not what weewx imports** — `weewxd` loads `user.*` from the baked venv — and the running container
  had **no `rtldavis.py` mount at all**. The "fix" would have been a silent no-op.
- **The real find: `docker-compose.yml` was mounting the STOCK driver over the baked one.** Line 33 (and
  line 47 of the **public**, committed compose) bind-mounted `weewx-data/bin/user/rtldavis.py` — the
  stock driver `weectl extension install` lays down — straight over the patched one. Prod escaped it only
  because the live container was hand-run without the mount; **every downstream user of the published
  image was running the stock driver** (no rain filter, no SensorQC), regardless of image contents. This
  is the run-time twin of the S30 build-time `cp` clobber. Removed, with a "do NOT re-add" note at the
  exact line. → **DEC-0031** (driver is BAKED, never mounted; supersedes DEC-0004's driver half).
- **v2.0.4 built + deployed** (native amd64 on the NAS, `docker kill` per DEC-0008). Verified against the
  **running process**, not the version tag: `import user.rtldavis` → `SensorQC: True`, `sensor_qc True` in
  the log, `RestartCount: 0`, no driver mount. Reception came back **75–80%** (up from 63–70%). `:v2.0.3`
  retained for rollback. The live `docker-compose.yml` now genuinely describes production (it still said
  `:rw250-test`, an image two releases stale — a loaded gun for any future `compose up`).
- **Rain errata closed — all three phantoms, both stores.** A full-history sweep of InfluxDB and the
  SQLite archive finds **exactly three** implausible rain points ever. ERR-0002 (**new**, 2026-05-25
  23:22 EDT, +1.28" — a bit-7 flip; S69 spotted it, re-verified from scratch here) is now logged and
  corrected; ERR-0001's long-pending InfluxDB correction is finally applied. Both stores now agree
  exactly (2026-07-04 = 0.56", 2026-05-25 = 0.06"), which fixes the public water-balance charts.
  The "no `influx` CLI on the NAS" blocker in STATUS was **false** — there is one in the container.
- **DEC-0032 — retrospective correction: correct to the KNOWN value, flag it in-band.** DEC-0006's
  null-on-rejection rule governs the **runtime filter**, not retrospective correction. The phantoms are
  bracketed by zeros for ±20 min, so `0.0` is a *known fact* and `NULL` would have understated what we
  know. Corrected points carry a sparse **`rain_qc = 1`** flag (3 points in all of history; InfluxDB is
  schemaless, so it costs ~nothing and normal queries never see it) — WMO/MADIS practice, and it gives
  the dashboard its "corrected" marker without a parallel list. `DATA_ERRATA.md` stays narrative truth.
  → **INTERFACES.md** documents `*_qc` as an optional sparse field + pins the `record,binding=archive`
  series key.
- **`scripts/check_secrets.sh` never worked — fixed.** The allow-list ran with `grep -viE`; the `-i`
  erased the `[A-Z]` terms that carry the whole constant-vs-literal distinction, so the ALL_CAPS rule
  (meant to allow `= FOO_KEY`) also swallowed any unquoted lowercase literal — i.e. essentially every
  real secret written without quotes. **The gate was green because it caught nothing.** Now
  case-sensitive (the secret pattern keeps `-i`), plus two further holes closed that were live here *and*
  upstream: `# ` matched a comment anywhere on the line, and the docstring rule passed a capitalized
  single token. Verified 6/6 planted forms blocked, whole tracked tree clean. (Ports the dashboard's
  DEC-0063.)
- **The CRC question answered — DEC-0033 (and a retraction).** Chasing the owner-wanted community bug
  report, we first concluded the corruption *must* be transmitter-side, reasoning that CRC-16 cannot
  miss a single-bit error (verified: 0 of 64 single-bit flips of a valid 8-byte message pass).
  **That inference was invalid** — "catches all single-bit errors" does not imply "catches all errors".
  Raw packets posted by user *LloydR* in upstream issue `lheijst/weewx-rtldavis#15` settle it: two frames
  **262 µs apart** (a Davis ISS transmits every ~2.5 s), differing in **4 bits**, **both passing CRC** —
  the error pattern is a valid codeword. So one transmission is being decoded twice: the *receiver*
  makes the second frame. Model: the rtldavis Go demodulator emits spurious near-duplicate frames; most
  fail CRC and are dropped silently, ~1 in 65,536 passes and delivers garbage. The driver's dedup
  (`data != self._last_pkt`) is **exact-equality**, so a *corrupted* near-duplicate is by construction
  not a duplicate and sails past it. DEC-0029's original stated cause was right; DEC-0033 **confirms**
  it. Both rtldavis.py comments that had propagated the retracted claim are fixed.
- **The upstream contribution is drafted but NOT posted, and held out of git** (public repo). Research
  found issue #15 open since **Oct 2022** with three users reporting this exact symptom class and no
  root cause — so this is a **comment on their thread, not a new issue**. Our analysis explains *their*
  data: LloydR's counter values (115→49→115) run through the upstream handler give 0.62" + 0.66" =
  **1.28"**, matching the "1.3 inches" he reported in 2022. (The handler is wrong twice: once on the
  corrupt jump, once when the sensor returns to the truth.) Maintainer is responsive (commented
  2026-07-09); LloydR's PR #19 covers wind/temps, not rain, so we complement it.
- **`ops/find_duplicate_frames.py` — the "Lloyd test"**, to confirm the mechanism on our own hardware.
  Key property: the driver logs the raw `data:` line **before** the CRC check, so spurious frames are
  visible **even when they fail CRC** — this answers in hours, not weeks. Prod temporarily runs
  `debug_rtld = 2` + `user` logger at DEBUG to feed it (**revert steps in STATUS**).
- **Cross-repo handoff written** — `docs/handoffs/S36-to-eaglehunt-dashboard.md`: answers all three of
  dashboard S69's open questions, documents the new `rain_qc` contract, and returns a reciprocal finding
  (their secret gate still has two live holes we closed here).
- **Doc staleness swept:** ARCHITECTURE §6 claimed the running image was `rw250-test` and the Dockerfile
  "an rw350 experiment" (both stale since S30); CLAUDE.md + CONVENTIONS named the same dead tag. All now
  state the real image and the baked-driver rule. `weewx.conf.example` reconciled with the live station
  (S69's service reorder + tightened StdQC bounds); the stale DEC-0029 comment in `rtldavis.py` fixed.

## [S35] — 2026-07-09 — Docs diet (DEC-0030): tiered session read, DEC index+full split, CHANGELOG roll

Docs-only; no code, no prod change. Ports the family docs-diet pattern — born on the dashboard
(dash S57, its DEC-0081; recipe at `eaglehunt-weather-dashboard:docs/reference/docs-diet-playbook.md`),
proven on hyperlocal (its S143, DEC-0095) — to this repo, closing the three-repo alignment loop.
Session boot drops from ~130 KB ≈ 32K tokens to ~33 KB ≈ 8K tokens. **Invariant honored: text moved
verbatim, nothing rewritten or deleted; all rehomed files passed `scripts/check_secrets.sh` (public repo).**

- **DECISIONS split:** `docs/DECISIONS.md` is now a one-row-per-DEC **index** (+ open/deferred
  list); full append-only bodies moved verbatim to `docs/DECISIONS-FULL.md`. New DEC = full body
  there + index row. Noted explicitly: DEC-0018–0020 were never assigned (numbering gap).
- **CHANGELOG roll:** this file keeps ~3 live sessions; `[S31]` and earlier (back to `[Pre-S16]`)
  moved verbatim to `CHANGELOG-ARCHIVE.md` (append-only, same format).
- **CLAUDE.md doc map → two tiers** (Tier 1 always ≈ 33 KB; Tier 2 on demand, anti-loophole rule:
  *"working near it" means read it*), plus the stale-checkout guard the S35 pickup itself tripped
  over: **current docs live on `dev`** — read from `dev`'s tip if the local checkout lags.
- **Session-close ritual extended:** STATUS prune (shipped → CHANGELOG pointer, settled → DEC
  pointer), CHANGELOG roll, and a secret scan over anything a doc move rehomes.
- **ROADMAP reconciled + collapsed:** P0/P0.6/P1 → DONE pointer summaries (v2.0.3 shipped S32;
  code-quality fixes landed S24–S28); P1.5 → resolved by DEC-0029, deploy rides v2.0.4.

## [S34] — 2026-07-08 — S33 sensor-QC merged to `dev` (PR #17); health check clean; parked stable on v2.0.3

Short close-out session; owner goal: end in a place that holds for days/weeks. No production change.

- **Health check (read-only): clean.** Container on `:v2.0.3`, up 16 h, `RestartCount=0`;
  `rxCheckPercent` 68–80% live (6 h mean 74.6%, min 50, **360/360** minute rows — no archive gaps);
  **0 rain rejections ever**; monitor polling normally.
- **PR #17 merged → `dev`** (merge `db763c8`, checks green: secret-scan + lint): `SensorQC`
  decode-layer filter (DEC-0029) + DewpointCacher timeout-null (closes DEC-0022). **Staged, not
  deployed** — the driver is baked; ships with the owner-run v2.0.4 rebuild.
- **Rebuild pre-verified:** the `dev` Dockerfile COPYs the patched `rtldavis.py` into the venv
  (L99) with the S30 clobber trap explicitly guarded (L101 note) — the v2.0.4 image will genuinely
  contain `SensorQC`.
- **Reception Layer B (DEC-0024) decided: waits for v2.0.5.** v2.0.4 stays single-purpose so its
  live-verification and rollback stay unambiguous; Layer B is cosmetic + log-bloat relief, still
  undesigned (No-Rewrite), and the S31 monitor fix already made the reception emails honest.
- **Backlog: tuning infrastructure idea captured** (owner, S34) — live-tuning control panel and/or
  a statistically sufficient sweep plan (ties into DEC-0017); framing deferred to a future session.



## [S33] — 2026-07-08 — Bad-packet root cause + decode-layer sensor plausibility filter (DEC-0029, on `feature/s33-sensor-qc`, off `dev`)

The owner-priority bad-packet session. Evidence-first (owner: "pull the raw packet logs first;
let's be methodical"), then design approval, then code. **Not yet merged or deployed** — the driver
is baked, so this ships with the next image rebuild (v2.0.4).

- **Post-release health check (read-only): clean.** Container on `:v2.0.3`, `RestartCount=0`
  (expected post-reboot start 07:02 EDT), 0 rain rejections ever, monitor WINDOW 21/21 (100%).
- **Evidence dead end that matters:** the `RAW_CHANNEL_PAYLOAD` log lines never contained packet
  payloads — only frequency-hop metadata — and the v2.0.3 upstream-default binary silenced even
  those (weewx.log 16.6 → 7.5 MB/day). **No bit-level packet capture exists**; the archive DB
  (68,877 records, 2026-05-19→07-08) became the evidence base.
- **Root cause CONFIRMED from the archive** (details in DEC-0029): 18 one-minute **outHumidity**
  glitch spikes under flat radiation + flat temp, deviations clustering at 25.6/3 and 12.8/2 —
  the bit-7/bit-8 flip signature of the raw %×10 field; a physically impossible **UV 16.29** under
  overcast; midday-only pattern shown to be a **selection effect** (night glitches land >100% RH →
  StdQC nulls → carry-forward masks). **outTemp/wind archives clean** — dashboard temp + 201 mph
  wind spikes ride the unfiltered loop-JSON path (`LoopJsonWriter` runs before all QC). S30's
  suspected `MAX_WIND_DELTA` unit bug **disproven** (post-StdConvert = mph, correct).
- **Fix (DEC-0029): `SensorQC` decode-layer filter in `rtldavis.py`**, applied in `_data_to_packet`
  (rain's choke point): Davis-spec bounds (temp −40..65 °C, hum 0..100%, wind 0..89.4 m/s, UV 0..16,
  rad 0..1800 W/m²) + per-reading delta with baseline-resync (temp 4 °C, hum 10%, wind 20 m/s, UV 8;
  **no delta for radiation** — cloud edges are genuine). Honest null on rejection (DEC-0006), logs
  `"rejecting implausible value"`, rejected wind also nulls same-packet `wind_dir`. Config:
  `sensor_qc` master switch + `qc_<field>_max_delta` overrides (documented in `weewx.conf.example`).
- **DEC-0022 closed: `dewpoint_service.py` carry-forward → timeout-null.** The temp/hum/rad/UV cache
  still bridges the message-type rotation but expires after 300 s of sensor silence; dewpoint/
  heatindex computed only from fresh values. Failed sensors now read null, not frozen.
- **Tests:** `test_sensor_qc.py` (16, recorded signatures: +25.6% humidity flip, UV 16.29, 201 mph)
  + `test_dewpoint_timeout_null.py` (6). **Suite 85/85**; `ruff check` clean; secret scan green.

## [S32] — 2026-07-08 — v2.0.3 RELEASED (`v2.0.3` + `prod-baseline-20260705`); S31 monitor live; Gmail app-password rotation

**v2.0.3 released end-to-end.** Soak day 4 = clean, so the S30 hold cleared: 24 h `rxCheckPercent`
avg **75.4%** (1427/1429 records populated, min 50 / max 105 — the known floor-division cosmetic),
**0** rain-glitch rejections since the Jul-5 deploy, `RestartCount=0`, and the container rode out an
*unplanned NAS reboot* (~06:57) with a clean dongle handoff — the strongest soak evidence we could
have asked for. Only third-party upload blips (Windy/WOW 429s, a transient OWM outage). Steps:

- **PR #15** — `main`'s independent S26 secret-gate commits (PR #7) conflicted with `dev`'s (PR #6) on
  `ci.yml`, making the promotion PR un-mergeable; merged `main` into `dev` once, keeping `dev`'s
  DEC-0027 `ci.yml` (no `ruff format` gate). *(First attempt took the wrong side of the conflict —
  caught by CI's lint job doing exactly what DEC-0027 built it for, fixed before merge.)*
- **PR #11 merged** — `dev` → `main` (`f64f8d8`); `main` = production truth again.
- **Tagged `v2.0.3` + `prod-baseline-20260705`**; **GitHub release** published with the S30-drafted
  notes; **Docker Hub push `:v2.0.3` + `:latest`** (same digest `9dfd9b57…`, 281 MB) — the first
  public image that actually contains the driver fixes (rain filter, `rxCheckPercent` H2, honest-null
  wind, clobber fix).

**S31 monitor deployed + verified live — after diagnosing a reboot-broken boot task.** The morning's
NAS reboot restarted the `weewx_monitor` esynoscheduler task as a **non-root user**: its
`/etc/sudoers` append got Permission-denied and `sudo -u weewx-monitor` failed every 5 min ("a
terminal is required"), so the monitor was **down 06:56→17:28** with sudo-spam filling its log. Owner
reset the task user to root. Since the monitor was down, the S31 deploy needed no kill: scp'd `dev`'s
`weewx_monitor.py` (sha `23dfa03d…` verified; backup `weewx_monitor.py.bak-20260708-105410`), owner
ran the task, and the new code came up clean — pidfile written, incremental byte-offset polling,
startup email delivered ("Eagle Hunt PWS": `STATION_NAME` is now set, closing that housekeeping
item). First 6 h dropped-packets summary due at the next 00/06/12/18 boundary.

**Security — Gmail app password exposed in public history; rotated same-day (DEC-0028).** Found the
monitor's Gmail app password hardcoded in the legacy NAS `weewx_monitor.sh` *and* in two public-repo
history commits of `weewx_monitor.py` (`d2fb080` May 22, `eff3f56` May 24 — reachable from `main`+
`dev`, exposed ~6 weeks; the DEC-0012 gate scans trees/diffs, not history, so it never fired). Owner
revoked the credential, issued a replacement into the NAS `monitor.env` (via a clipboard-pipe
one-liner after interactive-prompt approaches failed through the `!` runner), and the monitor's
startup email verified SMTP auth on the new value. Legacy script's copy neutered to a placeholder.
**No history rewrite** — rotation kills the credential's value; force-pushing a public repo's history
doesn't un-leak it (DEC-0028).


---

*Older entries (S31 and earlier, back to [Pre-S16]) live in `CHANGELOG-ARCHIVE.md` — moved
verbatim, append-only (DEC-0030). Roll the oldest live entry there at session close once this file
exceeds ~3 sessions.*
## [S31] — 2026-07-08 — RF reception metric audited; daily email re-sourced from rxCheckPercent

**Audit finding:** the daily RF-reception email measured publish *liveness*, not reception. It counted
`Wunderground-RF: Published` log lines ÷ expected/min — a count padded by the freqError freq-hop
publishes (DEC-0024) so it reads ~100% even during real ~25% packet loss. Live proof: 14 straight
minutes pinned at "100%" while the driver's own `rxCheckPercent` ran 59–95% (median 75%); the metric's
only movement off 100% is a crash to 0% during a total stall. That bimodal 100↔0 behaviour, plus the
denominator churn (24→dedup→21) and the old ~150% reading, is why the numbers had been "all over the
place." The honest metric — the driver's `rxCheckPercent` (good CRC-decoded packets / theoretical max
per archive period) — was already in the archive DB; the email just wasn't using it.

**Layer A (monitor-only, no image rebuild):** re-source the daily summary from the archive's
`rxCheckPercent`. The email now reports packets **transmitted / received / dropped** plus hourly mean +
min — not "windows above a threshold." Verified against the live DB: 2026-07-06 = mean **75%**, 30,720
transmitted, **~7,701 dropped**. Read-only DB access with a safe fallback to the legacy scrape summary
on any hiccup; real-time `WINDOW` logging + outage alerting left unchanged (No-Rewrite, DEC-0014).
`tests/test_reception_db_summary.py` (+7); **suite 61/61**. Refines DEC-0024 (its epoch-dedup fixed the
*count*; this fixes the *source*). **Deploy = monitor restart (owner-run scp + `sudo kill`), not yet
done.** Driver-side follow-up (persist raw packet counts; fix the ~1–2 pt floor-division optimism)
folds into a later driver build.

**Reception summary cadence: daily → every 6 h (env-tunable).** A once-a-day midnight report was being
read the next morning — too late to act. The summary email now fires every `RF_REPORT_INTERVAL_HOURS`
(default **6** = 00/06/12/18 local; set 12 for twice-daily or 24 for the old daily cadence), aligned to
local-midnight blocks and reporting the window that just closed. Generalized `db_reception_summary` to
explicit epoch bounds + added `period_floor`/`period_label`; the formatter now labels the window and
lists only its hours. Verified live (mean 75%, ~1,900 dropped per 6 h window). `+2` tests, **suite
63/63**. Ships with the same monitor deploy as Layer A above.

**Also this session — CI lint made honestly green (DEC-0027).** The `lint` job had been red on every
branch (incl. `dev`) — a broken check erodes the "`main` = production truth" signal. Audited the debt:
27 `ruff check` findings (17 in vendored code, 10 ours) + `ruff format --check` wanting to reformat 25
files incl. the baked driver. Decision: lint what we maintain, don't police style or vendored code —
(1) dropped the `ruff format --check` CI gate (the codebase uses deliberate column alignment; the
driver is baked → reformatting it is No-Rewrite churn), (2) excluded vendored uploaders (`influx.py`,
`wcloud.py`, `ogoxeUploader.py`) via new `ruff.toml`, (3) fixed the 10 findings in our code
(`rtldavis.py` unused imports + bare `except`; `weewx_monitor.py` import split; test ambiguous `l`→`ln`;
`ops/*` unused imports). `ruff check .` now passes; driver logic + formatting untouched. Merged via PR #13.

---

## [S30] — 2026-07-05 — v2.0.3: driver fixes finally go live (clobber fix + build)

**Built (native amd64 on the NAS) and deployed to prod.** After deploy, `rxCheckPercent` went
NULL→real (**70–82%**) within two archive cycles — the driver's honest reception metric alive for the
first time since 2026-06-18, proving the clobber fix baked the patched driver. Packets flowing, clean
dongle handoff (no USB reset), old `rw250-test` image kept for rollback. *Still owner-gated: promote
`dev`→`main` + tag `v2.0.3`, GitHub release, Docker Hub push.*

The image folds in H1/H2/M3 (already on `dev`) plus:

- **Dewpoint service — wind honest-null (ported from the reviewed Jun-16 draft).** `_filter_wind` no
  longer substitutes the last cached `windSpeed` into a packet whose `windSpeed` is `None`. The Davis
  ISS transmits wind in **every** anemometer packet (`rtldavis.py:1122`), unlike temp/humidity/rain/UV
  which rotate across message types — so `windSpeed` is `None` only when the reading is genuinely absent
  (a "no sensor" raw `0,0` packet) or was just delta-rejected as a corrupt spike. In both cases an honest
  null is correct; a stale carried-forward value looks like live wind when there is none (e.g. a failed
  vane) and is harder to diagnose. Calm air still writes an explicit `0.0`, so charts stay continuous.
  Archive records aggregate many LOOP packets, so an occasional null packet does not blank the record;
  uploads omit nulls rather than sending bad data. **Temp/humidity/radiation/UV keep the carry-forward**
  for now — those rotating sensors legitimately miss most packets (DEC-0022 sensor-QC hardening, later).
  New `tests/test_dewpoint_wind_honest_null.py` (5 tests); **suite 54/54**.
- **receiveWindow reconciled (ARCHITECTURE §6).** Dropped the `Dockerfile` `sed 300→350` patch so the
  build ships the **upstream-default receiveWindow** — v2.0.3 carries only the proven software fixes, not
  the unproven rw350 experiment (its 24 h sweep stays backlogged). `main.go` is left unpatched.
- **Dockerfile clobber fixed — the driver fixes actually ship now (major).** `Dockerfile:101` did
  `cp /opt/weewx-data/bin/user/rtldavis.py …/site-packages/user/rtldavis.py`, overwriting the patched
  driver `COPY`'d one step earlier with the **stock** driver that `weectl extension install` lays down
  from upstream `src.tgz`. Since weewx imports `user.*` from the venv `site-packages/user/` (confirmed on
  the running container three ways: the weewx path resolver, `.pyc` presence only in that dir, and a
  content grep showing the live driver has **no** `rain_delta_tips` and the deadlocked H2), **every built
  image has shipped the stock driver** — no rain filter, no H1/H2/M3. This explains both open mysteries at
  once: `rxCheckPercent` NULL (stock's `pct_good_all` deadlock) *and* the July-4 phantom rain entering the
  archive (no live rain filter). Driver hot-swaps were landing in `data/bin/user/` — a path weewx does not
  import. Removed the clobbering `cp` (kept the `__init__`/`extensions` touches). With this, the v2.0.3
  rebuild bakes the patched driver → weewx imports it → the **rain filter, H1/H2/M3, and dewpoint
  honest-null go live for the first time**, and the public Docker Hub image finally contains them. *(The
  reception-metric fix and ERR-0001 were the NAS monitor + a DB edit, not the driver — those were already
  live.)*
- Bumped the `Dockerfile` header `v2.0.2 → v2.0.3` and refreshed the stale rtldavis `COPY` comment.
- **Committed `logging.additions` — the build was not reproducible from a clean clone.** `Dockerfile:80`
  `COPY logging.additions` referenced a file that was **untracked** (present only in the owner's checkout,
  never committed, not gitignored), so `docker build` from a fresh `git clone` failed at that step. Found
  when the v2.0.3 image was built on the NAS from the `dev` tarball. Also de-duplicated its contents (the
  `[Logging]` block had been accidentally appended twice). Now tracked → the image builds from a clean
  checkout on any host.

## [S29] — 2026-07-05 — RF-metric honesty, rxCheckPercent root cause, ERR-0001 correction

Turned the "how is reception really doing?" question into trustworthy answers, and reconciled the
July-4 rain glitch. Two owner-run prod steps deployed live (agent-guided, read-only-verified).

- **Reception "91%" was a denominator artifact — fixed + deployed.** The monitor divided the WU-publish
  count by a hardcoded **24**, but this ISS (Transmitter 4) transmits every ~2.8125 s → only ~**21.3**
  records/min are physically sent. Live measurement: **21.75/min**, ~2.78 s mean spacing, no multi-second
  gaps → **~100% reception**, not 91%. Set `WU_RF_EXPECTED` → **21** (env-overridable per station) and
  added `wu_pct()` (single source of truth, capped at 100). New `tests/test_reception_pct.py` (9 tests);
  **suite 49/49**. Merged **PR #10 → `dev`** (also carries the S28 M-A/L-B incremental read) and
  **deployed** (monitor restart); live log flipped `WINDOW: 22/24 (92%)` → **`WINDOW: 23/21 (100%)`**.
- **`rxCheckPercent` root-caused (dead since 2026-06-18).** The driver's own honest reception metric
  populated the archive 2026-05-26 → 2026-06-18 18:42 UTC (avg **67.5%**, the pre-LNA baseline), then
  went NULL. Traced to a **weewx engine reload at 2026-06-18 14:44 EDT** whose code carries the S24 "H2"
  `pct_good_all` deadlock (`rtldavis.py:1006` guards the assignment with `… and pct_good_all is not None`,
  but it's reset to `None` every period → can never pass). **Fix already on `dev`** (`:1011`,
  regression-tested); ships with the v2.0.3 image rebuild. (Reception genuinely improved ~70% → ~100% via
  the LNA between June and July — right when both honest metrics were dark.)
- **DEC-0025 — known-bad data: preserve-and-flag, never delete.** New public append-only
  **`docs/DATA_ERRATA.md`** + the reconciliation model (as-transmitted / errata / corrected best-estimate).
- **ERR-0001 applied — July-4 phantom honest-nulled.** The +1.28" 3 AM glitch (old driver, `rain_count=-64`
  → +128) was confirmed baked into the archive **and** the Weather Underground record (day total **1.84"**;
  MADIS almost certainly too — precip is barely QC'd downstream). Owner nulled the two 3 AM records
  (`dateTime IN (1783148640, 1783148700)`) + `weectl database rebuild-daily --date=2026-07-04`; July-4 rain
  **1.84" → 0.56"** — surgical (the day's genuine 0.56" evening rain preserved). InfluxDB copy still carries
  it (cross-repo follow-up); external WU/MADIS immutable, reconciled by the errata.
- **DEC-0026 — v2.0.3 confidence gate waived.** Cut the release with the rain fix baked in rather than wait
  weeks for a live glitch; the fix is already protecting prod, is tested, and the pipeline was validated
  end-to-end this session.
- **Housekeeping:** merged PR #10 (branch deleted). `dev` now carries rain + reception (metric + denominator)
  + governance + S24/S25 code-quality. **Next session ships v2.0.3** (image rebuild on Mac Docker Desktop →
  redeploy → promote `dev`→`main` + tag → GitHub/Docker Hub → live-confirm `rxCheckPercent` repopulates).

## [S28] — 2026-07-05 — Monitor incremental read (M-A/L-B) + branch cleanup

Release still calendar-gated (no real rain glitch yet); this session cleared the unblocked follow-ups.

- **P1 verified (read-only, live).** Rain wild-watch: **0** `rejecting implausible counter delta`
  events across the full log range (2026-06-05 → now) — the first real glitch still hasn't fired, so
  v2.0.3 stays parked. Reception Layer A confirmed live: WINDOW **88–100%**, 5-window avg **91–92%
  [OK]**, 0 bad windows; monitor healthy (PID alive under the esynoscheduler wrapper). Layer B
  signature still present live (driver emits `RAW_CHANNEL_PAYLOAD`/`FreqError` + double-publishes the
  same record epoch — exactly what Layer A dedups; weewx.log ~10 MB/day).
- **M-A + L-B: monitor incremental byte-offset read (PR #10 → `dev`, draft).** Replaced
  `get_linecount()` + `get_new_lines()` — which each re-read the whole (~10 MB/day, growing)
  `weewx.log` on every 30 s poll — with a single byte-offset read: `get_log_size()` +
  `get_new_lines(offset)` → `(lines, new_offset)` via one `seek()`. Fixes the O(n)-per-poll re-scan
  (**M-A**) and the double-open size/read race that double-counted appended lines (**L-B**, resolved
  for free by the `seek()`). Rotation (`get_log_size() < offset` → reset) + partial-line (hold back a
  line with no trailing newline) guards. New `tests/test_monitor_incremental_read.py` (6 tests);
  **suite 40/40**; secret-scan green; `lint` red (known pre-S24 ruff baseline, non-blocking).
  **Not yet deployed** — owner-gated (scp + `sudo kill`, same as Layer A).
- **Branch housekeeping.** Deleted merged remote branches `s20-governance-hardening` and
  `feature/influxdb-grafana` (moved off Grafana to Influx; its only driver-relevant bit — the
  wind-warmup one-liner `3f5470f` — was already in `dev`). `s27-p3-deployed` was already
  auto-deleted on PR #9's merge (stale local ref pruned). Remote-URL casing was already correct
  (both no-ops). Remote now: `dev`, `main`, `feature/rain-spike-filter` (kept for v2.0.3),
  `feature/s28-monitor-incremental-read`.
- **Still owner/calendar (→ S29):** review + merge + deploy PR #10; watch for the first real rain
  glitch → then cut v2.0.3; rotate the exposed WU key; set `STATION_NAME` in the NAS `monitor.env`
  (emails currently fall back to "My PWS").

## [S27] — 2026-07-05 — Land the secret gate + collapse the review stack onto `dev`

Tied up the S23–S26 PR backlog (five open, nothing merged). No prod/driver code touched; all the
review work landed on `dev`, and `main` got only the secret gate.

- **Secret gate now blocking (P1).** Merged **PR #6 → `dev`** (`90ef51b`) and **PR #7 → `main`**
  (`490e776`) — `main` previously had zero secret scanning. CI on both merge commits: `secret-scan` =
  pass, `lint` = fail (expected pre-S24 ruff, non-blocking to the gate). Then set **`secret-scan` as a
  required status check** in branch protection on `dev` + `main` (via the keyring token — the PAT's 403
  was a scope problem; `enforce_admins: false`, no required reviews). The DEC-0012 gate is no longer
  advisory.
- **Governance/review stack collapsed onto `dev` (P2).** The whole stack merges clean — the predicted
  `ci.yml`/`check_secrets.sh` conflict never materialized because the stack's S20 gate fix (`2a6327c`)
  is byte-identical to dev's #6 fix. Retargeted **PR #5** (`feature/s24-code-quality-review`, whose tip
  already carried reception-dedup + s23-governance + s24/s25) to base `dev` and merged it (`2c75c5e`),
  bringing all S18–S26 work — the rain fix, reception Layer A, the S23 governance docs (LICENSE/AGENTS/
  ASSESSMENT), and the S24/S25 code-quality fixes — onto `dev` in one gated merge (secret-scan green,
  34/34 tests). Closed **#3** and **#4** as merged-via-#5.
- **S23 tail closed.** Folded the 8 still-open items from the retired root `cleanup_backlog.md` into
  `BACKLOG.md` (dedup'd against what it already carried) and deleted `cleanup_backlog.md` + the
  duplicated `logging.additions` fragment (`7025afa`).
- **`main` untouched beyond the gate.** The `dev`→`main` v2.0.3 promotion stays parked pending the rain
  fix's first wild glitch + the dewpoint rebuild.
- **Reception Layer A DEPLOYED live (DEC-0024).** scp'd the dev `weewx_monitor.py` to the NAS (backup
  `weewx_monitor.py.bak-20260705-141508`), `sudo kill`ed the monitor; the esynoscheduler `sleep 300`
  wrapper respawned it on the new code. **Confirmed**: the RF WINDOW metric dropped from a steady
  ~150–162% to **92%** (`22/24`) on the first post-restart window — same packet volume, correct
  epoch-dedup. Reversible via the backup.
- **Still owner/calendar actions (→ S28):** watch for the first real rain glitch; rotate the exposed WU
  key; the influxdb-grafana cherry-pick + stale-branch cleanup; remote-URL casing; set `STATION_NAME`
  in `monitor.env` (emails currently fall back to "My PWS").

## [S26] — 2026-07-05 — Fix the secret gate's mainline coverage (draft PRs #6 → dev, #7 → main)

A dashboard (dash) cross-repo note flagged the ported DEC-0012 secret gate as neutered and warned this
repo's gate "almost certainly has the same hole." Verified empirically — the concern is real, but not
where the note assumed. **No prod/driver code touched; two draft PRs, nothing merged.**

- **Diagnosis (empirical).** The neuter bug — the `grep -n` `<lineno>:` prefix matched the docstring
  allow-rule's bare `:` and silently whitelisted real `ident = secret` lines — was **already fixed** on
  the governance feature-stack in S20 (`2a6327c`, `:` → `[A-Za-z]:`); the current gate catches a planted
  secret assignment (a real-looking `api_key` value) that the old gate passed clean. But the fix
  never reached the mainline:
  - **`main`/`origin/main`** — **no `check_secrets.sh` and no `ci.yml` at all.** A fresh clone of the
    public default branch had zero secret scanning.
  - **`dev`/`origin/dev`** — the **neutered S17 gate**, *and* its secret-scan was the last step of a
    single CI job behind `ruff check`, which fails on the pre-S24 tree (32 errors) — so the whole job
    went red at ruff and the scan never ran. Doubly dead.
- **PR #6 → `dev`** (`s26-secret-gate-dev`) — replaced `check_secrets.sh` with the fixed version; split
  `.github/workflows/ci.yml` into an independent **`secret-scan`** job + a `lint` job so a lint failure
  can never skip the gate.
- **PR #7 → `main`** (`s26-secret-gate-main`) — added `check_secrets.sh` (fixed) + the two-job `ci.yml`
  + `.pre-commit-config.yaml` (main had none of the apparatus).
- **Verified.** On both PRs, CI **`secret-scan` = pass** (clean tree) and **`lint` = fail** (expected,
  pre-S24 ruff; non-blocking to the gate). Locally: planted secret caught (exit 1); the fixed gate scans
  each whole tracked tree clean (exit 0, no false positives).
- **Open (→ S27):** (1) mark **`secret-scan`** a **required** status check in branch protection on `dev`
  + `main` (needs repo admin; PAT 403'd) — until then CI is advisory, not blocking. (2) Reconcile the
  s20→s24 governance stack's old single-job `ci.yml` to this two-job structure when it merges. (3) Review
  + merge #6 then #7. Cross-repo finding recorded; the corrected takeaway for dash: verify against the
  branch that actually carries the fix, and confirm its own gate uses the `[A-Za-z]:` guard.

## [S25] — 2026-07-05 — Finish the S24 review fixes (on `feature/s24-code-quality-review`)

Completed the S24 review's deferred tail. **Branch-only, not deployed;** the driver changes still ride
the next rebuild + hot-swap. No-Rewrite honored — every change is surgical. Full offline suite green
(34/34: the prior 29 + 5 new `owm` tests).

- **U1/U2 (`owm.py` rebase)** — the uploader overrode `RESTThread.run_loop` with a hand-rolled
  `queue.get`/`urlopen` loop, silently discarding every resilience knob it was constructed with
  (`post_interval`/`max_backlog`/`stale`/`max_tries`/`retry_wait`/`skip_upload`) — a transient network
  failure dropped the record with no retry. Re-based on the standard hooks: kept `format_url`, moved the
  JSON body to `get_post_body(record) → (body, 'application/json')` (the same contract `influx.py`
  uses), deleted `run_loop`/broken `post_request`/`import time`/unused `urllib.request`. RESTThread now
  owns retry/backoff. New `tests/test_owm_post_body.py` (5 tests: kwargs forwarded, hooks not
  overridden, body shape + km/h→m/s conversion, None-field omission, appid URL).
- **U4 (`influx.py` TLS)** — `post_request` unconditionally used `ssl._create_unverified_context()` for
  any `https://` endpoint (silent MITM exposure). Added a `verify_ssl` option (**default `True`** =
  verifying context; explicit opt-out restores unverified for self-signed/internal endpoints), wired
  through the service `__init__` + `InfluxThread`, documented in the docstring. Moot for the current
  local `http://` Influx; drop-in.
- **M4 (dead code)** — deleted `_fmt` (py2-only `ord()`) and `parse_readings` from `rtldavis.py`; both
  had zero callers repo-wide.
- **L6 (driver nits)** — fixed the per-transmitter debug guard to test the list *element*
  (`stats['pct_good'][i] is not None`) instead of the always-truthy list; hoisted `_stderr_sample_count`
  init out of the hot read loop into `__init__`; annotated the unreachable `elif lines:` branch. **L5:**
  documented the `@staticmethod`-that-takes-`self` convention at `parse_raw` rather than restructuring.
- **Nit sweep** — `weewx_monitor.py`: narrowed three bare `except:` → `except OSError:`, and made the
  three hardcoded `/volume1/...` paths env-overridable (`WEEWX_RTLDAVIS_DIR`/`MONITOR_LOG`/
  `MONITOR_PIDFILE`/`WEEWX_LOG`) for parity with the env-sourced credentials. `windy.py`: replaced the
  `__import__('queue')` wart with a normal `import queue`. `influx.py __main__`: `os.environ[...]` →
  `.get(...)` so `--version`/`--help` no longer `KeyError`, and fixed the `InluxDfB` typos.
  `ogoxeUploader.py`: reconciled the contradictory `server_url` comments and logged the real
  hardcoded URL instead of `None`.
- **SPDX** — added per-file `SPDX-License-Identifier: GPL-3.0-or-later` headers to the driver + all
  reviewed satellites (`rtldavis`, `weewx_monitor`, `owm`, `windy`, `influx`, `ogoxeUploader`, `wcloud`,
  `loop_json_writer`).
- **Deferred (still, → S26):** **M-A** (monitor incremental read) and its coupled **L-B** (double-read
  race) — both wait for the DEC-0024 Layer A monitor deploy so they don't step on the queued
  `weewx_monitor.py`. The S24 driver fixes (H1/H2/M3) + these still need the rebuild/hot-swap.
- Verified: `py_compile` clean on all 8 touched modules; offline suite **34/34 green**; secret-scan
  passes on every changed file.

## [S24] — 2026-07-05 — Code-quality review + first fixes (on `feature/s24-code-quality-review`, stacked on S23)

Reviewed the driver and its satellites, then fixed the two real bugs plus the log-bloat source. **Fixes
are branch-only; the driver ones need a rebuild + hot-swap and are NOT deployed.** No-Rewrite honored —
every change is surgical.

- **`docs/CODE_REVIEW_S24.md` (new)** — deliverable-of-record: ranked findings across `rtldavis.py`
  (1506 ll), `weewx_monitor.py`, and all uploaders (`owm`/`windy`/`ogoxe`/`wcloud`/`influx`) +
  `loop_json_writer.py`. Draft **PR #5**, based on the S23 branch. Records a verification note: a
  candidate `setDaemon`/`setName` finding was **dropped** after testing against the live Python 3.14.5.
- **H1 (`0929952`)** — `parse_raw` unknown-channel branch referenced an undefined `raw` (param is
  `pkt`) → `NameError` inside `genLoopPackets` instead of the intended log line. One-line fix +
  `tests/test_parse_raw_channel.py` (proven to fail with the exact NameError pre-fix).
- **H2 (`970c47e`)** — `pct_good_all` bootstrap deadlock: `_update_summaries` only set it under a guard
  that also required it to be non-`None`, but `_init_stats`/`_reset_stats` null it every period, so the
  driver's own `rxCheckPercent` was **never populated** (likely why the log-scraping monitor exists).
  Dropped the self-defeating clause + `tests/test_reception_stats.py` (drives two archive periods +
  `new_archive_record`; fails pre-fix). Live-confirm `rxCheckPercent` on deploy.
- **M3 + U3 (`8872947`)** — the `weewx.log` bloat (DEC-0024 Layer B family): gated the driver's
  per-packet `RAW_CHANNEL_PAYLOAD`/`RAW_RTL_HOP`/`RAW_RTL_STDERR_SAMPLE` INFO logging behind
  `debug_rtld`, and dropped `influx.py`'s per-record `loginf` → `logdbg` (also fixed the "Bindding"
  typo). Pure log-level changes, no behavior change.
- **Deferred (in STATUS handoff → S25):** M-A (monitor incremental read — waits for the Layer A deploy
  to avoid stepping on it), U1/U2 (`owm.py` RESTThread rebase for retry/backoff), U4 (`influx.py` TLS
  verification), and the M4 dead-code + minor-nits + SPDX-header sweep.
- Verified: full offline suite **29/29 green** (H1 2, H2 2, plus the existing 25); secret-scan passes
  on every changed file; both edited modules `py_compile` clean.

## [S23] — 2026-07-05 — Cross-project governance alignment (on `feature/s23-governance-alignment`)

Docs-only, **no driver or prod code touched, not deployed.** Piloting a shared governance standard
across the three-repo Eagle Hunt family (this repo is the pilot; ASSESSMENT.md §2/§5).

- **`docs/ASSESSMENT.md` (new)** — cross-repo governance audit (weewx vs `eaglehunt-weather-dashboard`
  vs `hyperlocal-forecast`), the "isolate content / harmonize form" alignment model, a draft
  **Governance Standard v1** (shared core + per-repo profiles), ranked recommendations, and the
  pilot→harvest→propagate roadmap toward a generic project template.
- **`LICENSE` (new)** — GPLv3, verbatim canonical text (reused from `hyperlocal-forecast` for
  guaranteed-correct text + cross-repo consistency). Fills the gap of a public, published tool with no
  license; ecosystem-standard for a WeeWX-derived work. Per-file SPDX headers deferred to the S24 review.
- **`AGENTS.md` (new)** — cross-agent entrypoint (the `AGENTS.md` convention) pointing at CLAUDE.md +
  STATUS.md, so a non-Claude agent or human can pick the repo up from GitHub alone.
- **ROADMAP restructured** — shared `P0–P4` vocabulary mapped to short/medium/long horizons; folded to
  post-S22 reality with ✅ done-markers and a "vision" preamble; added the P0.5 governance-alignment
  workstream. P0 governance bootstrap marked done.
- **STATUS.md made the single source of truth** for the session number (DEC-0023) and the
  **next-session handoff moved into the repo** (out of Claude-private memory, now a pointer) — the
  north-star fix so handoff state is visible on GitHub. Doc-map reordered to put STATUS at slot #2.
- Verified: secret-scan gate (DEC-0012) passes on all changed files; docs-only diff.

## [S22] — 2026-07-05 — Merge PR #2 + reception metric Layer A fix (on `feature/reception-dedup`, off `feature/rain-spike-filter`)

Picked up the S21 handoff. No driver or prod code touched; not yet deployed.

- **Merged PR #2** (`s20-governance-hardening` → `feature/rain-spike-filter`): the S20 governance work
  (independent numbering DEC-0023 + two `check_secrets.sh` gate fixes) now rides with the rain fix
  toward v2.0.3. Resolved three append-conflicts keeping both S20 and S21 content (CHANGELOG S21→S20,
  DECISIONS DEC-0023 above DEC-0024, STATUS last-updated). Merge commit `1a265e7`.
- **Reception-metric Layer A fix (DEC-0024, `20bf7c0`):** `weewx_monitor.py` counted raw
  `Wunderground-RF … Published` log lines, but the driver publishes freqError freq-hop packets as
  duplicate publishes of the **same record epoch** — over-reading reception to ~150%. A live read-only
  sample (2026-07-05) showed a clean 2× (same `(epoch)` posted twice). Fix: a pure `wu_record_key()`
  helper dedups on the trailing `(<unix_epoch>)`; the window now counts **unique epochs**.
  `close_reception_window` + the driver are untouched. 6 offline tests
  (`tests/test_reception_dedup.py`). **Deploy = monitor restart only** (respawn loop reloads on-disk
  code); reversible. **Layer B stays deferred.**
- **Live read-only check (SSH):** confirmed no rain glitch has fired in the wild yet (v2.0.3 promotion
  still calendar-bound); verified the live `weewx_monitor.py` was byte-identical to the repo copy
  (md5 match) before patching.

## [S21] — 2026-07-04 — Reception metric ~150% root cause (DEC-0024) + numbering made independent (on `feature/rain-spike-filter`)

Investigation + governance, **no driver or prod code touched**. (The S20 governance-hardening
CHANGELOG entry rides in separately via draft PR #2 — see below.)

- **Reception-metric ~150% — root cause confirmed (DEC-0024, OPEN).** Live read-only diagnosis: the
  daily RF-Reception emails over-count because `weewx_monitor.py` counts `Wunderground-RF: Published`
  *log lines* ÷ `WU_RF_EXPECTED`(=24), but the driver publishes freqError freq-hop `CHANNELPacket`s as
  extra **dataless loop packets** (~1.66×; live sample 1605 publishes / 968 unique record epochs,
  single Transmitter:4). True reception was ~90%. Cosmetic — real weather data + the rain fix are
  unaffected. Documented Layer A (monitor counts unique epochs — safe, monitor-restart-only) vs
  Layer B (driver stops publishing dataless freqError packets + disable `RAW_*` debug logging; also
  fixes the 15 MB / 122 k-line `weewx.log` bloat). Fix **deferred** (diagnosis + docs only).
- **Doc-vs-reality flag:** BACKLOG claimed the Go binary emits no `ChannelIdx`/`FreqError`; the running
  binary emits **both** — the likely trigger. BACKLOG finding corrected.
- **Session numbering made independent per-repo (DEC-0023, supersedes DEC-0013).** A forensic audit
  showed the "shared lineage with the dashboard" premise never held (the dashboard runs its own
  continuous S1→S40 counter and never referenced a shared one). Each repo now counts its **own**
  sessions; number from *this repo's* CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S21` vs
  `dash S40`); this repo's line is contiguous S16→…→**S20**→**S21**. The prior draft PR that tried to
  *reunify* into a shared counter (mislabeled "S40") was reworked into the **S20** governance-hardening
  session and now rides as **draft PR #2** (`s20-governance-hardening`; PR #1 auto-closed by the branch
  rename). That branch also carries two real `check_secrets.sh` fixes.

## [S20] — 2026-07-04 — Governance hardening: independent session numbering + fix secret-scan gate (on `s40-governance-hardening`, off `feature/rain-spike-filter`)

Governance audit ("does our governance make sense, is it robust, is it aligned with the sibling
repos") + the fixes it surfaced. No driver/prod code touched.

- **Session numbering made independent (DEC-0023, supersedes DEC-0013):** a forensic audit showed the
  "shared lineage with the dashboard" premise never held — the dashboard runs its own continuous
  S1→S40 counter and never referenced a shared one; this repo's DEC-0013 invented a parallel counter
  that re-used numbers (S16–S19) the dashboard had long passed. Resolution: **each repo counts its own
  sessions**; number from *this repo's* own CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S20`
  vs `dash S40`). This repo's line stays contiguous **S16→S17→S18→S19→S20**. (An earlier draft of this
  session tried to *reunify* into the shared counter and relabel this session "S40"; reversed before
  merge so `main` never sees the detour.) Updated `CLAUDE.md`, `docs/STATUS.md`.
- **Secret-scan gate hardened (`scripts/check_secrets.sh`)** — the load-bearing DEC-0012 gate, two bugs:
  1. **False-negative (serious, latent since S17):** the generic assignment-style detector (branch b)
     was effectively **dead**. Its allow-list runs against `grep -n` output, and the docstring-param
     rule `:[[:space:]]*[A-Z][a-z]` matched the `<lineno>:` prefix (e.g. `1:api_key = "…"` → the `:a`),
     silently whitelisting virtually every real `ident = "secret"` line. Tightened to `[A-Za-z]:…`
     (require an alpha char before the colon) so the numeric prefix no longer matches. Verified: a
     planted fake credential (an `sk_live_…`-style token assignment) is now caught; the whole tracked
     tree still scans clean (no new false positives); genuine docstring params still allowed. (This
     very reword was itself flagged by the fixed gate — dogfooding. The S16 leaks were caught by the
     *identifier* branch, which skips this filter — so the hole went unnoticed.)
  2. **Empty-array crash:** threw `files[@]: unbound variable` under `set -u` when run by hand with no
     staged files (bash-3.2 empty-array expansion). Added a clean-pass guard so the manual whole-tree
     audit path fails safe. CI (`git ls-files | xargs`) and pre-commit were already unaffected by both.
- **Doc note (`docs/CONVENTIONS.md`):** the macOS dev box has only `python3` (no bare `python`); the
  prescribed `python -m …` validation commands don't run verbatim locally — noted, plus how to run
  the secret gate standalone.
- **Audit verdict:** governance is coherent and well-aligned with the dashboard's nine-file model
  (intentional, documented divergences: `INTERFACES.md` ← `DATA-MODEL.md`, added `BACKLOG.md`); the
  one real drift was STATUS.md going stale after the S18 deploy — already reconciled in `689b12c`.

## [S18] — 2026-07-04 — False-rain fix (on `feature/rain-spike-filter`, off `dev`)

Confirm-first diagnosis then fix for the phantom-rain bug. Not yet deployed (pending a dry-window
live hot-swap) or merged. Target release v2.0.3.

- **Diagnosis (read-only):** root cause confirmed from code + archive DB + driver logs — the driver
  treated *any* negative rain-counter delta as a 127→0 wraparound and added 128, converting an
  RF-decode glitch into phantom rain. Two events found in 63k archive records: 2026-05-25 (1.28",
  exceeds the world 1-min rainfall record) and 2026-07-04 (0.64"×2, `rain_count=-64` in the log),
  both flat-zero-bracketed and false vs the WeatherLink Live console. Corrected two prior
  assumptions: the counter is 7-bit (not 8-bit), and the recent event was −64→+64 (not a single +128).
- **Fix (`rtldavis.py`):** extracted the pure `rain_delta_tips()` helper (DEC-0021) — only near-−128
  deltas are wraparounds; small-negative and >60-tip (0.60") deltas → `None` (null-on-rejection,
  DEC-0006). Self-documenting docstring explains the bug for future readers.
- **Tests (`tests/test_rain_filter.py`):** 13 offline cases against the exact recorded signatures
  (both glitches reject; real −127 wraparounds and normal rain pass); stubs weewx so it runs with no
  install, wired for CI.
- **Backstop (`weewx.conf.example [StdQC]`):** `rain 0,10 → 0,1.0`; added `rainRate 0,16` — the
  live-config edit happens at deploy time.
- **Audit found (deferred to S19, DEC-0022):** `dewpoint_service.py` still substitutes stale
  temp/humidity/radiation/UV (DEC-0006 violation); minor windGust/radiation/UV StdQC gaps.
- **Email alert (`weewx_monitor.py`):** watch the weewx log for the driver's rejection line and
  email on each caught glitch (reusing the monitor's existing Gmail + log-tail; the driver stays
  pure I/O-free). Reports the counter values and the false rainfall the old code would have
  recorded. `--test-alert` sends a sample email for verification. Detection unit-tested
  (`tests/test_rain_glitch_alert.py`, 6 cases — no false positives on real wraparounds/uploads).
  DEPLOYED (rain driver + StdQC) to the live container 2026-07-04 via reversible hot-swap with an
  in-container import pre-flight; verified healthy. Monitor file staged; alert activates on the next
  monitor restart.

## [S17] — 2026-07-04 — Documentation governance bootstrap (on `dev`)

- Authored the nine-file governance package modeled on `eaglehunt-weather-dashboard` (DEC-0010):
  `CLAUDE.md` + `docs/{PRINCIPLES, CONVENTIONS, DECISIONS, ARCHITECTURE, INTERFACES, ROADMAP,
  STATUS}` + `CHANGELOG.md` + `BACKLOG.md`.
- `DECISIONS.md`: backfilled genesis ADRs DEC-0001…0009 (reconstructed, approximate dates) and
  recorded the governance-era decisions DEC-0010…0017 (governance model, branch model, secret
  hygiene, session numbering at S16, No-Rewrite, hyperlocal tooling graft, Opus 4.8 driver, and the
  interim gain-372 amendment).
- `INTERFACES.md`: documented the two consumer contracts — the loop-JSON real-time surface (field
  table + units + sparse-field caching) and the InfluxDB 2.x line-protocol schema — so the driver
  stays re-pointable toward non-Davis / CumulusMX producers (PRINCIPLES §1).
- Added Python tooling grafted from the hyperlocal-forecast repo (DEC-0015): `.pre-commit-config.yaml`
  (ruff, ruff-format, secret-scan) and `.github/workflows/ci.yml`.
- All authored on `dev`; `main` untouched.

## [S16] — 2026-07-04 — Reconcile repo with production reality → `prod-baseline-20260704`

The published repo had drifted badly from the live NAS system; the drift ran in *both* directions
(GitHub missing runtime files, but also GitHub *ahead* with corrupted uploaders). Captured what is
actually running as the truth on `main`. Commit `7e79d15`, tagged `prod-baseline-20260704`.

- **Added** runtime/driver files missing from the repo: `rtldavis.py` (the driver), `influx.py`,
  `loop_json_writer.py`, `ogoxeUploader.py`.
- **Fixed corrupted uploaders**: GitHub's `owm.py`/`windy.py` had stale duplicate class definitions
  appended that shadowed the clean RESTThread classes (Python uses the last definition) — a latent
  regression for anyone deploying from the public repo. Reconciled to the running versions.
- **Synced infra** stale v2.0.1 → live v2.0.2: `Dockerfile` (rtl-sdr pkg, `receiveWindow` patch,
  influx2 install, COPY steps) and `entrypoint.sh` (dropped syslogd, added `rtl_biast -b 1` bias-tee).
- **Regenerated `weewx.conf.example`** from the live config with maximum scrub (all credentials,
  station IDs, `station_url`, coordinates, and the InfluxDB org name → `YOUR_*` placeholders).
- **Curated `docker-compose.yml`** to driver-only; documented the hot-swappable extension mounts and
  treated downstream consumers (InfluxDB, dashboards) as external (DEC-0010, INTERFACES).
- **Expanded `.gitignore`** (secrets, backups, logs, data, dashboard artifacts, vendored deps).
- **Versioned `ops/`** RF/operational tooling under clean canonical names (dropped version-numbered
  sweep iterations); `wxcheck.sh` scrubbed of a hardcoded WU API key + PWS id.
- **Secret hygiene:** three real leaks caught and scrubbed pre-commit (a hardcoded WU API key + the
  PWS id in `wxcheck.sh`; a station-location chart title in `gain_sweep_analyze.py`; the InfluxDB
  org name). Verified the tracked tree carries zero personal identifiers.
- Resolved the four verify-at-start items: gain is live at **372** (not 207); the v2.0.3 dewpoint fix
  never shipped; the `rw250-test` Dockerfile exists (no reconstruction needed) but diverges toward
  rw350; live `weewx_monitor.py` matches GitHub.
- Discovered `v2.0.2` was never git-tagged (DEC-0003 gap); the vestigial `loopdata.py` mount.

---

## [Pre-S16] — pre-governance history (reconstructed, approximate)

- **v2.0.2** (~2026-05-31, built, never git-tagged): baked-in `rtldavis.py` windDir patch,
  `rtl_biast -b 1` bias-tee in `entrypoint.sh`, `rtl-sdr` package added.
- **v2.0.1** (~2026-05-29): RF reception monitoring in `weewx_monitor.py`, wind-filter iterations,
  elevation fix, StdCalibrate wind offset, STATION_NAME de-personalization.
- **v2.0-ubuntu26** (~2026-05-26): Ubuntu 26.04 / Python 3.14 multistage build (979 MB → 278 MB).
- **v1.0-ubuntu22** (~2026-05): original working image, Ubuntu 22 base.
- Extensive RF tuning (gain/fc/ppm/receiveWindow sweeps), the custom `loop_json_writer.py`, and the
  11-service upload chain were built across these sessions. See BACKLOG.md for the durable RF findings.
