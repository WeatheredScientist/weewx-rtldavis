# MANIFEST — weewx-rtldavis

**Always-load, tier 1.** What to pull on demand, and when. *"Working near it" means read it.* A row names
a class (rule 9); instances self-describe at source.
A file in no class gets its own row.

## Governance & history

| Artifact | Load when |
|---|---|
| `docs/DECISIONS.md` (index) + `DECISIONS-FULL.md` (bodies) | working near a settled area; never re-litigate a listed decision. Grep the DEC id in FULL |
| `CHANGELOG.md` + `CHANGELOG-ARCHIVE.md` | writing a closeout entry |
| `docs/ROADMAP.md` — sequenced plan, P0–P3 | choosing what's next; updating a line a DEC shipped |
| `BACKLOG.md` — ideas, RF findings, standing watches | RF or horizon-scale work; whether a watch fired |
| `docs/CONVENTIONS.md` — git workflow, secrets, exact gates | any gate or commit |
| `docs/GOTCHAS.md` (§-indexed) | a tool's zero/green (§1); a PR/merge or handoff write (§2); a marvin/campaign task (§3, NAS-era entries at its end); judging live or shipped (§4). New traps land here, not in `BOOT.md` |
| `docs/PRINCIPLES.md`, `CODE_REVIEW_S145.md`, `CODE_REVIEW_S192.md` (cruft audit); `ASSESSMENT.md` (S23 snapshot, historical) | weighing a decision; picking the next cleanup |
| `docs/UPSTREAM-THREADS.md` | replying upstream; whether a thread moved |
| `docs/INSTALL-RESEARCH.md` — install-path research behind DEC-0225 (answered: shipped in v2.2.0/v2.3.0) | the reasoning behind the install path; options not taken |

## Technical

| Artifact | Load when |
|---|---|
| `docs/ARCHITECTURE.md` · `docs/INTERFACES.md` (loop-JSON + InfluxDB contract: the deliverable) · `docs/DATA_ERRATA.md` (`ERR-####`) | the ISS→driver→WeeWX→sinks chain; what a consumer reads; a suspect historical reading |
| `CHANGES-FROM-UPSTREAM.md` — one section per forked or own module (DEC-0034) | changing a forked file; preparing an upstream PR |
| Root runtime modules: driver `rtldavis.py`; uploaders `influx.py`, `ogoxeUploader.py`, `wcloud.py`, `windy.py`, `owm.py` (the last two share `rest_site.py`); services `pressure_service.py`, `dewpoint_service.py`, `loop_json_writer.py` | any behavior change. `CONSTANTS.md`'s deploy-layers table says which layer wins in prod |
| `weewx_monitor.py` (root) — host-side watchdog, alerter, reception tracker | "what handles X at runtime?"; read before calling a capability missing (DEC-0074) |
| `ops/*`, `scripts/*`, `usb_reset.sh`, `entrypoint.sh`; records `docs/CAMPAIGN-B-RUNBOOK.md` (retired) and `docs/INFLUXDB-MIGRATION.md` (executed) | any ops task; the history of a campaign or the InfluxDB move. A script's header is its manual; `ops/campaign_analyze.py` is the only campaign readout (DEC-0069) |
| `extensions/<name>/` (influx DEC-0219, loopjson DEC-0211) + its `scripts/build_<name>_zip.sh`, `prove_<name>.sh`, `.github/workflows/<name>.yml` | that module's version, installer or paths; cutting a `<name>-v*` release |
| Go decoder: `patch/rtldavis-*.patch` (gates DEC-0135, DEC-0216, DEC-0223, DEC-0229), `tests/go/` | the Go decoder |
| Entrypoint and first start: `entrypoint.sh` dispatches its first argument (DEC-0228); `seed_config.py` runs before weewxd (DEC-0225; a no-op when `weewx.conf` exists); `doctor.py` is the `doctor` check, exit codes 10 to 14 | what a new install gets, the first-run environment variables (incl. `WEEWX_DRIVER`), `doctor`, `entrypoint.sh` |
| Image and release: `Dockerfile`, `.github/workflows/image*.yml`, `scripts/join_multiarch.sh` and helpers (DEC-0214/0215) | a release, the Dockerfile, anything a Pi user pulls |
| Public face: `README.md`, `docs/QUICKSTART.md` (the install document, DEC-0225), `CONTRIBUTING.md`, `SECURITY.md`, `AGENTS.md`, `LICENSE`, `docs/DEPLOY.md`, `examples/`, `docker-compose.yml` | anything user-visible, an adopter install, or a report. Scrub rules: no host, tenant or unit names |

## Not in a clone, never in the load path

| Thing | Why |
|---|---|
| `ARCHIVE/` | local-only, gitignored (DEC-0012) |
| `docs/handoffs/` | retired handoffs (S36, S37, S38, S71), cited by path from `DECISIONS-FULL.md` and `CHANGELOG-ARCHIVE.md`; leave in place |
| `docs/upstream/` | gitignored drafts, never posted without an explicit go; state in `UPSTREAM-THREADS.md` |
| Dashboard code and decisions | `eaglehunt-weather-dashboard` (DEC-0010) |
| Real infra values, coordinates, security follow-ups | the gitignored local-infra doc |
| Cross-repo coordination, shared constants, `~/.claude/` guards | `eaglehunt-ops` (private; never a prerequisite, DEC-0063) |
