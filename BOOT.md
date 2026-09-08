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

## ▶ Resume here (S134 → S135)

### What's settled (do not re-derive)

**`#370`/`#373` (the reception-outage crash loop) diagnosed AND fixed this session, not just
tracked — DEC-0154. `eaglehunt-ops#288` (the tree-swap restore-list gap) closed this session with
`ops/tenant_mounts.py` — DEC-0155, PR #375 merged.**

- **The `#370` outage's real cause: a stale container device view (DEC-0075's predicted "stale
  container view" signature, seen live for the first time), not the RF/hop-tracking problem #370
  itself reported.** `weewx.service` started before the owner's physical dongle-port move, so its
  one-time `/dev/bus/usb` snapshot never saw the new device node; `rtldavis` crash-looped silently
  for 71 minutes, zero archive records. Fixed with `marvinctl --tenant weewx restart weewx.service`
  (self-service) — re-snapshots the device tree, no owner gesture needed. Recovery verified against
  the archive directly: clean records resuming 23:45:00 EDT. Full account: DEC-0154.
- **`#373` filed for the monitor's real blind spot, not fixed here** — its own log read identically
  (`WINDOW: 0/21`) across the whole 71-minute outage whether the station was degraded or fully dead.
  A design question for DEC-0081/DEC-0120's existing alert-class machinery, still open.
- **`ops/tenant_mounts.py` derives a tree-swap's restore list from live unit *files*** (periodic
  units print no `ExecStart` in `marvinctl unit`'s runtime status once inactive — files are
  authoritative regardless), classified TRACKED/IGNORED/UNDOCUMENTED against this repo's own git
  tree. Live-verified against marvin: independently reproduces DEC-0151's `influxdb/`/`nas-lease`
  finding by a different method. 16 tests, full suite green, merged PR #375. Full account: DEC-0155.
- **Tracker sweep closed inline:** #337 is stale (this repo's own `ops/weewx-monitor.service:95`
  already has the fix; the bug is only in marvin's un-synced vendored copy — nothing to change
  here, marvin's own follow-through to re-vendor). ops#286/#287 confirmed already closed (S131).
  ops#265 confirmed unchanged (wired, unexercised, waiting on the next version cut). ops#110
  acknowledged (2027 sky-sensor plan, nothing to build yet, no blocking questions).
- **`eaglehunt-ops` S42's full-history-enumeration ask, closed by S133 before this session's own
  closeout ran** — unchanged here, see prior session's account. This session found and fixed one
  more instance of S42's own flagged mislabel pattern (`#373`'s issue body cited `eaglehunt-ops#370`
  instead of this repo's own #370) — `docs/GOTCHAS.md` §2 now names the trap.
- **Model tier: this session ran entirely on Sonnet, no escalation.** Nothing to restore.

### ▶▶ S135 JOB LIST

1. **Re-run `ops/freeze_baseline.py` after a quiet stretch** (no ops-driven restarts in the window)
   to check whether S131's AT-RECORD-MAX reading (4.03/day vs DEC-0083's ~1.49/day baseline) holds
   or was an artifact of incident/deploy activity — this session's own `weewx.service` restart
   (DEC-0154) adds one more confound to wait out, not fewer. Still not re-read as of this note.
2. Consider porting `ops/backfill_influx.py` to run natively against marvin (NAS-path and
   `localhost:8086` defaults) — three incidents now (DEC-0151, DEC-0153, DEC-0155's sibling
   ERR-0009 attempt) have solved this ad hoc inside the live container rather than fixing the tool
   itself; still not filed as its own item.
3. **`#373`** — decide whether `weewx_monitor.py` needs a distinct alert class for a
   full outage vs. partial degradation (filed S134/DEC-0154, not investigated further).
4. **Marvin's own follow-through, not weewx's action item, just watch for it:** re-vendor
   `weewx-monitor.service` from the merged `REMEDY_SYSTEMCTL` fix (issue #337).
5. **Whether reception at the dongle's new physical position (`5-1`) is actually better or worse
   than the old `7-1.2` cluster is unmeasured** — DEC-0154 fixed the crash loop, not this open
   question from #370's own original ask; needs a longer `rxCheckPercent` read once enough windows
   accumulate.
6. Carry forward job 8's remaining untouched items (EnvironmentFile, `marvin-release.sh`) exactly
   as S126 left them — none are due, none are blocked on anything weewx can do alone.
7. **Watch [lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7) for a maintainer reply** —
   repo's been dormant since 2023-12-22, don't chase it, just notice if it moves.
8. `CONSTANTS.md` infra re-verify (S105-era, still stale outside what S129/S130 touched) ·
   `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `CHANGELOG.md` archive rollup
   overdue — S122 and earlier still inline, past the ~3-session guideline (pre-existing debt,
   carried again, one session closer).

### Current state (S134 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` **restarted 23:42:48 EDT 09-07 to fix the `#370` crash loop** (DEC-0154) — otherwise unaffected this session. `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session |
| weewx-monitor | unchanged this session — flock-based lock (PR #367) still live and stable; `#373`'s alert-class question still open (filed this session) |
| Reception | **recovered 23:45:00 EDT 09-07** (DEC-0154); whether the new dongle position is better/worse than the old one is unmeasured (job 5) |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S134: PR #375 (`eaglehunt-ops#288`/DEC-0155) merged to `dev`. `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (marvin's file to fix) · #370 CLOSED-worthy but left to the owner/marvin to close (physical siting question, job 5) · #373 open (DEC-0154's filed monitor question) · ops: #288 CLOSED this session · #265/#110 open, correctly gated/deferred |

## Blockers

1. **weewx process freezes — was 1.31/day median 240s (DEC-0088); S131's live read showed 4.03/day
   AT RECORD MAX, plausibly confounded by that session's own ops-driven restarts** — now joined by
   this session's own restart (DEC-0154). Root cause unproven either way — re-read after a quiet
   window (job 1 above), still not done.
2. **RF-dead episode root cause unknown** (DEC-0081) — first clean post-fix baseline read taken
   S126 (100% mean, zero episodes observed yet); watch continues, re-read after a longer stretch.
3. **ERR-0005** — unchanged.
4. **`#373`** — monitor can't distinguish full outage from partial degradation (job 3).
5. 6-hourly reception email watch — unchanged since S125.

## Model tier

**Floor confirmed restored, no action needed.** S134 ran entirely on Sonnet, no `/model` switch.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New this
session (§2):** a bare `#N` written while thinking about a cross-repo incident silently inherits
the wrong repo — cite the number from a fresh `gh issue view`/grep, not from whichever repo felt
right in the moment (this session's own `#373` issue body got it wrong once, same slip S132's
`ERR-0008` draft made).

_Last updated: 2026-09-08 (S134). Session summary: checked in on the full tracker sweep (repo +
ops). Found `#370`'s crash loop was still live and diagnosed it independently — a stale
`/dev/bus/usb` container view after the physical port move, DEC-0075's predicted signature, fixed
with a self-service `weewx.service` restart; filed `#373` for the monitor's real blind spot rather
than patching it under pressure. Built and merged `ops/tenant_mounts.py` for `eaglehunt-ops#288`,
independently reproducing DEC-0151's finding. Investigated a user-reported missing-InfluxDB-data
question, corrected an over-hasty "unrecoverable" conclusion once a concurrent session's WU-backfill
approach surfaced. Participated in `eaglehunt-ops` S42's cross-repo gap enumeration and fixed one
more instance of its flagged issue-number mislabel, in this repo's own #373._
