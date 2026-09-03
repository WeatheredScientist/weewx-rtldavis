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

## ▶ Resume here (S114 → S115)

### What's settled (do not re-derive)

**RF TUNING IS OVER — every axis is measured flat (DEC-0128, DEC-0129). Do not re-sweep any of
them without a new reason.** Gain holds at 372; flat axes are **gain · receive window (`-ex`) ·
physical siting · frequency offset**. The ~25% loss is **not SNR-limited, not reachable by tuning,
has no excess variance beyond binomial** — deterministic and structural, and **the owner's Davis
console at comparable distance drops single digits, so the gap is OURS.** Full chain of evidence:
DEC-0128 → 0129 → 0130 → 0131 → **0132 (S114, this session)**.

**History was rewritten and force-pushed 2026-09-01 (DEC-0127) — every SHA changed, old clones must
re-clone.** Support purge ticket still pending (job 2, untouched this session).

**`SCHEDULE=` is stood down (DEC-0096), marvin's live copy is inert** (state `BASELINE`, no-ops on
`want == have`). No Class C write owed.

**ops#253 is CLOSED (both stages, this session).** `exec_devices = 0bda:2838` is live on marvin
(owner-ratified, installed S114 before this session's capture); stage 2 (a real capture, not just
`rtl_test`) ran clean — see below. `t-weewx`'s `marvinctl` key was never actually unminted (S113's
finding); that confusion is fully resolved now.

### S114 spectrum capture — DEC-0132: RFI looks right, the 925.5–926.5 MHz tie doesn't hold up

Ran DEC-0131's proposed capture (`rtl_power`, 924.5–927.5 MHz, 5 min, gain 37.2 dB matching prod's
372) via `marvinctl exec-ro`; weewx down ~6 min. Noise floor flat and stable the whole run
(no rolloff shape) — argues against a static gain rolloff or fixed antenna null. But **16 of 60
ten-second windows carried transient bursts (5–34 dB above floor) spanning 925.15–927.48 MHz**,
nearly the whole capture band — only 7 of 16 fall in DEC-0130's flagged 925.5–926.5 MHz
(channels 46–48); the single largest (+34.5 dB) hit 927.34 MHz, well outside it. **Reading: RFI
strengthens as the mechanism (bursty + wideband is its signature); the exclusive tie to
channels 46–48 weakens.** Blocker 6 stays open — full detail and numbers in DEC-0132,
`BACKLOG.md`'s ceiling item. **Free next step, not done yet: cross the 16 spike frequencies
against DEC-0130's existing 51-channel miss histogram** — arithmetic over data already in hand,
no new capture.

**Owner's call for S115: run that analysis on Fable, not Sonnet** — it's open-ended
hypothesis-forming over an ambiguous result (does RFI explain the whole channels-46–48 cluster, or
does something channel-specific survive it?), not mechanical execution. Escalate at session start.

### ▶▶ S115 JOB LIST

**Live, in order:**
1. **[Fable — judgment work, escalate at start] DEC-0132 follow-up analysis** — cross the 16 spike
   frequencies against DEC-0130's 51-channel miss histogram; decide whether RFI explains the whole
   cluster or something channel-specific remains, and whether blocker 6 has a next real step or
   needs a longer/repeated capture to say more.
2. **Check the GitHub Support purge ticket** — if purged, verify an old SHA 404s, update
   `LOCAL_INFRA.md`'s PENDING line and drop this job.
3. **Port `campaign_analyze.py` to marvin** (tracked as ops#250). Its `fetch()` still ssh's to the
   NAS (pre-DEC-0118); transport already works via `marvinctl exec-ro` — this is weewx's own
   porting work, no blocker.
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
conversion + image-rebuild question (can marvin build natively?) · NAS-LEASE cross-host wiring
(low) · `CONSTANTS.md` infra re-verify · ops CONSTANTS §5
register row check (`ef8e9af8`) · ops#241 BOOT-over-cap (this file sits right at the 2.5K cap by
chars/4 — re-measure with ops' own `checks/tier-sweep.sh` before closing).

### Current state (S114 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box (`t-hlf`, ops#234) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, **gain 372 — now measured-and-unbeaten, not provisional (DEC-0128)** |
| Campaigns | **None running, none planned.** `SCHEDULE=` stood down; the gain axis is closed |
| Git | History rewritten 2026-09-01 (DEC-0127) — all SHAs changed; old clones must re-clone. Support purge pending (job 2) |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live; `weewx-rx-experiment.timer` still ticking but a confirmed no-op |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) |
| Trackers | ops#233 (deploy+live-restart owed) · ops#241 (BOOT cap) · #216/#214/#110 open · repo #274 open. **ops#253 CLOSED this session (both stages).** |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open).
3. **ERR-0005** — unchanged.
4. ~~`ppm`/`fc` unmeasured~~ — **CLOSED (DEC-0129).** Measured +2.41 ppm systematic offset, but
   reception is flat across a 10x offset range: the AFC absorbs it. `-noafc` is contraindicated
   by the same result, not merely untested.
5. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.
6. **The ~25% reception ceiling is unexplained** (DEC-0128, sharpened DEC-0129/0130/0131/**0132**).
   Deterministic, structural, ours. S114's spectrum capture (DEC-0132) found transient RFI bursts
   across nearly the whole 925.15–927.48 MHz band, not confined to the 925.5–926.5 MHz cluster
   DEC-0130 flagged — RFI as the mechanism strengthens, but the exclusive tie to channels 46–48
   does not hold up as cleanly as hoped. Next: cross the spike frequencies against DEC-0130's
   histogram (S115 job 1, Fable).
7. ~~`max_count` is not the constant it should be~~ — **EXPLAINED and closed, DEC-0130.** Our ISS
   is **transmitter ID 4, not 0** (`loop_times[4] = 2.8125 s`), which reproduces the observed
   19–23 `max_count` spread exactly. Not a defect.

## Model tier

S114 ran on Sonnet (default floor) — appropriate, it was execution against a pre-scoped step
(run DEC-0131's proposed capture, merge a green PR) plus mechanical DEC/BOOT writeup, not
open-ended hypothesis-forming. **S115 job 1 is different: the owner has explicitly called for
Fable** to analyze DEC-0132's ambiguous result and decide what it means — escalate via the
desktop picker at session start, per OPS-DEC-0036/0062 (the switch persists until flipped back).

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
