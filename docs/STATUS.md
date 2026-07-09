# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**
- **This file is the single source of truth for the current session number and the next-session
  handoff** (DEC-0023). Every other doc — and Claude memory — points *at* this; none carries its own
  copy. Handoff state lives here (in the repo, visible on GitHub), never only in private memory.

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short — **prune at every session
close** (DEC-0030): shipped blocks out, superseded notes out; if CHANGELOG or a DEC already tells
the story, this file only points at it.

> **Current session: S35** (2026-07-09) — **Docs diet (DEC-0030): tiered session read ported from
> the siblings.** The dashboard's DEC-0081 playbook (`docs/reference/docs-diet-playbook.md` there)
> + hyperlocal's DEC-0095 port, applied here: DECISIONS split into index + `DECISIONS-FULL.md`,
> CHANGELOG rolled to ~3 live sessions + `CHANGELOG-ARCHIVE.md`, CLAUDE.md doc map now two-tier,
> STATUS prune + CHANGELOG roll added to the close ritual. Session boot: ~32K → ~8K tokens.
> Docs-only — **no code, no prod change**; prod still on `:v2.0.3`, S34's parked state unchanged.

_Last updated: 2026-07-09 (S35 — docs diet, DEC-0030; substantive next move is still the owner-run
v2.0.4 rebuild whenever convenient)._

---

## Active thread

> **▶ Resume here (S35 → S36).** Sensor-QC (DEC-0029 + DEC-0022) is **merged to `dev`, undeployed**.
> Prod is stable on `:v2.0.3` and can stay there indefinitely. The single next move is the
> **owner-run v2.0.4 image rebuild → deploy → live-verify** (see "Next session actions"). Nothing
> else is time-sensitive.

## Open threads (not yet shipped)

- **Sensor plausibility filter (DEC-0029) — merged to `dev` (PR #17, S34), undeployed.** The driver
  is baked, so this needs the v2.0.4 rebuild (same native-amd64-on-NAS procedure as S30). On deploy,
  live-verify: watch weewx.log for `rejecting implausible value` (expect ~0.4+/day humidity), confirm
  the dashboard gauges stop spiking, and confirm dewpoint goes null (not stale) during any sensor
  outage.
- **Follow-up filters anticipated (S33, not yet designed):** (1) **monitor alert** on the new
  rejection signature — extend `weewx_monitor.py`'s rain-glitch email to the sensor rejections
  (deliberately distinct log text; needs its own pattern + a rate cap so a flapping sensor doesn't
  spam); (2) **cross-sensor consistency** (UV↔radiation ratio would have caught UV 16.29 even
  in-bounds; dewpoint≤temp) — marginal value until the delta filter's live rejection data says
  otherwise; (3) **rainRate plausibility** (`time_between_tips` corruption) — StdQC `rainRate 0,16`
  backstop exists, low priority.
- **Watch for the first real rain glitch in the wild** — filter live + released; expect log
  "rejecting implausible counter delta" + clean archive + the alert email (~1 glitch/2–3 wk; 0 to
  date as of 2026-07-08).
- **Reception Layer B (driver, DEC-0024):** persist raw `count`/`missed`; stop publishing dataless
  freqError packets; fix the ~1–2 pt floor-division optimism. No-Rewrite applies; needs a rebuild.
  **Decided S34: waits for v2.0.5** — v2.0.4 stays single-purpose so its live-verify and rollback
  read cleanly. Needs its own design discussion + approval before any code.
- **ERR-0001 InfluxDB honest-null** — the dashboard's InfluxDB copy still carries the July-4 phantom
  rain; cross-repo (DEC-0010), handle dashboard-side or via the Influx API (no `influx` CLI on NAS).
- **Gain 372, interim** (DEC-0017) — awaiting a 24 h averaged no-preamp sweep to settle vs 207.
- **Vestigial `loopdata.py`** — mounted + `[LoopData]` present but in no active service list; safe to
  remove, not urgent.

## Needs a check / housekeeping

- **NAS boot task fragility (S32):** after the next DSM update/reboot, verify the `weewx_monitor`
  scheduler task still runs as root (symptom: `sudo: a terminal is required` spam, no pidfile).
- **Rotate the exposed WU API key** (NAS `wxcheck.sh`; scrubbed from repo S16, real key still live).
  Owner-acknowledged; still owed.
- **Docker Hub README auto-sync:** add repo secrets `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` to
  activate `.github/workflows/dockerhub-description.yml` (green no-op until then). Owner action.
- **Branch/tag cleanup:** delete merged `feature/rain-spike-filter` + `s32-reconcile-main`; retire
  the misnomer `rw250-test` image tag when rollback confidence allows.
- **Snow / freezing / no heating tape** (parked, owner's future thread) — cold-weather failure modes
  we haven't designed for. 2026 = learning year.

## Next session actions (S35 done → S36)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S35 (2026-07-09):** docs diet (DEC-0030) — see CHANGELOG `[S35]`. Docs-only; prod
untouched, still the S34 parked state (see CHANGELOG `[S34]`): `:v2.0.3` healthy, SensorQC staged
on `dev`, no timer running — resume whenever convenient.

**▶ ON RETURN (S36), the one thread that matters:**
1. **Build + deploy v2.0.4** (owner-run, same S30 procedure: native amd64 build on the NAS,
   verify the baked driver contains `SensorQC` before `docker rm -f` + re-run, keep `:v2.0.3`
   for rollback). Then live-verify: `rejecting implausible value` rejections appear at a sane rate
   (~0.4+/day expected from the humidity evidence, more at night), gauges stop spiking, archive
   stays clean, and dewpoint nulls (not freezes) during sensor silence.
2. After v2.0.4 has ridden clean for a few days: merge `dev` → `main`, tag the release + new
   `prod-baseline`, then pick up the deferred threads (Layer B design for v2.0.5, the S33
   follow-up filters, branch/tag cleanup).

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for
any `git push` (keyring token, not the PAT).
