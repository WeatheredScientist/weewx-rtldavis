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

## ▶ Resume here (S66)

### ▶▶ NEXT SESSION (S67) — agreed at S66 close, do these two in order

1. **Check hyperlocal-forecast first.** It was left **stale** by the DEC-0071 WAL rollback and needs
   a container restart by an HLF session (ops#141). Verify before anything else:
   `curl -s http://<nas>:8000/api/v1/current` → is `quality.is_stale` false and `observation_time`
   advancing? weewx and the DB are fine; only HLF is affected. Also open on that side:
   **hyperlocal-forecast PR #286** adds a 30 s busy timeout to its read-only archive connection —
   the reader half of DEC-0070. If still unmerged, say so rather than letting it sit (S37's lesson).
2. **Then launch campaign B.** Nothing blocks it. The work is mechanical and the order is in
   "Before B can launch" step 5 below: promote + tag → rebuild `:v2.0.12` from the merged tip →
   push → **regenerate the SCHEDULE= dates** (they are in the past; `install` refuses a stale
   schedule) → Class C deploy → `install`. `docs/CAMPAIGN-B-RUNBOOK.md` governs the night.

**Both of campaign B's DEC-0066 gates are handled, and there is nothing left to wait for — WAL was
tried and abandoned (DEC-0071). Launching B is a decision, not remaining build work.** Prod healthy;
LNA out. Freeze root cause stays unexplained (DEC-0067/0068) and **gates nothing**.

**Gate 1 — metric is freeze-aware (DEC-0069).** `ops/campaign_analyze.py` (+14 tests) reads
per-minute `rxCheckPercent` from the archive DB and excludes freeze artifacts *structurally*.
`ops/rx_experiment.sh` deliberately untouched. The gate turned out to be a **resolution** problem:
the old 5-minute aggregate let one frozen minute wreck four good ones (~0.8 pts); per-minute, the
real correction is **±0.03 pts against a 2.0-pt bar**. Campaign A recomputed — A 74.81 / C 74.37 /
D 74.17 / B 73.87, spread 0.94, no arm near adoption — **which unsealed A's winner ahead of B**
(side effect of tool validation, not a decision; DEC-0069 sealing note). A-vs-B must be read on the
same metric; the tool guarantees that.

**Gate 2 — DB lock BOUNDED, not cured (DEC-0070).** Two untouched defaults, not a bug:
`journal_mode=delete` + weedb's **5 s** timeout meant six seconds of reader cost ~5–10 min of
outage. **`timeout = 30` now live** → capped at ~30 s, verified in the running system. *New
behaviour:* weewx now **blocks** rather than erroring, and such a stall is indistinguishable from a
DEC-0067 freeze — correctly excluded by `campaign_analyze.py`, **not a bug to chase**.

**⛔ WAL WAS TRIED AND ROLLED BACK — do not retry it (DEC-0071).** HLF shipped the directory mount,
WAL went live 06:56 EDT, and HLF **froze on a stale snapshot within minutes**. Two blockers, both
missed: a Docker `:ro` bind makes the **files** read-only (DEC-0070's test only chmod'd the
*directory*, so it never reproduced this — structurally blind, DEC-0035 again), and SQLite creates
`weewx.sdb-wal` mode **0555**, so even a read-write mount leaves a non-root reader unable to write
it. Rolled back at 07:24 via `[[[pragmas]]] journal_mode = DELETE` — **left in place on purpose**,
it re-pins `delete` every start. Rolling back cost a **~6 min crash loop** from writing that pragma
as a scalar when weedb wants a mapping. `timeout = 30` already delivers most of WAL's practical
benefit; the remaining upside does not justify this. Detail: ops#141.

### Current state — re-verified at S66 close

| Thing | State |
|---|---|
| Branches | **steady state restored (S66): exactly `dev` + `main`, local and remote.** Nine merged S62–S66 feature branches deleted. Nothing stale to reconcile |
| `:v2.0.12` image | S62's local build is **gone**. Rebuild from the merged tip when B launches |
| Campaign B apparatus | schedule shifted in-repo; **NOT on the NAS** (its `rx_experiment.sh` is still campaign A's, mtime Jul 29) |
| Watchdog (DEC-0065) | **deployed and live** — NAS copy matches repo tip byte-for-byte, zero resets since |
| Prod right now | **v2.0.11**, LNA **out**, gain 372, ~70–80%. Restarted 08-06 07:24 (DEC-0071 rollback); `journal_mode=delete` pinned by pragma, `timeout = 30` live |
| hyperlocal-forecast | ⚠️ **left STALE by the DEC-0071 rollback** — needs a container restart by an HLF session (ops#141). weewx and the DB are fine; don't trust forecast/dashboard readings until it's restarted |
| Campaign A | **STOPped, sentinel in place.** Do not clear it |
| Campaign B | **HELD (DEC-0066).** Schedule dates are a placeholder (08-10 → 08-19) |

**The schedule dates are a placeholder** — arbitrary, existing only so nothing sits in the past.
Re-shift the whole `SCHEDULE=` block by a constant offset when a launch is agreed (S62's method: 39
substitutions; the structure tests confirm the square survives). You do not have to remember this:
`install` **refuses** a schedule whose first row has passed (`schedule_started()`, DEC-0066), because
`due_arm()` picks the *latest* row already passed — so a stale schedule fails silently, joining
mid-square with no pilot or recording the campaign complete without running it. Both look like
success, and prose would not have caught it (DEC-0040).

### Before B can launch (DEC-0066)

1. ~~Explain the two unexplained outages~~ — **substantially done (DEC-0067).** The recurring class
   is explained in kind (process freeze, RF unaffected), bounded (~1/day, ~3.5 min, ~0.4 % of
   wall-clock) and pre-dates the LNA. ERR-0005 is unexplained but is a **single incident**.
2. ~~Make the campaign metric freeze-aware~~ — **DONE (DEC-0069, S66).** `ops/campaign_analyze.py`.
   Read B with `--campaign B`; read A with `--campaign A --since 1785384300` (its aborted 07-29
   attempt shares the same apparatus log — the tool warns, but pass it anyway).
3. **DB-lock defect — BOUNDED (DEC-0070); WAL tried and abandoned (DEC-0071).** `timeout = 30` live,
   outages ~30 s not ~10 min. **There is nothing further to wait for** — WAL is not viable as scoped.
   This gate is as closed as it is going to get.
4. ~~Deploy the watchdog~~ — **done**, verified live at S63 open.
5. Then: promote + tag → rebuild `:v2.0.12` from the **merged tip** (`bdc4f9f`) → push `:v2.0.12`
   (`:latest` only after our own station proves it) → regenerate the schedule → the Class C deploy
   steps → `install`.

`docs/CAMPAIGN-B-RUNBOOK.md` still governs the mechanics; only the timing is open.

### What we learned about the LNA — hold it loosely

**Campaign A, recomputed at S66 on per-minute `rxCheckPercent` (DEC-0069):** A (372/ex0) **74.81%**
· C (372/ex50) 74.37 · D (207/ex50) 74.17 · B (207/ex0) 73.87 — spread **0.94 pts**, no arm near the
2-pt bar. **B's 372 anchor must be read against A's arm A (74.81%), same tool, same metric** —
`ops/campaign_analyze.py` guarantees that. The old 72.4% is monitor-scrape and runs ~1.9 pts low; do
not mix the two. Also ~14 h LNA-out at 372 gave 72.6% with no hour-07 notch — **suggestive only, do
not conclude futility from it.** *A's winner was sealed until after B; S66's tool validation
unsealed it (DEC-0069 sealing note).* Reasoning: DEC-0069.

**Root cause of ERR-0005 is still unestablished.** A container recreate fixed it; a `kill`+`start`
20 minutes earlier had not. Nobody knows why. That gap is why DEC-0065 declined to automate the
recreate.

**Model note:** S66 escalated to **Opus 5** for the DEC-0069 design work via `/model claude-opus-5`
— the *argument* form, which per OPS-DEC-0010 persists as the new-session default rather than being
session-only. **Checked at close: `~/.claude/settings.json` still reads `"model": "sonnet"` — floor
intact, nothing to restore.** Worth a glance at next session start anyway, since the desktop app
behaves differently here (OPS-DEC-0036/0062).

## Blockers

1. **The weewx process freezes, roughly once a day, ~2-4 min. Cause not fully explained (DEC-0067,
   DEC-0068).** Seen 07-30 08:04, 08-02 13:46, 08-03 02:59, 08-03 23:23, 08-04 17:48 EDT, 08-04
   19:13 EDT — the last 3 have detailed thread-state captures, all `S`, never `D`. **DEC-0068:
   coffee-radar (shares this NAS) was confirmed running during the 08-04 19:13 freeze, with loadavg
   at 12.39 vs. a 0.3–0.7 baseline** — a real contributor, not the sole cause (the 08-04 17:48
   freeze, same night, had neither). n=1 correlated of 3 captures. `ops/freeze_watch.sh` (committed
   S65) is the reusable tool for any further catch. **Does not block campaign B** — item 3 below is
   now the *only* remaining gate (DEC-0069 closed the metric one, and bounded these freezes at
   **±0.03 pts** on a pooled arm mean). Full reasoning: DEC-0068; detail: `docs/ROADMAP.md` P0 item.
2. **ERR-0005 is still unexplained** — but is demonstrably a **single incident**, not the head of a
   pattern (21 driver detections that day, 0 on every other). Do not let it block B on its own.
3. ✅ **`database is locked` — BOUNDED at S66 (DEC-0070).** Cause was two untouched defaults, not a
   bug: `journal_mode=delete` + weedb's 5 s timeout. `timeout = 30` now live, so a slow reader costs
   ~30 s instead of 5–10 min. **Still on `delete` journal** — WAL awaits ops#141. Watch for it
   recurring *despite* the cap: that would mean a reader holding the lock >30 s, which is a
   different problem.
- **`ppm`/`fc` still unmeasured** and deliberately unchanged for B (would confound the LNA contrast).

## Ordered backlog

1. **Decide whether campaign B launches now.** Both DEC-0066 gates are handled: the metric is
   freeze-aware (DEC-0069) and the DB lock is **bounded** to ~30 s outages (DEC-0070). **Waiting for
   WAL is no longer an option** — it was tried and abandoned (DEC-0071), and `timeout = 30` already
   delivers most of its practical benefit. So this is purely a judgment call with nothing left to
   build. Freeze root cause stays unexplained (DEC-0067/0068) and **gates nothing**.
2. **Check ops#141 for HLF's restart** before trusting any dashboard/forecast reading — HLF was left
   stale by the WAL rollback and needs its container restarted by an HLF session.
3. **Doc hygiene: one done, one still owed.** ✅ The full `docs/ROADMAP.md` reconciliation ran at
   S66 — 8 open items diffed, 4 stale ones fixed (including a DEC-0057 update missed the day
   before), next check due **by S76**. ❌ **This file is ~4,000 tokens against its ~2,500 cap** and
   needs ~1,500 rehomed to `MANIFEST.md` rows — per DEC-0063 that means moving content, not raising
   the cap. Best candidates: "Standing watches", "What we learned about the LNA", "Before B can
   launch".
4. **WeatherLink Live backfill for ERR-0005** — approved, not applied. ~7 records at
   `interval = 15` + `backfill = 1` flag, ERR-0003's path. Back up the DB first.
5. Post-campaign: LNA-in vs LNA-out grand comparison (A × B) — **run `ops/campaign_analyze.py` over
   both windows** so the contrast is one metric on both sides. Final prod config decision, whether
   the LNA goes back in — and whether it was ever worth anything.
6. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten (DEC-0060 recipe is minutes-long).
7. **`WU_RF_MIN_PCT = 60` may need retuning for the no-LNA regime** — it fired on a dew dip at
   03:15. Wants B's data, not a guess.
8. **Consider `.claude/transient-state`** (ops#113). Opt-in is this repo's call.
9. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

## Standing watches — read-only, none block the above

✅ **Dropouts watch CLOSED (DEC-0067)** — replaced by Blocker 1. **Never re-open it on a
  `WINDOW: 0/21` reading**: that metric cannot tell a freeze from deafness, which was the whole
  problem. The rule is a >150 s gap **with** `rtldavis process stalled` = RF; silent = freeze.
- **Co-rejection grep** (DEC-0054): **0 hits through 08-01 18:30**. Single-token pattern
  `co-rejecting` — *multi-word `nasctl grep` patterns silently match nothing*; positive-control any
  zero.
- **Humidity-spike watch** — unfired. **Method and arithmetic are in DEC-0044 — do not re-derive.**
- **DEC-0049 phantom-rainRate** — unfired. Next calm, saturated, cooling night is a free test.
- **First frost** — the signed decode's negative branch gets its first live air test.
- **DEC-0056 revisit trigger** — a rain-rejection email on a genuinely *wet* day.
- **Upstream replies** — four open threads (lheijst #22/#23, issue #15, david-lutz#1). See MANIFEST.
- **Dependabot** may open a deps PR — review, don't auto-merge.

✅ Closed, do not re-run: **#74 calm-windDir** (S59) · **campaign-A abort near-miss** (S62,
  DEC-0065 — the abort was correct, DEC-0061's budget holds).

## Gotchas that survive here because they are NOT in the canonical docs

The non-negotiables (public repo · prod is sacred · `docker kill` not `stop` · pause before every
commit · No-Rewrite · pyc cache) live in **`CLAUDE.md`**; gates, interpreter and git workflow in
**`docs/CONVENTIONS.md`**; the deploy-layer table in **`CONSTANTS.md`**. *Restating them here was a
second copy, which STANDARD rule 5 calls a defect — deleted at S66.* What is left is only what those
files do not say:

- **The secret gate also exits 0 with `nothing to scan` when nothing is staged.** A green run proves
  nothing until you `git add` first (DEC-0039/0045), and it wants a planted-payload positive control.
- **Ask "which layer wins in prod?" per file, every time** (DEC-0046) — a previous session's answer
  about a *different* file proves nothing. `CONSTANTS.md` has the table; a shipped config change must
  also patch the live NAS copy and be verified in the **running system**.
- **This file is the single source of truth for the session number and the handoff** (DEC-0023);
  prefix cross-repo refs (`weewx S66` vs `dash S151`).

_Last updated: 2026-08-05 (S66) — **DEC-0069** (metric freeze-aware, per-minute `rxCheckPercent`,
structural exclusion; campaign A recomputed and thereby unsealed) and **DEC-0070** (DB lock bounded:
`timeout = 30` live, ~30 s not ~10 min; WAL blocked cross-repo → ops#141). Both DEC-0066 gates now
handled — launching B is a judgment call, not more work. Also: branch steady state restored; this
file's duplicated rule sections deleted per STANDARD rule 5. Session numbering: this repo's own
counter; governed era runs S16 → …_
