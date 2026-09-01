# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). *Temporarily
over the 2.5K cap (~3.0K) by design: the LIVE-ON-PROD banner below is safety-critical and comes
out the moment the debug window is reverted. Do not shrink this file by deleting that banner.*
Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3 — the "escape the WeatherLink lock" tool. A public, published
WeeWX extension (Docker Hub + GitHub releases), GPLv3. Its real contract is the **data it emits**
(loop-JSON + InfluxDB line-protocol schema), not any one consumer. The dashboard that consumes it
is a **separate repo** — don't make dashboard changes here.

---

## ▶ Resume here (S113 → S114)

### What's settled (do not re-derive)

**RF TUNING IS OVER — every axis is measured flat (DEC-0128, DEC-0129). Do not re-sweep any of
them without a new reason.** Campaign D ran clean and gain 328–496 came back as one plateau (1.70
pts spread vs a ~1.61-pt per-arm SE, best delta +0.01); 207 is the only real arm (−6.80, t=−3.75),
consistent with the LNA being out. Gain holds at 372, no config change, ROADMAP P2 closed. Flat
axes: **gain · receive window (`-ex`) · physical siting** (DEC-0118's closer, fewer-walls position
moved 372 by −0.01, 496 by −0.85) **· frequency offset** (DEC-0129). The ~25% loss is **not
SNR-limited, not reachable by tuning, and has no excess variance beyond binomial** — it is
deterministic and structural. **The owner's Davis console at comparable distance drops single
digits, so the signal is there and the gap is OURS.** That is job 1.

**History was rewritten and force-pushed 2026-09-01 (DEC-0127) — every SHA changed, old clones must
re-clone.** Full story in the DEC; specifics in gitignored `docs/LOCAL_INFRA.md`. **Still owed: if
any NAS/marvin bare mirror of this repo exists it needs a force-push re-seed** — flagged to ops,
existence unconfirmed.

**`SCHEDULE=` is stood down (DEC-0096), and marvin's live copy is inert** — state `BASELINE`, tick
no-ops on `want == have`, guard exits at its `BASELINE` check, nothing logged since 01:30:39. Only
drift is the emptied block; the deploy rides the next real one. **No Class C write is owed.**

**ops#235 is still OPEN — BOOT previously overstated it.** The `-i` stdin fix landed and the
`marvinctl exec-ro` *workaround* works (used for campaigns C and D); the tenant read verb the issue
asks for does not exist.

### ⚠ LIVE ON PROD RIGHT NOW — REVERT THIS FIRST (S113)

**A diagnostic window is running on marvin's live weewx config and MUST be reverted.** Two
owner-authorized Class C edits on 2026-09-01 (~10:46–10:51 ET): top-level `debug = 1`, and the
`[[[user]]]` logger raised `INFO` → `DEBUG`. The second is the one that mattered — DEC-0043's
`[Logging]` block pins logger levels, so the global debug flag alone did nothing. Purpose: surface
the three `logdbg` diagnostics that are otherwise invisible — the Go binary's per-channel miss
histogram, `totInit`, and `ARCHIVE_STATS`.

**To revert:** restore the `.s113-debug-backup` sibling of the live config (in
`/srv/docker/weewx/weewx-data/`) over it, then
`marvinctl --tenant weewx restart weewx.service`. The backup predates both edits, so one restore
undoes both. A ready script — refuses if the backup is absent, verifies byte-identity, clears the
backup after — is in S113's scratchpad as `revert_debug.sh`; if that scratchpad is gone the restore
is a two-step copy + restart, and the backup on the box is authoritative. **Harvest before
reverting** — the counters are cumulative in the Go process, so the LAST `missed per freq` line in
`logs/weewx.log` carries the whole histogram.

**If marvin is powered down before this is reverted** (a hardware install is planned this week,
per the marvin session), the window's data is lost but the revert obligation still stands.

### ▶▶ S114 JOB LIST

**Live, in order:**
1. **Harvest the debug window, then REVERT it (banner above), then read the histogram.** The
   per-channel miss counts answer the hop question directly: **uniform across the 51 channels = a
   timing/retune problem; clustered = specific frequencies are bad.** Owner's framing is that a
   distinctive, teachable signature beats a one-off diagnosis — if the shape is clear it becomes a
   detector (a monitor check, and something other rtldavis users can run), not a guess. Also grab
   `totInit` (re-init count; each re-init costs up to ~149 s of near-total loss) and `ARCHIVE_STATS`.
2. **Read the deployed Go demodulator's hop-tracking / retune path.** DEC-0129 established the
   ~25% loss is deterministic and **ours**, not the link's — the owner's Davis console at comparable
   distance runs single-digit drop. Leading (untested) hypothesis: the US band is 26 MHz/51 channels
   and an RTL-SDR sees ~2.4 MHz, so it must retune per hop; hops whose retune doesn't settle are
   lost regardless of signal. **The source is publicly fetchable** — `Dockerfile:46` pulls `src.tgz`
   from `weewx-contrib/weewx-rtldavis`, building `src/lheijst/rtldavis`. No prod access, no
   campaign, no owner-mediated step; `CONSTANTS.md` notes it has never been read directly. Do this
   before any further measurement.
3. **Check the GitHub Support purge ticket** — if purged, verify an old SHA 404s, update
   `LOCAL_INFRA.md`'s PENDING line and drop this job.
4. **Port `campaign_analyze.py` to marvin.** Its `fetch()` still ssh's to the NAS (pre-DEC-0118);
   two campaigns have now been read through a hand-assembled `marvinctl exec-ro` transport. Port it
   before a third. Pairs naturally with commenting/closing ops#235.
5. **Audit Phase 2, session A (mechanical, Sonnet-able):** version/doc sync per the BACKLOG item —
   README + Docker Hub banner, driver/influx version numbers, weewx.conf.example, ARCHITECTURE
   stamps/paths, broken commands, CONTRIBUTING CI wording, tag + release v2.0.12–14, BIAS_TEE docs.
6. **Audit Phase 2, session B (judgment, Opus):** scrub internal IDs from what the code emits at
   RUNTIME (monitor emails, log lines — comments keep their DEC citations), driver docstring
   upstream defaults, stale test line refs, the unfailable assertion
   (`test_input_staleness.py:195`), internal-vs-user banners in `ops/`.
7. **Audit Phase 2, session C (design, owner + Opus/Fable):** public-surface reorg — root governance
   files (8 of 14 root docs are internal; alphabetically ahead of README), docs/ index, PR-title
   convention, tier-label rename, GitHub topics/description/templates, `DECISIONS-FULL.md` over
   GitHub's render limit, and the privacy-first question of moving the governance corpus private.
   Needs DECs.
8. **Flip `REMEDY_MODE=none` → `restart_unit`** — grant confirmed present (MARVIN-DEC-0099); only
   the live-restart exercise remains, belongs at a real deploy.
9. **Durable logrotate fix for marvin** — still unaddressed.

**Carried forward, untouched:** `main` promotion for v2.0.14 (DEC-0114) · DEC-0117 control-file
conversion + image-rebuild question (can marvin build natively?) · Foundation decommission timing
(owner) · NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra re-verify · ops CONSTANTS §5
register row check (`ef8e9af8`) · ops#241 BOOT-over-cap (this file sits right at the 2.5K cap by
chars/4 — re-measure with ops' own `checks/tier-sweep.sh` before closing).

### Current state (S113 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box (`t-hlf`, ops#234) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372 — now measured-and-unbeaten, not provisional (DEC-0128)** |
| Campaigns | **None running, none planned.** `SCHEDULE=` stood down; the gain axis is closed |
| Git | History rewritten 2026-09-01 (DEC-0127) — all SHAs changed; old clones must re-clone. Support purge pending (job 2) |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live; `weewx-rx-experiment.timer` still ticking but a confirmed no-op |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) |
| Trackers | ops#233 (deploy+live-restart owed) · ops#235 (read verb, open — workaround works) · ops#241 (BOOT cap) · #216/#214/#110 open · repo #274/#253 open |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open).
3. **ERR-0005** — unchanged.
4. ~~`ppm`/`fc` unmeasured~~ — **CLOSED (DEC-0129).** Measured +2.41 ppm systematic offset, but
   reception is flat across a 10x offset range: the AFC absorbs it. `-noafc` is contraindicated
   by the same result, not merely untested.
5. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.
6. **The ~25% reception ceiling is unexplained** (DEC-0128, sharpened DEC-0129). Now known to be
   **deterministic, structural, and ours**: no excess variance beyond binomial, unresponsive to
   gain/window/siting/frequency offset, and a real Davis console at comparable distance drops only
   single digits. Job 1 is the next attempt.
7. ~~`max_count` is not the constant it should be~~ — **EXPLAINED, S113.** The debug window's
   startup line reads `tr=16 … actChan=[4]`: our ISS is **transmitter ID 4, not 0**, so
   `loop_times[4] = 2.8125 s` — confirmed independently, the init wait logs 149 s = 53 × 2.8125.
   `curr_ts` is a packet arrival time, so `period` jitters in whole 2.8125 s quanta around 60 s,
   mapping exactly onto the observed 19–23. Not a defect. Fold into a DEC at S114 close.

## Model tier

S113 ran on Opus (desktop picker, still on the escalated tier after S112's Fable session). Reading a
pre-registered campaign and writing its decision is judgment work, so this was defensible — but per
OPS-DEC-0036 the picker persists across sessions: **the owner flips it back to Sonnet; a mechanical
session (job 4) should not start on Opus unflagged.**

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-09-01 (S113). Session summary: pulled Campaign D's overnight readout and logged
its verdict as DEC-0128. The pilot ran exactly as pre-registered and self-terminated clean, and the
result is a flat curve — gain 328–496 spread 1.70 pts against a ~1.61-pt per-arm SE, best delta
+0.01, nothing near the 2.0-pt bar — so a shortlisting pilot shortlisted nothing and the confirmatory
campaign is withdrawn rather than deferred. 207 is the one real arm (−6.80, t=−3.75) and agrees with
the LNA being out since 08-02. Checked the HIGH→LOW ordering confound the pre-registration had
knowingly accepted: three independent gain-372 anchors (pre-baseline, in-block, post-baseline) span
0.80 pts across six hours, so time-of-night is not first-order here and 207's deficit is the gain.
The larger, undesigned finding is that three axes are now flat at ~73–75% — gain, receive window,
and physical siting (DEC-0118's closer, fewer-walls position moved 372 by −0.01 and 496 by −0.85) —
which says the missing ~25% is not SNR-limited and not reachable by tuning. ROADMAP P2 closed on
that basis and a new cheapest-first BACKLOG item replaces the tuning axes. `SCHEDULE=` stood down;
marvin's live copy left alone after confirming it is genuinely inert (state BASELINE, tick and guard
both no-op, sha matched HEAD) rather than spending a Class C write on a no-op. Corrected BOOT's
inherited claim that ops#235 was fixed — the `-i` stdin fix landed and the workaround works, but the
read verb the issue asks for does not exist and the issue is open. Green gate clean: ruff clean,
457 passed / 17 skipped, mypy clean (66 files), secret gate exit 0 and positive-controlled 3/3 —
it first returned "nothing to scan", which is its false-zero shape when nothing is staged._
