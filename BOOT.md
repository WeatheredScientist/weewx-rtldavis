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

## ▶ Resume here (S138 → S139)

### What's settled (do not re-derive)

**Four items landed: two answered a cross-session ask, two closed carried BOOT-job debt.**

- **`eaglehunt-ops#306`/`#312`/`#313` fixed (PR #387).** `BOOT.md` gained its three missing
  universal sections (`## Current state`, `## Files needed at session start`, `## Style`);
  `MANIFEST.md` gained the coverage row for 9 repo-root WeeWX runtime modules. `#312`/`#313`
  closed on the tracker with verified numbers. `MANIFEST.md`'s own cap stays over (4816 vs 4000
  chars) — the new coverage row is required content; coverage-beats-cap per OPS-DEC-0101, same
  call S136 made on this file. `#306` commented, left open on that basis. `eaglehunt-ops#265`'s
  trigger re-confirmed unfired (no version cut pending).
- **DEC-0198: freeze-rate re-read confirms DEC-0088's 1.31/day (PR #388).** Checked
  `weewx.service`'s uptime first (continuous since 09-07 23:42:48 EDT, zero restarts) before
  trusting the re-measurement. Current rolling windows: 0 freezes, 0.0th pct. S131's 4.03/day
  traced to that session's own 09-07 incident cluster (24 of 49 freezes, one 8580s outlier) —
  excluding it, ~1.51/day, matching baseline. Blocker 1 reworded; ROADMAP P0 line reconciled.
- **DEC-0199: `#373` closed — FULL OUTAGE reception alert class (PR #389/#390).** The
  driver-process side already had distinct escalating classes (DEC-0081/DEC-0120), so the real
  gap was narrower than the issue's title. New `classify_reception_alert()` cross-references two
  independent signals (all-zero windows, or `WD['escalated']`), either sufficient alone — same
  shape as `freeze_baseline.py`'s RF-dead classification. 10 new tests (zero prior coverage on
  `close_reception_window()`). **Not yet deployed to marvin** (job 1).
- **`eaglehunt-ops#326`/`#320` answered** via cross-session ring: probed the new `marvinctl
  notify-log weewx.service` verb (clean, "no page recorded" shape), posted verbatim, rang back.
- **`CHANGELOG.md`'s archive rollup done** (debt carried since ~S128): S115–S135 moved verbatim to
  `CHANGELOG-ARCHIVE.md`, header-count-verified lossless (120 before, 120 after, no dupes). Only
  S138/S137/S136 stay inline now.
- **Session-start checks, nothing new.** `estate-context-heartofgold`/`-2` re-confirmed
  stale/local-only again; the closeout-debt hook fired three more times, same harmless shape each
  time — **a BOOT.md-touching PR's own merge commit always trips this FYI once, right after; not
  evidence of missed work.**

### ▶▶ S139 JOB LIST

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
5. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) — the other half of the old doc-debt
   line; the `CHANGELOG.md` archive rollup half is now done (see above).
6. **`eaglehunt-ops#306`'s residual `MANIFEST.md` cap overage** (still over its own 4000-char cap;
   coverage-beats-cap carry) — no further action expected unless a future pass finds a real
   instance-collapse to make.

## Current state (S138 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unaffected this session — no restarts, no incidents. `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147. **Reception-alert code fix (DEC-0199) is on `dev`, not yet on marvin** (job 1) |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session |
| weewx-monitor | flock-based lock (PR #367) still live and stable; carries both the `REMEDY_SYSTEMCTL` fix and DEC-0199, neither vendored to marvin yet (job 1) |
| Reception | unchanged since DEC-0154's recovery; whether the new dongle position is better/worse than the old one is unmeasured (job 2) |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S138: PRs #387/#388/#389/#390 merged to `dev` (tier-file conformance, DEC-0198, DEC-0199 + writeup). `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (job 1) · #370 CLOSED-worthy, left to owner/marvin (job 2) · #373 CLOSED (DEC-0199) · #380 open (marvin's pager, informational) · ops: #306 residual (job 6) · #312/#313/#265/#326/#320/#308/#321 answered |

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

_Last updated: 2026-09-14 (S138). Session summary: answered two cross-session asks from ops
(`eaglehunt-ops#306`/`#312`/`#313`/`#265` — tier-file conformance, PR #387; `eaglehunt-ops#326`/
`#320` — notify-log probe); closed two carried BOOT-job items (DEC-0198 freeze-rate re-read, PR
#388; DEC-0199 `#373` full-outage alert class, PR #389/#390); rolled `CHANGELOG.md`'s ~10-session
archive debt (S115→S135 to `CHANGELOG-ARCHIVE.md`, lossless per header-count check). Four PRs
merged to `dev`, all green before merge, none touched `main`. Green gate clean throughout (506
passed/17 skipped, ruff/mypy clean, secret gate 0). One process gap noted honestly rather than
smoothed over: `#373`'s design decision should have prompted a tier-escalation call and didn't._
