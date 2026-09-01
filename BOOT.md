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

## ▶ Resume here (S112 → S113)

### What's settled (do not re-derive)

**The entire git history was rewritten and force-pushed 2026-09-01 (DEC-0127) — every commit SHA
changed.** A public-accessibility audit (four parallel reviews) found private-infrastructure
identifiers in two files' historical blobs and the owner's personal email in early commit metadata.
Owner's explicit call: privacy outranks history immutability. filter-repo replace-text + mailmap,
all refs/tags force-pushed, verified clean with positive controls on every axis, zero forks, branch
protection lifted/restored exactly, local clone re-pointed. NAS SSH port rotated FIRST (Phase 0);
UniFi port-forward table verified empty — never WAN-reachable, privacy scrub not compromise.
Specifics: gitignored `docs/LOCAL_INFRA.md` only. Public record: `SECURITY.md` re-clone notice
(deliberately generic) + DEC-0127. Merged as PR #298. **The ops session was briefed in full**
(cross-session, S112) — their DEC row + nas.env/alias updates are ops-side work; the new port value
lives in no Claude transcript by design. **If any NAS/marvin bare mirror of THIS repo exists, it
needs a force-push re-seed from the Mac clone** — flagged to ops, unconfirmed whether one exists.

**GitHub Support purge ticket SUBMITTED, PENDING** — until it lands, pre-rewrite SHAs still resolve
by direct URL (e.g. via API) and `refs/pull/*` pins hold the old objects. Check "My Tickets" on
support.github.com; when confirmed, update `LOCAL_INFRA.md`'s PENDING line and delete this
sentence.

**The stale-schedule CI tripwire compared in the RUNNER's timezone, fixed S112** —
`test_current_schedule_is_not_fully_stale` now evaluates in America/New_York (the SCHEDULE
contract's own clock). It first fired 4–5 h early on UTC runners, mid-Campaign-D, against PR #298.
Verified with `TZ=UTC` both ways.

**Campaign D ran overnight 2026-08-31T21:00 → 09-01T01:30 ET (DEC-0126) — readout NOT yet pulled**
(deliberate: session closed before the terminator). Six gain-only arms 496→207, 45 min each,
arm-selection input only, never adoption evidence.

**S112's public-accessibility audit found the rest of the repo publishable-but-stale** — full
findings in the four audit reports (this session's transcript) and condensed into `BACKLOG.md`
§"Public-maturity push". Headline: README/Docker Hub advertise v2.0.12/ws.4/weewx 5.4 (live:
v2.0.14/ws.5/5.5.0), no GitHub release tag past v2.0.11, internal DEC/ops IDs leak into
user-facing emails and log output, install paths contradict each other, `BIAS_TEE` (hardware-risk
default) near-undocumented. Comment quality itself was judged unusually good — preserve, don't strip.

### ▶▶ S113 JOB LIST

**Live, in order:**
1. **Pull Campaign D's readout and log the arm-selection result** — `marvinctl exec-ro` +
   `campaign_analyze.py --campaign D` (ops#235 fixed, self-service works). Then empty `SCHEDULE=`
   back to DEC-0096 stand-down — the (now TZ-correct) tripwire fails every PR until this lands.
2. **Check the GitHub Support ticket** — if purged, verify an old SHA 404s, update LOCAL_INFRA +
   this file.
3. **Audit Phase 2, session A (mechanical, Sonnet-able):** version/doc sync per the BACKLOG item —
   README + Docker Hub banner, driver/influx version strings, weewx.conf.example, ARCHITECTURE
   stamps/paths, broken commands, CONTRIBUTING CI wording, tag + release v2.0.12–14, BIAS_TEE docs.
4. **Audit Phase 2, session B (judgment, Opus):** scrub internal IDs from RUNTIME-EMITTED strings
   (monitor emails, log lines — comments keep their DEC citations), driver docstring upstream
   defaults, stale test line refs, the unfailable assertion (`test_input_staleness.py:195`),
   internal-vs-user banners in `ops/`.
5. **Audit Phase 2, session C (design, owner + Opus/Fable):** public-surface reorg — root
   governance files (8 of 14 root docs are internal; alphabetically ahead of README), docs/ index,
   PR-title convention, tier-label rename, GitHub topics/description/templates, `DECISIONS-FULL.md`
   over GitHub's render limit, and the privacy-first question of moving the governance corpus
   private. Needs DECs.
6. **Flip `REMEDY_MODE=none` → `restart_unit`** — grant confirmed present (MARVIN-DEC-0099);
   only the live-restart exercise remains, belongs at a real deploy.
7. **Durable logrotate fix for marvin** — still unaddressed.

**Carried forward, untouched:** `main` promotion for v2.0.14 (DEC-0114) · DEC-0117 control-file
conversion + image-rebuild question (can marvin build natively?) · Foundation decommission timing
(owner) · NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra re-verify · ops CONSTANTS §5
register row check (`ef8e9af8`) · ops#241 BOOT-over-cap (this rewrite trimmed toward it).

### Current state (S112 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box (`t-hlf`, ops#234) |
| Prod | v2.0.14, driver ws.5, weewx 5.5.0, gain 372 (DEC-0125). Campaign D ran overnight per DEC-0126; readout owed (job 1) |
| Git | **History rewritten 2026-09-01 (DEC-0127) — all SHAs changed; old clones must re-clone.** Support purge pending (job 2) |
| Alerting | `weewx_monitor.py` (`REMEDY_MODE=none`) live; `weewx-rx-experiment.timer` running (goes no-op once SCHEDULE= is stood down, job 1) |
| Open risks | Gmail SMTP 535 breaking the 6-hourly summary (owner-side, unchanged) |
| Trackers | ops#233 (deploy+live-restart owed) · ops#241 (BOOT cap) · #216/#214/#110 open · repo #274/#253 open · ops briefed on DEC-0127 port-rotation story (their DEC row pending, ops-side) |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open).
3. **ERR-0005** — unchanged.
4. `ppm`/`fc` — still unmeasured; no sweep data exists.
5. **6-hourly reception-summary email broken** — Gmail 535, needs the owner's Google account.

## Model tier

S112 escalated to Fable (`/model claude-fable-5`, desktop app) for the history-rewrite judgment
work. `~/.claude/settings.json` floor verified still `"model": "sonnet"` at close — but per
OPS-DEC-0036 the desktop picker persists independently: **owner flips the picker back to Sonnet;
S113 should confirm it's not still running Fable unflagged.**

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-09-01 (S112). Session summary: merged S111's PR #297, then a public-maturity
audit (four parallel reviews: doc drift, PII/secrets, comment quality, newcomer experience) found
real private-infra identifiers and the owner's personal email reachable in public git history.
Owner-directed privacy-first response, executed same session: NAS SSH port rotated, UniFi
forwarding verified empty, full history rewritten (filter-repo, 661 commits, all refs/tags),
verified clean with positive controls, force-pushed (owner-run — the auto-mode classifier refused
the rewrite command class, correctly leaving the human holding the pen on every irreversible step),
protection restored, GitHub Support purge requested, SECURITY.md notice + DEC-0127 shipped (PR
#298). Along the way: the stale-schedule tripwire's UTC-runner bug found live (bit #298
mid-Campaign-D) and fixed with a TZ-pinned comparison. Ops session briefed in full on the rotation
story cross-session. Campaign D launched on schedule at 21:00 ET and was left to finish overnight;
readout deliberately deferred to S113. Green gate clean: ruff clean, 465 passed / 9 skipped, mypy
clean (66 files), secret gate positive-controlled 54/54._
