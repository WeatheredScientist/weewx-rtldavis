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

## ▶ Resume here (S137 → S138)

### What's settled (do not re-derive)

**Single-item session: adopted `eaglehunt-ops#321`'s cross-repo dispatch ring protocol.** No
S137-job-list items were touched — this was a fresh ask, not backlog work.

- **`eaglehunt-ops#321` (DEC-0197).** `CLAUDE.md`'s Session ritual gains a **Cross-repo dispatch**
  bullet, next to the existing inbox-pull step: after posting a tracker ask to another repo, ring
  that repo's live session (`ListAgents`) with one line; receivers read, act within their own
  permissions, answer on the tracker, ring back; nothing Class C rides a message. Wording mirrors
  hlf's/coffeeradar's/heartofgold's already-adopted text. PR #385 merged to `dev`.
  `**Answered:** weewx-rtldavis` posted on the issue.
- **Session-start checks, nothing new:** this repo's own tracker and the ops `repo:weewx` inbox
  were already fully reflected below; `estate-context-heartofgold` confirmed old/merged-away, not
  a stranded PR; the closeout-debt hook's flag against `8111407` was a false alarm (that commit
  **is** S136's own BOOT.md fold-in, not undocumented drift).
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.

### ▶▶ S138 JOB LIST

1. **`#373`** — decide whether `weewx_monitor.py` needs a distinct alert class for a
   full outage vs. partial degradation (filed S134/DEC-0154, not investigated further). Adjacent
   context, not a fix: `weewx-monitor.service` also got a box-wide crash pager at S136
   (`weewx-rtldavis#380`) — a separate signal (unit died) from what #373 is about (the monitor's
   own RF/reception judgment), but worth reading together when designing #373.
2. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337).
3. **Whether reception at the dongle's new physical position (`5-1`) is actually better or worse
   than the old `7-1.2` cluster is unmeasured** — DEC-0154 fixed the crash loop, not this open
   question from #370's own original ask; needs a longer `rxCheckPercent` read once enough windows
   accumulate.
4. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`) exactly
   as S126 left them — none are due, none are blocked on anything weewx can do alone.
5. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
6. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S135/S136/S137 all still inline, well past the ~3-session guideline (pre-existing
   debt, carried forward again).
7. **`eaglehunt-ops#306`'s residual MANIFEST.md cap overage** (still over its own 4000-char cap;
   coverage-beats-cap carry, see PR #387) — no further action expected, left open per OPS-DEC-0101
   unless a future pass finds a real instance-collapse. `#312`/`#313` fixed this session (PR #387).

## Current state (S137 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unaffected this session — no restarts, no incidents. `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session |
| weewx-monitor | flock-based lock (PR #367) still live and stable; marvin's box-wide crash pager (`weewx-rtldavis#380`, heartofgold) still needs `#373`'s own alert-class question resolved (job 2) |
| Reception | unchanged since DEC-0154's recovery; whether the new dongle position is better/worse than the old one is unmeasured (job 4) |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S137: PR #385 (cross-repo dispatch adoption, DEC-0197) merged to `dev`. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (marvin's file to fix) · #370 CLOSED-worthy but left to the owner/marvin to close (job 4) · #373 open (job 2) · #380 open (marvin's pager wiring, informational) · ops: #306/#312/#313 residual deferred (job 8) · #308/#321 answered, no action owed · #265/#110 correctly gated/deferred |

## Blockers

1. **weewx process freezes — rate confirmed 1.31/day median 240s (DEC-0088, reconfirmed DEC-0198
   S138); root cause/mechanism still unproven** (DEC-0068/DEC-0094). S131's 4.03/day "at record
   max" traced to that session's own 09-07 incident cluster, not a regression — no active watch on
   the rate; re-derive only if a fresh elevated reading appears.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. **`#373`** — monitor can't distinguish full outage from partial degradation (job 2).
5. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed at Sonnet, no action needed.** Session ran entirely on Sonnet, no `/model`
switch. Nothing to restore going into S138.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). No new entries
this session.

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-13 (S137). Session summary: answered `eaglehunt-ops#321` — adopted the
owner's cross-repo dispatch ring protocol (OPS-DEC-0215) into `CLAUDE.md`'s Session ritual as a
**Cross-repo dispatch** bullet next to the existing inbox-pull step, mirroring hlf/coffeeradar/
heartofgold's wording; logged as DEC-0197, PR #385 merged, answered on the tracker. Session-start
checks (this repo's tracker, the ops inbox, the closeout-debt hook, the stray
`estate-context-heartofgold` branch) all came back clean or already-known — nothing else landed.
No S137-job-list item was touched; the full list carries forward to S138 unchanged except for two
small enrichments (job 7's session count, job 8's issue numbers). Green gate clean throughout (496
passed/17 skipped, ruff/mypy clean, secret gate 0)._
