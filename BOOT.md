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

**Reception metric chain DEC-0134→0139 complete; `v2.0.16` is prod** (marvin, since 09-03 20:29 ET,
gain 372, banner `0.20+ws.5`), promoted to `main` = `prod-baseline-20260904`, on Docker Hub as
`:v2.0.16` (byte-identical, `CONSTANTS.md` Release row); `:latest` = v2.0.13, moves only by the
owner's gesture. `DISC-0001` in `docs/DATA_ERRATA.md` carries both boundaries. Campaigns A–D are
*untested*, not re-run (`docs/ROADMAP.md` P2).

**ops#265 is WIRED (09-04 evening, ops session FYI):** marvin installed the `push`/`tag` verbs and
the owner placed the Hub PAT. The next release publishes with `marvinctl --tenant weewx push
weatheredscientist/weewx-rtldavis:vX.Y.Z` (versioned tags only; `:latest` stays the owner's). No
manual save/scp/load/push again. Nothing to do until a release.

**InfluxDB is the LAST weather workload on Foundation (ops#260 step 3).** HLF (09-04 12:26 ET) and
EHWD (09-04 ~19:35 ET) both cut over; ops posted the owner's ask for weewx's plan. S124 answered
with **DEC-0141** + the runbook `docs/INFLUXDB-MIGRATION.md` + `ops/weewx-influxdb.service`.
Settled there: stopped-server raw copy of the v2.7.12 store (**16.4 MB**, measured), container/unit
`weewx-influxdb` inside the manifest globs (self-service lifecycle, no manifest change), `--user
996:986`, pinned image `--pull=never`, Foundation instance kept stopped `--restart=no`. All three
consumers already run on marvin — weewx (`weewx.conf` **and** `.rx-baseline`), dashboard
`proxy.env` + `event-detect.env`; HLF has none. **Nothing executed yet.**

**Monitor deploy path (S119):** transport owner-run, restart self-service, verify by sha +
start-after-mtime + `Remedy armed:`. #316 fixed live 08-30, untested end-to-end (no stall since).

**Also settled:** loop period `(41 + id)/16` s (#313). ops#256 closed empty. A marvin release is
**two** Class C confirmations (`docs/GOTCHAS.md` §3). #320/#314 closed S123 (DEC-0140); #327 filed.

### ▶▶ S125 JOB LIST

1. **InfluxDB move — execute `docs/INFLUXDB-MIGRATION.md`, stage by stage.** Stage 0: marvin
   vendors + installs the unit, pulls `influxdb:2.7.12`, creates `/srv/docker/weewx/influxdb`;
   dashboard preps its two env edits. Stage 1: dark-parallel from a snapshot (start, verify, stop,
   wipe). Stage 2: one attended window (~20–30 min; **not** 01:00–01:30 or 03:10–03:40 ET); the
   archive gap is backfilled from SQLite with the DEC-0119-fixed `ops/backfill_influx.py` — **the
   copy on marvin is the old buggy one**, transport first. Stage 3: docs, backup timer, drill section.
   Ledger: [ops#270](https://github.com/WeatheredScientist/eaglehunt-ops/issues/270) + ops#260. Sonnet-shaped: the design is settled.
2. **ops#257 limb 2 — the `tag` step is weewx's, in order** (MARVIN-DEC-0116): marvin installs
   `tag` → weewx runs `marvinctl --tenant weewx tag weatheredscientist/weewx-rtldavis:<running>
   …:marvin-live` (read `<running>` off `inspect weewx-rtldavis-v2`) → marvin installs the unit +
   `daemon-reload`. `tag` is installed now (ops#265's wiring) — check whether marvin's unit half is.
3. **#331 — GitHub Releases backfill** (`git tag v2.0.12`…`v2.0.16` + `gh release create`) **and
   write the step into CONVENTIONS.md / the closeout skeleton.** Public → owner go per step.
4. **#327 — GPLv3 §5(a) notice in the dupgate `main.go`** — Go source → build + Dockerfile tripwire +
   deploy; ride the next image cut.
5. **Retire the campaign residue** — `weewx-rx-experiment.timer` (`marvinctl disable --now`) and the
   unimplemented `campaign.inhibit` lifecycle at `ops/weewx-monitor.service:88`.
6. **`ExecStop=docker stop` in `weewx.service`** (DEC-0008) — owner root-edit path.
7. **Upstream issue/PR to `lheijst/rtldavis`** — draft in `docs/upstream/`, owner tone review first.
8. **Post-fix baseline watch** — RF-dead episodes (blocker 2), observation only.
9. Audit Phase 2 A/B/C · `campaign_analyze.py` port (ops#250) · logrotate for marvin `logs/` ·
   ops#260 drill (weewx's section, after job 1) · ops#110 (2027 build).

**Carried forward:** NAS-LEASE cross-host wiring — **moot once job 1 ships** (DEC-0141; close the
`BACKLOG.md` item then) · `CONSTANTS.md` infra re-verify · `docs/ROADMAP.md` tripwire **S126**.

### Current state (S124 close)

| Thing | State |
|---|---|
| Prod | marvin, `weewx.service` in `/weather.slice`, `docker run --rm`; **`v2.0.16`**, weewx 5.5.0, gain 372, since 09-03 20:29:06 ET |
| `main` | `prod-baseline-20260904`; `dev` ahead by doc PRs only |
| Docker Hub | `:v2.0.16` (09-04 11:30 ET, owner route) · `:latest` = v2.0.13 · **self-service `push` LIVE** (ops#265) |
| GitHub Releases | dead since v2.0.11 — #331, job 3 |
| InfluxDB | **still on Foundation**: `influxdb:2.7` = v2.7.12, 16.4 MB, up since 06-19, 8086 LAN-published. Runbook written, nothing executed — job 1 |
| Monitor | dev tip's file (sha `147f3eff…`); `REMEDY_MODE=restart_unit` armed |
| Git | S124: PR (runbook + unit + DEC-0141 + ROADMAP P1.8) → `dev` |
| Trackers | repo #327, #331 open · ops #260 (step 3 = us), **#270** (the InfluxDB move — ledger), #264 (closes on the next green sweep), #265 (wired — close on first self-service push), #257 limb 2, #250, #110 |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081) — measurable post-DEC-0136; job 8.
3. **ERR-0005** — unchanged.
4. 6-hourly reception email arriving again since 09-03; watch, don't chase.

## Model tier

S124 opened on Sonnet; the owner escalated to **Fable** for the InfluxDB design with a bare `/model`
— **the desktop switch PERSISTS** (OPS-DEC-0036/0062): restore Sonnet at close or the next session
inherits Fable. S125 job 1 is execution of a settled design → **Sonnet**; escalate only if a stage
finds the design wrong. State the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS or campaign task (§3) · judging a component live, dead, or shipped (§4). **New traps land
there.** S124's two — the `nasctl ls` permission false-zero and the stale compose port comment — are
recorded in the runbook's §0.

_Last updated: 2026-09-04 (S124 close). Session summary: opened on the owner's "InfluxDB porting"
focus, escalated to Fable; measured Foundation's store and marvin's tenant shape, wrote the runbook,
the unit and DEC-0141, filed the ops issue and answered ops#260's owner ask. No prod touched._
