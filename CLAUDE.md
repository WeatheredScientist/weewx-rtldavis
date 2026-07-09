# CLAUDE.md — weewx-rtldavis

**This is the entrypoint.** Follow the tiered session-start read below (DEC-0030) before touching
code. This repo is the **driver + Docker build** for a Davis 6263 / VP2+
ISS *passively intercepted* at 915 MHz via an **RTL-SDR Blog v3** dongle — the "escape the
WeatherLink lock" tool. It is a **public, published** WeeWX extension (Docker Hub +
GitHub releases). The **dashboard** that consumes this data lives in a **separate repo**
(`eaglehunt-weather-dashboard`) — don't make dashboard changes here (DEC-0010).

Its real contract is the **data it produces** — the loop-JSON file + the InfluxDB line-protocol
schema — not any single consumer. Keep it re-pointable so non-Davis WeeWX and eventually CumulusMX
can use it (PRINCIPLES §1, docs/INTERFACES.md).

## Documentation map — tiered session-start read (DEC-0030)

The docs outgrew "read everything in order" (~130 KB ≈ ~32K tokens per session boot, measured S35 —
the pattern the dashboard fixed at its S57/DEC-0081 and hyperlocal at its S143/DEC-0095). The
protocol is now two tiers. **The current docs live on `dev`** — check
`git log origin/main..origin/dev --oneline` and read docs from `dev`'s tip if `main` lags.

**Tier 1 — read at every session start:**

| Doc | Answers |
|-----|---------|
| `CLAUDE.md` (this) | where everything is + the rules that must never break |
| `docs/STATUS.md` | **where we are right now** — current session + active thread + next actions (single source of truth) |
| `docs/CONVENTIONS.md` | how we operate — paths, commands, workflow, infra constants |
| `docs/PRINCIPLES.md` | durable intent behind the design |
| `docs/DECISIONS.md` | **index** of settled choices — scan it; **do not re-litigate** anything listed |
| `CHANGELOG.md` | the last few sessions (older entries: `CHANGELOG-ARCHIVE.md`) |

**Tier 2 — read on demand, when the task touches them (never skip because of the tier —
"working near it" means read it):**

| Doc | Read when |
|-----|-----------|
| `docs/DECISIONS-FULL.md` | full ADR text — grep the DEC id whenever a listed decision is near your change |
| `docs/ARCHITECTURE.md` | touching the ISS→RTL-SDR→driver→WeeWX→sinks chain, volume mounts, entrypoint |
| `docs/INTERFACES.md` | touching the data contract — loop-JSON fields + InfluxDB schema |
| `docs/ROADMAP.md` | choosing or re-prioritizing what to work on next |
| `BACKLOG.md` | open ideas / durable RF findings |
| `CHANGELOG-ARCHIVE.md` | history older than the live CHANGELOG |
| `docs/ASSESSMENT.md` | the strategic anchor (cross-repo governance alignment) |
| `docs/DATA_ERRATA.md` | known-bad observations + corrections (DEC-0025) |

Also: `AGENTS.md` — cross-agent entrypoint (points here + at STATUS); `LICENSE` — GPLv3.

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

- **Start:** read the Tier 1 set (STATUS.md first, **from `dev`'s tip if the checkout lags**);
  `git fetch && git status`; read STATUS.md "Active thread" + "Next session actions". A clean-pickup
  check: `git status` clean and `pytest` green before new work.
- **End:** update STATUS.md (session #, active thread, next actions — it's the source of truth),
  append to CHANGELOG.md, `git status` should show *up to date*. Don't strand the next session's
  handoff in private memory — it lives in STATUS.md so it's visible on GitHub.
- **Docs-diet ritual at close (DEC-0030):** prune STATUS to bench state (shipped → CHANGELOG
  pointer, settled → DEC pointer, superseded → delete); roll CHANGELOG entries beyond ~3 sessions
  to `CHANGELOG-ARCHIVE.md` verbatim; new DECs = full body in `DECISIONS-FULL.md` + index row in
  `DECISIONS.md`. **Move text, never delete or rewrite history** — and because this repo is public,
  run `scripts/check_secrets.sh` over anything a doc move rehomes.
- Sessions use **this repo's own independent counter** — a session number means something only within
  this repo (cross-repo refs are prefixed, e.g. `weewx S23` vs `dash S40`). **`docs/STATUS.md` is the
  single source of truth for the current session number** — take it from there (+1 for a new session),
  not from CHANGELOG or memory; every other doc points at STATUS. DEC-0023 supersedes the old
  shared-counter idea in DEC-0013. The governed era runs **S16 → S17 → S18 → S19 → S20 → S21 → S22 →
  S23 → …**; pre-S16 history is reconstructed/approximate.
