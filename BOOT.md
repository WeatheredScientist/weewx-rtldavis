# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
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
digits, so the signal is there and the gap is OURS.** That is the active thread — see the S114
job list.

**History was rewritten and force-pushed 2026-09-01 (DEC-0127) — every SHA changed, old clones must
re-clone.** Full story in the DEC; specifics in gitignored `docs/LOCAL_INFRA.md`. **Still owed: if
any NAS/marvin bare mirror of this repo exists it needs a force-push re-seed** — flagged to ops,
existence unconfirmed.

**`SCHEDULE=` is stood down (DEC-0096), and marvin's live copy is inert** — state `BASELINE`, tick
no-ops on `want == have`, guard exits at its `BASELINE` check, nothing logged since 01:30:39. Only
drift is the emptied block; the deploy rides the next real one. **No Class C write is owed.**

**ops#235 is CLOSED — BOOT previously overstated it as open.** The `-i` stdin fix landed and the
`marvinctl exec-ro` *workaround* works (used for campaigns C and D), which is what closed it. The
tenant read verb it asked for still does not exist — that gap is now tracked separately as
**ops#253** (`t-weewx`'s `marvinctl` key was never minted; blocks job 1 and ops#250).

### S113 debug window + Go source read — DEC-0130/DEC-0131 (S114)

Debug window: live 2026-09-01 ~10:46–20:55 ET, then reverted (`weewx.conf` restored from
`.s113-debug-backup`, sha256-verified, `weewx.service` restarted 20:55:08 ET, confirmed
INFO-only again). Transmitter ID is **4**, not the assumed 0 — resolves `max_count`'s 19–23
jitter (blocker 7, closed). The miss histogram is **not uniform**: channels 46–48 ran ~2x the
rest. Read the deployed Go source (`Dockerfile:46`'s tarball) to test the retune hypothesis:
the code shows **no PLL-settle haste** (300+ ms cushion vs. sub-ms typical lock time), which
weakly argues against "retune doesn't settle." Mapped 46–48 to actual frequencies —
**925.500/926.002/926.503 MHz** — and found they're scattered across hop-sequence order (not
adjacent in the cycle), ruling out a clock-drift artifact and pointing at something tied to
**that specific frequency slice**. Full detail: DEC-0130, DEC-0131. **Blocker 6 stays open.**

### ▶▶ S114 JOB LIST

**Live, in order:**
1. **Spectrum capture 924.5–927.5 MHz** (`gqrx`/`rtl_power`, same antenna) — DEC-0131's next
   step, cheap and bounded, to see whether 925.5–926.5 MHz has a visible interferer or a gain
   rolloff vs. the rest of the band. Capture itself is ~15 min, but it runs on marvin's dongle
   and there is no self-service path there yet — **blocked on ops#253** (`t-weewx` key unminted).
2. **Check the GitHub Support purge ticket** — if purged, verify an old SHA 404s, update
   `LOCAL_INFRA.md`'s PENDING line and drop this job.
3. **Port `campaign_analyze.py` to marvin** (tracked as ops#250). Its `fetch()` still ssh's to the
   NAS (pre-DEC-0118); two campaigns have now been read through a hand-assembled `marvinctl exec-ro`
   transport. Port it before a third — blocked on ops#253's key mint for a real transport.
4. **Audit Phase 2, session A (mechanical, Sonnet-able):** version/doc sync per the BACKLOG item —
   README + Docker Hub banner, driver/influx version numbers, weewx.conf.example, ARCHITECTURE
   stamps/paths, broken commands, CONTRIBUTING CI wording, tag + release v2.0.12–14, BIAS_TEE docs.
5. **Audit Phase 2, session B (judgment, Opus):** scrub internal IDs from what the code emits at
   RUNTIME (monitor emails, log lines — comments keep their DEC citations), driver docstring
   upstream defaults, stale test line refs, the unfailable assertion
   (`test_input_staleness.py:195`), internal-vs-user banners in `ops/`.
6. **Audit Phase 2, session C (design, owner + Opus/Fable):** public-surface reorg — root governance
   files (8 of 14 root docs are internal; alphabetically ahead of README), docs/ index, PR-title
   convention, tier-label rename, GitHub topics/description/templates, `DECISIONS-FULL.md` over
   GitHub's render limit, and the privacy-first question of moving the governance corpus private.
   Needs DECs.
7. **Flip `REMEDY_MODE=none` → `restart_unit`** — grant confirmed present (MARVIN-DEC-0099); only
   the live-restart exercise remains, belongs at a real deploy.
8. **Durable logrotate fix for marvin** — still unaddressed.

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
| Trackers | ops#233 (deploy+live-restart owed) · ops#253 (t-weewx key unminted, blocks job 1/ops#250) · ops#241 (BOOT cap) · #216/#214/#110 open · repo #274/#253 open |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open).
3. **ERR-0005** — unchanged.
4. ~~`ppm`/`fc` unmeasured~~ — **CLOSED (DEC-0129).** Measured +2.41 ppm systematic offset, but
   reception is flat across a 10x offset range: the AFC absorbs it. `-noafc` is contraindicated
   by the same result, not merely untested.
5. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.
6. **The ~25% reception ceiling is unexplained** (DEC-0128, sharpened DEC-0129/DEC-0130/DEC-0131).
   Deterministic, structural, ours, and now sharpened further: the S113 miss histogram clusters
   at 925.5–926.5 MHz specifically, scattered across hop-sequence order (not a drift artifact),
   and the deployed source shows no PLL-settle haste — arguing against the simple retune theory.
   Job 1 (spectrum capture 924.5–927.5 MHz) is the next attempt.
7. ~~`max_count` is not the constant it should be~~ — **EXPLAINED and closed, DEC-0130.** Our ISS
   is **transmitter ID 4, not 0** (`loop_times[4] = 2.8125 s`), which reproduces the observed
   19–23 `max_count` spread exactly. Not a defect.

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
