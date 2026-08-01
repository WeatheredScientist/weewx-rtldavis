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

**`BOOT.md` is the single source of truth** for the current session number and the active work.
Read it first — do not infer "where we are" from any other doc.

## Required reading — three files, then stop (DEC-0063)

1. `BOOT.md` — where we are right now: session #, active work, blockers, backlog, standing watches
2. `CONSTANTS.md` — durable facts: infra, deploy layers, release/rollback, hardware, git model
3. `MANIFEST.md` — one row per on-demand artifact, and when to load it

Everything else (`CLAUDE.md`'s rules, conventions, principles, decisions, architecture, interfaces,
roadmap) is pulled **by name from `MANIFEST.md` when the task touches it**. Lazily loaded is not
optional-to-read — *"working near it" means read it*, and `MANIFEST.md` says when.
`ARCHIVE/` is never in the load path.

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
  `BOOT.md`. Prefix cross-repo references (`weewx S23` vs `dash S40`).

## Validation

**The authoritative gate list is `docs/CONVENTIONS.md` §"Python / validation" — use it verbatim.**
It is stated there once and nowhere else, deliberately: a duplicate list lived in this file until
S60 and had drifted into naming `ruff-format`, which **DEC-0027 exists to reject** and which would
reformat 30 of 33 files. The same drift was found and fixed in `CLAUDE.md` (S59b) and in
`.pre-commit-config.yaml` (S43). Three copies, three drifts — hence one copy now.

Two things worth knowing before you run anything:

- Use the **repo venv** (`.venv/bin/python`). Neither a bare `python` nor `python3` on this box
  carries pytest, mypy or ruff.
- `pre-commit run --all-files` is a useful pre-flight, but a local mypy "Passed" is **not** proof CI
  will pass — the incremental cache can mask real errors. `rm -rf .mypy_cache` first.

## Sibling repos (same governance family, don't edit from here)

- `eaglehunt-weather-dashboard` — the reference consumer (front-end + `eh-proxy`).
- `hyperlocal-forecast` — the forecast API; the most mature governance reference in the family.

All three conform to a shared **Eagle Hunt Governance Standard** (see `docs/ASSESSMENT.md`) — same
skeleton and process, isolated content, per-repo profiles for legitimate differences.
