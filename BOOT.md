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

**S66 closed campaign B's metric gate (DEC-0069).** New `ops/campaign_analyze.py` (+14 tests) reads
per-minute `rxCheckPercent` straight from the archive DB, excludes freeze artifacts **structurally**,
and prints each arm's uncleaned mean beside the cleaned one. `ops/rx_experiment.sh` was deliberately
**not touched** — the unattended prod-config writer stays as-is, and its `harvest()` output remains
an independent cross-check.

**The gate was mostly a RESOLUTION problem, not a freeze problem.** `harvest()` read the monitor's
*5-minute* `RECEPTION:` aggregate, where one frozen minute drags the whole bucket (measured 16 % and
27 % against a ~72 % neighbourhood). That is where the ~0.8-pt estimate came from, and it was right
*for that metric*. The archive stores the same measurement **per minute**. Net correction on a
pooled arm mean: **±0.03 pts against a 2.0-pt adoption bar** — real, ~60× smaller than believed.
**The contaminated record is the one adjacent to each gap; the freeze minutes are simply absent
rows** (BOOT had assumed they scored as zeros — that assumption was the whole error).

**Campaign A is recomputed, and this unsealed its arm winner ahead of B** (DEC-0066 had sealed it;
validating the tool necessarily computed it — design uncompromised, but it was a side effect, not a
decision). A 74.81 / C 74.37 / D 74.17 / B 73.87, spread **0.94 pts**, no arm near adoption.
Cross-check: the ~1.9-pt offset from the old 72.4 % matches `weewx_monitor.py`'s own documented
"~1–2 pts optimistic" note — **so A-vs-B must be read on the same metric**, which the tool now
guarantees for both.

**Campaign B stays HELD (DEC-0066), now on ONE gate: the DB lock.** Prod healthy; LNA out; schedule
dates still a placeholder. Freeze root cause remains unexplained (DEC-0067/0068) and **no longer
gates anything** — `ops/freeze_watch.sh` is committed if another spot-check is ever wanted.

### Current state — re-verified at S66 close

| Thing | State |
|---|---|
| Branches | **steady state restored (S66): exactly `dev` + `main`, local and remote.** Nine merged S62–S66 feature branches deleted. Nothing stale to reconcile |
| `:v2.0.12` image | S62's local build is **gone**. Rebuild from the merged tip when B launches |
| Campaign B apparatus | schedule shifted in-repo; **NOT on the NAS** (its `rx_experiment.sh` is still campaign A's, mtime Jul 29) |
| Watchdog (DEC-0065) | **deployed and live** — NAS copy matches repo tip byte-for-byte, zero resets since |
| Prod right now | **v2.0.11**, LNA **out**, gain 372, ~70–80%, up since 08-02 05:48 |
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
3. **Fix the DB-lock defect — the SOLE remaining gate.** Independent of the freezes. Try **WAL mode**
   on the archive DB first; bound the uploader-thread joins second.
4. ~~Deploy the watchdog~~ — **done**, verified live at S63 open.
5. Then: promote + tag → rebuild `:v2.0.12` from the **merged tip** (`bdc4f9f`) → push `:v2.0.12`
   (`:latest` only after our own station proves it) → regenerate the schedule → the Class C deploy
   steps → `install`.

`docs/CAMPAIGN-B-RUNBOOK.md` still governs the mechanics; only the timing is open.

### What we learned about the LNA — hold it loosely

~14 h at gain 372 with the LNA out: mean **72.6%**, **no hour-07 notch** (S58 measured a ~2 pt notch
LNA-in). **Campaign A, recomputed at S66 on the honest per-minute metric (DEC-0069):** A (372/ex0)
**74.81%**, C (372/ex50) 74.37%, D (207/ex50) 74.17%, B (207/ex0) 73.87% — spread **0.94 pts**, no
arm near the 2-pt bar. The old pooled 72.4% figure came from the monitor scrape and runs ~1.9 pts
low against `rxCheckPercent`, as `weewx_monitor.py` itself documents. The clean comparison is B's
372 anchor against **A's arm A, 74.81%** — same metric, same tool. **Do not conclude futility from
the ~14 h figure above.** *A's arm winner was sealed until after B; S66's tool validation unsealed
it — see DEC-0069's sealing note.*

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
3. **`database is locked` is recurrent and pre-dates the LNA removal** (08-01 15:08, 08-02 19:45;
   earlier S59). Independent of the freezes. The 10-min outage decomposes as ~106 s hung threads +
   **120 s of weewx's own hardcoded wait** + ~5 min restart — the hang is only ~18 % of it, and the
   identical lock on 08-01 cost 4 min because threads exited in 0.26 s. **The archive DB is not in
   WAL mode** — the standard cause of this contention, and the first thing to try.
- **`ppm`/`fc` still unmeasured** and deliberately unchanged for B (would confound the LNA contrast).

## Ordered backlog

1. **Fix the DB lock, then launch B** — the metric gate closed at S66 (DEC-0069), so this is the
   only thing between here and campaign B. **Try WAL mode on the archive DB first** (it is not in
   WAL mode; that is the standard cause of exactly this contention), bound the uploader-thread joins
   second. Freeze root cause stays unexplained (DEC-0067/0068) and **gates nothing**.
2. **Two overdue doc-hygiene items, both self-reported by their own tripwires.** (a) The full
   `docs/ROADMAP.md` reconciliation: its guardrail says "by S66" and S66 did only the targeted
   DEC-0069 pass. (b) **This file is ~3,970 tokens against its ~2,500 cap** and has been over since
   before S66 — per DEC-0063 that means content moves to `MANIFEST.md` or `ARCHIVE/`, not a bigger
   cap. Neither is hard; both need a session that isn't mid-design.
3. **WeatherLink Live backfill for ERR-0005** — approved, not applied. ~7 records at
   `interval = 15` + `backfill = 1` flag, ERR-0003's path. Back up the DB first.
4. Post-campaign: LNA-in vs LNA-out grand comparison (A × B) — **run `ops/campaign_analyze.py` over
   both windows** so the contrast is one metric on both sides. Final prod config decision, whether
   the LNA goes back in — and whether it was ever worth anything.
5. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten (DEC-0060 recipe is minutes-long).
6. **`WU_RF_MIN_PCT = 60` may need retuning for the no-LNA regime** — it fired on a dew dip at
   03:15. Wants B's data, not a guess.
7. **Consider `.claude/transient-state`** (ops#113). Opt-in is this repo's call.
8. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

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

## Standing rules that bite most often

- **Ask "which layer actually wins in prod?" for any file we ship (DEC-0046).** Driver +
  `pressure_service.py` + `entrypoint.sh` are **baked** (image); `weewx.conf` is **mounted**
  (live edit); `influx.py` is mounted (scp correct). Exact inverses; a release changing shipped
  config must patch the live NAS copy in the same window and verify in the **running system**.
- **The transcript is an egress path (DEC-0047).** `readconf` for configs, `scan-transcripts` to
  audit; never a line-count window on a sectioned config. **Logs are not covered (DEC-0062)** —
  never log key material.
- **`docker kill`, never `docker stop`** (DEC-0008). **`docker logs` always with `--tail N`**
  (DEC-0036; hook-blocked).
- **Prod is sacred.** One dongle, one receiver (DEC-0011). `main` = production truth; `dev` = work.
- **Pause for approval before every commit and before any push.** Discuss design before coding.
- **No-Rewrite Rule (DEC-0014).**
- **After patching any `.py` the WeeWX venv imports, clear the pyc cache.**
- A shipped/closed/reprioritized DEC gets its `docs/ROADMAP.md` line updated the **same session**
  (DEC-0057). ROADMAP is **P0–P3 only** (DEC-0058); long-horizon items live in `BACKLOG.md`.

## Style notes & contribution conventions

**This repo is PUBLIC and has external contributors** — the only one in the family that does.

- **No credential, live `weewx.conf`, `monitor.env`, or `proxy.env` ever enters any commit on any
  branch** (DEC-0012). Committed source carries `YOUR_*` placeholders; infra facts use
  `<NAS_HOST>` / `<NAS_USER>` / `<SSH_PORT>` placeholders with real values in the gitignored
  local-infra doc. Show every secret found *before* scrubbing so it can be rotated.
- **Run the secret gate with a planted-payload positive control.** It prints nothing and exits 0 on
  a clean pass — *and also exits 0 with `nothing to scan` when no files are staged*. `git add`
  first (DEC-0039/DEC-0045).
- **Validation gates and the exact interpreter are in `docs/CONVENTIONS.md`** — use them verbatim;
  **`ruff format` is not a gate and must not be run** (DEC-0027).
- Prose: **US spelling, concise over thorough, friendly and non-shaming** in anything public-facing.
  Community posts and upstream comments are drafted, owner-reviewed, never posted without a go.
- Sessions use **this repo's own independent counter** (DEC-0023); prefix cross-repo references
  (`weewx S61` vs `dash S151`). **This file is the single source of truth for the current session
  number and the handoff.**

_Last updated: 2026-08-05 (S66) — DEC-0069: campaign metric moved to per-minute archive
`rxCheckPercent` with structural (not magnitude-based) freeze exclusion; new `ops/campaign_analyze.py`
+14 tests, `ops/rx_experiment.sh` untouched. The gate was mostly a resolution problem — net
correction **±0.03 pts** against a 2.0-pt bar, ~60× smaller than the estimate that made it a gate.
Campaign A recomputed (and thereby unsealed). Campaign B now on **one** gate: the DB lock. Session
numbering: this repo's own counter; governed era runs S16 → …_
