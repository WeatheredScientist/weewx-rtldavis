# MANIFEST — weewx-rtldavis

**Always-load, tier 1.** What to pull on demand, and when; *"working near it" means read it.* A row
names a class (rule 9) and instances self-describe at source; a file in no class gets its own row.

## Governance & history

| Artifact | Load when |
|---|---|
| `docs/DECISIONS.md` (index) + `docs/DECISIONS-FULL.md` (bodies) | near a settled area; never re-litigate a listed decision |
| `CHANGELOG.md` + `CHANGELOG-ARCHIVE.md` | writing a closeout entry |
| `docs/ROADMAP.md` (P0–P3) | choosing what's next; a line a DEC shipped |
| `BACKLOG.md`: ideas, RF findings, standing watches | RF or horizon work; whether a watch fired |
| `docs/CONVENTIONS.md`: git workflow, secrets, exact gates | any gate or commit |
| `docs/GOTCHAS.md` | a tool's zero/green (§1); a PR, merge or handoff write (§2); marvin or campaign work (§3); judging live or shipped (§4). New traps land here |
| `docs/PRINCIPLES.md`; reviews `docs/CODE_REVIEW_S*.md`, `docs/ASSESSMENT.md` (S23), `docs/INTERFACES-AUDIT-S197.md`, `docs/LOOPJSON-1.2-DESIGN.md` (DEC-0234) | weighing a decision; the next cleanup; generalizing the contract (P3); the loop writer's contract version, schema or checker |
| `docs/UPSTREAM-THREADS.md` | replying upstream; whether a thread moved |
| `docs/INSTALL-RESEARCH.md` (behind DEC-0225) | why the install path is what it is |

## Technical

| Artifact | Load when |
|---|---|
| `docs/ARCHITECTURE.md` · `docs/INTERFACES.md` (the data contract: loop JSON, InfluxDB, SQLite) · `docs/DATA_ERRATA.md` | the ISS→driver→WeeWX→sinks chain; what a consumer reads; a suspect reading |
| `CHANGES-FROM-UPSTREAM.md` (DEC-0034) | changing a forked file; an upstream PR |
| Root runtime modules: driver `rtldavis.py`; uploaders `influx.py`, `owm.py`, `windy.py`, `wcloud.py`, `ogoxeUploader.py` and their base `rest_site.py`; services `pressure_service.py`, `dewpoint_service.py`, `loop_json_writer.py` | any behavior change; `CONSTANTS.md`'s deploy layers say which copy wins |
| `weewx_monitor.py`: host-side watchdog, alerter, reception tracker | "what handles X at runtime?" (DEC-0074) |
| `ops/*`, `scripts/*`, `usb_reset.sh`; runbooks `docs/CAMPAIGN-B-RUNBOOK.md`, `docs/INFLUXDB-MIGRATION.md`, `docs/WINDGUST10-MIGRATION.md` (DEC-0232, not run) | any ops task. A script's header is its manual; `ops/campaign_analyze.py` is the only campaign readout (DEC-0069) |
| `extensions/<name>/` + its `scripts/*_<name>*.sh` and `.github/workflows/<name>.yml` | that module's version or installer; a `<name>-v*` release |
| `contract/`: the loop file's JSON Schema, the stdlib checker `check_contract.py`, conformance fixtures, the adopter's `README.md`; run over the fixtures by `scripts/check_contract_fixtures.sh` (DEC-0234) | the loop writer's output or the contract's version; validating a feed or a reader |
| Go decoder: `patch/rtldavis-*.patch`, `tests/go/` | the Go decoder and its gates |
| First start: `entrypoint.sh` (DEC-0228), `seed_config.py` (DEC-0225), `doctor.py` | what a new install gets; first-run env vars; `doctor` |
| Image and release: `Dockerfile`, `.github/workflows/image*.yml`, `scripts/join_multiarch.sh`; dongle support and pinning `docs/RTLSDR-V4-AND-PINNING.md` (DEC-0235) | a release; anything a Pi user pulls; a second dongle, `-d`, the librtlsdr pin |
| Public face: `README.md`, `docs/QUICKSTART.md`, `docs/DEPLOY.md`, `CONTRIBUTING.md`, `SECURITY.md`, `AGENTS.md`, `examples/`, `docker-compose.yml` | anything user-visible. No host, tenant or unit names |

## Never in the load path

| Thing | Why |
|---|---|
| `ARCHIVE/` | local-only, gitignored (DEC-0012) |
| `docs/handoffs/` | retired handoffs, cited by path from the archives; leave in place |
| `docs/upstream/` | gitignored drafts, never posted without an explicit go |
| Dashboard code and decisions | `eaglehunt-weather-dashboard` (DEC-0010) |
| Real infra values, coordinates | the gitignored local-infra doc |
| Cross-repo coordination, `~/.claude/` guards | `eaglehunt-ops` (private, never a prerequisite) |
