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
- **Gain re-sweep at marvin's RF position — mini-campaign launched, STOPPED CLEAN at 01:08:16 ET for
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
  which earns a real multi-day campaign rather than a config change.
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

## Durable RF findings (from 2026-06-01 tuning sweeps — keep; these guide P2)

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
- **Caveat on provenance (S56):** the equivalence was read from upstream *master*. The deployed binary
  is built from weewx-contrib's bundled `src.tgz` and is demonstrably older — it lacks master's
  startup settings line (`tr=… gain=… ex=… receiveWindow=…`), which is absent from both `weewx.log`
  and the container stdout. The deployed source has not been read directly.

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
