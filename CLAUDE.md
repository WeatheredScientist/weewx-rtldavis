# CLAUDE.md — weewx-rtldavis

**This is the entrypoint.** Follow the tiered session-start read below (DEC-0063) before touching
code. This repo is the **driver + Docker build** for a Davis 6263 / VP2+
ISS *passively intercepted* at 915 MHz via an **RTL-SDR Blog v3** dongle — the "escape the
WeatherLink lock" tool. It is a **public, published** WeeWX extension (Docker Hub +
GitHub releases). The **dashboard** that consumes this data lives in a **separate repo**
(`eaglehunt-weather-dashboard`) — don't make dashboard changes here (DEC-0010).

Its real contract is the **data it produces** — the loop-JSON file + the InfluxDB line-protocol
schema — not any single consumer. Keep it re-pointable so non-Davis WeeWX and eventually CumulusMX
can use it (PRINCIPLES §1, docs/INTERFACES.md).

## Documentation map — session-start read (DEC-0063)

**Read exactly three files at session start. Nothing else.**

| File | Answers |
|------|---------|
| `BOOT.md` | **where we are right now** — current session, active work, blockers, ordered backlog. The single source of truth for the session number and the handoff. *Standing watches moved to `BACKLOG.md` at S67 (DEC-0072)* |
| `CONSTANTS.md` | durable facts — infra, deploy layers, release/rollback, hardware, git model |
| `MANIFEST.md` | one row per on-demand artifact: what it holds and when to load it |

Everything else — `docs/DECISIONS.md`, `CHANGELOG.md`, `docs/CONVENTIONS.md`, `docs/PRINCIPLES.md`,
`docs/ROADMAP.md`, `BACKLOG.md`, architecture, interfaces, errata — is pulled **by name from
`MANIFEST.md`, mid-session, when the task touches it.** Lazily loaded is not optional-to-read:
*"working near it" still means read it*, and `MANIFEST.md` says when.

`ARCHIVE/` is **never** in the load path — history preserved, not carried.

**The current docs live on `dev`** — check `git log origin/main..origin/dev --oneline` and read from
`dev`'s tip if `main` lags. If a doc is missing or contradicts another, stop and flag it — don't
guess.

> This supersedes DEC-0030's six-file Tier-1 table. Measured at adoption: that set had reached
> ~25.5K tokens and was growing **~1.1K per session close**, structurally, because the closeout
> ritual appends to STATUS and CHANGELOG every time (DEC-0063).

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

## Infra reference

**In `CONSTANTS.md`** — NAS, Docker, deploy layers, release/rollback, hardware, git model. Stated
once, there, and nowhere else (STANDARD rule 5: a second copy is a defect, not redundancy — it is
the drift this exists to stop). *A quick-reference duplicate lived here until S60 and had already
gone stale on two values: the reception baseline and the driver-vs-config layer table.*

## Session ritual

- **Start:** read `BOOT.md` + `CONSTANTS.md` + `MANIFEST.md` (**from `dev`'s tip if the checkout
  lags**); `git fetch && git status`. A clean-pickup check: `git status` clean and `pytest` green
  before new work. Then check **this repo's own tracker** — a separate read from the ops-inbox
  below, found missing at S99 (#268): an issue filed directly here (like #264) was structurally
  invisible to every session start until this line existed, independent of what BOOT/BACKLOG/
  ROADMAP say, because nothing ever ran this query:
  `gh issue list -R WeatheredScientist/weewx-rtldavis --state open`
  Then pick up cross-repo assignments (ops-DEC-0005; Claude sessions only — one
  command, the rest of eaglehunt-ops stays not-a-session-start-read):
  `gh issue list -R WeatheredScientist/eaglehunt-ops --label repo:weewx --state open`
- **End (closeout skeleton — DEC-0052, adapted from eaglehunt-ops OPS-DEC-0016):**
  1. **Green gate** — run the commands **exactly as `docs/CONVENTIONS.md` spells them** (they need
     the repo venv and, for mypy, explicit arguments; three of the four previously documented here
     did not work as written — S59b). If skipped, state why.
  2. **`BOOT.md` rewrite** — update the `▶ Resume here` block (session #, active work, next
     actions). **Rewritten in place, never appended** (STANDARD rule 1): resolved items are
     deleted, a conclusion survives as one line. Over the ~2,500-token cap means content belongs in
     `ARCHIVE/` or as a `MANIFEST.md` row — *not* a bigger cap. Don't strand the handoff in private
     memory; it lives here so it's visible on GitHub.
  3. **CHANGELOG.md entry** — one line for what landed. Roll entries beyond ~3 sessions to
     `CHANGELOG-ARCHIVE.md` verbatim. **Move text, never delete or rewrite history** — and because
     this repo is public, run `scripts/check_secrets.sh` over anything a doc move rehomes.
     Update `MANIFEST.md` if the session added or retired an artifact.
  4. **Decision-log row** — if a design call was made this session, full body in
     `DECISIONS-FULL.md` + index row in `DECISIONS.md`, same session, not deferred.
  5. **ROADMAP.md reconciliation** (DEC-0057) — if a DEC logged in step 4 ships, closes, or
     reprioritizes a line item on `docs/ROADMAP.md`, update that line now, same session, not
     deferred. `docs/ROADMAP.md` also carries its own tripwire (a next-check-due session number
     under "Keeping this current") — if the session counter is at or past it, run the full
     reconciliation pass regardless of whether a DEC prompted this session.
  6. **Model-tier restore check** *(new)* — if a bare `/model` switch happened this session,
     confirm the Sonnet floor is restored before ending, or confirm a session-only switch was
     used and there is nothing to restore.
  7. **Commit + push**, per the branch model — subject to the pause-for-approval rule above
     (Non-negotiable rules).
  8. **Name the session** (DEC-0112, adopted from `CLOSEOUT-TEMPLATE.md`'s step 7 / OPS-DEC-0114 —
     renumbered to 8 here since this skeleton already had a step 7). As the **last** action of the
     closeout, call `set_session_title` on `"self"`, in this repo's own grammar: `weewx
     S<nums>[ ✓] · <slug>`. Write the `✓` **iff steps 1–7 actually completed this session** — it
     attests only that this session ran its own closeout, nothing about whether a PR merged
     (`ccAutoArchiveOnPrClose`'s job) or whether the window is still resumable (`isRunning`). Last on
     purpose: written any earlier it could outlive its own truth. A session that crashes or is
     abandoned simply never writes it — the absence is the honest report, not a missing one.
- Sessions use **this repo's own independent counter** — a session number means something only within
  this repo (cross-repo refs are prefixed, e.g. `weewx S23` vs `dash S40`). **`BOOT.md` is the
  single source of truth for the current session number** — take it from there (+1 for a new session),
  not from CHANGELOG or memory; every other doc points at it. DEC-0023 supersedes the old
  shared-counter idea in DEC-0013. The governed era runs **S16 → S17 → S18 → S19 → S20 → S21 → S22 →
  S23 → …**; pre-S16 history is reconstructed/approximate.
