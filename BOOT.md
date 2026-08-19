# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3 — the "escape the WeatherLink lock" tool. A public, published
WeeWX extension (Docker Hub + GitHub releases), GPLv3. Its real contract is the **data it emits**
(loop-JSON + InfluxDB line-protocol schema), not any one consumer. The dashboard that consumes it
is a **separate repo** — don't make dashboard changes here.

---

## ▶ Resume here (S91 → S92)

### ⚠️ FIRST THING NEXT SESSION: pin down the probe's actual stop time before anything else

`proc_probe_nas.sh` (pid **28699**)'s stated end epoch is "2026-08-19 05:00" (DEC-0098), with no
explicit timezone written down anywhere. Per this repo's own gotcha below — treat a bare
timestamp as UTC until proven local — **05:00 UTC is 01:00 EDT, which had already passed by S91
close (~01:05 EDT).** If the epoch was meant in UTC, the probe has already stopped; if it was
meant local, ~4h remained as of S91 close. **Don't compute an answer — check the actual process
state directly** (`nasctl ps` / a startup-line-after-mtime check per DEC-0074's rule) before
deciding whether this is still time-sensitive. Then: harvest read-only into a file (never onto the
terminal), `ops/proc_probe.py --ingest <pulled> && ops/proc_probe.py --analyze logs/proc_probe.csv`
(ingest is idempotent, analyze de-dupes, so a partial/late harvest is safe either way), then clean
up the NAS (`proc_probe_nas.sh`, `.pid`, `logs/proc_probe_nas.{log,err}`) — Class C, needs the
in-chat path. Full context: job 2 below.

### What's settled (do not re-derive)

**S91: the full code audit (BOOT job 7) is DONE — two independent halves, both wrapped.**

- **Security pass** (4 DEC-primed finder agents + an Opus-tier adversarial verification pass): 2
  confirmed findings, both fixed, merged same session. **DEC-0101**: unverified SMTP TLS at both
  alert-mail call sites (`weewx_monitor.py`'s `send_email()`, `ops/rx_experiment.sh`'s
  `send_mail()`) exposing `GMAIL_PASS` to an on-path attacker, and the WeatherLink API key leaking
  into `weewx.log` via exception text on any connection failure (`pressure_service.py`). PR #229,
  merged. Bundled into the same close-out window: PR #228, a pre-3.12 Python `SyntaxError` in
  `ops/proc_probe.py` (a multi-line f-string conditional needing PEP 701) found by the ultrareview
  cloud pass — unrelated to security but relevant to job 2 above; and a structural fix to
  `docs/DECISIONS.md` (DEC-0093–0101 had been sitting under `## Open / deferred` despite every one
  being `Accepted` — moved into the main table, also caught by ultrareview).
- **Correctness pass** (10 independent finder angles + Opus-tier verification of all 21 surviving
  candidates + a sweep pass that found 6 more): **26 distinct findings survived** (20 confirmed, 6
  plausible). 2 further candidates were independently **REFUTED** during verification — the
  packet-duplicate-detector "aliasing bug" is inert because the Go binary already dedups
  byte-identical frames upstream, so the dict-mutation issue never actually fires. **Filed as
  GitHub issues, not fixed yet** — grouped into 8 issues (#219–226) by shared root cause /
  fix-pattern rather than 1:1, sequenced in tracking issue **#227**, which is the map for the next
  several sessions of this work (each sub-issue states its own model tier). Cross-repo heads-up
  posted: **eaglehunt-ops#180** (informational only, no action expected from other repos).
  **Deploy gate for every one of #219–226**: `rtldavis.py` (and very likely
  `dewpoint_service.py` — verify with `nasctl inspect`, don't assume the pattern transfers) are
  baked into the Docker image, so none of it can deploy before Campaign B closes (~08-23). Design
  and merge to `dev` freely any time; hold the image cut for the v2.0.14 window already queued
  below — except #225/#226 (lowest priority, confirmed dormant on this station's actual config),
  which should ride a *later* v2.0.15+ cut rather than compete for scope in v2.0.14.

**ultrareview's own scope note, worth carrying forward**: `/code-review ultra`'s cloud launcher
parses its argument as a base-branch slot, not a path-target list — passing file paths gets read
as a free-text "note," and it silently falls back to the `dev`→`main` diff instead. The **local**
`/code-review <level> <target>` command (no `ultra`) *does* support a path target per its own Phase
0 instructions ("If a PR number, branch name, or file path was passed as an argument, review that
target instead") — use that, not `ultra`, when the goal is auditing stable/unchanged files rather
than a diff.

**The v2.0.14 queue (post-campaign, ~08-23) is fully staged on `dev`, window has a MANDATORY
OPENING MOVE (unchanged from S90):**

0. **FIRST PR of the window: empty the SCHEDULE block** (stand-down, DEC-0096) — until this
   trivial, self-green deletion lands, every other PR sits red on the staleness guard.
1. Image cut: weewx **5.5.0** (merged, PR #208) + #183's pressure package (merged) + monitor trio
   (DEC-0090/0091). NAS-native build (DEC-0078); the recreate re-verifies CONSTANTS' three
   live-config deviations **and** the LNA-out hardware-timeline line.
2. Move `:latest` to v2.0.13 once the square proves it.
3. Copy the new `loop_json_writer.py` (with `current_interval`) to the NAS *project root* — not
   the image, not `weewx-data/bin/user/` (mounted not baked, DEC-0093). Verify with `nasctl
   inspect` before; confirm the startup line reads `every 60 s` after.
4. NAS-side (ops#169/DEC-0092): `noatime` on `/volume1`, `chattr +C` on the archive DB, move our
   logrotate off 00:05.
5. **NAS-LEASE first adoption (DEC-0099):** mount `LEASE_DIR` read-only at the recreate;
   `influx.py` checks it at its own poll, raises `post_interval` while a foreign lease is held; the
   NAS image build wraps `docker build` with acquire→flock→release as weewx's first HOLDER.
   Renewal in-place only (seek+write+truncate) — never `tmp`+`os.replace`, DEC-0051's idiom would
   silently strand the flock.
6. **New this session**: the S91 correctness-audit fixes ready by then (#219–224 per the
   sequencing in #227) ride this same cut where the tier allows.

**Resume machinery (DEC-0087/0089) remains proven**: 12+ pause/resume cycles across five nights
now, all auto-recovered, zero unintended STOPs. Still unexercised: the 120-min ceiling escalation,
the swap-deferral path, rotated-log reads across a `.1` boundary.
*(`rx_experiment.STOP.campaignA` at the project root is campaign **A**'s sentinel, not live — leave
in place absent an explicit say-so.)*

**Hardware history (CONSTANTS.md): LNA in ~01Jun→02Aug, out since.** Attribution for the elevated
stall rate stays open (DEC-0083), a post-campaign characterization question.

### ▶▶ S92 JOB LIST

**Job 2 is time-sensitive — resolve the timezone question above before anything else this
session. Everything else here is watch-, execution-, or backlog-tier; #219–227's work (job 7's
output) has its own sequencing inside #227 and doesn't need re-planning here.**

1. Daily square watch (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
   **Verified good through block 17 (08-19 00:07, arm A)** at S91 close — soak 16 pass / 2
   expected-WARN, reception 57–62%, no STOP/PAUSE/lock. `remote probe took Ns` ≥20s is a
   NAS-load signal, not noise.
2. ⚠️ **Probe harvest — see the timing note at the top of this file. Class C, needs the in-chat
   path.**
3. Resume machinery — keep counting cycles; watch for the three untested paths noted above.
4. **[ops#173] BOOT.md over cap — TRACKED, do not re-derive or open a second issue.** Diet at the
   square's close (~08-23). This session's rewrite trimmed the now-resolved S90/S91 narrative but
   added the new job-7 outcome and #219–227 pointers — net effect not measured, the diet itself is
   still owed and still deferred on purpose.
5. **v2.0.14 prep is DONE**, now including the S91 audit fixes as they land (queue item 6 above).
   Nothing to decide before ~08-23.
6. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
7. **Code-audit remediation — #227's sequenced plan.** Pick up #219 (ProcManager lifecycle,
   frontier tier) first per the plan's own stated rationale, or #220 (battery-low regex, mid tier)
   if the session doesn't have room for a frontier-tier design pass. Each sub-issue states its own
   model tier — read it before starting.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[weewx#227]: https://github.com/WeatheredScientist/weewx-rtldavis/issues/227

### Current state (S91 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b, sha+process verified |
| Campaign B | **Live and on schedule — block 17 of 32, arm A since 08-19T00:07:23.** Square through `08-23T00:05` (~4.1 d left). STOP/PAUSE/lock absent (confirmed via `rx_experiment.state` direct read). Soak (re-run S91 close): 16 pass / 2 expected-WARN, reception 57–62% |
| Swap settle time | n=10 (unchanged since S90): 82/139/198/137/197/79/136/196/144/84 s — not a trend |
| Retention | **BOTH halves SETTLED** (DEC-0095/DEC-0100), unchanged since S90 |
| `dev` beyond prod | Everything for v2.0.14 (unchanged from S90) **plus** the S91 security fixes (DEC-0101, merged) and the correctness-audit fixes as #219–226 land |
| Freeze rate | DEC-0088-corrected (1.31/day), untouched this session |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | **Steady state restored: exactly `dev` + `main`.** PR #228 (proc_probe.py syntax) + PR #229 (DEC-0101 + DECISIONS.md structure) merged 08-19 (S91), both branches deleted |
| Trackers | **New this session: #219–226 (S91 audit fixes, open) + #227 (tracking/sequencing issue, open).** #158 closed · #172/#144 open until v2.0.14 · #204 open (current.json cadence heads-up) · ops#163/#176 closed · ops#180 (S91 cross-repo heads-up, informational, open) |
| Cross-repo (S91) | One new thread, informational only: ops#180 flags the audit methodology (multi-angle + adversarial verify + sweep) as possibly worth reusing on HLF/dashboard — not a request, no reply expected |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected), separate phenomenon**
   from DEC-0081's RF-dead episodes. Still hard-aborts. Root cause still unproven (thread blocking
   on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068). Evening 18:00–21:00
   carries the signal (DEC-0094); the mechanism probe (job 2 above) is the next real step, not more
   timestamp counting. Unchanged this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds a timing
   signature: episodes cluster 00:00–04:00. Unchanged this session.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains the
   largest on record. Unchanged.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B. Unchanged.

## Gotchas that survive here because they are NOT in the canonical docs

- **`/code-review ultra`'s cloud launcher wants a base branch, not a path target — the local
  `/code-review <target> <level>` command is the one that honors a path/PR/branch argument.**
  Passing file paths to `ultra` gets silently read as a free-text note and it falls back to a
  `dev`→`main` diff instead. Found S91, burned one of three free ultrareview slots learning it.
- **Campaign clocks are LOCAL (EDT); most tool output is UTC — convert before comparing.** Two
  prior sessions already hit this from opposite sides (S83, DEC-0068); S91 added a third: a
  NAS-side apparatus end-epoch (`proc_probe_nas.sh`, DEC-0098) was written down as a bare
  "2026-08-19 05:00" with no timezone recorded anywhere, so which one it means is now itself an
  open question for S92 to resolve by checking the process, not by assuming.
- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` trips every NAS `scp` deploy** (S81/S82/S82b) — the settled fallback:
  hand the owner the single command, saying explicitly it runs on the Mac.
- **A guard block can be a MISFIRE — check before you go near the mint path** (S85, ops#176).
  Rung 0: re-spell it (`Write`/`Edit` for file content instead of a shell heredoc) before asking
  for a mint.
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("3 of 3 required status checks are expected" from `gh pr merge`, or `mergeStateStatus: BEHIND`
  — both faces of the same thing). Fix: `gh api -X PUT repos/<r>/pulls/<n>/update-branch`, wait for
  the CI rerun, then merge. Re-confirmed S91 on PR #229 after #228 merged first.
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is
  correct; a holder older than 1800s is broken automatically and loudly.
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations need the Class C mint path (confirm in chat, mint,
  re-run identical — mint and re-run as TWO separate calls).
- **`due_arm()` never returns `NONE` once the pilot block has run** — check `current_arm()`/state +
  STOP/PAUSE directly, not log silence. *(An EMPTY schedule does return `NONE` — the DEC-0096
  stand-down state; `install` refuses it before it can matter.)*
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root, but its LOG output does
  not**: `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the root; `.log`/`_data.log` under `logs/`.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** —
  multi-word patterns silently return a FALSE ZERO through the ssh quoting layer. Positive-control
  any zero count. `nasctl cat`/`tail` need **absolute** paths.
- **Merging several same-session PRs in sequence: re-`git fetch`/`git pull` before every
  merge-into, not just the first.** And **never `git checkout -- <file>` to unplant a staged
  positive-control payload** — it restores the planted version from the index; edit the lines out
  instead.
- **GitHub's API can degrade on WRITES while READS stay fine** — verify with a GET before assuming
  a mutation failed either way.
- **`gh pr merge`'s output is never trustworthy either way** — a totally silent/empty stdout can
  mean success just as easily as an explicit error can mean a transient, retryable state. Only
  `gh pr view --json state,mergedAt` is trustworthy, every time. Re-confirmed S91 on PR #228 (empty
  stdout, actually merged).
- **zsh reserves `$status` as an alias for `$?`** — a shell loop variable literally named `status`
  fails to assign with `read-only variable: status`. Minor, but costs a retry if you reach for that
  name in a polling loop.

_Last updated: 2026-08-19 (S91 close — Sonnet throughout, no `/model` switch — nothing to restore).
Green gate re-verified at close on merged `dev`: ruff clean, **305 passed**, mypy clean/52 files.
This was the owner's planned focus for the session, decided at S90 close: the full code audit
(BOOT job 7). Both halves — security and correctness — are now complete and their outputs landed:
DEC-0101 shipped and merged (PR #229, plus the unrelated-but-bundled PR #228), and the 26
correctness findings are filed as a sequenced 8-issue remediation plan (#219–227) for the next
several sessions rather than fixed in this one — the volume made same-session fixes impractical,
and several (the ProcManager lifecycle issue, the wind-filter redesign) are explicitly judgment-tier
work better done as their own deliberate sessions. Cross-repo heads-up posted (ops#180,
informational). Campaign B checked twice this session (start and close), both times healthy,
untouched by any of this session's work — the audit and its fixes are entirely off the campaign's
critical path. ROADMAP.md checked: nothing here ships/closes/reprioritizes an existing P0–P3 line
(the audit's findings are new work, not a resolution of a tracked item), so no reconciliation
needed; tripwire still S96._
