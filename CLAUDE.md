# CLAUDE.md — weewx-rtldavis

**This is the entrypoint.** Read the documentation map below in order at the start of every
session before touching code. This repo is the **driver + Docker build** for a Davis 6263 / VP2+
ISS *passively intercepted* at 915 MHz via an **RTL-SDR Blog v3** dongle — the "escape the
WeatherLink lock" tool. It is a **public, published** WeeWX extension (Docker Hub +
GitHub releases). The **dashboard** that consumes this data lives in a **separate repo**
(`eaglehunt-weather-dashboard`) — don't make dashboard changes here (DEC-0010).

Its real contract is the **data it produces** — the loop-JSON file + the InfluxDB line-protocol
schema — not any single consumer. Keep it re-pointable so non-Davis WeeWX and eventually CumulusMX
can use it (PRINCIPLES §1, docs/INTERFACES.md).

## Documentation map (read in this order)

| # | Doc | Answers |
|---|-----|---------|
| 1 | `CLAUDE.md` (this) | where everything is + the rules that must never break |
| 2 | `docs/CONVENTIONS.md` | how we operate — paths, commands, workflow, infra constants |
| 3 | `docs/PRINCIPLES.md` | durable intent behind the design |
| 4 | `docs/DECISIONS.md` | ADR log — settled choices; **do not re-litigate**, supersede with a new DEC |
| 5 | `docs/ARCHITECTURE.md` | the ISS→RTL-SDR→driver→WeeWX→sinks chain; volume-mount map; entrypoint |
| 6 | `docs/INTERFACES.md` | the data contract — loop-JSON fields + InfluxDB schema (what consumers depend on) |
| 7 | `docs/ROADMAP.md` | what's next, in what order |
| 8 | `docs/STATUS.md` | what's on the bench right now (in-flight threads) |
| 9 | `CHANGELOG.md` | what changed recently (read the latest entry); `BACKLOG.md` = open ideas |

If a doc is missing or contradicts another, stop and flag it — don't guess.

## Non-negotiable rules (full detail in the docs cited)

- **This repo is PUBLIC.** The live `weewx.conf`, `monitor.env`, and anything with credentials or
  tokens must NEVER enter any commit on any branch. Show every secret found before scrubbing; run a
  token-pattern grep before every commit (DEC-0012, CONVENTIONS §Secrets).
- **Pause for approval before every commit and before any push.**
- **Discuss design before coding.** No production code until the approach is agreed (PRINCIPLES §8).
- **No-Rewrite Rule** (DEC-0014): no subsystem rewrite without documented cause, an alternative, a
  migration plan, a DEC entry, and explicit approval. Favor incremental change.
- **`docker kill`, never `docker stop`** (DEC-0008). `docker logs` always with `--tail N`.
- **After patching any `.py` the WeeWX venv imports, clear the pyc cache:**
  `find /opt/weewx-venv -name "*.pyc" -path "*/user/*" -delete` (ARCHITECTURE §pyc-gotcha).
- **Prod is sacred; deploy to dev first.** `main` = what is actually running in production (tagged
  `prod-baseline-YYYYMMDD`); `dev` = working branch. There is **no drop-in dev WeeWX** — one dongle,
  one receiver — so runtime testing needs a deliberate strategy (Simulator-backed container or
  reversible live hot-swap); agree it before touching prod (DEC-0011, ROADMAP).

## Quick infra reference (full table in CONVENTIONS)

- NAS: `<NAS_HOST>` (Synology DS918+) · `<NAS_IP>` · SSH port `<SSH_PORT>` · user `<NAS_USER>` ·
  `scp -P <SSH_PORT> -O` · no `bc`/`tmux`/`screen` (use bash integer arithmetic + `nohup`).
  Real values in gitignored `docs/LOCAL_INFRA.md`.
- Docker: `/usr/local/bin/docker` (no sudo); container `weewx-rtldavis-v2`,
  image `weatheredscientist/weewx-rtldavis:rw250-test`
- Project root on NAS: `/volume1/docker/weewx-rtldavis/` · live config:
  `.../weewx-data/weewx.conf` · container venv user files:
  `/opt/weewx-venv/lib/python3.14/site-packages/user/`
- Hardware: Davis 6263 VP2+ ISS · 6410 hall anemometer · RTL-SDR Blog v3 + inline LNA (bias-tee) ·
  915 MHz vertical · ~150 ft through walls · reception baseline ~67–70% (noise-floor limited)
- Attribution: **WeatheredScientist**. Station coordinates in gitignored `docs/LOCAL_INFRA.md`.

## Session ritual

- **Start:** read this map; `git fetch && git status`; read STATUS.md "Active thread".
- **End:** update STATUS.md, append to CHANGELOG.md, `git status` should show *up to date*.
- Sessions draw from a **single shared counter** across this repo and the dashboard repo: before
  numbering, check the sibling's latest `CHANGELOG.md` / `STATUS.md` and take the next integer. This
  repo's governed era began at S16, drifted into an independent S16–S19, and **rejoined the shared
  counter at S40** (the dashboard was at S39) — see DEC-0013 and **DEC-0023**. Pre-S16 history is
  reconstructed/approximate.
