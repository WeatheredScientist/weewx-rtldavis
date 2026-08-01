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

## ▶ Resume here (S61)

**The DEC-0063 tiering migration is DONE (S60)** — this file, `CONSTANTS.md` and `MANIFEST.md` are
now the entire session-start read. Always-load went **91,806 B (~25.5K tok) → 25,819 B (~7.2K)**, a
72% cut, and `docs/STATUS.md` is retired (content distributed here, to `BACKLOG.md`, and to
`docs/UPSTREAM-THREADS.md`). Nothing about the migration is outstanding except one owner call: the
corrected measurements and the §3 public-vs-private spec gap are owed back to ops#130 as a comment.

**Campaign A is running clean — keep tracking, don't intervene.** As of 2026-08-01 15:45: **10 of 32
blocks** harvested, block 11 (**arm A**) live since 12:08:21, **11/11 swaps healthy, zero aborts**,
no STOP sentinel. Completes **~08-07 00:05**. Blocks balanced so far (A 2, B 2, C 3, D 3).

**Do not read partial results.** As of S58 both main effects were flat — gain 207 vs 372 −0.1 pts
(±0.36 SE), ex 50 vs ex 0 −0.1 (±0.36) — against DEC-0059's **≥2.0-pt** adoption bar. A −1.2 pt
gain effect that looked real on day 1 dissolved by day 3. That is what the 8-blocks-per-arm design
exists to prevent.

**Tracking, in order:** state is `rx_experiment.state` (`arm|epoch|timestamp`); swap history is
`logs/rx_experiment.log`; samples are `logs/rx_experiment_data.log` (`ts|arm|rx|pct` at 5-min ticks,
interleaved `ts|arm|dup|N` at ~1-min). Drop the first 2 samples of each block (post-swap settle)
before averaging. Cross-check the archive's own `rxCheckPercent` when anything looks odd — it is an
independent metric and it corroborated the one real dip. `ops/rx_experiment.sh status` is **not** a
`nasctl` verb. `rx_experiment.log` was **never rotated**, so it still carries the aborted 07-29 run
at its head — the live campaign starts at `swapping NONE -> A` on 07-30 00:05; counting swaps
without allowing for that gives 2 phantom blocks.

**One unscheduled restart, logged not chased (S59).** 2026-08-01 15:08:22, `weewxd CRITICAL Database
OperationalError exception: database is locked`; weewx waited its built-in 2 min, re-initialized
cleanly 15:10:22, resumed publishing (verified 15:43). First of the live campaign. Consequence: the
campaign drops samples after a *swap*, not after an unscheduled restart, so **block 11 carries a
~2-min gap plus an unmasked transient**. If it recurs, it becomes a thread rather than a footnote.

## Active work

1. **Campaign A tracking** (above) — watch only, completes ~08-07.
2. **When it completes:** design **campaign B** (LNA physically removed, gain arms centered higher
   ~{372, 496} — **do not reuse A's arms**, the optimum moves up once ~20 dB of front-end gain is
   gone), and cut the image release carrying **DEC-0062**.

## Blockers

- **DEC-0062 is fixed in the repo but INERT IN PROD** — `pressure_service.py` is **baked**
  (`Dockerfile:117`), not mounted, so it needs an image rebuild. Deliberately **not** rebuilt
  mid-campaign: swapping the image under a running 8-day factorial confounds its arms. Ships with
  the post-campaign release. Specifics stay out of this public repo (see gitignored local-infra doc).
- Nothing else blocks. No open PRs, no open issues.

## Ordered backlog

1. Campaign B design (gated on campaign A completing ~08-07).
2. Post-campaign image release carrying DEC-0062.
3. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten. Phase 0 confirmed the telemetry
   exists; all four campaign-A arms run unmeasured `-fc 0 -ppm 0`. If picked up: a *minutes-long*
   pass per DEC-0060's recipe, not a multi-hour one.
4. **Consider `.claude/transient-state`** (ops#113) — a tracked `<revert-by-epoch> <ref> <desc>`
   file a SessionStart hook surfaces as OVERDUE. Would have caught the Phase 0 revert-window miss
   (~14.5h vs. a planned 3h). Opt-in is this repo's call.
5. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

## Standing watches — read-only, none block the above

- **Co-rejection grep** (DEC-0054): **0 hits through 15:43 08-01**. Single-token pattern
  `co-rejecting` — *multi-word `nasctl grep` patterns silently match nothing*; positive-control any
  zero. Each hit is a frame v2.0.8 would have partially trusted.
- **Humidity-spike watch** — unfired (largest step 0.7 pts in the 240 samples to 08:52 07-28). Needs
  the 16–37 pt DEC-0044 single-step signature, not an ordinary 5–10 %/min swing. **Method and
  arithmetic are in DEC-0044 — do not re-derive them.**
- **DEC-0049 phantom-rainRate** — unfired. A third event on the next calm, saturated, cooling night
  is a free test, with a sharp prediction: **the tip counter still will not advance.**
- **First frost** — the signed decode's negative branch gets its first live air test. Expected:
  ordinary sub-zero readings, no bounds trips, no co-rejection storm. If a cold snap instead lights
  up `co-rejecting` pairs, that is a DEC-0055 regression — investigate before anything else.
- **DEC-0056 revisit trigger** — a rain-rejection email on a genuinely *wet* day. Dry day = the
  filter catching a glitch; log it and move on.
- **Upstream replies** — four open threads (lheijst #22/#23, issue #15, david-lutz#1). See MANIFEST.
- **Dependabot** may open a deps PR — review, don't auto-merge.

✅ **#74 calm-windDir is CLOSED (S59)** — do not re-run. Five consecutive clean days, positive
control 21 hits on 07-27. Reopens only on a `windDir expired` WARNING while `windSpeed` is nonzero.

## Standing rules that bite most often

- **Ask "which layer actually wins in prod?" for any file we ship (DEC-0046).** The **driver** is
  baked and the mount is inert (DEC-0031). The **config** is mounted and the image is inert
  (DEC-0046). They are exact inverses. A release changing shipped config **must patch the live
  `weewx.conf` on the NAS in the same window**, and verify in the **running system**, never in the
  artifact.
- **The transcript is an egress path (DEC-0047).** Use `readconf` to read a config (section-scoped)
  and `scan-transcripts` to audit; never a line-count window on a sectioned config. **Logs are not
  covered by that guard (DEC-0062)** — never log key material.
- **`docker kill`, never `docker stop`** (DEC-0008). **`docker logs` always with `--tail N`** — a
  bare one wedged the Synology daemon for 7h18m (DEC-0036); now hook-blocked.
- **Prod is sacred.** One dongle, one receiver, no drop-in dev WeeWX — runtime testing needs an
  agreed strategy first (DEC-0011). `main` = production truth; `dev` = work.
- **Pause for approval before every commit and before any push.** Discuss design before coding.
- **No-Rewrite Rule (DEC-0014)** — no subsystem rewrite without documented cause, an alternative, a
  migration plan, a DEC entry, and explicit approval.
- **After patching any `.py` the WeeWX venv imports, clear the pyc cache.**
- A shipped/closed/reprioritized DEC gets its `docs/ROADMAP.md` line updated the **same session**
  (DEC-0057). ROADMAP is **P0–P3 only** (DEC-0058); long-horizon items live in `BACKLOG.md`.

## Style notes & contribution conventions

**This repo is PUBLIC and has external contributors** — the only one in the family that does.

- **No credential, live `weewx.conf`, `monitor.env`, or `proxy.env` ever enters any commit on any
  branch** (DEC-0012). Committed source carries `YOUR_*` placeholders; infra facts use
  `<NAS_HOST>` / `<NAS_USER>` / `<SSH_PORT>` placeholders with real values in the gitignored
  local-infra doc. Show every secret found *before* scrubbing so it can be rotated.
- **Run the secret gate with a planted-payload positive control.** It prints nothing and exits 0 on
  a clean pass — *and also exits 0 with `nothing to scan` when no files are staged*. Those look
  alike and are not alike. `git add` first (DEC-0039/DEC-0045).
- **Validation gates and the exact interpreter to use are in `docs/CONVENTIONS.md`** — three of the
  four previously documented commands did not work as written (S59b). Use the ones there verbatim;
  in particular **`ruff format` is not a gate and must not be run** (DEC-0027).
- Prose: **US spelling, concise over thorough, friendly and non-shaming** in anything public-facing.
  Community posts and upstream comments are drafted, reviewed by the owner, and never posted without
  an explicit go.
- Sessions use **this repo's own independent counter** (DEC-0023) — a session number means something
  only within this repo; prefix cross-repo references (`weewx S59` vs `dash S151`). **This file is
  the single source of truth for the current session number and the handoff.**

_Last updated: 2026-08-01 (S60). Session numbering: this repo's own counter; governed era runs S16 → …_
