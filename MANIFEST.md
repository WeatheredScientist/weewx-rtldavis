# MANIFEST — weewx-rtldavis

**Always-load, tier 1.** What to pull on demand, and when; *"working near it" means read it.* A row
names a class (rule 9) and instances self-describe at source; a file in no class gets its own row.

## Governance & history

| Artifact | Load when |
|---|---|
| `docs/DECISIONS.md` (index) + `docs/DECISIONS-FULL.md` (bodies) | near a settled area; never re-litigate a listed decision |
| `CHANGELOG.md` + `CHANGELOG-ARCHIVE.md` | writing a closeout entry |
| `docs/ROADMAP.md` (P0–P3); `docs/ROADMAP-ARCHIVE.md` | choosing what's next; a line a DEC shipped; closed-item detail |
| `BACKLOG.md`: ideas, RF findings, standing watches | RF or horizon work; whether a watch fired |
| `docs/CONVENTIONS.md`: git workflow, secrets, exact gates | any gate or commit |
| `docs/GOTCHAS.md` (sections as in BOOT) | before trusting a zero, a merge, a marvin step or a "shipped". New traps land here |
| `docs/PRINCIPLES.md`; reviews, audits, designs, research: `docs/*REVIEW*`, `*AUDIT*`, `*DESIGN*`, `*RESEARCH*`, `ASSESSMENT.md` | weighing a decision; the next cleanup; why a design is what it is |
| `docs/UPSTREAM-THREADS.md` | replying upstream; whether a thread moved |

## Technical

| Artifact | Load when |
|---|---|
| `docs/ARCHITECTURE.md` · `docs/INTERFACES.md` (the data contract: loop JSON, InfluxDB, SQLite) · `docs/DATA_ERRATA.md` | the ISS→driver→WeeWX→sinks chain; what a consumer reads; a suspect reading |
| `CHANGES-FROM-UPSTREAM.md` (DEC-0034) | changing a forked file; an upstream PR |
| Root runtime modules: driver `rtldavis.py`; uploaders `influx.py`, `owm.py`, `windy.py`, `wcloud.py`, `ogoxeUploader.py` and their base `rest_site.py`; services `pressure_service.py`, `dewpoint_service.py`, `loop_json_writer.py` | any behavior change; `CONSTANTS.md`'s deploy layers say which copy wins |
| `weewx_monitor.py`: host-side watchdog, alerter, reception tracker | "what handles X at runtime?" (DEC-0074) |
| `ops/*`, `scripts/*`, `usb_reset.sh`; runbooks `docs/*RUNBOOK*`, `docs/*-MIGRATION.md` | any ops task. A script's header is its manual; `ops/campaign_analyze.py` is the only campaign readout (DEC-0069) |
| `extensions/<name>/` + its `scripts/*_<name>*.sh` and `.github/workflows/<name>.yml` | that module's version or installer; a `<name>-v*` release |
| `contract/`: loop-file JSON Schema, checker, fixtures, adopter `README.md` (DEC-0234) | the loop writer's output or the contract's version; validating a feed or reader |
| Go decoder: `patch/rtldavis-*.patch`, `tests/go/` | the Go decoder and its gates |
| First start: `entrypoint.sh` (DEC-0228), `seed_config.py` (DEC-0225), `doctor.py` | what a new install gets; first-run env vars; `doctor` |
| Image and release: `Dockerfile`, `user_init.py` (the venv `user` package), `.github/workflows/image*.yml`, `docs/RELEASE-NOTES-NEXT.md`; dongles and pinning `docs/RTLSDR-V4-AND-PINNING.md` | a release; anything a Pi user pulls; a second dongle, `-d`, the librtlsdr pin |
| Public face: `README.md`, `docs/QUICKSTART.md`, `docs/DEPLOY.md`, `CONTRIBUTING.md`, `SECURITY.md`, `AGENTS.md`, `examples/`, `docker-compose.yml` | anything user-visible. No host, tenant or unit names |

## Never in the load path

| Thing | Why |
|---|---|
| `ARCHIVE/` | local-only, gitignored (DEC-0012) |
| `docs/handoffs/` | retired, cited by path; leave in place |
| `docs/upstream/` | gitignored drafts; never posted without a go |
| Dashboard code and decisions | `eaglehunt-weather-dashboard` (DEC-0010) |
| Real infra values, coordinates | the gitignored local-infra doc |
| Cross-repo coordination, guards | `eaglehunt-ops` (maintainer-only, never a prerequisite) |
