# MANIFEST — weewx-rtldavis

**Always-load, tier 1.** One row per on-demand artifact: what it holds, and when to load it.
Nothing here is read at session start — pull by name, mid-session, when the task touches it.
*"Working near it" means read it.*

## Governance & history

| Artifact | Contents | Load when |
|---|---|---|
| `docs/DECISIONS.md` | index of settled decisions, one row each | starting work near a settled area — **scan before proposing anything; do not re-litigate a listed decision** |
| `docs/DECISIONS-FULL.md` | full append-only ADR bodies (~180 KB) | **grep the DEC id** whenever a listed decision is near your change — never read whole |
| `CHANGELOG.md` | recent sessions, most recent first | reconstructing what shipped when, or writing a closeout entry |
| `CHANGELOG-ARCHIVE.md` | history older than the live CHANGELOG (~120 KB) | forensic lookup only |
| `docs/ROADMAP.md` | the actively-sequenced plan, **P0–P3 only** (DEC-0058) | choosing or re-prioritizing what to work on next; **updating a line a DEC just shipped/closed (DEC-0057, same session)** |
| `BACKLOG.md` | open ideas · **durable RF findings** · long-term direction | RF work, or anything horizon-scale |
| `docs/PRINCIPLES.md` | durable intent behind the design | weighing a new decision for consistency |
| `docs/CONVENTIONS.md` | how we operate — command hygiene, git workflow, secrets, **the exact validation gates and interpreter** | before running any gate; before any commit |
| `docs/ASSESSMENT.md` | the strategic anchor, cross-repo governance alignment. **Predates DEC-0063** — its "STATUS.md is the single source of truth" rows describe the S23 state, not today's | governance/consistency work, read as a dated audit |
| `docs/UPSTREAM-THREADS.md` | the four open contribution threads upstream (lheijst ×2 + issue #15, david-lutz), and the posting etiquette | replying upstream, preparing a PR, or checking whether a thread moved |

## Technical

| Artifact | Contents | Load when |
|---|---|---|
| `docs/ARCHITECTURE.md` | the ISS→RTL-SDR→driver→WeeWX→sinks chain, volume mounts, entrypoint, the **pyc gotcha** | touching any part of that chain |
| `docs/INTERFACES.md` | **the data contract** — loop-JSON fields + InfluxDB schema | changing anything a consumer reads; this is the repo's real deliverable |
| `docs/DATA_ERRATA.md` | known-bad observations + corrections (`ERR-####`, DEC-0025) | investigating a suspect historical reading, or making a retrospective correction |
| `CHANGES-FROM-UPSTREAM.md` | honest statement of the fork's divergence (DEC-0034) | changing driver behavior vs. upstream; preparing an upstream PR |
| `ops/rx_experiment.sh` | the RX campaign apparatus — schedule, swap, health check, abort. Currently loaded: **campaign B** (pilot + hold + square, DEC-0064) | campaign tracking or campaign design |
| `docs/CAMPAIGN-B-RUNBOOK.md` | the swap-night checklist — owner gates, timeline, rollback paths, expected numbers | the 08-07 swap night, or any campaign-B question |
| `ops/soak_check.sh` | acceptance-criteria verdict (`EXPECT_IMAGE` tracks the deployed tag) | after any deploy; any time a fresh verdict is wanted |
| `ops/campaign_analyze.py` | **the campaign readout** (DEC-0069) — per-minute `rxCheckPercent` from the archive DB, structural freeze exclusion, per-arm means with the uncleaned figure alongside | reading ANY campaign result, A or B; the A-vs-B LNA contrast. **Pass `--since` for campaign A** — its aborted 07-29 attempt is in the same log (the tool warns) |
| `ops/freeze_watch.sh` | read-only DEC-0067/DEC-0068 freeze watcher — polls `weewx.log`, captures paired `S`/`D`/`R` thread samples + a `nasctl ps` snapshot on a stall, macOS-notifies | investigating the process freeze, or verifying it's resolved |
| `scripts/check_secrets.sh` | the secret gate (+ `scripts/test_check_secrets.sh`) | before every commit — **with a planted-payload positive control** |

## Public-facing

| Artifact | Contents | Load when |
|---|---|---|
| `README.md` · `CONTRIBUTING.md` · `SECURITY.md` | what external users and contributors read | changing anything user-visible, or handling a report |
| `AGENTS.md` | cross-agent entrypoint (points at `BOOT.md`) | another agent tool is involved |
| `LICENSE` | GPLv3 | licensing questions |

## ARCHIVE/ — never in the load path, and **local-only, not in the repo**

> **Read this before looking for these files in a clone — they are not there.** `ARCHIVE/` is
> gitignored (`.gitignore` `archive/`, which matches case-insensitively on macOS) and its contents
> were **never tracked**. That is deliberate and must stay that way: these are pre-governance
> conversation dumps from S16, and a scan found **IP-shaped and credential-shaped strings** in two
> of the three. This repo is **public** — DEC-0012 forbids committing them, and STANDARD §6 requires
> the audit before any such file is committed. So this is a divergence from STANDARD rule 3's
> "history stays in the repo and in `ARCHIVE/`": **for this repo, history stays in git *history* and
> on the owner's disk, not in a committed `ARCHIVE/`.** Nothing is lost that was ever in the repo —
> these three were untracked working files all along.

Retired, resolved narrative. Forensic lookup only, on the owner's machine.

| Artifact | Contents |
|---|---|
| `ARCHIVE/weewx-rtldavis_Consolidation_20260704.md` | the pre-governance consolidation + Claude Code migration plan (S16 provenance). **Contains unscrubbed infra strings — never commit** |
| `ARCHIVE/weewx-rtldavis_ClaudeCode_Kickoff_20260704.md` | the S16 kickoff brief, companion to the above. **Contains an IP-shaped string — never commit** |
| `ARCHIVE/DECISIONS_staging_20260704.md` | the pre-repo decision staging buffer, superseded by `docs/DECISIONS.md`. Scanned clean, but stays uncommitted with its siblings |

**Retired content that IS in the repo** lives in git history — `docs/STATUS.md` up to its S60
retirement, and every superseded doc revision. `git log --follow <path>` reaches all of it.

## docs/handoffs/ — retired as startup artifacts, but still cited

Not in the load path and not archived: all three are **referenced by path** from live docs, so
moving them would break those citations for no gain (DEC-0063). The shared archiver does not match
them — they are session-numbered, not date-stamped.

| Artifact | Contents | Load when |
|---|---|---|
| `docs/handoffs/S38-cross-repo-architecture.md` | **the source of the four-line agent protocol the whole Eagle Hunt family runs on.** Cited from `docs/DECISIONS-FULL.md` and formerly `docs/STATUS.md` | any cross-repo architecture or agent-protocol question — **this row exists so that pointer is never lost** |
| `docs/handoffs/S37-to-all-projects-stdout-freeze.md` | the stdout/log-freeze finding sent family-wide. Cited from `docs/DECISIONS-FULL.md` | investigating a container/daemon wedge (DEC-0036/0041) |
| `docs/handoffs/S36-to-eaglehunt-dashboard.md` | the S36 handoff to the dashboard repo. Cited from `CHANGELOG-ARCHIVE.md` | tracing a cross-repo contract back to its origin |

## Not in this repo

| Thing | Where |
|---|---|
| Dashboard code and its decisions | `eaglehunt-weather-dashboard` (separate repo — **don't make dashboard changes here**, DEC-0010) |
| Real infra values, coordinates, security follow-ups | gitignored local-infra doc |
| **Upstream draft text** (`docs/upstream/`) | **local-only, gitignored on purpose** — drafts are owner-reviewed and **never posted without an explicit go**. Present in the owner's checkout, absent from a fresh clone. The *state* of those threads is `docs/UPSTREAM-THREADS.md`, which is tracked |
| Cross-repo coordination, shared constants, the `~/.claude/` guards | `eaglehunt-ops` (**private** — owner-only; never a prerequisite for anything here, DEC-0063) |
