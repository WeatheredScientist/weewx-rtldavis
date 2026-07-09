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
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short.

> **Current session: S33** (2026-07-08) — **bad-packet root cause CONFIRMED + fixed (DEC-0029), not
> yet merged/deployed.** Evidence-first per owner: the `RAW_CHANNEL_PAYLOAD` lines turned out to hold
> only hop metadata (no payloads exist anywhere), so the archive DB became the evidence base — and it
> was enough: 18 one-minute humidity glitch spikes with the exact bit-flip signature (25.6/3, 12.8/2),
> an impossible UV 16.29 under overcast, midday-only pattern proven to be a StdQC+carry-forward
> masking artifact. Built the decode-layer `SensorQC` filter in `rtldavis.py` (Davis-spec bounds +
> per-reading delta with baseline-resync; no delta for radiation) and closed **DEC-0022** with the
> DewpointCacher timeout-null (300 s). Suite **85/85**, ruff + secret scan clean. Work is on
> `feature/s33-sensor-qc` (off `dev`). Post-release health check: clean. See CHANGELOG [S33] + DEC-0029.

_Last updated: 2026-07-08 (S33 — sensor plausibility filter built + DEC-0022 closed; awaiting merge,
then the v2.0.4 rebuild to ship it)._

---

## Active thread

> **▶ Resume here (S33 → S34).** The sensor-QC work is code-complete on `feature/s33-sensor-qc`;
> next is merge → **v2.0.4 image rebuild → deploy → live-verify** (see "Next session actions").

## Open threads (not yet shipped)

- **Sensor plausibility filter (DEC-0029) — code-complete, unmerged, undeployed.** The driver is
  baked, so this needs the v2.0.4 rebuild (same native-amd64-on-NAS procedure as S30). On deploy,
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
  freqError packets; fix the ~1–2 pt floor-division optimism. No-Rewrite applies; needs a rebuild —
  natural v2.0.4 passenger *if* designed/approved in time, else v2.0.5.
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

## Next session actions (S33 done → S34)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S33 (2026-07-08, on `feature/s33-sensor-qc`):** post-release health check clean
(container `:v2.0.3`, RestartCount=0, monitor 21/21); bad-packet root cause confirmed from the
archive (DEC-0029 has the full evidence chain); `SensorQC` decode-layer filter + DewpointCacher
timeout-null (closes DEC-0022) built with 22 new tests (suite 85/85). PR + merge pending owner
approval at session close.

**▶ ON RETURN (S34), do this first:**
1. **Quick health check** (read-only): container on `:v2.0.3`, `rxCheckPercent` flowing ~70–90%,
   0 rain rejections, 6 h dropped-packets emails arriving and reading sanely (~75% mean).
2. **Merge the S33 PR** (`feature/s33-sensor-qc` → `dev`) if not already merged.
3. **Build + deploy v2.0.4** (owner-run, same S30 procedure: native amd64 build on the NAS,
   verify the baked driver contains `SensorQC` before `docker rm -f` + re-run, keep `:v2.0.3`
   for rollback). Then live-verify: `rejecting implausible value` rejections appear at a sane rate
   (~0.4+/day expected from the humidity evidence, more at night), gauges stop spiking, archive
   stays clean, and dewpoint nulls (not freezes) during sensor silence.
4. Decide whether **Reception Layer B (DEC-0024)** rides the same v2.0.4 rebuild (design discussion
   first, No-Rewrite applies) or waits.

**Live access:** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in gitignored
`docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use `env -u GH_TOKEN` for
any `git push` (keyring token, not the PAT).
