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

## ▶ Resume here (S123 → S124)

### What's settled (do not re-derive)

**The DEC-0134→0139 chain is complete: both `rxCheckPercent` distortions found, fixed, deployed,
confirmed.** Repeat-packet dedup (`v2.0.15`, DEC-0134→0136) and the slot-count denominator
(`v2.0.16`, DEC-0137→0139) each independently inflated the metric; both are gone. `v2.0.16` running
on marvin since 2026-09-03 20:29:06 EDT, no CRITICAL since restart, gain 372 holds, driver banner
`0.20+ws.5`. First fully-post-cutover monitor window: **0/360 records over 100%**, down from the
pre-fix 197/360 (55%) — **#317 closed** (DEC-0139). `docs/DATA_ERRATA.md`'s `DISC-0001` carries both
boundaries. Campaigns A-D remain *untested*, not re-run (no reason to — see `docs/ROADMAP.md` P2).

**`v2.0.16` promoted to `main`, tagged `prod-baseline-20260904`** (PR #324, 267 commits S75->S122).
`main`/`dev` are in sync. **Docker Hub has `:v2.0.16`** (owner-pushed 09-04 11:30 ET, verified
byte-identical to prod — `CONSTANTS.md` Release row); `:latest` still `v2.0.13`. The self-service
publish path is [ops#265](https://github.com/WeatheredScientist/eaglehunt-ops/issues/265) — for the
*next* release. **GitHub Releases stopped at v2.0.11** — five versions untagged/unreleased, #331.

**S122's public-release audit found two more items:** README three releases stale — fixed (PR
#325); this file over its 2,500-token cap — [ops#264](https://github.com/WeatheredScientist/eaglehunt-ops/issues/264),
trimmed under cap at S123 (measured with ops' `boot-cap-check` method; closes when the sweep runs green).

**S122 never ran its own closeout** (ops#218, third recurrence) — repaired by S123 (PR #326); no
done-marker. **S123 then closed #320** (`CHANGES-FROM-UPSTREAM.md` Go-decoder row, delta recount
+1204/−166) **and #314** (DEC-0140: the `rx > 100` backstop is dormant post-#317, left as-is on
purpose — read the DEC before touching it), PR #328. #320's "worth checking" answer: the patched
`main.go` carries **no GPLv3 §5(a) notice** of its own — **#327**, needs a build+deploy pass.

**The per-transmitter-ID loop period is verified:** `(41 + id)/16` s, id 4 = DIP ID 5, mean
2.8124 s/slot (S115/S119, #313) — background fact, not an open question.

**The monitor deploy path (S119):** file transport is owner-run (tenant key is forced-command);
restart is self-service `marvinctl --tenant weewx restart weewx-monitor.service`; unit edits are
owner-run. Verify by sha, start-after-mtime, `Remedy armed:` line. **#316** (unquoted
`REMEDY_SYSTEMCTL`) fixed live since Aug 30 16:20 ET — still untested end-to-end (no stall since).

**Also settled:** ops#256 closed empty (dashboard has no reception consumer). Repo #253/#216 fixed
S118. Marvin releases need **two** separate Class C confirmations, not one — `docs/GOTCHAS.md` §3.

### ▶▶ S124 JOB LIST

1. **ops#265 — the durable self-service push, once marvin installs `983b43b`.** `:v2.0.16` is
   **already on Hub** (owner-pushed 09-04 11:30 ET, byte-identical to prod — `CONSTANTS.md`
   Release row; S123 wrongly told ops it was at `:v2.0.13` and corrected it). Design settled: ops'
   client (`marvinctl push`/`tag`, OPS-DEC-0190) installed; **weewx's yes to `latest`-as-a-gesture
   given** (S123). Waits on the owner's Hub PAT + marvin's install. First self-service use is the
   *next* release. `:latest` (= v2.0.13) moves only by the owner's gesture — their call, not a job.
2. **ops#257 limb 2 — the `tag` step is weewx's, in order.** S122 picked the **tag shape**
   (`:marvin-live` floating own-tag + `tag` verb, MARVIN-DEC-0109) — *not* `EnvironmentFile`.
   Install order is load-bearing (MARVIN-DEC-0116): marvin installs `marvin-own` with `tag` →
   **weewx** runs `marvinctl --tenant weewx tag weatheredscientist/weewx-rtldavis:<running>
   …:marvin-live` (read `<running>` off `inspect weewx-rtldavis-v2`, never assume) → marvin
   installs the unit + `daemon-reload`, no restart. Skipping our step strands the unit on a
   missing tag at the next restart. Same installer run as job 1's verbs.
3. **#331 — GitHub Releases backfill** (`git tag v2.0.12`…`v2.0.16` on the commits that built each
   image + `gh release create` with CHANGELOG notes) **and write the step into CONVENTIONS.md /
   the closeout skeleton** so a version-changing `main` promotion is not "done" without it. Cheap;
   public-facing. Tags/releases are Class-C-shaped (public, hard to unpublish) — owner go per step.
4. **#327 — GPLv3 §5(a) notice in the dupgate patch's `main.go`** (cheap code, but it is a Go
   source change → needs a build, a sibling `grep` tripwire in the Dockerfile, and a deploy pass;
   ride it with the next image cut rather than cutting one for it).
5. **Retire the campaign residue** — `weewx-rx-experiment.timer` (self-service `marvinctl disable
   --now`) and the `campaign.inhibit` lifecycle at `ops/weewx-monitor.service:88` that no code
   implements. Fix the comment or implement it; not both.
6. **Fix `ExecStop=docker stop` in `weewx.service`** (DEC-0008) — owner root-edit path.
7. **Upstream issue/PR to `lheijst/rtldavis`** — draft in `docs/upstream/`, owner tone review,
   never posted without a go.
8. **Post-fix baseline watch** — RF-dead episodes (blocker 2) are measurable now; observation only.
9. **Audit Phase 2** sessions A (Sonnet, mechanical), B (judgment), C (design, owner) — unchanged.
10. `campaign_analyze.py` port to marvin (ops#250) · durable logrotate for marvin `logs/` ·
   ops#260 (Foundation decoupling umbrella, frontier) · ops#110 (frontier, 2027 build).

**Carried forward, untouched:** NAS-LEASE cross-host wiring (low) · `CONSTANTS.md` infra re-verify ·
`docs/ROADMAP.md` tripwire fires at **S126** (two sessions out).

### Current state (S123 close)

| Thing | State |
|---|---|
| Prod host | marvin · `weewx.service` in `/weather.slice`, `docker run --rm` — two-tenant box |
| Prod | **`v2.0.16`**, driver ws.5 + dupgate + slot-count denominator, weewx 5.5.0, gain 372. Since 09-03 20:29:06 ET (DEC-0138) |
| `main` | promoted, tag `prod-baseline-20260904` (PR #324) — in sync with `dev` |
| Docker Hub | **`:v2.0.16`** since 09-04 11:30 ET (owner route), byte-identical to prod · `:latest` = `v2.0.13` · `v2.0.14`/`v2.0.15` never pushed · job 1 (ops#265) is the next release's path |
| GitHub Releases | **dead since `v2.0.11`** (2026-07-28) — no `v2.0.12`…`v2.0.16` tags or releases; #331, job 3 |
| Monitor | dev tip `bd499d3`'s file (sha `147f3eff...`); `REMEDY_MODE=restart_unit` armed and executable |
| Git | S122: PRs #322–#325 · S123: #326 (closeout repair), #328 (#314/#320), #329 (close), #330 (job-list fix), #332 (Hub state) — all merged to `dev`; `main` unchanged at `prod-baseline-20260904` |
| Open risks | the 6-hourly email was thought broken (Gmail 535) and arrived 09-03; cause of recovery unknown, not ours to chase |
| Trackers | repo **#327** (cheap, needs a build pass), **#331** (GitHub Releases dead since v2.0.11 — backfill v2.0.12–16 tags/releases, add the step to the convention) open · ops **#264** (closes on the next green sweep), **#265**, #257 (limb 2), #250, #110, #260 open · repo #314, #317, #320, #313, #316, #253, #216 closed; ops#256, #233 closed |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open) — measurable post-DEC-0136.
   Job 8.
3. **ERR-0005** — unchanged.
4. ~~6-hourly reception-summary email~~ — arriving again as of 09-03; watch, don't chase.

## Model tier

S123 ran on **Sonnet** for the closeout repair and #320, then the owner switched to **Fable** for
#314's design call — and the Sonnet first-pass recommendation was wrong (DEC-0140): it had not
checked whether #317 already changed the ceiling. Lesson carried: *"moot once X ships" in a job
list is a claim to re-verify against source, not a fact.* S124's jobs 1–2 are now execution of
settled designs (OPS-DEC-0190 / MARVIN-DEC-0109) — **Sonnet**. Desktop switches persist
(OPS-DEC-0036/0062): **the Fable switch from S123 is still live unless the owner restored Sonnet**;
state the running model in the first reply.

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). **New traps are appended THERE.**

_Last updated: 2026-09-04 (S123 close). Session summary: opened on a closeout-debt hook (ops#218,
third recurrence) — S122 had closed #317 (DEC-0139), promoted `v2.0.16` to `main`
(`prod-baseline-20260904`), and refreshed the README, but never ran BOOT/CHANGELOG/DEC or a session
title. Repaired that first (PR #326), then closed #320 and #314 (PR #328, DEC-0140, #327 filed).
Four gates green on every commit: ruff clean, 475 passed / 17 skipped, mypy 68 files, secret gate 0._
