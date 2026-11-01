# MANIFEST — weewx-rtldavis

**Always-load, tier 1.** What to pull on demand, and when; never read at session start. *"Working
near it" means read it.* A row names a class (rule 9); instances self-describe at source.
A file in no class gets its own row. Check size with `boot-cap-check.sh`.

## Governance & history

| Artifact | Load when |
|---|---|
| `docs/DECISIONS.md` (index) + `DECISIONS-FULL.md` (ADR bodies) | before working near a settled area; never re-litigate a listed decision. Grep the DEC id in FULL |
| `CHANGELOG.md` + `CHANGELOG-ARCHIVE.md` | writing a closeout entry |
| `docs/ROADMAP.md` — sequenced plan, P0–P3 | choosing what's next; updating a line a DEC shipped. |
| `BACKLOG.md` — ideas, RF findings, standing watches | RF work, horizon-scale work, or whether a watch fired |
| `docs/CONVENTIONS.md` — git workflow, secrets, exact gates | before any gate or commit |
| `docs/GOTCHAS.md` (§-indexed) | before trusting a tool's zero/green (§1); a PR/merge or handoff write (§2); a NAS/marvin/campaign task (§3); judging live or shipped (§4). New traps land here, not in `BOOT.md` |
| `docs/PRINCIPLES.md`, `ASSESSMENT.md`, `CODE_REVIEW_S145.md` | weighing a decision; picking the next cleanup |
| `docs/UPSTREAM-THREADS.md` | replying upstream, or checking whether a thread moved |
| `docs/INSTALL-RESEARCH.md` — install-path research and the ranked v2.2.0 proposal (DEC-0225) | building any P0.8 phase 6 item; changing what a new user types |

## Technical

| Artifact | Load when |
|---|---|
| `docs/ARCHITECTURE.md` · `docs/INTERFACES.md` (loop-JSON + InfluxDB contract: the real deliverable) · `docs/DATA_ERRATA.md` (`ERR-####`) | touching the ISS→driver→WeeWX→sinks chain; changing anything a consumer reads; a suspect historical reading |
| `CHANGES-FROM-UPSTREAM.md` — one section per forked or own module (DEC-0034) | changing a forked file, checking for an upstream, preparing an upstream PR |
| Root runtime modules: driver `rtldavis.py`; uploaders `influx.py`, `ogoxeUploader.py`, `wcloud.py`, `windy.py` and `owm.py` (these two share the base `rest_site.py`); services `pressure_service.py`, `dewpoint_service.py`, `loop_json_writer.py` | changing any behavior. `CONSTANTS.md`'s deploy-layers table says which layer wins in prod |
| `weewx_monitor.py` (root) — host-side watchdog, alerter, reception tracker | any "what handles X at runtime?" question; read before concluding a capability is missing (DEC-0074) |
| `ops/*`, `scripts/*`, `usb_reset.sh`, `entrypoint.sh`, `docs/CAMPAIGN-B-RUNBOOK.md`, `docs/INFLUXDB-MIGRATION.md` | any ops task, swap night, InfluxDB cutover. A script's header is its manual; `ops/campaign_analyze.py` is the only campaign readout (DEC-0069) |
| `extensions/influx/` + `scripts/build_influx_zip.sh`, `prove_influx.sh`, `.github/workflows/influx.yml` (DEC-0219) | changing `influx.py`'s version, the installer, or the image's uploader install; cutting an `influx-v*` release |
| `extensions/loopjson/` + `scripts/build_loopjson_zip.sh`, `prove_loopjson.sh`, `.github/workflows/loopjson.yml` (DEC-0211) | changing the writer's version, paths or install; cutting a `loopjson-v*` release |
| Go decoder: `patch/rtldavis-*.patch` (dup time-gate DEC-0135, CRC counters DEC-0216, burst gate DEC-0223), `tests/go/` | any change to the Go decoder |
| Entrypoint and first start: `entrypoint.sh` dispatches its first argument (DEC-0228); `seed_config.py` runs before weewxd (DEC-0225; a no-op when `weewx.conf` exists, so prod is untouched); `doctor.py` is the `doctor` check, exit codes 10 to 14 | changing what a new install gets, the first-run environment variables, `doctor`, or `entrypoint.sh` |
| Image and release: `Dockerfile`, `.github/workflows/image*.yml`, `scripts/join_multiarch.sh` and its helpers (DEC-0214/0215) | cutting a release, changing the Dockerfile, anything a Pi user pulls |
| Public face: `README.md`, `docs/QUICKSTART.md` (the install document, DEC-0225), `CONTRIBUTING.md`, `SECURITY.md`, `AGENTS.md`, `LICENSE`, `docs/DEPLOY.md`, `examples/`, `docker-compose.yml` | changing anything user-visible, an adopter install, or handling a report. Written to the dashboard's scrub rules: no host, tenant or unit names |

## Not in a clone, never in the load path

| Thing | Why |
|---|---|
| `ARCHIVE/` | local-only, gitignored (DEC-0012) |
| `docs/handoffs/` | retired handoffs that live docs cite by path; keep `S38-cross-repo-architecture.md` |
| `docs/upstream/` | gitignored drafts, never posted without an explicit go; state is in `UPSTREAM-THREADS.md` |
| Dashboard code and decisions | `eaglehunt-weather-dashboard`; not changed here (DEC-0010) |
| Real infra values, coordinates, security follow-ups | the gitignored local-infra doc |
| Cross-repo coordination, shared constants, `~/.claude/` guards | `eaglehunt-ops`, private, never a prerequisite (DEC-0063) |
