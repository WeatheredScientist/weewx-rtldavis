# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
