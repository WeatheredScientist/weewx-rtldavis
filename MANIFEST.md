# MANIFEST — weewx-rtldavis

**Always-load, tier 1.** What to pull on demand, and when — never read at session start. *"Working
near it" means read it.* **Classes, not instances** (STANDARD rule 9): one row names a set and its
convention; instances self-describe at their source.

## Governance & history

| Artifact | Load when |
|---|---|
| `docs/DECISIONS.md` + `docs/DECISIONS-FULL.md` — the settled-decision index; full ADR bodies (~180 KB) | before working near a settled area. **Scan the index; do not re-litigate a listed decision.** Grep the DEC id in FULL, never read it whole |
| `CHANGELOG.md` + `CHANGELOG-ARCHIVE.md` — what shipped when, recent first | writing a closeout entry; the archive is forensic |
| `docs/ROADMAP.md` — the sequenced plan, P0–P3 (DEC-0058) | choosing what's next; **updating a line a DEC just shipped (DEC-0057, same session)**. Carries its own next-check-due tripwire |
| `BACKLOG.md` — open ideas · durable RF findings · **the standing watches** · long-term direction | RF work, anything horizon-scale, or whether a watch has fired |
| `docs/CONVENTIONS.md` — command hygiene, git workflow, secrets, **the exact gates and the only interpreter with the tooling** | before any gate; before any commit |
| `docs/PRINCIPLES.md` — durable intent · `docs/ASSESSMENT.md` — governance anchor | weighing a new decision for consistency. ASSESSMENT **predates DEC-0063**: a dated audit of S23, not of today |
| `docs/UPSTREAM-THREADS.md` — the four open upstream threads, and the etiquette | replying upstream, or checking whether a thread moved |

## Technical

| Artifact | Load when |
|---|---|
| `docs/ARCHITECTURE.md` — ISS→RTL-SDR→driver→WeeWX→sinks, mounts, entrypoint, the **pyc gotcha** | touching any part of that chain |
| `docs/INTERFACES.md` — **the data contract**, loop-JSON + InfluxDB schema | changing anything a consumer reads. The repo's real deliverable |
| `docs/DATA_ERRATA.md` — known-bad observations and corrections (`ERR-####`) | a suspect historical reading, or a retrospective correction (DEC-0025) |
| `CHANGES-FROM-UPSTREAM.md` — the fork's divergence, stated honestly (DEC-0034) | changing driver behavior vs. upstream; preparing an upstream PR |
| **`ops/*` + `scripts/*` — the harness**, plus `docs/CAMPAIGN-B-RUNBOOK.md` (swap-night gates, timeline, rollback, expected numbers) | any ops task, and the swap night. **Each script's header is its manual — read it before using or extending one.** Each states why it exists, the lying symptom it catches, and its gotchas. `ops/campaign_analyze.py` is the **only** sanctioned campaign readout (DEC-0069) |
| `README.md` · `CONTRIBUTING.md` · `SECURITY.md` · `AGENTS.md` · `LICENSE` (GPLv3) — the public face | changing anything user-visible, handling a report, or when another agent tool is involved |

## Not in a clone, never in the load path

| Thing | Why it is not here |
|---|---|
| `ARCHIVE/` | local-only, gitignored, **never tracked** — S16 dumps carrying IP- and credential-shaped strings, which a public repo must never hold (DEC-0012, a deliberate divergence from STANDARD rule 3). Nothing once *in* the repo is lost — `git log --follow` reaches it all, `docs/STATUS.md` included |
| `docs/handoffs/` | three retired handoffs, kept because live docs cite them **by path**. Never lose `S38-cross-repo-architecture.md` — source of the agent protocol the whole Eagle Hunt family runs on |
| `docs/upstream/` | drafts, gitignored — **never posted without an explicit go**. Thread *state* is the tracked `UPSTREAM-THREADS.md` |
| Dashboard code and decisions | `eaglehunt-weather-dashboard` — **don't make dashboard changes here** (DEC-0010) |
| Real infra values, coordinates, security follow-ups | the gitignored local-infra doc |
| Cross-repo coordination, shared constants, `~/.claude/` guards | `eaglehunt-ops` — **private**, never a prerequisite (DEC-0063) |
