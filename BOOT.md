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

## ▶ Resume here (S145 → S146)

### What's settled (do not re-derive)

**v2.0.17 has run in prod since 2026-09-28 13:32:39 ET (DEC-0204); S145 changed nothing on marvin.**
DEC-0203's monitor gate is verified live: the 6-hourly reports read `ISS battery: OK -- flag clear in
all 355/360/360 healthy-reception minutes` (S144's job 1, done).

**S145 was a code audit, DEC-0205.** Six read-only reviewers covered the whole tree at `7d06cbf` and
found 39 items. The ten high ones are filed as #402–#411 (plus `eaglehunt-ops#358`, private) and
fixed on seven PRs, #412–#418, all squash-merged into `dev` on 2026-09-29 (07:2x–08:2x ET) behind
green checks. Issues #406–#411 are closed; #402–#405 stay open until the fixes reach prod. The combined tree is
green: 591 tests in both collection orders, ruff, mypy, secret gate, 160 planted gate controls (was
63). The 29 medium/low items live in `docs/CODE_REVIEW_S145.md`. `patch/rtldavis-dupgate.patch`
applies at offset 0, fuzz 0 to today's upstream tarball, so S144's job 2 is moot unless the next
build log disagrees.

### ▶▶ S146 JOB LIST

1. **Release v2.0.18** per `CONSTANTS.md` Release mechanics: #412's seed fix and ws.6 banner, #414's
   rain units. At the same deploy set `ops/soak_check.sh`'s `EXPECT_DRIVER` to `0.20+ws.6` (its image
   default now reads the Dockerfile stamp). `git tag -a v2.0.18` + `gh release create` ride the
   promotion (CONVENTIONS).
2. **Deploy the monitor** (#413): `marvinctl --tenant weewx pull`, then a deliberate
   `restart weewx-monitor.service`; verify the `Remedy armed:` line and sha = `dev`; add the
   heartofgold CHANGELOG line (estate rule).
3. **ROADMAP tripwire fires this session** (due S146): run the full reconciliation pass. S145 shipped
   no roadmap line.
4. **Owner decisions the fixers left**: (a) #408 — OgoXe's `StdService.__init__` row says "reason
   not recorded"; mark it deliberate or restore upstream's call. (b) #405 — OWM and Windy rain has
   published 10× low since 2026-05-21; ERR entry or not. (c) File the gate's detector holes from
   #415's mutation pass as a `tier:mid` issue: quoted key names unscanned, `SECRET_KEY` /
   `private_key` / `access_key` missed, allow terms applied per line. (d) Put
   `CHECK_SECRETS_REQUIRE_IDENTIFIERS=1` in the owner's shell profile, never in CI.
5. **Inbox**: `eaglehunt-ops#357` (repo:weewx, tier:mid) asks for WeatherLink `bar_absolute` in the
   loop feed for HLF's barometer check. Unread at S145.
6. Carry forward: freeze lead (blocker 1), measure when next working freezes; `dev` → `main`
   promotion (`main` is v2.0.13), owner's timing; S126's job-8 items, the lheijst/rtldavis#7 watch,
   ops#306's residual, the local-infra marvin entry: none due.

## Current state (S145 close)

| Thing | State |
|---|---|
| Prod | marvin, **`v2.0.17`** as `:marvin-live` (image `621710f7…`) since 2026-09-28 13:32:39 ET, weewx 5.5.0, gain 372, `t-weewx` (996:986). `:v2.0.16`/`:v2.0.15`/`:v2.0.14` local for rollback. Unchanged in S145 |
| InfluxDB | marvin, `weewx-influxdb.service`, unchanged |
| weewx-monitor | sha = `dev`@`7d06cbf` (`8a07efd7…`), `REMEDY_MODE=none`, battery gate verified; #413 pending (job 2) |
| Reception | 99.9% mean at USB port `5-1` |
| `main`/`dev` | `dev` = `7d06cbf` + the seven S145 squash merges (#412–#418). `main` is still v2.0.13, unpromoted (job 6) |
| Docker Hub | `:v2.0.16` · `:latest` = v2.0.13 · v2.0.17 not pushed (`eaglehunt-ops#265`) |
| Trackers | repo: #402–#405 open until deploy (jobs 1–2), #406–#411 closed; #380 informational · ops: #358 new (private, owner ask) · #357 new, unread (job 5) · #265/#110 deferred-trigger · #306 residual · #344 macOS LAN (this desktop session reached marvin) |

## Blockers

Unchanged from S144: 1 freeze mechanism (DEC-0068/0094; lead: corrupt frames at outage onsets),
2 RF-dead root cause (DEC-0081), 3 ERR-0005, 4 the 6-hourly email watch. Nothing new.

## Model tier

**S145 ran on Fable 5.1 throughout** (a corpus audit is long-horizon judgment; declared in the first
reply). Subagents: Sonnet ×5 and Haiku ×1 as reviewers; Opus ×1 and Sonnet ×6 as fixers, each in an
isolated worktree. No `/model` switch. **Desktop app:** the model persists. S146's jobs 1–3 are
execution (Sonnet).

## Gotchas — they live in `docs/GOTCHAS.md`

**Read it when:** trusting any tool's zero/empty/green (§1) · any PR/merge or handoff write (§2) ·
any NAS, marvin or campaign task (§3) · judging a component live, dead, or shipped (§4). **Read §3
before the marvin task, not after.** **New this session:**
- §1: a Haiku cross-referencer reported zero issue citations in code and zero missing DEC ids. Both
  were false zeros (29 and 2 by hand). A subagent's zero is a claim.
- §1: `patch` fuzz is tool-dependent. Apple patch and `git apply` saw offset 0, fuzz 0 where GNU
  patch in the build log said fuzz 2.
- §2: `gh issue create` in a shell loop must not split fields on `:`; titles carry colons. Ten issues
  failed with mangled labels before the delimiter changed.
- §2: `gh pr edit` and `gh issue comment` bodies must come from a real file via `--body-file`; the
  comment guard fails closed on heredocs and substitutions (OPS-DEC-0216).

## Files needed at session start

This file + `CONSTANTS.md` + `MANIFEST.md` — nothing else. Everything else is pulled by name from
`MANIFEST.md`, mid-session, when the task touches it. Full rationale: `CLAUDE.md`'s Documentation
map (DEC-0063).

## Style

Git workflow, secrets handling, and the exact test-gate commands: `docs/CONVENTIONS.md`.

_Last updated: 2026-09-29 (S145). Audit DEC-0205; #402–#411 filed and fixed; PRs #412–#418 merged
to `dev`. Job 1 is v2.0.18, job 2 the monitor restart, and the ROADMAP tripwire fires at S146._
