# Backlog — weewx-rtldavis

Unordered near-term ideas and durable findings not yet scheduled, **plus long-term/uncalendared
direction** (its own section below, moved here from ROADMAP.md's old P4 + "Longer horizon" at
DEC-0058, S56 — keeps ROADMAP.md down to the actively-sequenced P0–P3 plan). Scheduled work lives
in ROADMAP.md; in-flight work in `BOOT.md`. Carried forward from the pre-governance NAS
`BACKLOG.md`; the open items from the retired root `cleanup_backlog.md` were folded in here (S27,
S23 tail). **The "Open threads" and "Needs a check" sections below moved here verbatim from the
retired `docs/STATUS.md` at S60 (DEC-0063)** — they were never in-flight work, and `BOOT.md` is
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
  aside on the NAS in case of rollback. DEC-0005, CHANGELOG `[S47]`.

## Standing watches — read-only, none of these block anything (moved from BOOT.md, S67)

They live here rather than in `BOOT.md` because a watch is not in-flight work: it fires or it
doesn't, and until it fires there is nothing to do. Check them when something looks odd, or when a
trigger below is plainly satisfied.

- **Co-rejection grep** (DEC-0054): **0 hits through 2026-08-12 (S76), positive-controlled** — the
  identical pipeline returns 2308 for a token known to be present. Single-token pattern
  `co-rejecting` — *multi-word `nasctl grep` patterns silently match nothing*; positive-control any
  zero before believing it, every time.
- **Humidity-spike watch** — unfired. **Method and arithmetic are in DEC-0044 — do not re-derive.**
- **DEC-0049 phantom-rainRate** — unfired, and **already instrumented**: `soak_check.sh` computes
  `rainRate>0 while rain=0` every run, so this watch needs no manual check. The next calm,
  saturated, cooling night is still the free test.
- **First frost** — the signed decode's negative branch gets its first live air test.
- **DEC-0056 revisit trigger** — a rain-rejection email on a genuinely *wet* day.
- **Upstream replies** — four open threads (lheijst #22/#23, issue #15, david-lutz#1).
  `docs/UPSTREAM-THREADS.md` holds the state and the etiquette.
- **Post-DEC-0135 reception baseline (new S116)** — the deliberate replacement for re-running the
  campaigns, and the one thing that decides whether any of them ever come back. After the fix
  deploys, read `rxCheckPercent` over several days with no apparatus and no pre-registration.
  **~99% closes the RF question permanently.** **Materially lower (say < 95%) is a real signal** —
  and the first one a campaign could actually resolve, because the ~27% of background pseudo-loss
  that swamped every previous sweep is gone. **This watch is also how blocker 2 becomes measurable:**
  an RF-dead episode currently hides inside that background; against a flat ~99% baseline it stands
  out sharply. Do not read a *pre*-fix figure against a post-fix one — the metric steps ~26 points at
  the deploy (`docs/DATA_ERRATA.md` DISC-0001).
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

**S78: first observed case of a freeze severe enough to gate the campaign.** Two back-to-back
freezes (240s + 420s, 2026-08-12 19:46–20:02) tripped `rx_experiment.sh`'s 30-min reception floor
and aborted the H-hold; STOP cleared same session, well ahead of the next scheduled swap. The
freeze *rate* itself stayed unremarkable through the event — see `BOOT.md` S78 for the full
reconstruction.

✅ **S79: stall burst plateau CONFIRMED** — fourth flat reading. 48h/72h still exactly record-max
6/6, 24h back to 1 episode (68th pct), no new episode since 2026-08-12 01:36. This is the
confirmation the S76→S78 sequence was watching for; treat the burst as settled unless a fresh
climb reopens it.

**S79: freeze rate's first elevated rolling-window reading** — 48h at 92.5th pct (current 7,
record-max 12), the other three windows (24h/36h/72h) stayed unremarkable. Driven by a same-day
cluster: 4 freezes on 2026-08-12 alone (00:45, 19:46, 19:55, 21:04) landing in the same 48h window
as 2 from 08-11. One window out of four — not a confirmed trend by this doc's own standard, but
the same night as the S78 event above. The 21:04 freeze traced separately: it landed while STOP
was still present from the 19:55:35 abort, so it folds into the S78 event above, not a new
incident. Re-run `ops/freeze_baseline.py` next check for a corroborating second window.

✅ **S80: the "elevated window" was a measurement artifact, not a trend (DEC-0088)** — the flagged
48h window itself had cooled to unremarkable on re-run, but 24h/36h had newly gone elevated
instead. Before crediting that, the freshest event was checked against the tick log and turned out
to be this same session's own abort-recovery restart, not a freeze — `freeze_baseline.py`'s swap
check only knew the fixed 0/6/12/18 schedule, with no way to see an ad hoc restart landing off it.
Fixed and verified directly against the log: the "19:55 freeze" noted just above **is** the
19:55:35 abort's own `RESTORING baseline snapshot` restart, not a second independent event — one
of 7 (of 47) miscounted the same way across the full window. Corrected reading: rate 1.54/day →
1.31/day, all four rolling windows unremarkable (49th–67th pct). Closed — not a trend, and the
tool is more accurate going forward (DEC-0087's pause/resume will keep producing this exact class
of ad hoc restart).

✅ **S84d: freezes split by hour-of-day — the nightly-window lead is refuted, the evening one is
real (DEC-0094).** Run over the 40 DEC-0088-corrected events (07-14 → 08-13) at **zero prod cost**:
`freeze_baseline.py` prints every individual event by design, and those listings survive in session
transcripts, so no fresh sweep was needed — the deferral in `BOOT.md` had priced a *fresh run*, not
the split. **Nightly maintenance window (00:10–04:30, 18.1% of the day): 9 vs 7.2 expected,
P=0.29 — explains nothing**, and median duration inside (240 s) equals outside. **Evening
18:00–21:00: 12 vs 5.0, P=0.0027**; coffee-radar's own ~18:30–20:00 window 7 vs 2.5, P=0.011;
across **10 distinct dates**. That converts DEC-0068's "n=1, not a base rate" into one: **30% of
freezes in 12.5% of the day.** **Two limits, stated:** the evening cluster was found post hoc and
the omnibus X²=30.8 (df=23, crit 35.2) does **not** reject uniformity, so it corroborates DEC-0068's
mechanistic hypothesis rather than proving it independently; and the window pre-dates the campaign,
so a fresh run post-square should confirm. **If this is recomputed, use the DEC-0088-corrected run
only** — three pre-fix runs (1.48/1.54/1.57) also sit in the transcripts, and the positive control
is whether 2026-08-12 19:55 is *absent* (corrected) or *present* (pre-fix). **Mechanism remains the
open half**: `weewxd` stays `S`, never `D`, so "correlates with" is still not "is blocked by".

✅ Closed, do not re-run: **#74 calm-windDir** (S59) · **campaign-A abort near-miss** (S62, DEC-0065
— the abort was correct, DEC-0061's budget holds).

## Why USB resets fire but never work — evidence and the decisive test (S67)

Open. `BOOT.md` blocker 4 carries the summary; this is the working material.

> ✅ **RESOLVED 2026-08-07 (S67) — deployed and verified.** Finding 1's fix is live: the NAS runs
> `97fe334` at the time, matching the then-current `dev` tip, and the monitor restarted as pid 3870 at 19:28 — **two
> hours after** the file landed at 17:10, which is what proves the running process loaded the new
> code rather than merely that the file on disk is right. (A sha match alone proves neither, and
> believing otherwise is what cost this repo 2.5 months — DEC-0074.)
>
> **So reset lines logged from 2026-08-07 19:28 onward are trustworthy.** Anything earlier says
> `RESET: triggering syno_vbus_reset`, an operation that never ran — **when reading historical logs
> for this investigation, treat every pre-19:28 reset line as naming the wrong mechanism.** That
> misdirection is what sent S67 down the wrong path.
>
> The corrected line will not actually appear until the next stall, which may be days out. Nothing
> is pending; the code is right and the process is running it.

**Finding 1 — the log line names an operation that does not happen.** `reset_dongle()`
(`weewx_monitor.py:347`) logs `RESET: triggering syno_vbus_reset`, but it never touches that node.
It shells out to `usb_reset.sh`, which is a **driver unbind/rebind, not a power cycle**:

```sh
echo '1-3' > /sys/bus/usb/drivers/usb/unbind ; sleep 3 ; echo '1-3' > /sys/bus/usb/drivers/usb/bind
```

The retired `usb_watchdog.sh` genuinely did `echo 1 > syno_vbus_reset`. When the logic moved into the
monitor the *action* changed and the *message* did not, so every reset line in every log for months
has named the wrong operation. Fix the message before anyone reasons from it again.

**Hypothesis (NOT established) — the reset treats the device while the fault is the consumer's grip
on it.** Unbind/rebind re-probes the driver without power-cycling the port, so the dongle stays
enumerated (still `devnum 5`, `/dev/bus/usb/001/005`). The stalled consumer is `rtldavis` inside a
privileged container holding an open libusb handle, and nothing in the reset path makes it drop that
handle or restarts it. Consistent with: 3/3 failures 08-06, 9/9 on 08-02, ERR-0005 (host could see
the dongle while `rtldavis` could not claim it), and DEC-0065's note that a container **recreate**
fixed ERR-0005 where `kill`+`start` had not.

> ✅ **The decisive test is BUILT, S68 — see DEC-0075, and do not re-derive its design here.**
> `ops/usb_forensics.sh` brackets every reset with the host USB tree, the container's view via
> `/proc/<pid>/root`, and `rtldavis`'s open fds. **LIVE since 2026-08-09**, deployed and verified
> from merged tip `ad7e5a4`, smoke-tested on the NAS. Blocked on the event alone now (~1/day), so
> the reading of it is genuinely the next session's work, not this material's.

**Also worth deciding:** the escalation ladder tops out at "email a human that the ineffective thing
was ineffective." It never tries the intervention that has actually worked (container recreate).
DEC-0065 declined to automate that while ERR-0005's cause was unknown — coherent, but it means three
failed resets currently produce no further action.

## USB watchdog: not running since 2026-05-22 — the evidence (S67)

> ⚠️ **Read DEC-0074 first. The conclusion drawn from this evidence was wrong.** Everything below
> about `ops/usb_watchdog.sh` being dead is accurate and still stands — but it did **not** mean the
> watchdog *function* was missing. `weewx_monitor.py` carries it and handled every stall. The script
> was a superseded predecessor and is now retired; kept here because the *method* is reusable and
> the failure of reasoning is worth not repeating: nobody checked whether something else did the job.

- **How it was established.** `ops/usb_watchdog.sh` logs `Watchdog started` unconditionally at
  line 32, *before* its `tail -F | while read` loop — so every start writes that line. The complete
  log is **845 bytes** and contains exactly **one**, dated `2026-05-22 16:00:00`. The deployed
  script's mtime is `May 22 16:00`, the same minute: hand-started once, from a shell.
- **Nothing supervises it.** No `/etc/crontab` entry matching watchdog/weewx/rtldavis, and no
  pidfile beside `weewx_monitor.pid` (the monitor has one; this doesn't).
- **NAS uptime 29.6 days** at the check (booted ~2026-07-08), so a loop started in May could not
  have survived regardless. Dead since 07-08 at the very latest.
- **It went unnoticed because its failure is silent by construction** — a watchdog that isn't
  running produces exactly the same log (nothing) as one running with nothing to do.
- **The script is not the problem.** On 2026-05-22 it performed correctly: 3 stalls detected, 2
  resets fired, the middle one properly skipped for the 300 s cooldown. NAS copy is byte-identical
  to the repo — sha256 `fc65a0d7f3fd30a0efd94371bf107a02e63198043b62ff19157f988d03141818`, 1238
  bytes both. **Only supervision is missing.**
- **The claim that hid it:** BOOT read *"deployed and live — NAS copy matches repo tip
  byte-for-byte, zero resets since."* Both literal sub-claims were true and re-verified. The
  conclusion was still wrong: zero resets because nothing was listening, not because nothing needed
  resetting. **A sha match answers "is the file right", never "is the process alive."**
- **Open design call before it can be fixed:** how to supervise it. `weewx_monitor.py` uses
  esynoscheduler with a pidfile and is respawned within ~5 min — the obvious precedent. Restarting
  it is a NAS mutation (Class C, owner-run).

## Needs a check / housekeeping (moved from STATUS.md, S60)

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
- **⚠️ Campaign B's DSM scheduled tasks are STILL FIRING, three days after it closed (found S104).**
  `rx_experiment.log` shows `tick` and `guard` passes every few minutes through 2026-08-25, churning
  `LOCK: breaking stale lock` and `another instance holds the lock`. The state file reads `BASELINE`,
  so **no arm is being swapped and no data is at risk** — but "Campaign B closed, nothing further
  scheduled" was only ever true of the *campaign*, never of the *scheduler*. The two DSM Task
  Scheduler entries created at campaign setup outlived it. **Owner action** — they live in the DSM UI,
  which no read-only tool here can enumerate, so no session can see them from this side.
  **This is also the leading hypothesis for the unexplained 2026-08-25 21:40 prod restart** (see the
  next entry): it is the one thing left on the box still holding a mandate to touch this container.
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
  earlier); not a USB reset (`usb-forensics/` untouched for two days). **What remains is a deliberate
  external kill+start by something that writes to none of our logs** — DSM Task Scheduler is the only
  unexamined surface, and it needs the DSM UI. If it recurs, capture `docker events` if anything is
  watching, and check the DSM task list *first* rather than re-walking the elimination above.
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

- **Public-maturity push (S112 audit) — three planned sessions, owner-requested.** Goal: as the fork
  approaches true maturity, make it maximally accessible — clean code/comments, accurate docs,
  proper git accoutrement, minimal and clear public surface. Four parallel S112 audit reviews
  (doc drift, PII/secrets, comment quality, newcomer experience) produced the findings; the PII
  finding shipped immediately as DEC-0127. The rest, staged (full detail in the S112 transcript;
  jobs 3–5 in `BOOT.md`):
  - **Session A — mechanical version/doc sync (Sonnet):** README + Docker Hub banner stuck at
    v2.0.12/ws.4/weewx 5.4 vs live v2.0.14/ws.5/5.5.0; `influx.py` ws.1→ws.2 refs; no GitHub
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

- ✅ **▶ Where is the ~25% ceiling? — RESOLVED S115 (DEC-0134): there is no RF ceiling.** The Go
  demodulator's byte-only duplicate filter discards the ISS's genuine repeat packets (byte-identical,
  re-sent one hop later, ~27% of transmissions on a wall-clock cadence of its own) and the skipped
  hop lets the pending timer book each one as a `packet missed`. Standalone 15-min run of the
  deployed binary: 295 hops, 81 misses, 80 preceded by a `duplicate packet` line 0.363 s earlier —
  **real loss 1/295 = 0.3%.** `rtl_test` at the Go geometry: zero lost samples. Explains every flat
  axis (gain, window, siting, offset, frequency, host: 72.83 vs 72.82 is the ISS's repeat fraction
  measured twice), the console's single-digit loss, the flat 51-channel histogram, and DEC-0133's
  wall-clock period that moved between nights. **`rxCheckPercent` has under-reported a ~99% link as
  ~73% since the receiver was built.** Path here: DEC-0128 (three axes flat) → 0129 (denominator
  honest, offset dead) → 0130 (ID 4; histogram clustered) → 0131 (46–48 frequency-tied) → 0132
  (spectrum capture) → 0133 (RFI explains 46–48 = ~2 pts; loss periodic in wall-clock time) → 0134.
  Real loss mechanisms that remain, both small: the ~400 kHz-comb FHSS neighbour on channels 46–48
  (~2 pts, DEC-0133) and the RF-dead runs ≥10 (blocker 2, ~4 pts on Sep 1). Raw captures in local
  `ARCHIVE/s115-capture/`.

  **The fix is BUILT — S116, DEC-0135** (`patch/rtldavis-dupgate.patch` + `rtldavis.py`; deploy
  pending). Three corrections to how it was scoped above:
  - **"make `rtldavis.py` tolerate byte-identical consecutive packets" was a no-op as written** —
    the driver already tolerated them. Its `self._last_pkt` guard has been **dead code since it was
    written**: `data` carries `curr_cnt0..3`, cumulative counters that advance on every packet, so
    the comparison was unconditionally true. Rain and `log_humidity_raw` were never at risk. The
    real question underneath was **emit or suppress**, and the call is **suppress** — the payload is
    byte-identical, so forwarding it would add ~37% loop packets, InfluxDB points and loop-JSON
    writes for zero information. `rxCheckPercent` is fixed by the Go change alone; it never depended
    on that guard.
  - **One threshold, not two.** Measured separation is 2.1 ms vs 2.8117 s with **nothing between
    0.05 s and 2.5 s**, so the "< 500 ms / ≥ 1 s" pair collapses to a single 500 ms gate
    (`-dupwindow`), which must stay under the shortest loop period (2.5625 s, id 0).
  - **The build-host question is ANSWERED:** `marvinctl build <path> -t <tag>` is a tier-2
    own-resource verb — self-service, no NAS, no `docker save`/`load`. `/srv/docker/weewx/` already
    carries the whole `build-v2.0.4 … build-v2.0.14` tree.

  Also verified this session, closing the one alternative DEC-0134 had not ruled out: the long-gap
  duplicates are **fresh receptions, not buffer replays** — 80 of 80 carry their own correlation
  magnitude and symbol vector, on a different channel after a retune. Every ~73% baseline here, in
  `docs/ROADMAP.md`, and in the dashboard's thresholds is stale (dashboard via eaglehunt-ops#256,
  DEC-0010) — **and so is the reception-quality-correlated wind guard proposed under
  `ERR-0004`/`ERR-0006`**, whose "9.2% / 13.2% against a 60–90% baseline" discriminator is stated in
  the pre-fix scale (see `docs/DATA_ERRATA.md` DISC-0001). Upstream issue/PR to `lheijst/rtldavis`
  drafted in `docs/upstream/`, posted only on a go (`docs/UPSTREAM-THREADS.md`); the patch header is
  already most of it. Items 2/4/5/6 below are moot; kept as opened, S113, for the record.

  *(as opened, S113)* Three independent axes are now measured flat at ~73–75%: tuner gain
  (328–496, campaign D, spread 1.70 pts), receive window (`-ex` 0 vs 50, +0.45 and −0.06 pts,
  campaigns A/B — and larger windows are *worse*, rw400 ≈ 63%), and **physical siting** (DEC-0118
  moved the receiver measurably closer with fewer walls; 372 went 72.83 → 72.82 and 496 went
  74.83 → 73.98). A link that ignores a 168-count gain range *and* a materially better path is not
  SNR-limited. **Stop looking for a setting; find the ceiling.** Cheapest first:

  1. **Is the denominator honest? (free, local, read-only — do this first.)**
     `max_count = period // loop_times[x]` (`rtldavis.py:1622`) counts *every* ISS transmission with
     no discount for the 51-channel frequency hop or for re-acquisition after one. If the receiver
     structurally cannot be on-channel for some fraction of transmissions, part of the "missing 25%"
     is **definitional, not lost data**, and every other item here is moot. The driver already emits
     the per-transmitter breakdown — `ARCHIVE_STATS: station N: max_count=… count=… missed=…` at
     debug level — so this needs one debug window and arithmetic, not a campaign. Also confirm
     `loop_times[x]` is indexed by the right transmitter id for our single-ISS setup.
  2. **Rule out the known decoder defects as the cause — they point the wrong way.** DEC-0035's
     double-decode (~722/day) *inflates* `count`, so it makes `rxCheckPercent` read high, not low;
     it cannot explain a deficit. Recorded here so it is not re-proposed as the mechanism.
  3. **`ppm` / `fc` by MEASUREMENT, not by sweeping (free, read-only — closes blocker 4 without a
     campaign).** The `FreqError` telemetry exists and is confirmed live (S57 Phase 0, DEC-0024),
     and the archive carries the remapped freqError columns the S58 notch work already used. Pull
     the distribution and look for a systematic non-zero centre: if it is centred, the axis is
     **dead** and blocker 4 closes on evidence; if it is offset, set `ppm` once by arithmetic. The
     prior is that it is centred — **AFC is on by default** (`-noafc` defaults false) and hour 06
     has excellent reception (~75%) at the *highest* measured freqError, so the AFC is visibly
     absorbing the offset. That prior is exactly why this must be measured rather than swept: a
     sweep would cost a campaign to learn what one query can tell us.
  4. **`-noafc` — the last untested binary flag, and a low prior.** If the AFC is absorbing offset
     (item 3's evidence), disabling it should *hurt*. Worth an arm only if item 3 finds an offset
     the AFC is failing to track. Not worth a campaign of its own.
  5. **Narrower receive window (< 300 ms) — the one untested direction on a wash axis.** Needs
     negative `-ex` (unvalidated; may produce a negative loop period) or a rebuild. Both tested
     directions were flat-to-worse, so the prior is poor and the cost is real. Low.
  6. **LNA back in — low prior, and the flat curve is the reason.** More front-end gain is what
     campaign D just showed does nothing. An LNA improves *noise figure* rather than gain alone, so
     it is not strictly the same axis, but a link that is demonstrably not noise-limited is the
     wrong place to spend a hardware change with a bias-tee risk attached.
  7. ~~**Spectrum capture, 924.5–927.5 MHz (added S114, DEC-0131).**~~ **DONE — S114 ran it
     (DEC-0132), S115 cross-referenced it (DEC-0133): an FHSS neighbour on a ~400 kHz comb explains
     channels 46–48 exactly once the ±134 kHz passband is applied, and the whole cluster is ~2 pts.
     Closed by DEC-0134.**

  **What this item is not.** It is not a licence to re-sweep gain (closed, DEC-0128) or to re-run
  the receive-window axis (a wash, twice). Items 1 and 3 are both free and read-only; neither
  touches prod; between them they either explain the ceiling or retire the last CLI knob. Do those
  before proposing anything that costs a night of production.

- ✅ **Campaign D — marvin gain pilot — CLOSED (DEC-0128, S113): the curve is flat, the pilot
  shortlists nothing, and the gain axis is exhausted at marvin.** Ran exactly as pre-registered
  below — six 45-min blocks HIGH→LOW, 2026-08-31 21:01 → 09-01 01:30 ET, no aborts, self-terminated
  and restored prod at 01:30:39. **P496 74.65 · P449 73.79 · P402 74.98 · P372 74.97 (incumbent) ·
  P328 73.29 · P207 68.17.** Gain 328–496 is one plateau: 1.70 pts of spread against a ~1.61-pt
  per-arm SE, best delta **+0.01**, nothing near DEC-0059's 2.0-pt bar. Per the pre-committed
  reading below, a pilot that selects no arm selects no arm — **the multi-day confirmatory campaign
  this list held open is withdrawn, not deferred.** 207 is the one separable result (−6.80,
  t=−3.75) and is consistent with the LNA being out since 08-02 (campaign A's near-parity for 207
  was LNA-in; DEC-0017's "207 optimal" is a with-preamp finding). Gain holds at 372, no config
  change, `SCHEDULE=` stood down. Caveats on the record in DEC-0128: D's absolute level runs ~2 pts
  high because it deliberately sat in the site's best hours, so **D's arms compare to each other,
  not to campaign B/C absolutes**; n≈33/arm resolves ~4 pts, so a 2-pt effect is not excluded, only
  a large one; one night. *Original framing, kept:* triggered directly by Campaign C (DEC-0125) —
  496 lost to 372 at marvin after winning at Foundation, which means Foundation's pilot-derived
  shortlist {372, 496} was never actually validated as the right *candidates* for marvin. This
  re-ran the shortlisting step, at marvin, and found the shortlist empty.

  ### ▶ PRE-REGISTERED, S111 (2026-08-31) — written before any data exists

  - **Six gain-only blocks, HIGH → LOW: 496, 449, 402, 372, 328, 207.** `-ex 0` fixed throughout
    (found inert, Campaign B). The first five reuse Foundation's own original pilot points — real
    R820T2 hardware steps, directly comparable to that curve. **207 is added**: Campaign C dropped
    it from the square on a Foundation-only judgment ("known-worst there, barely separable") — the
    same shape of assumption that just failed for 496, and 207 has zero data at marvin.
  - **HIGH → LOW, not randomized or notch-balanced.** Matches Foundation precedent, and is a
    deliberate safety choice for a pilot specifically: if a weak low-gain arm hits the abort floor
    and kills the run, the higher/more-likely-useful arms are already harvested. A pilot is
    arm-selection input only (PRINCIPLES §3) — it does not need campaign C's Latin-square-grade
    drift/notch balancing; strict monotonic order is the right trade here, not a shortcut.
  - **45-min blocks, 4h30m total (21:00 → 01:30 ET).** Matches Foundation's original pilot cadence
    exactly — pilot-grade duration, not adoption-grade. Starts well clear of the site's known notch
    hours (07-09 and 19 — 19 is Foundation's own finding, kept as a conservative inclusion since
    marvin hasn't been separately characterized at that hour) and finishes well before them too,
    even crossing midnight.
  - **Metric: per-minute `rxCheckPercent` via `ops/campaign_analyze.py --campaign D`** — the
    sanctioned DEC-0069 readout, now pullable immediately after the pilot closes: `marvinctl exec-ro`
    works end-to-end (ops#235, fixed and verified same day as this pre-registration), no
    owner-mediated wait this time.
  - **Live in `ops/rx_experiment.sh`'s `SCHEDULE=` block**, machine-checked by
    `tests/test_rx_experiment.py`'s campaign-D structural tests (arm order/gains, cadence, notch
    clearance, self-termination, no stray hold/square arm).
  - **Pre-reqs before launch:** a fresh hands-off-guest declaration (MARVIN-DEC-0088's window
    lapsed with Campaign C's close), `logs/campaign.inhibit` for the duration so the monitor doesn't
    fight per-arm restarts, monitor confirmed still healthy.
  - **No USB-reset safety net, and none needed.** Foundation's `usb_reset.sh` was retired, not
    ported, to marvin (MARVIN-DEC-0100) — the fault it existed for doesn't recur on marvin's
    CPU-attached xHCI placement (DEC-0064, 0 lost samples/million measured). Each arm swap already
    restarts the container, giving every gain a fresh driver acquisition regardless.

  **Pre-committed reading of the result.** This is arm-selection input only — it does not itself
  decide anything (same doctrine as Foundation's own pilots). Output feeds which two (or more)
  values go into a real confirmatory campaign, if the question is judged worth pursuing further.

- ✅ **Gain re-sweep at marvin's RF position — CLOSED (DEC-0125, S111): 496 does not clear the
  2.0-pt adoption bar at marvin, 372 holds.** Campaign C ran the pre-registered design below exactly
  as planned; ops#235's stdin-pipe fix landed same-day and unblocked the sanctioned per-minute
  readout. Real result: A (372) 72.82% (n=368) vs B (496) 73.98% (n=350), **+1.16 pts** — smaller
  than the coarse 5-min proxy's +1.87 lean, still under the bar. Per the pre-committed reading below,
  this is the "does not clear" outcome: no config change, and the finding is that Foundation's
  DEC-0115 answer doesn't transfer to marvin's site, not that DEC-0115 was wrong for Foundation.
  Design, pre-registration and power-check detail kept below for the record; **a real multi-day
  campaign remains an open idea if this question is worth resolving further** — not owed as a
  follow-up from this result.

- ~~**Gain re-sweep at marvin's RF position — mini-campaign launched, STOPPED CLEAN at 01:08:16 ET for
  an unrelated higher-priority marvin event; TREAT AS NO DATA, deferred to post-Phase-4-bind
  (2026-08-29, S105 same night).** DEC-0115 adopted 496 on Foundation's own Campaign B square; the
  host move (DEC-0118) put the receiver at a measurably closer, fewer-walls position, and the
  incident that night tried 372 without a controlled comparison (the actual defect was a USB
  controller, not gain).
  **What ran:** launched 01:01:20 as a self-driving script (transient systemd unit on marvin,
  `weewx-gain-campaign`), arms 207/372/496 × 2 non-adjacent reps, 45 min dwell, exit-trapped to
  restore gain 372 + restart weewx regardless of outcome. **Stopped 6.5 minutes into block 1 (arm
  207)** — the owner overrode Phase 4's soak gate and ordered the GPU passthrough bind the same
  night ("this build is not Foundation, we are stress testing it"), and the campaign yielded the box
  cleanly rather than compete with it. The exit trap worked exactly as designed: gain back to 372,
  weewx restarted, full record in the results log. **~6.5 minutes of one arm is not partial data —
  treat the whole night as zero data points**, not a truncated-but-usable set.
  **Re-run deferred to POST-BIND, not just "next quiet night" — marvin's own recommendation, and it's
  right.** Passing the GPU to the guest changes the box's RF/EMI environment (a GPU under load next
  to the antenna's USB port cluster) — a campaign run now would measure an environment already
  scheduled to change again, making the data stale before it's even analyzed. Expect a host reboot in
  the following hour(s) as part of the bind; weewx will go down and reacquire after — **not a new
  incident**, don't chase it as one.
  **Design carries forward as-is** (arms, dwell, exit-trap, non-adjacent-rep reasoning — see the
  git history of this line for the original full rationale, not re-typed here) — **the self-driving
  script pattern is proven and reusable**, kept in a marvin session's records, redeployable on one
  owner approval whenever the post-bind environment is stable. **Still explicitly NOT
  adoption-quality when it does run** — one night, unreplicated, no multi-day averaging (PRINCIPLES
  §3's own bar); a directional prior for a real follow-up campaign, not a replacement. The DEC-0117
  hot-swap control file makes that real campaign cheaper than either prior one was, once it's
  actually in prod (`BOOT.md` job 3).

  ### ▶ PRE-REGISTERED, S107 (2026-08-30) — written before any data exists

  **Bind is done** (marvin, final since 08-29, confirmed by a marvin-side session), so the post-bind
  gate is satisfied. **The owner asked for a 4-hour run this morning and it was declined on this
  repo's own power math** — that refusal is part of the record, not a footnote:

  | design | time/arm | detectable (80% power) |
  |---|---|---|
  | 4 h, 2 arms | 2.0 h | ~3.8 pts |
  | 4 h, 3 arms (the S105 design) | 1.3 h | ~4.7 pts |
  | **effect of interest** | — | **2.0 pts** |

  DEC-0059 measured 24 h/arm resolving 1.1 pts; scaling gives ~7.3 h/arm to reach 2.0. Derived a
  second, independent way (implied 6 h-block sd ≈ 0.56 pts → 1.67 pts at 40-min blocks) to the same
  answer. A 4 h run returns "no difference" nearly regardless of truth. **Do not let a short run be
  re-proposed as a cheap version of this one — it is not a weaker answer, it is a non-answer.**

  - **Arms: 2 — gain 372 vs 496.** 207 is dropped, deliberately: at Foundation it was the known-worst
    and barely separable (S66: 207 arms 73.87 / 74.17 vs 372's 74.81, spread 0.94 pts), it is not a
    live candidate, and a third arm costs ~40% of the power on the question actually being asked.
  - **15 h total, 90-minute blocks, 5 per arm.** Block size is a real trade, not a default: each
    switch is a container restart (driver init up to 133 s), so 10 switches at 90 min loses ~3% of
    the window while 20 at 45 min loses ~7% and doubles the disturbances; going longer than 90 min
    buys little and shrinks the block count the variance estimate rests on.
  - ~~**Order `A B B A B A A B B A`** — balanced against linear time drift (index sums 28/27 vs an
    ideal 27.5), claimed to make the hour-07 notch land on both arms.~~ **WRONG, corrected the same
    day, before any data (S107).** Laying the blocks against the actual clock disproved the claim:
    the notch is not one hour but **hours 07–09, deepening to 2–3.5 pts during a campaign** (§Durable
    RF findings, S58) — *larger than the 2.0-pt effect*. Under that order blocks 8 **and** 9 were both
    B, putting **1.67 of 2.0 block-equivalents of notch exposure on gain 496**, the arm expected to
    win, against 0.33 on 372. It would have manufactured a false negative and looked clean doing it.
    Balancing linear drift is not the same as balancing a localized dip, and the first draft
    confused the two.
  - **Order `A B B A B A A B A B`** (A=372, B=496), start **2026-08-31T20:00**, terminator
    **2026-09-01T11:00|BASELINE**. Splits notch exposure **exactly 1.00 / 1.00** block-equivalents
    while keeping drift sums at 27/28 — both balances hold at once, neither traded for the other.
    A 15 h overnight window cannot dodge both notches (19:00 and 07–09 are 12 h apart), so the order
    absorbs the notch rather than avoiding it. Live in `ops/rx_experiment.sh`'s `SCHEDULE=` block.
  - **The balance is machine-checked, with a positive control.** `tests/test_rx_experiment.py`
    asserts notch exposure, drift sums, block spacing and run length for campaign C — and a control
    test asserts that the *originally* pre-registered order still reads as lopsided. If that control
    ever passes, the check has lost its teeth and the shipped order needs re-deriving rather than
    trusting (this file's own `test_old_global_regex_is_destructive` tradition).
  - **Discard the first 5 minutes of every block** (driver init + archive alignment). At
    `archive_interval = 60` a block yields ~85 usable per-minute records.
  - **Metric: per-minute `rxCheckPercent` via `ops/campaign_analyze.py`** — the only sanctioned
    readout (DEC-0069), including its gap-adjacency exclusion for freeze contamination (DEC-0067).
    Not the WU-publish scrape, which measures publish liveness (S31).
  - **Exit trap: restore gain 372 + restart weewx regardless of outcome**, and remove the inhibit
    file. S105's trap worked exactly as designed under an abort; keep it identical.
  - **Create `logs/campaign.inhibit` for the duration** (DEC-0120). The monitor is not deployed yet,
    so this is belt-and-braces today and load-bearing the next time.
  - **Abort floor: sustained reception below 50%** → abort and restore, matching Campaign B.
  - **Declared confound, recorded not controlled: the GPU.** The 2070 now lives in the win11 guest
    full-time and is driver-active even at idle; owner gaming is ad-hoc and unschedulable. **This run
    needs an owner hands-off-the-guest declaration for the window.** If the guest is used anyway, the
    affected blocks must be recorded and excluded — never silently averaged in.
  - **Deployment needs a marvin-side session** — this repo has no arbitrary file write on marvin.

  **Power re-checked against marvin's OWN measured noise, not Foundation's (S107, same day).** ~15 h
  of post-bind gain-372 telemetry already existed in the archive; read out as 40-min block means
  (23 blocks, 21 full; owner-run query, relayed by a marvin session). **`NULL_COUNT` was 0**, so no
  freeze-signature exclusion applies to that window by `campaign_analyze.py`'s own criterion.

  - Measured **block sd = 1.403 pts at 40 min** → **0.936 pts at 90 min**. That is **0.84× the sd
    implied by Foundation's DEC-0059 figure** — marvin is slightly *quieter*, so the design above was
    sized conservatively and holds with margin.
  - **The planned 5 × 90 min/arm (15 h) gives an MDE of ~1.66 pts against the 2.0-pt bar.** It clears
    it rather than scraping it; 15 h is sufficient, not marginal. Going to 18 h buys only 1.51.
  - **Mean reception at marvin, gain 372: 73.88%** (range 70.03–75.94 across the 21 full blocks).
    Set against Campaign B's Foundation figures — 372 → 72.83%, 496 → 74.83% — **marvin at 372 is
    already within ~0.95 pts of Foundation at 496**, and ~1.05 pts above Foundation at 372.
    Uncontrolled cross-environment comparison, so a prior and nothing more; but it is a prior that
    cuts against assuming 496 will repeat its 2.00-pt win here. **Do not treat that as a result** —
    it is the reason to run the campaign, not a substitute for it.
  - **Incidental, worth its own look later: zero gaps in ~15 h.** Blocker 1 records freezes at
    1.31/day (median 240 s) — a NAS-era measurement — which predicts ~0.8 in a window this size.
    One clean window is far from evidence, but it is the first post-migration data point on that
    blocker and it points the right way. Flagged, not concluded.

  **Pre-committed reading of the result.** Even at ≥2.0 pts this is one night, unreplicated, and
  therefore *directional* — it does not by itself re-open or re-confirm DEC-0115 as adoption
  evidence. Prod currently runs 372 while 496 is the adopted value (the 08-29 incident set 372
  without a controlled comparison; owner's call is to hold it until measured). So the two honest
  outcomes are: **496 clears the bar** → restore the adopted value with a same-position measurement
  behind it; **it does not** → the interesting finding is that marvin's position changed the answer,
  which earns a real multi-day campaign rather than a config change.~~ **It did not clear
  (DEC-0125, S111)** — see the ✅ entry above.
- **NAS-LEASE cross-host wiring for marvin (S105).** `influx.py`'s courtesy-yield mount (`/nas-lease`)
  points at a deliberately empty local directory on marvin (`MARVIN-DEC-0063`) rather than a live
  share of the NAS's real lease file — a permanent, silent no-op by design until someone builds the
  cross-host path. Low priority: the mechanism fails open (never blocks/delays anything if absent),
  and marvin currently has no other heavy-I/O tenant competing with weewx for shared storage anyway.
  Worth closing once that changes.
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
- **[CLOSED — see above] Hot-swap gain / receive-window without restarting the container (S89).**
  Asked while looking at how much restarting campaign B does. **Answer: nothing prevents it but
  the feature itself, and most of the machinery is already built.** Gain is only a CLI flag on the
  Go binary, carried inside the `cmd = /usr/local/bin/rtldavis -gain NNN ... -ex N` string in the
  mounted config. **`rtldavis.py` has no concept of gain at all** — `grep -i gain` returns five
  hits, four of which are the word "a*gain*st" and the fifth a comment documenting the flag; the
  driver passes the string to `Popen` and never looks inside. And the swap path exists:
  `ProcManager.startup(cmd, …)` takes the command **as a parameter**, `shutdown()` kills and reaps
  the child (ws.5), and that kill→respawn cycle is already exercised routinely by the driver's
  150 s watchdog — DEC-0081 confirmed it "fires and respawns correctly", three times in one night.
  **The whole gap is the trigger**: the config is read once in `__init__`, `self.cmd` is assembled
  once, and there is no runtime reload or control channel. A hot swap is `shutdown()` → rewrite
  `self.cmd` → `startup()`, plus something to ask for it (a watched control file or a signal).
  **The prize is larger than skipping a restart:** `-ex` rides the same string, so *both* axes of
  the 2×2 square could swap with no container touch — which would retire the **600 s settle
  window** (currently discarding 10 min of every 6 h block, ~2.8% of campaign data), remove the
  restart transient as a confound (settle times measured 79–198 s vs seconds for a child respawn),
  and eliminate the **abort-on-unhealthy-swap failure class** that has already cost real blocks
  (DEC-0082's +24 h shift; the S79 incident behind DEC-0087).
  **Constraints, so nobody starts this at the wrong moment:** (1) **not during campaign B** —
  changing the swap protocol mid-square breaks comparability, the exact confound DEC-0064's
  fixed-slot design exists to prevent; revisit once the square closes (~08-23) *and* the gated
  v2.0.14 queue has cleared. (2) The Go binary sets gain **only at startup** — there is no runtime
  control channel in the binary, so this is a child respawn, not a live `rtlsdr_set_tuner_gain()`.
  (3) It widens the vendored fork (`CHANGES-FROM-UPSTREAM.md`), though it looks upstreamable.
  (4) **Unmeasured:** how fast the RTL-SDR device re-opens after a deliberate SIGKILL under normal
  conditions — the watchdog does exactly this today so it works, but the gap length is unmeasured,
  and DEC-0081's "respawned children stay silent" finding is *episode-specific*, not normal
  operation. Don't conflate the two. Needs a DEC and approval before code (PRINCIPLES §8).
  Tracked jointly with ops: [ops#179](https://github.com/WeatheredScientist/eaglehunt-ops/issues/179).
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

> **Every percentage in this section is a repeat fraction, not link quality.** DEC-0134 showed the
> ~25% these numbers were measuring was the demodulator discarding the transmitter's re-sent packets
> and booking each as a miss; real RF loss is **0.3%**. So these findings no longer "guide P2" —
> P2 is closed, and there was never an RF problem to optimize.
>
> **They are demoted from *settled negative* to *untested*, not deleted.** DEC-0134's line that the
> campaigns' negative results "remain valid as don't-re-sweep evidence" is **withdrawn as too
> strong** (DEC-0135): a flat result from an insensitive instrument is not evidence of flatness, and
> campaign B's own run-to-run scatter (sd 8.47 at 496, sd 4.67 at 372) exceeded the entire real
> signal. What survives is the *relative* comparisons made on one tool and one metric — they were
> measured honestly, they just answer a smaller question than anyone thought.
>
> **They are still not worth re-running:** ~6 pts of total headroom (0.3% + ~2 pts channels-46–48
> RFI + ~4 pts RF-dead runs) against DEC-0059's 2.0-pt bar, both mechanisms identified and neither
> gain-responsive. Re-baseline by observation instead — see `docs/ROADMAP.md` P2, Campaign D's
> closing note.

**What campaign A says about the LNA — hold it loosely (moved from BOOT.md, S67):**
- **Recomputed at S66 on per-minute `rxCheckPercent` (DEC-0069):** arm A (372/ex0) **74.81%** ·
  C (372/ex50) 74.37 · D (207/ex50) 74.17 · B (207/ex0) 73.87. Spread **0.94 pts** — no arm anywhere
  near the 2-pt adoption bar.
- **Campaign B's 372 anchor must be read against arm A's 74.81%, on the same tool and metric.**
  `ops/campaign_analyze.py` is what guarantees that. The older 72.4% figure is a monitor-scrape and
  runs ~1.9 pts low — **never mix the two**.
- ~14 h of LNA-out at gain 372 gave 72.6% with no hour-07 notch. **Suggestive only — do not conclude
  futility from it.**
- A's winner was meant to stay sealed until after B; S66's tool validation unsealed it as a side
  effect of validating the tool, not as a decision (DEC-0069 sealing note).

**Site has a reproducible twice-daily reception notch at hours 07 and 19 (S58, 2026-08-01):**
- **The observation.** Archive `rxCheckPercent` binned by local hour, 07-24→07-29 (pre-campaign,
  n≈355/hour): **hr 07 = 72.6%, hr 19 = 72.7%**, against **74.2–75.6%** for every other hour.
  During the campaign the morning notch deepens to hours 07–09 at ~2–3.5 pts down, and it produced
  the campaign's single worst minute so far (07-30 08:00, `rxCheckPercent` **min 4.9%** — the same
  event the monitor logged as a 26% 5-minute sample, so **two independent metrics corroborate it**).
- **It predates the campaign**, so it is a property of the site/hardware, not of any experimental arm.
  This is what amends DEC-0059's "no detectable diurnal cycle" (true at 6 h resolution, false at 1 h).
- **Three explanations tested and FALSIFIED — do not re-propose them without new evidence:**
  - *Dew / wet vegetation* — backwards. The dewiest hours (temp−dewpoint spread 2.4–4.0 °F
    overnight) carry the **best** reception (~75%).
  - *Solar RF noise* — backwards. Radiation peaks midday (750–950 W/m²) where reception is normal;
    the notch sits at 35–144 W/m².
  - *Wind / foliage movement* — the **deepest** notch (07-31) occurred on a **zero-wind** morning.
- **`freqError` thermal drift is REAL but is NOT the mechanism.** Measured on our own hardware via
  the archive's remapped freqError columns: it tracks temperature strongly and inversely —
  **~2400–2600 at 65–69 °F → ~900–1200 at 77–84 °F**. But hour 06 has excellent reception (~75%)
  at the *highest* freqError, so the AFC is evidently absorbing the offset; reception tracks neither
  the level nor the rate of change monotonically. Useful characterization of the dongle, not an
  explanation of the notch.
- **Leading untested hypothesis:** a 915 MHz ISM-band neighbour on a human schedule — smart-meter
  reporting windows, garage/vehicle remotes on a commute cycle. A **07:00 and 19:00** pair that is
  temperature-independent and stable for weeks looks behavioural rather than physical. Testing it
  needs a spectrum capture during the window, which we have no instrument for today.
- **Does NOT threaten the RX campaign:** the notch is time-of-day-linked and arm-independent, and
  the Latin square gives every arm the same exposure to it. It inflates variance, it does not bias
  the comparison.

**CLI timing sweep (baseline, -ex 25/50/75/100, -maxmissed 25, combos):**
- All clustered ~63–66%; no material improvement over baseline.
- `-maxmissed 15` caused repeated 0/24 windows — **do not use**.

**receiveWindow — and `-ex` is the SAME AXIS (S56, DEC-0059):**
- **`-ex N` ≡ `receiveWindow 300 + N`.** Upstream sums them — `int64((receiveWindow + ex) * 1000000)`
  — and `receiveWindow` appears nowhere else in `main.go` (verified in lheijst/rtldavis master, S56).
  So the window axis is reachable from the **mounted** `weewx.conf`, with no image rebuild. The
  `rw250/rw350/rw400` images were not merely misnamed (DEC-0048) — they were **redundant**.
- That also means the two findings below are one axis measured twice, and they agree: the CLI sweep's
  `-ex 100` and the `rw400` image are the same configuration, and both landed ~63%. Independent
  corroboration of the equivalence.
- rw400-test (300ms → 400ms): ~63%, **worse** than baseline ~65%.
- Larger receiveWindow is not supported by evidence so far. **Untested direction: narrower than 300**,
  which needs negative `-ex` (unvalidated — could produce a negative loop period) or a rebuild.
- **Caveat on provenance (S56) — HALF FALSIFIED, S113.** The equivalence was read from upstream
  *master*, and the deployed source had not been read directly. **Both of those are now fixed, and
  the evidence offered for "demonstrably older" was wrong.** The startup settings line
  (`tr=… gain=… ex=… receiveWindow=…`) is **not absent** — it is emitted by the deployed binary and
  was simply invisible, because the driver routes unrecognized Go stderr to `logdbg` and DEC-0043's
  `[Logging]` block pins the `user` logger to INFO. Raise that logger and it appears immediately:
  `tr=16 fc=0 ppm=0 gain=372 maxmissed=51 ex=0 receiveWindow=300 actChan=[4] maxChan=1`.
  **Lesson, and it is this repo's own recurring one: "absent from the log" is not "absent from the
  program" — a suppressed emitter and a missing one look identical** (`docs/GOTCHAS.md` §1). The
  deployed source has since been read directly (S113, publicly fetchable via `Dockerfile:46`) and
  is version 0.15; whether it diverges from master on the `-ex`/`receiveWindow` sum should be
  re-checked against that source rather than inferred from a log absence.

**Gain, from the retired sweeps (kept because the scripts are gone, S56):**
- `fc_sweep.sh` held gain at 207, its header recording it as "confirmed best from gain sweep" — a
  pre-governance, unaveraged result, and the only surviving trace of that claim now the scripts are
  deleted. Consistent with DEC-0017 (207 optimal *with* the preamp). Weak evidence, but it is the
  directional prior the DEC-0059 campaign tests properly.

**FreqError — re-checked S56, still not visible.** Grepped the live `weewx.log` and the container
stdout for `FreqError` at the current `debug_rtld = 1`: **zero hits**, positive-controlled (a
`duplicate` grep on the same file returns hits). So the S21 observation below is not reproducible at
the current debug level. DEC-0059's Phase 0 raises `debug_rtld` to 2 for a few hours to settle
whether the telemetry exists at all — if it does, `ppm`/`fc` get set by *measurement* rather than by
sweeping; if it does not, that axis is dropped. Note AFC is on by default upstream (`-noafc`
defaults false), which likely absorbs offset anyway.

**FreqError / ppm-fc telemetry gap — SUPERSEDED by live evidence (S21):**
- ~~The compiled Go binary emits neither `ChannelIdx` nor `FreqError`.~~ **Contradicted:** the
  *running* binary emits **both** — live `weewx.log` shows `ChannelIdx:37 … FreqError:2765
  Transmitter:4` (S21, DEC-0024). Either the deployed binary changed since this finding, or the
  original `strings` check was against a different/stale binary. **Re-verify** `strings
  /usr/local/bin/rtldavis` in the live container and reconcile with the running image tag
  (rw250-test) — this matters because the emitted `ChannelIdx`/`FreqError` is what drives the
  DEC-0024 reception over-count.
- Upside if confirmed genuine: `-ppm`/`-fc` tuning *can* now be data-driven (freqError telemetry is
  live). Downside: those same channel packets are being published to WU as dataless loop packets
  (DEC-0024 Layer B).
- **Next investigation (still open):** diff the bundled `src.tgz` rtldavis Go source vs upstream
  `lheijst/rtldavis` to understand which version is actually deployed.

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
