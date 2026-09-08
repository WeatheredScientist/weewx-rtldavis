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

## ▶ Resume here (S131 → S132)

### What's settled (do not re-derive)

**The last of the NAS-ssh transport retired — DEC-0152. ops#286 and ops#287 both closed (with
comments), both PRs merged. Nothing outstanding on the port itself.**

- **PR #369 (ops#286):** `ops/freeze_baseline.py` + `ops/stall_baseline.py` ported to
  `marvinctl --tenant weewx` (`stall_baseline.py` had to move too — `freeze_baseline.py`'s own
  `main()` calls it directly). Live-verified against marvin: 11 log files/2 episodes;
  15,273 archive rows/44 freezes classified.
- **PR #371 (ops#287):** `ops/soak_check.sh` fully rewritten for `marvinctl` — ~15 separate calls
  replacing the one ssh round trip. **Fixed a real bug found along the way:** the old
  `EXPECT_IMAGE` canary compared image TAG strings; marvin's `set-image` deploy flow runs
  containers under a local alias tag (`marvin-live`), so a string compare would have failed
  permanently on a healthy station — now compares image ID via `marvinctl check-image`, confirmed
  live (`marvin-live` and `:v2.0.16` share one sha256 ID). `tests/test_soak_check.py` (not named in
  ops#287, found broken by the transport change) rewritten around a fake `marvinctl` stub, 22 tests.
  Live-verified against marvin: 17 passed/1 warning/1 real fail (today's own S130 deploy restarts,
  22min apart — the script's own comment already names this as an attended-deploy false positive).
- Both branches needed a `dev` merge mid-flight (#369 merged first; #371's branch was then behind)
  — clean, no conflicts, different files. Green gate clean throughout (480 passed/17 skipped after
  both merged — +5 over the S130 baseline, matching net new test count).
- **New gotchas documented** (`docs/GOTCHAS.md` §3): `marvinctl grep` needs a whitespace-free
  pattern (use `.` for a literal space); its exit code 1 means either zero matches or a missing
  path, indistinguishably; `ls` takes no glob/flags; `stat`'s `Size:` line isn't column-0-anchored
  like `Modify:` is.
- **Live side-finding, NOT investigated this session:** `freeze_baseline.py`'s live run read
  **4.03/day, AT RECORD MAX across every rolling window**, against DEC-0083's ~1.49/day baseline.
  Plausible confound, not confirmed: today's own incident-driven restarts (DEC-0151's InfluxDB
  restart, the weewx-monitor PR #367 deploy restart) are exactly the kind of unscheduled,
  ops-triggered restart `freeze_baseline.py`'s swap classifier can't see — it only recognizes
  `rx_experiment.sh`'s own logged swap/restore lines, not an arbitrary `marvinctl restart`/`pull`.
  **Don't treat this as a confirmed regression; re-run after a quiet stretch (job 1 below).**
- Ops checked `marvinctl push` (cited against ops#265 in its own `--help` text) and confirmed
  ops#265 is already accurately tracked as "wired but unexercised" — not newly resolved, no update
  needed there.
- Full account: `docs/DECISIONS-FULL.md` DEC-0152.
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.

### ▶▶ S132 JOB LIST

1. **Re-run `ops/freeze_baseline.py` after a quiet stretch** (no ops-driven restarts in the window)
   to check whether the AT-RECORD-MAX reading above holds or was an artifact of today's own
   incident/deploy activity. If it holds, root-cause; if not, no further action needed.
2. **Fix DEC-0150's own runbook** — carried from S130, now tracked as its own item,
   [ops#288](https://github.com/WeatheredScientist/eaglehunt-ops/issues/288) (filed by ops, not
   this repo): derive a tree-swap restore list from every unit's bind-mount sources rather than
   from memory/git-diffing alone.
3. Consider porting `ops/backfill_influx.py` to run natively against marvin (NAS-path and
   `localhost:8086` defaults) — DEC-0151 solved one incident's window with an ad hoc inline script
   rather than fixing the tool itself; still not filed as its own tracker item.
4. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337) and install both unit
   changes in their next units gesture.
5. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`) exactly
   as S126 left them — none are due, none are blocked on anything weewx can do alone.
6. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
7. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S122 and earlier still inline, past the ~3-session guideline (pre-existing debt,
   carried again, one session closer).

### Current state (S131 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unaffected this session (no code touched what's actually running — this session ported tooling, not the driver/monitor). `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session, healthy since DEC-0151's S130 recovery |
| weewx-monitor | unchanged this session — flock-based lock (PR #367) still live and stable |
| Reception | unchanged this session — watch continues; see the freeze-rate side-finding above for a related but distinct signal |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S131: PR #369 (ops#286/DEC-0152) + PR #371 (ops#287/DEC-0152) both merged — `dev` at `26ff355`. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (unchanged, marvin's file to fix) · ops: #286/#287 **closed this session** · #288 (new, ops-filed) open · #265/#110 open, correctly gated/deferred |

## Blockers

1. **weewx process freezes — was 1.31/day median 240s (DEC-0088); a live `freeze_baseline.py` read
   this session showed 4.03/day AT RECORD MAX, plausibly confounded by today's own ops-driven
   restarts (see job 1 above).** Root cause unproven either way — don't treat the new figure as
   confirmed without a quiet-window re-read.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed restored, no action needed.** S131 ran entirely on Sonnet, no `/model` switch.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New this
session:** `marvinctl grep`/`ls`/`stat` each have a sharp edge (whitespace-free patterns, no glob,
`Size:`'s indentation) — see §3's new bullet before writing another `marvinctl`-based tool.

_Last updated: 2026-09-08 (S131, ~22:55 ET). Session summary: user asked to close out the open
ops backlog; triaged six items, started with the two mechanical NAS-ssh ports (ops#286, ops#287)
per user direction. Ported `freeze_baseline.py`/`stall_baseline.py` (PR #369) then, after a design
discussion on soak_check.sh's larger scope (confirmed by testing live against marvin: the
image-tag-vs-ID bug, the monitor-unit primitive, the windowing approach), fully rewrote
`soak_check.sh` and its test suite (PR #371). Both merged this session (owner-approved each time);
#371 needed a mid-flight `dev` merge after #369 landed first. Relayed status to a concurrent ops
session via `send_message` per this repo's cross-repo SOP, including a proactive flag on ops#265
that ops then verified and closed the loop on. Full account: DEC-0152._
