# Backlog — weewx-rtldavis

Unordered near-term ideas and durable findings not yet scheduled, **plus long-term/uncalendared
direction** (its own section below, moved here from ROADMAP.md's old P4 + "Longer horizon" at
DEC-0058, S56 — keeps ROADMAP.md down to the actively-sequenced P0–P3 plan). Scheduled work lives
in ROADMAP.md; in-flight work in `BOOT.md`. Carried forward from the pre-governance NAS
`BACKLOG.md`; the open items from the retired root `cleanup_backlog.md` were folded in here (S27,
S23 tail). **The "Open threads" and "Needs a check" sections below moved here verbatim from the
retired `docs/STATUS.md` at S60 (DEC-0063; that file no longer exists)** — they were never in-flight work, and `BOOT.md` is
capped for what is.

## Open threads — none of these block anything (moved from STATUS.md, S60)

- **Monitor alert on the new rejection signature (S33 follow-up #1)** — extend `weewx_monitor.py`'s
  rain-glitch email to SensorQC rejections; needs its own pattern + a rate cap so a flapping sensor
  can't spam. Only worth doing once we see the real rejection rate.
- **`DewpointCacher` × `SensorQC` interaction (S36, undecided).** The cacher carries `outTemp`/
  `outHumidity`/`radiation`/`UV` forward for up to 300 s, so a value SensorQC *rejects* gets refilled
  with the last good reading (~40 s old) rather than left null. The bad value never propagates either
  way — so this did **not** block v2.0.4 — but a rejected reading is currently indistinguishable from an
  absent one in the data (the rejection is still logged loudly). Decide whether that's right.
- **Errata → dashboard contract (cross-repo, dash S69 Q3).** The owner wants corrected points visibly
  asterisked on the water-balance chart. **Half-solved:** InfluxDB corrected points now carry a sparse
  `rain_qc = 1` flag (DEC-0032, documented in INTERFACES.md), so the dashboard can render the marker
  straight from the data with no parallel list. The dashboard side still has to *read* it.
- **Unported from the dashboard:** its `.claude/agents/` routing definitions (its DEC-0093).

**Resolved, kept as one-liners so nobody re-opens them** (STANDARD rule 1 — the full reasoning is in
the DEC, do not re-derive it):

- ✅ **rainRate** — ISS-side condensation artifact, hardware inspected and clean. DEC-0042, bounded
  by DEC-0049. A third event on the next calm, saturated, cooling night is a free test; the sharp
  prediction is that **the tip counter still will not advance**.
- ✅ **Cross-sensor coupling filter** — parked, deliberately not built. Its premise failed on our own
  data; **the mechanism is the open question, not the threshold**. DEC-0044.
- ✅ **Gain 372 interim** — absorbed into the designed RX experiment; do not tune gain or
  `receiveWindow` by feel. DEC-0017 → DEC-0048 → DEC-0059.
- ✅ **`loopdata.py` + `ops/reception_service.py` removed** (S47) — both vestigial, files renamed
  aside on the NAS in case of rollback (neither file exists in the repo any more). DEC-0005, CHANGELOG `[S47]`.

## Standing watches — read-only, none of these block anything (moved from BOOT.md, S67)

They live here rather than in `BOOT.md` because a watch is not in-flight work: it fires or it
doesn't, and until it fires there is nothing to do. Check them when something looks odd, or when a
trigger below is plainly satisfied.

- **Co-rejection grep** (DEC-0054): **first fired 2026-10-10 (found S159).** `frame failed
  message-type proof` at 2026-10-10 19:58, 10-13 10:39 and 10-18 06:43 ET, each co-rejecting one
  frame's wind fields, plus two `frame failed bounds proof` lines, in marvin's logs from 10-06 to
  10-19. The check working as designed; nothing to do unless the rate climbs. Was 0 hits through
  2026-08-12 (S76), positive-controlled — the identical pipeline returned 2308 for a token known to
  be present. Single-token pattern
  `co-rejecting` — *multi-word `nasctl grep` patterns silently match nothing*; positive-control any
  zero before believing it, every time.
- **Uploader rate limits (S159, not ours to fix)** — from 2026-10-06 to 10-19: WOW answered `Too
  frequent observations` every 15 minutes for 6 hours after the 2026-10-14 21:22 ET restart
  (21:25-03:45), plus about one a day otherwise; Windy answers `429 Too Many Requests` about twice a
  day. Records are simply not published; check after the next restart whether WOW repeats the
  6-hour pattern before considering a `post_interval` change.
- **Humidity-spike watch** — unfired. **Method and arithmetic are in DEC-0044 — do not re-derive.**
- **DEC-0049 phantom-rainRate** — unfired, and **already instrumented**: `soak_check.sh` computes
  `rainRate>0 while rain=0` every run, so this watch needs no manual check. The next calm,
  saturated, cooling night is still the free test.
- **First frost** — the signed decode's negative branch gets its first live air test.
- **DEC-0056 revisit trigger** — a rain-rejection email on a genuinely *wet* day.
- **Upstream replies** — four open threads (lheijst #22/#23, issue #15, david-lutz#1).
  `docs/UPSTREAM-THREADS.md` holds the state and the etiquette.
- **Post-DEC-0135 reception baseline (new S116) — first multi-day read taken, S126.** After the
  fix deploys, read `rxCheckPercent` over several days with no apparatus and no pre-registration.
  **~99% closes the RF question permanently.** **Materially lower (say < 95%) is a real signal** —
  and the first one a campaign could actually resolve, because the ~27% of background pseudo-loss
  that swamped every previous sweep is gone. **This watch is also how blocker 2 becomes measurable:**
  an RF-dead episode currently hides inside that background; against a flat ~99% baseline it stands
  out sharply. Do not read a *pre*-fix figure against a post-fix one — the metric steps ~26 points at
  the deploy (`docs/DATA_ERRATA.md` DISC-0001).
  **S126 read (2026-09-06): every fully-post-v2.0.16 6-hour `RECEPTION SUMMARY` window from
  2026-09-03 18:00 through 2026-09-06 06:00 (ten windows, ~2.5 days) reads `Mean reception: 100%`,
  `Packets dropped (est, lower bound)` 1-12 out of ~7680 per window (0.01-0.16%).** This clears the
  ~99% bar comfortably — the RF question reads closed, not just "not yet reopened." **Blocker 2 is
  still unfired, not resolved**: zero `rtldavis process stalled` lines across `weewx.log` for the
  same window (09-03 through today) — no RF-dead episode has occurred to measure, which is within
  normal variance for an intermittent phenomenon (the pre-fix base rate was ~21 episodes over ~30
  days, roughly one every 1.4 days, clustered) rather than evidence the episodes have stopped. Watch
  continues; re-read after a longer stretch, or immediately if a stall line appears — the flat
  baseline this session measured is exactly what would make the next one stand out.
- **Dependabot** may open a deps PR — review it, never auto-merge.
- **RF-dead pause/resume incident rate (DEC-0087, new S79)** — first fired S81 (2026-08-13
  19:40:05, arm H) and immediately escalated to a hard abort at the 120-min ceiling — not the
  self-resolving case the mechanism was built for, but a bug in it (DEC-0089: `recovered_since()`
  never saw a fresh RECOVERY line despite ~2h of healthy reception). Fixed same session. **S82's
  audit (DEC-0090) then revised the machinery again** — resume at the pause floor (not [OK]),
  rotated-log reads, swaps defer while paused, tick/guard lock — so the rate baseline starts
  from the S82 mechanism; incidents before 2026-08-14 are not comparable. n=0 on the current
  mechanism. The tracking half of DEC-0087's original ask (a future analysis script, same shape
  as `ops/stall_baseline.py`/`ops/freeze_baseline.py`, correlating incident count and
  paused-minutes against time-of-day/arm) stays deliberately deferred until enough
  *correctly-handled* incidents accumulate to be worth reading.
- **NAS-LEASE attribution-log correlation (DEC-0099, new S90)** — the shared `heavy-io.log` now
  carries real acquire/release timestamps (HLF's `daily-maintenance`, live since 08-16); weewx can
  correlate its own `freeze_baseline.py`/`stall_baseline.py` events against it for free, same
  zero-cost method as DEC-0094. **First read, S90: one real lease-held window exists**
  (2026-08-18 00:10–06:10 EDT) — n=1, nowhere near enough to test anything, but it contains both
  one RF-dead episode (02:41, 26.3 min span) and one freeze (03:15–03:22, 420 s). A lead, not a
  finding: a 6 h window is ~25% of a day, so any overlap at all is unremarkable on priors, and this
  does **not** revise DEC-0094's P=0.29 or the RF-stall P=0.32, both measured on far larger n.
  Revisit once enough lease cycles accumulate to test the evening/nightly split against real
  timestamps instead of DEC-0094's fixed schedule — not before HLF's DEC-0173 re-measurement
  settles their renewal floor.

✅ **Dropouts watch is CLOSED (DEC-0067)**, replaced by the process-freeze blocker. **Never re-open
it on a `WINDOW: 0/21` reading**: that metric cannot tell a freeze from deafness, which was the whole
problem. The rule is a >150 s gap **with** `rtldavis process stalled` = RF; silent = freeze.

**Freeze rate is now MEASURED, not eyeballed (S76, DEC-0083): 1.49/day, median 240 s** — 45 freezes
over 30.3 d, against the inherited "~once/day, ~3.5 min", which understates both by ~40 %. Applying
the rule above to archive gaps > 150 s over the full retention window gives 21 RF-dead / 12 arm-swap
/ 45 freeze. **Two traps if this is recomputed:** rows at `interval != 1` must be dropped first (the
S37 backfill wrote `interval=15` rows that read as 28 phantom 900 s freezes and inflate the rate by
~60 %), and the individual events must be printed, not just the summary rate — printing them is the
only reason that confounder was visible. **Working scripts: `ops/stall_baseline.py` covers the
stall half, `ops/freeze_baseline.py` (DEC-0085, S77) now covers the freeze half — both sides are
re-runnable and neither number decays.** First rolling-window placement for the freeze side (never
done before, S77): unremarkable across 24h–72h (36.6–78.3rd pct), moving independently of the
stall side's same-day record-max reading.

**S78 to S84d freeze readings (full text moved to `CHANGELOG-ARCHIVE.md`, "BACKLOG.md resolved and demoted blocks, rehomed S193").**
S78: two back-to-back freezes tripped the 30-min reception floor and aborted the H-hold; STOP cleared the same session.
✅ S79 stall burst plateau confirmed. ✅ S80: the "elevated window" was a measurement artifact, not a trend (DEC-0088; rate 1.54 → 1.31/day).
✅ S84d: the nightly-window lead is refuted (9 vs 7.2, P=0.29); the evening 18:00-21:00 one is real (12 vs 5.0, P=0.0027, DEC-0094). Mechanism still open (`weewxd` stays `S`, never `D`).
Recompute only with the DEC-0088-corrected run.

✅ Closed, do not re-run: **#74 calm-windDir** (S59) · **campaign-A abort near-miss** (S62, DEC-0065
— the abort was correct, DEC-0061's budget holds).

## Why USB resets fire but never work — evidence and the decisive test (S67)

NAS-era investigation, kept as history; the working material moved to `CHANGELOG-ARCHIVE.md` ("BACKLOG.md resolved and demoted blocks, rehomed S193"). Conclusions: `reset_dongle()` logged `syno_vbus_reset` but ran a driver unbind/rebind (message fixed and verified 2026-08-07, DEC-0074); the hypothesis that the consumer's open libusb handle, not the device, was the fault was never established; the decisive test, `ops/usb_forensics.sh`, was built S68 (DEC-0075). Left undecided on the NAS: the escalation ladder never tried a container recreate (DEC-0065 declined to automate it). The NAS-era reset script was retired, not ported, to marvin (MARVIN-DEC-0100).

## USB watchdog: not running since 2026-05-22 — the evidence (S67)

History: the retired `ops/usb_watchdog.sh` (the file no longer exists) was found unsupervised, and the conclusion drawn from that was wrong: `weewx_monitor.py` carried the watchdog function and handled every stall (DEC-0074). Lesson kept: a sha match proves the file, never the process; a watchdog that is not running produces the same log as one with nothing to do. Evidence moved to `CHANGELOG-ARCHIVE.md` ("BACKLOG.md resolved and demoted blocks, rehomed S193").

## Needs a check / housekeeping (moved from STATUS.md, S60)

- **Carry forward, none due (moved verbatim from `BOOT.md` job 6, S199, to keep BOOT under its cap):**
  S126's job-8 items, the lheijst/rtldavis#7 watch, ops#306's residual,
   the local-infra marvin entry, the reset-from-112-or-above phantom, whether to tell the
   `weewx-packages` maintainer about DEC-0218 option B, `git worktree prune` in heartofgold, CI mypy
   pinned `2.3.0` while the pre-commit rev lags, `WEEWX_CONTAINER` unset for the monitor since S159
   (a one-line heartofgold unit edit if the escalation email ever matters), the stale
   `weewx-data/wxcheck.py` on marvin (unused since #570).

- **⚠️ The freeze MECHANISM is still open (DEC-0036) — but the trigger and the fuel are both gone.**
  We never proved exactly which write blocked, and the evidence is gone. Do **not** invent one. What we
  now know for certain: the **trigger** (a bare `docker logs`) is blocked by a hook in both the agent and
  the shell; the **fuel** (StdPrint, ~25 MB/day to stdout) is removed (DEC-0041); and Synology's `db` log
  driver **cannot be size-capped** — it accepts `max-size` and ignores it (measured, and confirmed
  against the literature). If it ever recurs, capture `/proc/1/task/*/wchan` and `/proc/1/fd/*` **before**
  restarting anything.
- **The `db` log driver is uncapped and always will be.** All containers still run on it. That is now an
  accepted risk, not an oversight: the trigger is guarded, weewx's stdout is silent, and `influxdb`
  (~0.5 MB/day) plus HLF/eh-proxy (tens of KB) are not credible wedge candidates. Switching a container
  to `json-file` is the only way to bound its log, and it costs that container's DSM log tab. **Revisit
  only if a container starts generating real stdout volume.**
- **One `rtldavis process stalled` at the v2.0.7 startup (S41) — has not recurred across 2 further
  recreates.** Most likely the USB dongle being re-acquired while the old container was still releasing
  it. S47 added a 3 s `sleep` between `rm` and `run` and came back clean. **Not a blocker** — treat a
  future stall as a one-off unless it shows up on consecutive restarts.
- **NAS boot task fragility (S32):** after the next DSM update/reboot, verify the `weewx_monitor`
  scheduler task still runs as root (symptom: `sudo: a terminal is required` spam, no pidfile).
- **✅ RESOLVED (S126, ops#278) — Campaign B's DSM scheduled tasks, firing until 2026-09-05, never touched anything** (`rx_experiment.state` never left `BASELINE`; the owner unchecked both tasks; Foundation's project directory is deleted, ops#260 step 4). This removes the leading hypothesis for the 2026-08-25 restart below, so that mystery is more open, not less. Full text moved to `CHANGELOG-ARCHIVE.md` ("BACKLOG.md resolved and demoted blocks, rehomed S193").
- **The 2026-08-25 21:40 EDT prod restart has no cause in any artifact this repo keeps (S104).** The
  container stopped 21:40:51 and started 21:47:25 — 6m34s. Reception went 76% → 0%, the monitor
  alerted at 21:45:23, recovery at 21:50:27, episode logged (304 s). Prod healthy since.
  **Ruled out by evidence, so don't re-derive these:** not a host or daemon event (every other
  container's uptime spans it — influxdb 7 d, HLF 4 d, eh-proxy 24 h); not a weewx crash (zero
  `CRITICAL` that day, exactly one `Initializing weewxd`); not a graceful stop (no
  `SIGTERM`/`Shutting`/`Terminating`/`Exiting` — consistent with SIGKILL, i.e. `docker kill`); not the
  restart policy (`RestartCount: 0`, and `Created` still predates it, so it was stopped-and-started,
  never recreated); not the monitor (no `RESET`/`WATCHDOG`/`STALL`/`RESTART`/`ESCALAT` lines at all —
  it observed and emailed, it never acted); not the campaign harness (its log's last entry is 3 h
  earlier); not a USB reset (`usb-forensics/` untouched for two days). **Also ruled out (S126,
  ops#278): the `rx_experiment.sh` DSM tasks** — traced end to end, they could never reach
  `restart_container()` at any point past campaign B's close (see the entry above), so they are not
  the "something" either, closing the one surface this entry used to leave open. **What remains is
  a deliberate external kill+start by something that writes to none of our logs, with no remaining
  candidate on this list.** If it recurs, capture `docker events` if anything is watching — the DSM
  task list is no longer worth checking first, now that its one plausible mechanism is eliminated.
- **⚠️ Off-site backup is a MIRROR, not versioned — now UNBLOCKED, not yet designed (S105).**
  ops#209 established that the DS918+ runs Cloud Sync rather than Hyper Backup, so deletions and
  corruption **propagate off-site**. Two irreplaceable artifacts have no versioned copy anywhere:
  the live station config (only the `.example` template is tracked — deliberately, DEC-0012, since
  this repo is public) and the archive database (the whole record since 2026-05-01). The eight
  `.bak-*` archive copies do **not** cover this: they sit in the same directory on the same volume,
  and they were made to protect against a bad `UPDATE` — which they do — not against volume loss or
  a propagated delete. Not hypothetical for this repo: four retrospective archive corrections have
  been run, so writes to that DB are routine. **The migration this was deferred behind happened
  S105 (DEC-0118)** — weewx now runs on `marvin`, and the design should target that destination
  host. Note marvin already runs **restic** for its own tenants (`MARVIN-DEC-0020`), and a
  `weewx-db-dump.service`/`.timer` (SQLite `.backup` API, 03:15 daily) shipped S105 as the
  incident-driven fix for the *torn-copy* risk in that backup — but that timer's job is
  consistency, not versioning/off-site-ness, and hasn't been evaluated against this line's actual
  ask. Worth checking whether marvin's existing restic repo already closes this gap for free (it
  backs up `/srv`, which now includes weewx's tenant tree) before designing anything new — possibly
  a one-session close now that the blocker is gone, not a fresh design exercise.
- **Docker Hub README auto-sync:** add repo secrets `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` to
  activate `.github/workflows/dockerhub-description.yml` (green no-op until then). Owner action.
- **Snow / freezing / no heating tape** — parked, owner's future thread. 2026 = learning year.
- **Security follow-ups are tracked in the gitignored local-infra doc, not here.** This repo is
  public; operational security state does not belong in it.
- ✅ **No real credential has ever been committed to any of the three repos.** S40 scanned all 333
  blobs for commented credentials (zero); S41 scanned every live config value against the full
  history of all refs in all three repos (zero). One scare — a password apparently in
  `weewx.conf.example` since S16 — was the example's own placeholder. False positive, caught by
  re-checking evidence that looked internally weird (DEC-0047).

## Open ideas

- **Second dongle: RTL-SDR Blog V4 (USB-A), owner-bought 2026-10-30 (S183); arrives in weeks, usable
  from about early December.** Not a plan yet, only the places it earns its keep, to be agreed
  before any hardware moves:
  1. **Test bed for the Python port** (`weewx-packages/weewx-rtldavis`, tester request in #514):
     the port's own README says a second dongle lets it run beside the current stack, so prod's
     receiver stays untouched. This is the cleanest use.
  2. **A/B reception** against the v3 at the same site (DEC-0059's bar and metric), now that the
     current dongle can stay live.
  3. **Compatibility check first:** the V4 uses a different tuner front end (R828D plus an input
     switch) and needs a librtlsdr that knows it. The image bundles librtlsdr from `src.tgz`
     (`Dockerfile`), so confirm V4 support in that tree before any run, and the Go decoder's
     `-d` device selection before the second dongle is plugged into the prod host, or prod could
     enumerate the wrong stick.
  Ops and heartofgold were told the same day (inventory entry, USB port plan).

- **Public-maturity push (S112 audit) — three planned sessions, owner-requested.** Goal: as the fork
  approaches true maturity, make it maximally accessible — clean code/comments, accurate docs,
  proper git accoutrement, minimal and clear public surface. Four parallel S112 audit reviews
  (doc drift, PII/secrets, comment quality, newcomer experience) produced the findings; the PII
  finding shipped immediately as DEC-0127. The rest, staged (full detail in the S112 transcript;
  jobs 3–5 in `BOOT.md`):
  - **Session A — mechanical version/doc sync (Sonnet):** README + Docker Hub banner stuck at
    v2.0.12/ws.4/weewx 5.4 vs live v2.0.14/ws.5/5.5.0; `influx.py` ws.1→ws.2 refs (done S145); no GitHub
    release tag past v2.0.11 while README/SECURITY point at Releases as version truth; CHANGELOG
    has no per-release notes a puller can find; `weewx.conf.example` version stamp + superseded
    `fetch_interval=3600` (adopted: 300); ARCHITECTURE false "last updated" stamp, removed-LNA and
    NAS-path content; broken `usb_forensics.sh` install command (missing `ops/`); README docker-run
    vs docker-compose mount mismatch; CONTRIBUTING describes CI behavior ci.yml doesn't have and a
    `for f in tests/...` loop that silently skips 8 files (pytest should lead); `BIAS_TEE=1`
    default (DC to the antenna!) documented only in a changelog blockquote — needs Quick Start
    prominence.
  - **Session B — code-facing clarity (Opus):** strip internal IDs from RUNTIME-EMITTED strings
    only (monitor alert emails cite ops#233/DEC-0021/DEC-0056 to strangers; driver/monitor log
    lines similar) — comments KEEP their DEC/ERR trailing citations (public, resolvable, and the
    audit judged the prose unusually good; add a notation glossary paragraph to CONTRIBUTING
    instead). Driver docstrings still show upstream defaults (`/home/pi/...`, EU) that produce a
    broken config if copied; three test docstrings cite stale line numbers (cite symbols);
    `test_input_staleness.py:195` has an `... or True` unfailable assertion; `ops/` scripts need a
    one-line internal-vs-user banner each; `Dockerfile:127` claims v2.0.4.
  - **Session C — public-surface reorg (owner + Opus/Fable, needs DECs):** 8 of 14 root docs are
    internal governance, alphabetically ahead of README on GitHub; docs/ has no user-vs-maintainer
    index; `DECISIONS-FULL.md` (544KB) exceeds GitHub's render limit; PR titles are `S###:`-styled
    and issue labels publicly describe model economics (`tier:frontier` = "Fable/Opus"); zero
    topics/homepage/templates on the repo; open #274 is an internal cross-repo memo. Includes the
    privacy-first question of whether the governance corpus (BOOT/BACKLOG/DECISIONS narrating prod
    topology and known weaknesses) belongs in the private ops repo with pointers here.

- ✅ **▶ Where is the ~25% ceiling? — RESOLVED S115 (DEC-0134): there is no RF ceiling.** The Go demodulator's byte-only duplicate filter discarded the ISS's genuine re-sent packets and the pending timer booked each as a `packet missed`: real loss 0.3%, and `rxCheckPercent` under-reported a ~99% link as ~73%. Fix built S116 (DEC-0135, `patch/rtldavis-dupgate.patch` plus `rtldavis.py`; suppress byte-identical re-sends within a 500 ms gate). Real losses that remain: the FHSS neighbour on channels 46–48 (~2 pts, DEC-0133) and the RF-dead runs (blocker 2, ~4 pts on Sep 1). Every ~73% baseline in older docs is stale. The full text and the S113 as-opened list moved to `CHANGELOG-ARCHIVE.md` ("BACKLOG.md resolved and demoted blocks, rehomed S193").

- ✅ **Campaign D — marvin gain pilot — CLOSED (DEC-0128, S113): the curve is flat, the pilot shortlists nothing, the gain axis is exhausted at marvin, gain holds at 372.** P496 74.65 · P449 73.79 · P402 74.98 · P372 74.97 · P328 73.29 · P207 68.17; best delta +0.01 against DEC-0059's 2.0-pt bar. n≈33/arm resolves ~4 pts, one night. D's arms compare to each other, not to B/C absolutes.
- ✅ **Gain re-sweep at marvin's RF position (Campaign C) — CLOSED (DEC-0125, S111): 496 does not clear the 2.0-pt bar at marvin, 372 holds.** 372 72.82% (n=368) vs 496 73.98% (n=350), +1.16 pts; no config change. A short run is a non-answer: a 4 h run resolves ~3.8 pts against the 2.0-pt effect (~7.3 h/arm needed), so do not re-propose one as a cheap version.
- Their pre-registrations, the stopped S105 mini-campaign and the S107 power math moved to `CHANGELOG-ARCHIVE.md` ("BACKLOG.md resolved and demoted blocks, rehomed S193").
- ~~**NAS-LEASE cross-host wiring for marvin (S105).**~~ **CLOSED as overtaken, S125 (DEC-0141/0142,
  docs/INFLUXDB-MIGRATION.md §5.3).** The InfluxDB move means weewx now has zero NAS I/O left to
  yield — the courtesy-yield mount had one purpose (protect NAS-hosted InfluxDB writes from a
  concurrent NAS reader) and that store no longer lives there. `lease_dir` stays set (harmless no-op
  against the empty dir, `MARVIN-DEC-0063`); a later config-only cleanup may drop the key, but the
  cross-host wiring this item asked for will never be built.
- ~~**Hot-swap gain / receive-window without restarting the container (owner question, S89).**~~
  **BUILT S103, [DEC-0117](docs/DECISIONS.md).** Watched control file carrying bounds-checked
  `gain`/`ex` integers only (never a command string — `cmd` reaches `shlex.split()` → `Popen`);
  swap resets the stall-watchdog counters and widens the threshold to 240 s until the first packet,
  which is the hazard the analysis below missed: a respawned child restarts the US 133 s init
  period against a 150 s watchdog the respawn does *not* reset. Plus rollback, an ack file
  recording the measured respawn gap (answers constraint 4 below), and init-time honoring so a
  restart cannot silently revert a swap. **Default off; `rtldavis.py` is BAKED, so this is not in
  prod until an image rebuild.** Still open: converting `ops/rx_experiment.sh` to use it — a
  separate change, and the one that must not land mid-campaign. Original analysis kept below.
- **[CLOSED — built S103, DEC-0117] Hot-swap gain / receive-window without restarting the container (S89).** The original analysis (the trigger was the only gap; constraints; the unmeasured respawn gap) moved to `CHANGELOG-ARCHIVE.md` ("BACKLOG.md resolved and demoted blocks, rehomed S193"). Still open: converting `ops/rx_experiment.sh` to use it (BOOT job; #553). Tracked jointly with ops: [ops#179](https://github.com/WeatheredScientist/eaglehunt-ops/issues/179).
- ~~**Retention policy for the SQLite archive + the InfluxDB `weewx` bucket**~~ — **ANSWERED S87,
  [DEC-0095](docs/DECISIONS.md).** The weewx half of
  [ops#175](https://github.com/WeatheredScientist/eaglehunt-ops/issues/175) is settled:
  **accept-and-monitor, no prune.** Measured 2026-08-17, neither disk nor working set binds by 2–3
  orders of magnitude (archive 33.61 MB = 0.89% of 3.69 GiB RAM, 0.37 MB/day, ~7.3 yr to 1 GB), the
  `archive` table is the *deliverable* rather than a regenerable diagnostic, and upstream's 114
  `archive_day_*` summary tables already bound long-read cost. The reversal condition executes in
  `ops/soak_check.sh` (reopen at 10% of MemTotal, ~2.6 yr out) — don't re-derive it here.
  **InfluxDB half — ops broke the mutual wait with a strawman (accept-and-monitor + a permanent
  daily rollup so dashboard's all-time-record queries survive); weewx answered [DEC-0100](docs/DECISIONS.md):
  decline to build it, recommend dashboard builds it as an InfluxDB 2.x Task** (native scheduled
  Flux; neither write path changes). Not a mandate — if dashboard's build needs something from our
  write side, that's a fresh DEC-0010 conversation, not this one reopened.
- **Tuning infrastructure (owner idea, S34) — control panel and/or designed sweep plan.** Two
  complementary routes to better RF tuning, framing to be discussed in a future session:
  (a) a **front-end control panel** (in this repo or standalone) for live-changing select runtime
  variables — gain first, potentially receiveWindow etc. — without container rebuilds/restarts;
  (b) a **proper sweep plan** with a sufficient number of acquisitions per setting for statistical
  confidence (the 2026-06-01 sweeps and the pending DEC-0017 gain-372-vs-207 question suffered from
  short, unaveraged samples) — possibly better than (a), possibly both. Ties into DEC-0017 and the
  "Reception improvement beyond ~70%" idea below.
- Reception improvement beyond ~70% (noise-floor limited at ~150 ft through walls).
- Windows/macOS FHSS investigation (Docker Desktop USB passthrough findings for the README).
- ESP32 secondary sensor node — lightning (AS3935), pressure (BMP390), air quality (SEN55);
  solar-powered (parts shopping list done).
- Blitzortung lightning integration (System Blue — the detection-network route; longer term).
- **InfluxDB points carry no station identity (DEC-0053 Finding 2) — do NOT "just add the tag."**
  `influx.py` supports `tags = station=...`; the live config sets none, so every point in an
  infinite-retention bucket is anonymous. Adding a tag **forks the series key** (INTERFACES §2), which
  splits historical continuity and needs dashboard coordination. Harmless with one producer; revisit as
  a coordinated interface change if a second producer ever satisfies the contract (PRINCIPLES §1).
- **SQLite archive carries no correction flag (DEC-0053 Finding 3).** InfluxDB corrected points carry
  `rain_qc`/`rainRate_qc`/`backfill`; the archive carries nothing, so a corrected row is
  indistinguishable from a never-corrected one — the derived store is better provenanced than the
  system of record. Only `DATA_ERRATA.md` records it. Not urgent; a schema change isn't justified yet.
- Credential hygiene follow-ups — tracked in the gitignored local-infra doc, not here (this repo is public). Secrets belong in `monitor.env` as env vars, never inline (DEC-0012, DEC-0047).
- ~~Set `STATION_NAME` in the NAS `monitor.env`~~ — **already done, S31** (`STATION_NAME=
  "Eagle Hunt PWS"`, live-verified S56). This note was stale since S31 (dated "observed S27,"
  before the fix); see CHANGELOG-ARCHIVE `[S31]`. Pruned S56.
- Verify OWM (OpenWeatherMap) measurements propagate into their API over time — a post-integration
  sanity check that the uploader's values actually land.
- Long-term stability watch (uptime / reception drift / memory) — no formal monitor yet.
- ~~Reception-metric over-count (DEC-0024)~~ — **SHIPPED in v2.0.8 (S43):** both layers landed
  (monitor counts unique record epochs; driver no longer publishes dataless freqError packets — see
  CHANGELOG `[S43]`, DEC-0024 fully resolved). Pruned S52.
- ~~`weewx.log` bloat from `RAW_*` debug lines~~ — **resolved in practice:** the RAW logging moved
  behind `debug_rtld` levels (2026-07-05 driver change) and prod runs with it off — S52 grepped the
  live log: zero `RAW_` lines. Log rotation is daily and working. Pruned S52.

## Durable RF findings (from 2026-06-01 tuning sweeps) — ⚠️ **DEMOTED S116 (DEC-0135): read the caveat first**

**Every percentage in this section was a repeat fraction, not link quality** (DEC-0134: real RF loss is 0.3%). The findings are demoted from *settled negative* to *untested*, not deleted, and are not worth re-running (~6 pts total headroom against DEC-0059's 2.0-pt bar). The body moved verbatim to `CHANGELOG-ARCHIVE.md` ("BACKLOG.md resolved and demoted blocks, rehomed S193"). Durable one-liners kept here:
- Per-ID loop period is `(41 + id) / 16` s; this ISS is packet id 4 = DIP ID 5 = 2.8125 s (verified S119, #313).
- Site has a reproducible reception notch at hours 07 (deepening to 07–09 during a campaign) and 19 (S58); dew, solar noise and wind are falsified as causes; leading untested hypothesis is a 915 MHz ISM neighbour on a human schedule.
- `-ex N` ≡ `receiveWindow 300 + N` (one axis, S56/DEC-0059); `-maxmissed 15` caused repeated 0/24 windows, do not use.
- "Absent from the log" is not "absent from the program": a suppressed emitter and a missing one look identical (`docs/GOTCHAS.md` §1).

## Data integrity
- ~~May monthly rain totals were noted as compromised by dev restarts; reconcile against the Davis
  WeatherLink Live gold standard once the rain-spike fix lands.~~ — **done S48:** the console
  cross-check corroborated both ERR-0001 and ERR-0002, residual 0.01″ (DATA_ERRATA.md). Same fact
  also corrected in ROADMAP.md this session (S56); this was the last stale copy. Pruned S56.
- ~~[PRIORITIZED — owner, S30] Bad-packet root cause for temp/humidity/radiation/UV spikes~~ —
  **DONE (S33, DEC-0029):** root cause confirmed from the archive (bit-flip corruption passing CRC,
  same class as rain; 18 humidity spikes + impossible UV 16.29; loop-JSON path unfiltered) and fixed
  with the decode-layer `SensorQC` filter + the DewpointCacher timeout-null (closes DEC-0022).
  The S30 `MAX_WIND_DELTA` unit-mismatch lead was disproven (post-StdConvert = mph). Ships with the
  v2.0.4 rebuild. Follow-ups live in DEC-0029/STATUS: cross-sensor consistency checks (UV↔radiation),
  monitor alert on the new rejection signature.
- ~~**[PROPOSED — S98, in response to ERR-0006] Reception-quality-correlated wind guard.**~~
  **DONE S98 (DEC-0110):** measured first (93 days, 129,607 records) — genuine high wind and severe
  reception collapse have never co-occurred at this station, so the design couldn't false-null a
  real gust. Shipped as `dewpoint_service.py`'s `new_archive_record` (`rxCheckPercent<20%` AND
  `windGust>10mph` → null the wind triple + derived fields), 11 new tests including both incidents
  replayed verbatim. Ships with the ~08-23 v2.0.14 build (baked into the image). See DEC-0110.

## Long-term direction (moved from ROADMAP.md's P4 + "Longer horizon", DEC-0058, S56)

Uncalendared or aspirational — direction, not scheduled work. Nothing here needs attention now;
pull an item into ROADMAP.md's P0–P3 when it's actually about to be worked.

- **Credential hygiene follow-ups** — tracked in the gitignored local-infra doc, not here (this repo
  is public). Secrets belong in `monitor.env` as env vars, never inline (DEC-0012, DEC-0047). (Also
  listed under "Open ideas" above — same item, not duplicated content.)
- **Multi-source adaptability** (PRINCIPLES §1): keep the driver re-pointable so non-Davis WeeWX and
  eventually CumulusMX can rely on the same data contract. Record a DEC before any code depends on it.
- **Generic project-template harvest** (separate buildout): once the Governance Standard is proven
  here and propagated once, harvest it into a versioned GitHub *template repository* for all future
  projects (ASSESSMENT.md §5). Copy-not-link; tracked as its own effort, not part of this repo's
  release path.
- **Winter 2027 sky-state instrumentation** ([ops#110](https://github.com/WeatheredScientist/eaglehunt-ops/issues/110),
  opened S56): IR sky sensor alongside the lightning detector, targeted for the Jan–Feb 2027 winter
  build. Cross-repo with the dashboard (`repo:dashboard, repo:weewx, tier:frontier`). Planning
  horizon only — not scheduled.
- ~~**NAS-LEASE courtesy protocol — proposed, NOT adopted**~~ — **OPS-DEC-0107 LANDED 2026-08-15;
  HLF adopted (their DEC-0177, live since 08-16). weewx's own adoption is DEFERRED to the v2.0.14
  window, not declined — [DEC-0099](docs/DECISIONS.md).** The concrete plan (mount `LEASE_DIR`
  read-only at the recreate; `influx.py` checks it and raises `post_interval` while held; the NAS
  image build becomes weewx's first HOLDER) lives in BOOT.md's v2.0.14 queue and DEC-0099's full
  body — do not re-derive it here. S85's four findings (host-side client, in-container lever,
  forbidden tmp+rename idiom, `fcntl.flock()` needs no binary) are folded into DEC-0099 and pruned
  from this entry. Durable at [ops#169](https://github.com/WeatheredScientist/eaglehunt-ops/issues/169)
  (stays open against weewx until the window lands the client).
