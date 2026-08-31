# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
