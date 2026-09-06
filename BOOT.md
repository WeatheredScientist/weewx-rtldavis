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

## ▶ Resume here (S126 → S127)

### What's settled (do not re-derive)

**All eight S126 job-list items landed, nine PRs merged (#344–#352), dev clean and green.**

- **Job 1 — ROADMAP tripwire reconciliation, done.** One stale item found: P1.8's last checkbox
  (owner's tar deletion + ops#260 step 4 Foundation retirement) had landed S125 but sat unmarked.
  Fixed; tripwire reset to **S136**.
- **Job 2 — #331 closed.** Five annotated tags + GitHub Releases backfilled (v2.0.12–v2.0.16),
  anchored on verified-current commits (v2.0.14/15 on `dev`, since neither got its own `main`
  promotion). `docs/CONVENTIONS.md` + `CLAUDE.md` now require the `vX.Y.Z` tag + release as part of
  any version-bumping promotion (DEC-0145). Found and fixed a stale local tag cache from the
  DEC-0127/DEC-0144 history rewrites along the way — remote tags were already correct.
- **Job 3 — done, both halves.** `REMEDY_SYSTEMCTL` fixed to marvin's actual sudoers grant
  (ops#274) — **confirmed correct by marvin against the real sudoers file**. `ExecStop=docker kill`
  shipped live (MARVIN-DEC-0137). GPLv3 §5(a) notice added to the dupgate patch, #327 closed.
- **Job 4 — ops#278 closed (DEC-0146).** Traced `rx_experiment.sh` end to end: Foundation's frozen
  script could only ever resolve to `BASELINE`, so no code path ever reached `weewx.conf`/the
  container in the 13 days its DSM tasks kept firing (positive control: gain still 372, no drift).
  Also **eliminates**, doesn't confirm, the DSM scheduler as the still-unexplained 08-25 21:40
  restart's cause. `CAMPAIGN-B-RUNBOOK.md` retired (Foundation's directory is gone entirely).
- **Job 5 — upstream draft written, NOT posted.** `docs/upstream/dupgate-time-gate.md` (gitignored)
  proposes the DEC-0134/0135/0136 fix to `lheijst/rtldavis` (issues disabled there, dormant since
  2023-12-22, LloydR's complementary PR #2 credited). Sent for owner tone review — **still needs a
  go before anything is forked/posted.**
- **Job 6 — first post-fix baseline read, clean.** Every fully post-v2.0.16 window (09-03 18:00
  through 09-06 06:00) reads **100% mean reception**. Zero RF-dead stall lines in the same span —
  nothing to measure yet, not evidence it stopped; blocker 2 stays open, watch continues.
- **Job 7 — "Audit Phase 2 A/B/C" resolved**, best reconstruction "P2's Campaigns A/B/C" (never
  defined anywhere, traced through transcripts to no avail). Found `BACKLOG.md`'s Campaign-A section
  still stated the same ~73–75% figures DEC-0134/0135 demoted to *untested*, unlike `ROADMAP.md`'s
  P2 header — fixed. logrotate ask sent to marvin (not weewx's to act on; queued on their backlog).
- **Job 8 — one piece shipped, three correctly untouched.** `GOTCHAS.md`'s stale "two Class C gates"
  line fixed (OPS-DEC-0193 relaxed transport to advisory). Not touched: tenant `EnvironmentFile` for
  the monitor (the general pattern was rejected on the ops tracker, OPS-DEC-0194 — weewx-monitor's
  own already-unprivileged case may differ but needs the same sudoers verification job 3 did, not
  blind implementation); `weewx.service` as `t-weewx` (judgment work, escalate, DEC-0011); a tracked
  `marvin-release.sh` (reads as marvin's own repo's tooling).
- **ops#257 limb 3 settled** — `marvinctl grep` confirmed reaching both the startup line and the
  full reception-summary body today; the 09-05 restatement just hadn't rechecked. Limb 1 stays open.
- **ops#274 item 5 answered:** still root (`"User": ""`, no `USER` directive) — same judgment-work
  gate as job 8's `t-weewx` item, not a gap.
- **Tooling lessons, now in `docs/GOTCHAS.md` §2:** a subagent without `isolation:"worktree"` shares
  the parent's checkout and can switch its branch mid-task (found live, no data lost); two
  same-session PRs inserting at the same `DECISIONS.md` anchor conflict on `update-branch`, resolve
  by keeping both in DEC order; `gh pr merge` needs to be a bare standalone call, not wrapped in a
  larger script, to get the advisory-allow instead of a hard Class C block.

### ▶▶ S127 JOB LIST

1. **Job 5's tone review** — once the owner signs off on `docs/upstream/dupgate-time-gate.md`, fork
   `lheijst/rtldavis`, apply `patch/rtldavis-dupgate.patch`, open the PR. Not a repeat task; picks up
   exactly where S126 left it.
2. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix and install both unit changes in
   their next units gesture (queued, owner check-in pending on marvin's side as of S126 close).
3. Carry forward job 8's three untouched items (EnvironmentFile, `t-weewx`-as-root, `marvin-release.sh`)
   exactly as S126 left them — none are due, none are blocked on anything weewx can do alone.
4. `CONSTANTS.md` infra re-verify (S105-era, still stale) · `docs/ARCHITECTURE.md` mount table still
   NAS-pathed (S30) · `CHANGELOG.md` archive rollup overdue — S122 and earlier still inline, past the
   ~3-session guideline (pre-existing debt, carried again).

### Current state (S126 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` in `/weather.slice`; `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, `ExecStop=docker kill` (MARVIN-DEC-0137, S126) — still runs as root (ops#274 item 5) |
| Reception | **100% mean, every post-v2.0.16 6h window since 09-03 18:00** (job 6) — RF question reads closed; blocker 2 (RF-dead) unfired, watch continues |
| InfluxDB | marvin, `weewx-influxdb.service` since 09-04 22:35:02 ET, v2.7.12; backup timer armed |
| Foundation | fully decommissioned — project directory deleted, NFS export retired, DSM tasks disabled (ops#278 closed) |
| `main`/`dev` | `dev` carries all of S126 (DEC-0145/0146); `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · self-service `push` LIVE (ops#265, unchanged, still closes on first real push) |
| GitHub Releases | **v2.0.12–v2.0.16 backfilled, live** (#331 closed, DEC-0145) |
| Git | S126: PRs #344–#352, all merged → `dev`. No local branches left over |
| Trackers | repo: none open (#327/#331 closed) · ops: #257 limb 1 open (limbs 2/3 closed) · #250/#110/#274(items b/c) open, correctly gated/deferred · #278/#275/#273/#264/#218 closed prior sessions, #278 closed S126 |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

S126 ran entirely on Sonnet, no bare `/model` switch — nothing to restore. Used parallel subagents
for independent mechanical pieces (job 3's GPLv3 notice) per the owner's own instruction this
session; the two judgment-work items flagged (job 8's `t-weewx`-as-root, ops#274 item 5) were
correctly left untouched rather than actioned on the base tier.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). S126 added three
traps to §2 (subagent checkout collisions, same-anchor DEC conflicts, `gh pr merge`'s bare-command
requirement) — nothing left to move.

_Last updated: 2026-09-06 (S126 close, ~11:15 ET). Session summary: worked the full 8-item job list
end to end (nine PRs, all merged) — GitHub Releases backfilled after 5 releases shipped silently
(#331), two of three marvin unit-file fixes shipped (REMEDY_SYSTEMCTL confirmed correct against the
real sudoers file, ExecStop=docker kill live), ops#278 closed with a full code trace rather than a
re-asserted "looks harmless," the first clean post-fix RF baseline read taken (100% mean, blocker 2
still unfired), and two separate stale-doc findings (BACKLOG.md missing the DEC-0134/0135 campaign
correction, a pre-#317 footnote) caught while doing other work rather than left for someone else.
Settled a live cross-session discrepancy on ops#257 by checking the actual log rather than deferring
it. One item (job 5's upstream post) is deliberately left mid-flight pending the owner's tone
review — not a gap, the correct stopping point for that specific task._
