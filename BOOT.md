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

## ▶ Resume here (S135 → S136)

### What's settled (do not re-derive)

**`eaglehunt-ops#299`'s final open item — the repo-wide sweep for stale `marvin`-repo references
after the 2026-09-08 HeartOfGold merge (weewx-rtldavis#378) — done. One stale reference found and
fixed; everything else in this repo already pointed correctly at `heartofgold`.**

- **Full sweep, this repo's own tooling only** (`git grep` over every tracked file outside
  `ARCHIVE/`): searched for the old repo path (`~/Projects/marvin`, `marvin.git`), the old tracker
  file names (marvin's `STATE.md`/`DECISIONS.md`, as distinct from this repo's own `docs/DECISIONS.md`),
  and `marvin`+`repo` phrasing. Every other `marvin` mention in this repo (~400, across 31 files) is
  the host/tenant name — unchanged by the rename — not the old build repo.
- **One fix:** `docs/DECISIONS-FULL.md`'s DEC-0118 entry (dated 2026-08-28/29, provenance — not
  rewritten) named `` `marvin` repo, `MARVIN-DEC-0062` `` as a discoverability path. Added a one-line
  pointer note after the entry rather than editing the historical prose: the repo is now
  `~/Projects/heartofgold`, `MARVIN-DEC-0062` now lives in `heartofgold/MARVIN-DECISIONS.md`.
- **The estate block itself (`CLAUDE.md` "Estate context", added `#378`) was already correct** —
  not touched, per this session's own instructions.
- **Model tier: session inherited Fable 5.1** (desktop-app floor is inert, per `AGENT-ECONOMY.md`
  §3 — some prior session's escalation persisted). User switched to `claude-sonnet-5` mid-session;
  floor now correctly re-pinned at Sonnet. Nothing further to restore.

### ▶▶ S136 JOB LIST

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

### Current state (S135 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` **restarted 23:42:48 EDT 09-07 to fix the `#370` crash loop** (DEC-0154) — otherwise unaffected this session. `v2.0.16` as `:marvin-live`, weewx 5.5.0, gain 372, runs as `t-weewx` (996:986) since DEC-0147 |
| InfluxDB | marvin, `weewx-influxdb.service` — unchanged this session |
| weewx-monitor | unchanged this session — flock-based lock (PR #367) still live and stable; `#373`'s alert-class question still open (filed this session) |
| Reception | **recovered 23:45:00 EDT 09-07** (DEC-0154); whether the new dongle position is better/worse than the old one is unmeasured (job 5) |
| Foundation | fully decommissioned (unchanged) |
| `main`/`dev` | S135: PR #<PR#> (`eaglehunt-ops#299` sweep, docs-only) opened against `dev` via `land`, merge pending (owner Class C). `main` still weeks behind, unpromoted |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · unchanged this session |
| GitHub Releases | unchanged this session |
| Tenant tree | unchanged this session — real `git` checkout since S129, `marvinctl pull` self-service |
| Trackers | repo: #337 open (marvin's file to fix) · #370 CLOSED-worthy but left to the owner/marvin to close (physical siting question, job 5) · #373 open (DEC-0154's filed monitor question) · ops: #299 commented with PR #<PR#> this session (closing condition, pending heartofgold's REPO-NOTICES 6/6) · #265/#110 open, correctly gated/deferred |

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

**Floor confirmed at Sonnet, no action needed.** Session inherited Fable 5.1 (desktop-app floor is
inert — a prior session's escalation persisted, `AGENT-ECONOMY.md` §3); user switched to
`claude-sonnet-5` mid-session, which is both a persisting floor change and the correct floor for
this execution work. Nothing to restore going into S136.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). Nothing new filed
this session — the sweep came back clean.

_Last updated: 2026-09-09 (S135). Session summary: follow-up to the 2026-09-08 HeartOfGold
bootstrap (weewx-rtldavis#378, `eaglehunt-ops#299`) — swept this repo for every reference to the
old `marvin` build-repo path and old tracker file names (`STATE.md`/`DECISIONS.md`) left behind by
the merge into `~/Projects/heartofgold`. Found exactly one stale reference (a discoverability
pointer inside DEC-0118's dated, provenance-protected text in `docs/DECISIONS-FULL.md`) and added a
one-line pointer note beside it rather than rewriting history; every other `marvin` mention in this
repo already referred to the still-current host/tenant, not the retired repo. No living doc needed
a change — the estate block (`CLAUDE.md`, `#378`) was already correct. PR #<PR#> opened against
`dev` via `land`; `eaglehunt-ops#299` commented with the PR number._
