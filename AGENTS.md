# AGENTS.md — weewx-rtldavis

Cross-agent entrypoint (the `AGENTS.md` convention many coding agents read). **Claude's primary
entrypoint is `CLAUDE.md`** — read it in full; this file is the short door in for any other agent or
human and points at the same governed docs. If anything here and `CLAUDE.md` disagree, `CLAUDE.md`
wins and this file is the bug.

## What this repo is

The **driver + Docker build** for a Davis 6263 / VP2+ ISS *passively intercepted* at 915 MHz via an
RTL-SDR Blog v3 dongle — a **public, published** WeeWX extension (Docker Hub + GitHub releases). Its
real contract is the **data it produces** (loop-JSON file + InfluxDB line-protocol schema,
`docs/INTERFACES.md`), not any one consumer. Licensed **GPLv3** (see `LICENSE`).

## Where we are right now

**`docs/STATUS.md` is the single source of truth** for the current session number and the active
thread. Read it first — do not infer "where we are" from any other doc.

## Required reading (in order)

1. `CLAUDE.md` — the map + the rules that must never break
2. `docs/STATUS.md` — where we are right now (session #, active thread)
3. `docs/CONVENTIONS.md` — how we operate (paths, commands, workflow, secrets)
4. `docs/PRINCIPLES.md` — durable intent
5. `docs/DECISIONS.md` — settled ADRs; do not re-litigate, supersede with a new DEC
6. `docs/ARCHITECTURE.md` — the ISS→RTL-SDR→driver→WeeWX→sinks chain
7. `docs/INTERFACES.md` — the data contract consumers depend on
8. `docs/ROADMAP.md` — what's next, in what order

## Non-negotiable rules (full detail in the docs cited)

- **This repo is PUBLIC.** No credentials, tokens, or personal identifiers in any commit on any
  branch. The `scripts/check_secrets.sh` pre-commit gate is load-bearing (DEC-0012, DEC-0015).
- **Never paste a live secret into any LLM chat.** Treat anything that reaches a prompt as
  compromised and rotate it server-side.
- **Discuss design before coding**; pause for approval before every commit and every push.
- **No-Rewrite Rule** (DEC-0014): no subsystem rewrite without documented cause, an alternative, a
  migration plan, a DEC entry, and explicit approval. Favor incremental change.
- **Prod is sacred** — one dongle, one receiver, no drop-in dev. Deploy to dev first; agree a
  reversible test + rollback plan before touching prod (DEC-0011).
- Session numbering is this repo's **own** independent lineage (DEC-0023); take it from
  `docs/STATUS.md`. Prefix cross-repo references (`weewx S23` vs `dash S40`).

## Validation

Local quality gates (CI mirrors these); run before considering work complete:

```bash
pre-commit run --all-files        # ruff + ruff-format + mypy + the secret-scan gate (DEC-0015)
python -m pytest                  # offline unit tests (tests/)
```

## Sibling repos (same governance family, don't edit from here)

- `eaglehunt-weather-dashboard` — the reference consumer (front-end + `eh-proxy`).
- `hyperlocal-forecast` — the forecast API; the most mature governance reference in the family.

All three conform to a shared **Eagle Hunt Governance Standard** (see `docs/ASSESSMENT.md`) — same
skeleton and process, isolated content, per-repo profiles for legitimate differences.
