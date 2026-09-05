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

## ▶ Resume here (S124 → S125)

### What's settled (do not re-derive)

**InfluxDB serves from marvin since 2026-09-04 22:35:02 ET (DEC-0141 design, DEC-0142 execution;
ops#270).** `weewx-influxdb.service` in `/weather.slice`, `influxdb:2.7.12`, `--user 996:986`,
trees `/srv/docker/weewx/influxdb/`, self-service lifecycle. weewx publishing to it since 22:43:16;
dashboard's eh-proxy + event-detect repointed and verified end-to-end through the public site
(`verify_archive_fresh.py` GO 22:46). **Foundation hosts no weather workload** — its `influxdb`
container is stopped, `--restart=no`, retained as rollback until ops#260 step 4. As-run record with
every deviation: `docs/INFLUXDB-MIGRATION.md` §8. `weewx.conf` **and** `weewx.conf.rx-baseline`
(tenant ROOT) both point at marvin.

**Reception metric chain DEC-0134→0139 complete; `v2.0.16` is prod** (banner `0.20+ws.5`, gain
372), `main` = `prod-baseline-20260904`, Hub `:v2.0.16`; `:latest` = v2.0.13 (owner's gesture only).
**The running image tag is now `:marvin-live`** (alias of v2.0.16 — marvin tagged it during stage 0,
MARVIN-DEC-0121/0122, which also closes ops#257 limb 2's tag step by marvin's hand). Campaigns A–D
untested-not-rerun (`docs/ROADMAP.md` P2).

**ops#265 is WIRED:** next release publishes with `marvinctl --tenant weewx push
weatheredscientist/weewx-rtldavis:vX.Y.Z` (versioned tags only). Nothing to do until a release.

**Also settled:** monitor deploy path (S119: owner transport, self-service restart, verify by sha +
`Remedy armed:`); loop period `(41 + id)/16` s (#313); a marvin release is two Class C
confirmations (`docs/GOTCHAS.md` §3); #320/#314 closed S123 (DEC-0140); #327 filed.

### ▶▶ S125 JOB LIST

1. **InfluxDB stage 3 (ops#270) — Sonnet, mechanical.** **Backfill done, S125: 28 posted (not 29—
   22:40–22:42 don't exist in SQLite either, `weewx.service`'s own restart; [ERR-0007](docs/DATA_ERRATA.md),
   `docs/INFLUXDB-MIGRATION.md` §8), verified independently via `influx query`.** NAS-LEASE
   `BACKLOG.md` item closed (PR #336). Remaining: (b) marvin re-installs the unit with
   `SuccessExitStatus=2` (already on `dev` — confirmed live unit still lacks it). (c) owner deletes
   `influxdb-final-20260904-{data,config}.tar` from the marvin-data share (token store inside). (d)
   `weewx-influxdb-backup.service/.timer` drafted (PR #336, mirrors `weewx-db-dump`), needs
   installing on marvin — verify the CLI operator config first. (e) ops/dashboard doc rows (ops
   `NAS-RUNTIME.md`, `CONSTANTS.md` §5; dashboard `MARVIN-MIGRATION.md`) — theirs, nudge. (g) weewx's
   section of the ops#260 drill.
2. **#331 — GitHub Releases backfill** v2.0.12–16 + write the step into CONVENTIONS/closeout. Owner
   go per step (public).
3. **#327 — GPLv3 §5(a) notice in the dupgate `main.go`** — ride the next image cut.
4. **ops#257 limb 2 — remaining half:** the tag exists; confirm marvin's unit + `daemon-reload` half
   is complete (the installer already swept the re-pin in), then close.
5. **Retire the campaign residue** — `weewx-rx-experiment.timer` + the unimplemented `campaign.inhibit`
   at `ops/weewx-monitor.service:88`.
6. **`ExecStop=docker stop` in `weewx.service`** (DEC-0008) — owner root-edit path.
7. **Upstream issue/PR to `lheijst/rtldavis`** — draft in `docs/upstream/`, owner tone review first.
8. **Post-fix baseline watch** — RF-dead episodes (blocker 2), observation only.
9. Audit Phase 2 A/B/C · `campaign_analyze.py` port (ops#250) · logrotate for marvin `logs/` · ops#110.

**Carried forward:** `CONSTANTS.md` infra re-verify (the InfluxDB rows were rewritten S124; the
rest is S105-era) · `docs/ARCHITECTURE.md` mount table still NAS-pathed (S30) · `docs/ROADMAP.md`
tripwire **S126**.

### Current state (S124 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` in `/weather.slice`; **`v2.0.16`** as `:marvin-live`, weewx 5.5.0, gain 372, restarted 09-04 22:40:42 ET for the Influx repoint |
| InfluxDB | **marvin**, `weewx-influxdb.service` since 09-04 22:35:02 ET, v2.7.12; `weewx` 16 shards, `eh_rollup` 16 shards; backfilled S125 (28 records) — **22:40–22:42 permanently absent** (ERR-0007), not a hole to fill |
| Foundation | no weather workload; stopped `influxdb` (rollback) + dashboard's idle `eh-proxy`; read-only `weewx-data` overlay |
| `main` | `prod-baseline-20260904`; `dev` ahead by doc PRs only |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · self-service `push` LIVE (ops#265) |
| GitHub Releases | dead since v2.0.11 — #331, job 2 |
| Monitor | dev tip's file (sha `147f3eff…`); `REMEDY_MODE=restart_unit` armed |
| Git | S124: PR #334 (design) + the cutover-record PR → `dev` |
| Trackers | repo #327, #331 open · ops **#270** (stage 3 open), #260 (drill pending), #264, #265 (close on first push), #257 limb 2 (job 4), #250, #110 |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — measurable post-DEC-0136; job 8.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email arriving again since 09-03; watch, don't chase.

## Model tier

S124 opened on Sonnet; the owner escalated to **Fable** with a bare `/model` for the design and the
live cutover — **the desktop switch PERSISTS** (OPS-DEC-0036/0062): `~/.claude/settings.json` still
reads `sonnet`, so the app's own store holds Fable — restore it there. S125 job 1 is mechanical →
**Sonnet**. State the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New traps land
there.** S124's four are in `docs/INFLUXDB-MIGRATION.md` §8 for now: `nasctl ls` permission
false-zero; `&&` after a multi-file `sed` hides the verification grep; `marvinctl <verb> <unit> --now`
order; influxd exits 2 on SIGTERM. Move them to GOTCHAS at S125.

_Last updated: 2026-09-04 (S124 close, ~22:50 ET). Session summary: opened on the owner's "InfluxDB
porting" focus; measured, designed (DEC-0141, PR #334), then — owner's call — executed the same night
(DEC-0142): Foundation stopped 22:13:35, marvin store live 22:35:02, weewx publishing 22:43:16,
dashboard verified end-to-end 22:46. Two Class C NAS gestures, three owner-hands marvin gestures._
