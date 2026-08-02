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

## ▶ Resume here (S62)

**Campaign B is GO — designed, dry-run, staged (S61, DEC-0064).** The whole mission runs from
**`docs/CAMPAIGN-B-RUNBOOK.md` — follow it verbatim**, it is the checklist with the owner gates,
timeline, rollback paths and expected numbers. Landed in PR (S61): apparatus rewritten (pilot + H
hold + square, abort floor 50%), 13 tests, full DRY_RUN pass, v2.0.12 prepped (`BIAS_TEE` env +
DEC-0062 redaction), DEC-0064, runbook.

**The week's fixed points:**

1. **Thu 08-06 (daytime): pre-flight.** Build v2.0.12 on the dev machine, push `:v2.0.12` +
   `:latest` to Docker Hub, owner merges the release PR. Runbook §Pre-flight has the checklist.
2. **Fri 08-07 00:05: swap night.** Campaign A self-terminates → archive its artifacts → deploy
   the B apparatus → **owner GO in chat (GATE 1, owner at the dongle)** → v2.0.12 with
   `-e BIAS_TEE=0` (the night's one Class C command) → 20–40 s SMA swap → verify → `install` →
   pilot fires 00:35 (gain 496→328, 45 min/arm, arm-selection input only).
3. **Fri daytime: pilot readout (GATE 2).** Confirm/adjust the square's high arm with the owner;
   if arms change: literals + tests + re-scp before ~23:00.
4. **Sat 08-08 00:05 → Sun 08-16 00:05: campaign B runs.** Watch only; do not read partial
   results (the S58 lesson: a −1.2 pt day-1 "effect" dissolved by day 3). Adoption bar ≥2.0 pts,
   no duplicate-frame regression, incumbent wins ties (DEC-0059).

**Campaign A: watch only until 00:05 Friday.** As of S61 close (18:07 08-01): block 12 (arm B)
live, 12/12 swaps healthy, zero aborts, no STOP. State `rx_experiment.state`; swaps
`logs/rx_experiment.log` (never rotated — the live campaign starts at `swapping NONE -> A` on
07-30 00:05; earlier lines are the aborted 07-29 run); samples `logs/rx_experiment_data.log`
(drop first 2/block). **A's results stay unread and unadopted through the gap** — its winner is
moot once the LNA is out; its value is the LNA-in characterization + the drift error bar.

**Key S61 finding — there is NO honest no-LNA telemetry anywhere.** Owner confirmed the June
plateau (67.45, sd 3.22, gain 207) was LNA-IN; S29's "pre-LNA baseline" label was wrong, and the
no-LNA era sits in the metric-dark gap. Friday's pilot is the first real measurement — treat its
first samples as discovery. Bonus: both plateaus LNA-in ⇒ 207→372 = **+7.4 pts** same-hardware,
corroborating DEC-0017 directionally (uncontrolled).

**Model floor note:** S61 escalated to Fable via a bare `/model` (desktop — always persists).
Design is done; Thursday/Friday are execution. Restore Sonnet before the next session, or note
the running model at its start (OPS-DEC-0062 discipline).

## Blockers

- None. DEC-0062's deploy rides v2.0.12 on Thursday (no longer stranded — the between-campaigns
  window is the whole point). One unscheduled `database is locked` restart (S59, self-recovered)
  remains a logged one-off; recurrence makes it a thread.

## Ordered backlog

1. Campaign B execution (the four fixed points above).
2. Post-campaign: LNA-in vs LNA-out grand comparison (A's analysis × B's analysis), final prod
   config decision, and whether the LNA goes back in.
3. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten (DEC-0060 recipe is minutes-long).
   Deliberately NOT changed for campaign B (would confound the LNA contrast).
4. **Consider `.claude/transient-state`** (ops#113) — tracked revert-by file a SessionStart hook
   surfaces as OVERDUE. Opt-in is this repo's call.
5. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

## Standing watches — read-only, none block the above

- **Co-rejection grep** (DEC-0054): **0 hits through 18:30 08-01**. Single-token pattern
  `co-rejecting` on `/volume1/docker/weewx-rtldavis/logs/weewx.log` — *multi-word `nasctl grep`
  patterns silently match nothing*; positive-control any zero.
- **Humidity-spike watch** — unfired. Needs the 16–37 pt DEC-0044 single-step signature. **Method
  and arithmetic are in DEC-0044 — do not re-derive.**
- **DEC-0049 phantom-rainRate** — unfired. Next calm, saturated, cooling night is a free test;
  sharp prediction: the tip counter still will not advance.
- **First frost** — the signed decode's negative branch gets its first live air test. A
  `co-rejecting` storm on a cold snap = DEC-0055 regression; investigate first.
- **DEC-0056 revisit trigger** — a rain-rejection email on a genuinely *wet* day.
- **Upstream replies** — four open threads (lheijst #22/#23, issue #15, david-lutz#1). See MANIFEST.
- **Dependabot** may open a deps PR — review, don't auto-merge.

✅ **#74 calm-windDir is CLOSED (S59)** — do not re-run. Reopens only on a `windDir expired`
WARNING while `windSpeed` is nonzero.

## Standing rules that bite most often

- **Ask "which layer actually wins in prod?" for any file we ship (DEC-0046).** Driver +
  `pressure_service.py` + `entrypoint.sh` are **baked** (image); `weewx.conf` is **mounted**
  (live edit); `influx.py` is mounted (scp correct). Exact inverses; a release changing shipped
  config must patch the live NAS copy in the same window and verify in the **running system**.
- **The transcript is an egress path (DEC-0047).** `readconf` for configs, `scan-transcripts` to
  audit; never a line-count window on a sectioned config. **Logs are not covered (DEC-0062)** —
  never log key material.
- **`docker kill`, never `docker stop`** (DEC-0008). **`docker logs` always with `--tail N`**
  (DEC-0036; hook-blocked).
- **Prod is sacred.** One dongle, one receiver (DEC-0011). `main` = production truth; `dev` = work.
- **Pause for approval before every commit and before any push.** Discuss design before coding.
- **No-Rewrite Rule (DEC-0014).**
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
  a clean pass — *and also exits 0 with `nothing to scan` when no files are staged*. `git add`
  first (DEC-0039/DEC-0045).
- **Validation gates and the exact interpreter are in `docs/CONVENTIONS.md`** — use them verbatim;
  **`ruff format` is not a gate and must not be run** (DEC-0027).
- Prose: **US spelling, concise over thorough, friendly and non-shaming** in anything public-facing.
  Community posts and upstream comments are drafted, owner-reviewed, never posted without a go.
- Sessions use **this repo's own independent counter** (DEC-0023); prefix cross-repo references
  (`weewx S61` vs `dash S151`). **This file is the single source of truth for the current session
  number and the handoff.**

_Last updated: 2026-08-01 (S61). Session numbering: this repo's own counter; governed era runs S16 → …_
