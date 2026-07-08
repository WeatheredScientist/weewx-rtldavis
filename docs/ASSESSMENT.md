# Assessment — Cross-Project Governance Alignment (S23)

**Status:** Strategic anchor (cross-repo governance audit + alignment model + roadmap)
**Last updated:** 2026-07-05 (S23, Claude Opus 4.8)
**Scope:** the three-repo Eagle Hunt family — `weewx-rtldavis` (this), `eaglehunt-weather-dashboard`,
`hyperlocal-forecast`. This repo is the **pilot** for a shared governance standard (see §2, §5).
**See also:** CONVENTIONS.md, DECISIONS.md (DEC-0023 numbering, DEC-0010 repo separation),
ROADMAP.md, STATUS.md. Meta-goal recorded in Claude memory `cross-project-governance-alignment`.

---

## 1. Honest assessment (the cross-repo audit)

**Thesis:** the three repos share a common ancestor governance model but have **diverged** in exactly
the ways that make cross-project handoff expensive — while each is individually reasonable. The goal
is not "make them identical" but "make their *form* predictable and their *process* aligned to
external best practice, while keeping their *content* isolated."

### The family at a glance

| Dimension | weewx-rtldavis (this) | eaglehunt-dashboard | hyperlocal-forecast |
|---|---|---|---|
| Governance model | 9-doc | 9-doc (+DATA-MODEL, PR template) | Richest — meta-docs + session folders |
| Session-# source of truth | **scattered** (STATUS + CHANGELOG + Claude memory) | its own counter | **STATUS.md only** ✅ |
| Next-session handoff | **in Claude private memory** (invisible on GitHub) | STATUS "Active thread" | `docs/sessions/session_N/` (in repo) |
| AGENTS.md (cross-agent std) | ✗ | ✗ | ✅ |
| LICENSE | ✗ **(repo is PUBLIC + published!)** | ✗ | ✅ (repo is private) |
| pre-commit / CI / secret gate | ✅ **(strongest of the three)** | ✗ | ✅ |
| Full toolchain gate (ruff/mypy/pytest) | partial (pre-commit only) | n/a (JS) | ✅ |
| Doc-map slot for STATUS | #8 (near end) | #8 | **#2 (right after entrypoint)** |
| Changelog format | freeform prose | freeform | Keep-a-Changelog headings |

### What is genuinely good (keep)
- weewx has the **strongest public-repo secret discipline** of the three: pre-commit + CI + a
  load-bearing `check_secrets.sh` gate (DEC-0012, DEC-0015). Do not weaken this.
- All three already use DEC-NNNN ADRs, a 9-doc map, and independent session lineages — a solid shared
  skeleton to converge *onto*, not replace.
- weewx's domain principles (RF noise-floor honesty, hot-swap-vs-bake, prod-is-sacred, honest-nulls)
  are excellent and repo-specific. Harmonization must **not** homogenize these away.

### The hard truths
1. **Handoff state is trapped in Claude-private memory.** The "what to do next" for this repo lives in
   `~/.claude/.../next-session-actions.md` — a *different LLM or a human on GitHub cannot see it.* This
   is the single largest violation of the north star (any repo pickup-able from GitHub alone).
2. **Session number has no single source of truth.** It is repeated in STATUS + CHANGELOG + memory —
   the exact drift pattern hyperlocal already suffered (pointers disagreed four ways) and fixed by the
   rule "STATUS.md is the only place it lives; everything else points at it."
3. **No LICENSE on a public, published tool.** weewx ships on Docker Hub + GitHub releases with no
   license = legally unreusable/uncontributable — backwards from the private repo that *has* one, and
   contrary to the project's own "free tool others can use" mission.
4. **No cross-agent entrypoint.** No `AGENTS.md`, so non-Claude agents have no standard door in.
5. **Format drift.** Changelog and roadmap conventions differ across repos with no shared vocabulary,
   so "what to expect" changes per repo.

---

## 2. The alignment model (isolate content, harmonize form)

The resolving insight: **isolation and harmonization operate on different layers and do not conflict.**

- **Isolate content** — code, DECs, runtime, secrets, session lineage, "what's on the bench." This is
  correct and already enforced (DEC-0010, DEC-0023); keep it. Repos never touch each other.
- **Harmonize form** — the doc skeleton, process rules, and shared vocabulary. A shared *grammar*, not
  shared *state*.

**Mechanism (right-sized for a solo maintainer working with Claude):**

1. **One canonical Governance Standard**, authored once (see §3): the invariant skeleton + process +
   vocabulary, plus a **per-repo profile** for legitimate deviations.
2. **Each repo instantiates it fully, self-contained** — no submodules, no cross-repo links a reader
   must chase. A one-line conformance note per repo: *"Conforms to Eagle Hunt Governance Standard vN;
   deviations in CONVENTIONS."* (Rejected: a shared governance repo that others link to — it
   re-introduces the coupling we avoided and breaks GitHub-alone pickup.)
3. **Sync by audit, not by coupling** — a recurring lightweight cross-repo audit (this document's
   descendants) diffs the three against the standard, records "found stale during audit" notes (the
   dashboard's own pattern), and converges them. The audit *is* the anti-drift mechanism.
4. **Deviations are allowed but declared** via the profile — not silent drift.

---

## 3. Draft Governance Standard v1 (shared core + profiles)

| Layer | Shared core (all repos) | Per-repo profile (declared deviations) |
|---|---|---|
| **Docs** | CLAUDE.md map; STATUS, CONVENTIONS, PRINCIPLES, DECISIONS, ARCHITECTURE + one data-contract doc; CHANGELOG; BACKLOG | weewx: INTERFACES · dashboard: DATA-MODEL · hyperlocal: API_CONTRACT |
| **Entry** | CLAUDE.md (Claude) + AGENTS.md (generic agents), both pointing at STATUS | hyperlocal also: BOOTSTRAP.md (ChatGPT) |
| **Session #** | STATUS.md is the **single source of truth**; independent per-repo lineage; every other doc points at it | — |
| **Handoff** | Next-session state lives **in the repo** (STATUS at minimum), never only in private memory | hyperlocal: full HANDOFF_PROTOCOL + session folders (two-agent) |
| **Decisions** | DEC-NNNN ADRs: Status / Date+Session / Decision / Rationale; do not re-litigate, supersede | — |
| **Changelog** | Keep-a-Changelog headings: Added / Changed / Fixed / Removed / Decisions / Open | — |
| **Roadmap** | Shared P0–P4 tiers (short=P0/P1, medium=P2/P3, long=P4/horizon); ✅ done-markers; "found stale during audit" annotations; a "vision" preamble | — |
| **Process rules** | Discuss-before-building; No-Rewrite Rule; secrets never committed or pasted to an LLM; pickup gate (`git status` clean + tests green) | weewx: LICENSE + CI + secret-scan gate (public repo) |
| **Doc-map order** | STATUS at slot #2 (right after the entrypoint) — "where are we" is the first question | — |

---

## 4. Recommendations for weewx (ranked; this repo, this initiative)

1. **Move next-session/handoff state out of memory into the repo.** STATUS.md "Active thread" already
   nearly does this; make it authoritative and complete so memory only *points at* it. *(north-star fix)*
2. **STATUS.md = single source of truth for the session number**; bump STATUS to doc-map slot #2.
3. **Add LICENSE = GPLv3** (WeeWX-ecosystem standard; legally cleanest for a WeeWX-derived work; matches
   the "stays free/open" mission) + short per-file SPDX headers.
4. **Add AGENTS.md** — a thin cross-agent entrypoint pointing at CLAUDE.md + STATUS.md.
5. **Converge formats:** Keep-a-Changelog headings; ROADMAP restructured to P0–P4 / short-med-long,
   folded to current (post-S22) reality; DECISIONS entry skeleton aligned.
6. **Housekeeping stragglers found in the audit:** the root-level `cleanup_backlog.md` (119 lines,
   pre-governance, "Eagle Hunt PWS", mostly done ✅) should be archived/folded into BACKLOG; confirm
   `logging.additions` and the bare `additions` artifact are intentional; give them a home or remove.
7. **Thorough code-quality review** (rtldavis.py 1506 ll + weewx_monitor.py + uploaders) for
   sloppy/confusing/under-commented code — ranked findings, then agreed fixes on a branch. *(S24)*

---

## 5. Roadmap (this initiative; docs-first, zero prod risk)

- **S23 (now):** this ASSESSMENT; then the safe docs deliverables — LICENSE, AGENTS.md, ROADMAP
  restructure, STATUS as session-# SSOT + handoff-in-repo, doc-map reorder. All on a branch for review.
  No prod code, no deploy.
- **S24:** thorough code-quality review (findings → agreed fixes on a branch).
- **S25:** changelog-format + DECISIONS-skeleton convergence; then resume the v2.0.3 release path
  (rain fix + reception fix + baked dewpoint rewrite).
- **Ongoing:** propagate the settled standard to `eaglehunt-dashboard` and `hyperlocal-forecast` in
  *their* own sessions via the cross-repo audit.

### The generic project template (larger goal)
The Governance Standard, once proven here, is **harvested** into a project-agnostic
**GitHub template repository** (copy-not-link — the one place a 4th repo is justified, because a
template is meant to be copied from). New projects start via GitHub "Use this template": doc skeleton
+ CLAUDE.md/AGENTS.md stubs + the standard + LICENSE guidance + pre-commit/CI/secret-scan skeleton +
empty DECISIONS/ROADMAP/STATUS/CHANGELOG. The template is **versioned**; each project records its
birth version; the audit reconciles projects toward the current template. **Build the concrete thing
first (weewx), abstract second (template)** — never design the template in a vacuum.

---

## 6. Direction decisions (proposed defaults — override any of these)

1. **LICENSE = GPLv3** for weewx (and the eventual template offers it as the default, MIT/Apache as
   documented alternatives).
2. **Pilot the standard in weewx**, harvest it into a versioned GitHub template repo, propagate to the
   other two via audit — rather than authoring the standard in the abstract first.
3. **Harmonize by copy + periodic audit**, never by submodule/shared-repo runtime coupling — preserves
   isolation and GitHub-alone pickup.
4. **Keep content fully isolated** (code, DECs, runtime, session lineage) — only *form* converges.

These are proposed defaults, changeable without re-litigating the overall direction. To be recorded as
DEC candidates (DEC-0025 governance-standard adoption; DEC-0026 LICENSE = GPLv3) once approved.
