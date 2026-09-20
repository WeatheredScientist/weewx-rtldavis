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

## ▶ Resume here (S139 → S140)

### What's settled (do not re-derive)

**S139 closed one job: `docs/ARCHITECTURE.md` re-verified against live marvin state (PR #392,
job 5 from the S138 list).** Doc hadn't been touched since S17 (2026-07-04) and had drifted across
the DEC-0118 marvin move — stale weewx version (5.3.1 → 5.5.0), stale LNA/bias-tee claim (LNA is
out, `BIAS_TEE=0`), a NAS-pathed mount table duplicating `CONSTANTS.md`'s own (now a pointer,
STANDARD rule 5), and a NAS-side monitor section describing a DSM-Task user that no longer exists.
`CONSTANTS.md` itself checked out accurate — no changes needed there. Two rows stay flagged
unverified (marvin host tool availability, `LOCAL_INFRA.md`'s marvin entry) — both need an
interactive host shell or a secret-bearing file the read-guard rightly blocks.

**S139 ended without running its own closeout (`ops#218` closeout debt — the hook flagged it at
S140 start).** No live/concurrent session was found holding the work; recovered here at S140 start
per the repo's own recovery path: `CHANGELOG.md` gained the missing S139 entry, this pointer is
rewritten in its place. This session does not write S139's own done-marker — its absence is the
honest record. Nothing else from S139 needs recovery: PR #392 was the only change, gate was green
before merge (per its own CI), and no DEC-worthy design call was made (a doc re-verify, not a
decision).

### ▶▶ S140 JOB LIST

1. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337) — now also carries
   DEC-0199's `#373` fix. Both land together via `marvinctl pull` + a deliberate
   `weewx-monitor.service` restart; neither is live until then.
2. **Whether reception at the dongle's new physical position (`5-1`) is actually better or worse
   than the old `7-1.2` cluster is unmeasured** — DEC-0154 fixed the crash loop, not this open
   question from #370's own original ask; needs a longer `rxCheckPercent` read once enough windows
   accumulate.
3. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`) exactly
   as S126 left them — none are due, none are blocked on anything weewx can do alone.
4. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
5. **`eaglehunt-ops#306`'s residual `MANIFEST.md` cap overage** (still over its own 4000-char cap;
   coverage-beats-cap carry) — no further action expected unless a future pass finds a real
   instance-collapse to make.
6. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130/S139 touched) — the
   `docs/ARCHITECTURE.md` half of the old doc-debt line is now done (S139); this is the remainder.

## Current state (S139 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unaffected this session — no restarts, no incidents. `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147. **Reception-alert code fix (DEC-0199) is on `dev`, not yet on marvin** (job 1) |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session |
| weewx-monitor | flock-based lock (PR #367) still live and stable; carries both the `REMEDY_SYSTEMCTL` fix and DEC-0199, neither vendored to marvin yet (job 1) |
| Reception | unchanged since DEC-0154's recovery; whether the new dongle position is better/worse than the old one is unmeasured (job 2) |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S139: PR #392 merged to `dev` (`docs/ARCHITECTURE.md` re-verify). `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (job 1) · #370 CLOSED-worthy, left to owner/marvin (job 2) · #373 CLOSED (DEC-0199) · #380 open (marvin's pager, informational) · ops: #306 residual (job 5) · #265/#110 open, both deferred-trigger, unfired · #312/#313/#326/#320/#308/#321 answered |

## Blockers

1. **weewx process freezes — rate confirmed 1.31/day median 240s (DEC-0088, reconfirmed DEC-0198
   S138); root cause/mechanism still unproven** (DEC-0068/DEC-0094). No active watch on the rate;
   re-derive only if a fresh elevated reading appears.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed at Sonnet, no action needed.** Session ran entirely on Sonnet, no `/model`
switch. Noted honestly, not smoothed over: `#373`'s design decision (job 1) was judgment work —
deciding a new alert-classification scheme, not executing a locked design — and should have
prompted an escalation call when it started, per the user's global model-economy rule; it didn't.
Landed fine on Sonnet and the design held (user agreed, tests pin it), so nothing to redo — catch
the call earlier next time judgment work starts, not after.

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

_Last updated: 2026-09-20 (S140, recovering S139's closeout debt per `ops#218`). S139 summary:
`docs/ARCHITECTURE.md` re-verified against live marvin state (BOOT job 5), PR #392 merged to `dev`,
`main` untouched. S139 ended without running its own closeout; no live session was found holding
that work, so S140 recovered it at session start — `CHANGELOG.md` gained the missing entry, this
pointer rewritten, S139's own done-marker deliberately not written. Repo tracker: only #380 open
(informational). Ops `repo:weewx` inbox: #265/#110, both deferred-trigger, neither fired — no
action due._
