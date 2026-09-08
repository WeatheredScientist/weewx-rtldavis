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

## ▶ Resume here (S133 → S134)

### What's settled (do not re-derive)

**The `eaglehunt-ops` S42 full-history-enumeration ask is CLOSED. All four infrastructure-caused
gaps since 2026-05-19 (of 684 checked) are now accounted for: #1 (09-04 cutover) via ERR-0007
already; #2 (09-07 tree-swap, this session) via ERR-0009, declined as unrecoverable; #3 (09-07
reception outage, S132) via ERR-0008; #4 (09-07 hardware-install) already backfilled via DEC-0151.
No new ops issue needed — confirmed with the coordinating ops session.**

- **ERR-0009: the 09-07 14:15:00→14:26:00 EDT gap (DEC-0150's tenant-tree swap) has no recovery
  source.** Same WeatherLink→WU method as ERR-0003/ERR-0005/ERR-0008 — this time WU's own public
  table has no reading between 2:15 PM and 2:29 PM that day either. Both the archive boundary and
  the WU-side gap were found by a concurrent `eaglehunt-ops` session (S42) enumerating every
  archive gap since 2026-05-19, then **independently re-verified here** before writing anything
  down (this repo's standing rule — never accept a peer session's report unchecked). No DEC entry:
  nothing was decided, this documents a declined recovery, same shape as ERR-0004/ERR-0006.
- **S132's ERR-0008 (the `#370`/`#373` reception-outage backfill) merged as PR #374** — see prior
  session for that account; unchanged this session.
- Full account: `docs/DATA_ERRATA.md` ERR-0009 (no DEC needed, see above).
- **Concurrent work not part of this closeout:** another live session has uncommitted staged
  changes on branch `s132-tenant-mounts` (`ops/tenant_mounts.py`, `tests/test_tenant_mounts.py`) in
  the shared primary checkout — not touched here, this session worked from an isolated worktree
  instead. Whoever owns that branch should close it out on its own terms.
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.

### ▶▶ S134 JOB LIST

1. **Re-run `ops/freeze_baseline.py` after a quiet stretch** (no ops-driven restarts in the window)
   to check whether S131's AT-RECORD-MAX reading (4.03/day vs DEC-0083's ~1.49/day baseline) holds
   or was an artifact of S130/S131's own incident/deploy activity. If it holds, root-cause; if not,
   no further action needed. Still not re-read as of this note.
2. **Fix DEC-0150's own runbook** — [ops#288](https://github.com/WeatheredScientist/eaglehunt-ops/issues/288)
   (filed by ops, carried from S131): derive a tree-swap restore list from every unit's bind-mount
   sources rather than from memory/git-diffing alone.
3. Consider porting `ops/backfill_influx.py` to run natively against marvin (NAS-path and
   `localhost:8086` defaults) — three incidents now (DEC-0151, DEC-0153, and this session's
   ERR-0009 attempt) have solved this ad hoc inside the live container rather than fixing the tool
   itself; still not filed as its own item.
4. **`#373`** — decide whether `weewx_monitor.py` needs a distinct alert class for a
   full outage vs. partial degradation (carried from S132, not investigated further).
5. **Check in on branch `s132-tenant-mounts`** (see concurrent-work note above) — if abandoned or
   stale by S134, find out why before assuming it's still in progress.
6. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337).
7. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`) exactly
   as S126 left them — none are due, none are blocked on anything weewx can do alone.
8. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
9. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S122 and earlier still inline, past the ~3-session guideline (pre-existing debt,
   carried again, one session closer).

### Current state (S133 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` unaffected this session (docs-only, no config/code touched). `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session (ERR-0009 has nothing to write) |
| weewx-monitor | unchanged this session — flock-based lock (PR #367) still live and stable; `#373`'s alert-class question still open |
| Reception | unchanged this session (recovered per S132's own account) |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S133: PR pending for ERR-0009 docs (worktree branch `s132-err0009`). `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337, #370, #373 open (physical/monitor fixes tracked, not this session's to close) · ops: S42's enumeration ask CLOSED this session, #288/#265/#110 open, correctly gated/deferred |

## Blockers

1. **weewx process freezes — was 1.31/day median 240s (DEC-0088); S131's live read showed 4.03/day
   AT RECORD MAX, plausibly confounded by that session's own ops-driven restarts.** Root cause
   unproven either way — re-read after a quiet window (job 1 above), still not done.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. **`#373`** — monitor can't distinguish full outage from partial degradation (job 4).
5. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed restored, no action needed.** S133 ran entirely on Sonnet, no `/model` switch.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New this
session:** when the shared primary checkout has another live session's uncommitted work on a
different branch, use `git worktree add <scratchpad-path> -b <branch> origin/dev` instead of
touching it — this repo's own style notes already prescribe this for subagents, it applies just as
much to a concurrent peer session.

_Last updated: 2026-09-08 (S133). Session summary: a concurrent `eaglehunt-ops` session (S42)
enumerated every archive gap since 2026-05-19 at the owner's request and found one more
infrastructure-caused gap needing attention — the 09-07 14:15–14:26 EDT DEC-0150 tree-swap gap.
Independently re-verified both the archive boundary and the claimed WU-side gap before writing
anything down, rather than trusting the peer session's report outright. Confirmed unrecoverable
(WU's own table has nothing for that window either) and logged as ERR-0009. This closes out S42's
full-history-enumeration ask — all four known infrastructure gaps now have matching doc entries._
