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

## ▶ Resume here (S67)

### ▶▶ NEXT SESSION — launch campaign B

**Nothing blocks it.** Both DEC-0066 gates are handled, and there is no remaining build work —
launching is a decision, not a task list. `docs/CAMPAIGN-B-RUNBOOK.md` governs the night.

The sequence, in order:

1. **Promote + tag.** `dev` is **80 commits ahead of `main`**; `main` is the production-truth branch.
2. **Rebuild `:v2.0.12` from the merged tip.** ⚠️ **Take the tip from `git rev-parse origin/dev`, not
   from any sha written down here** — S66's copy of this list named `bdc4f9f`, which was 13 commits
   stale by S67 and predates DEC-0069/0070/0071 (no `campaign_analyze.py`, no `freeze_watch.sh`).
   Building from a remembered sha ships a green checkmark on a silently incomplete image.
3. **Push `:v2.0.12`.** `:latest` only after our own station proves it.
4. **Regenerate the `SCHEDULE=` dates** in `ops/rx_experiment.sh` — shift the block by a constant
   offset (S62's method: 39 substitutions; structure tests confirm the square survives). The 08-10 →
   08-19 dates are a placeholder. `install` **refuses** a schedule whose first row has passed
   (DEC-0066): without it a stale schedule joins mid-square with no pilot, or records the campaign
   complete without running it — both look like success.
5. **Bump `EXPECT_IMAGE` *and* `EXPECT_DRIVER` in `ops/soak_check.sh`** as part of the deploy —
   `:v2.0.12` and `ws.3` → `ws.4` together. Both were reset to prod's real values at S67 after being
   bumped early at S62; bumping them before the ship recreates exactly that.
6. **Class C deploy steps → `install`.**

### Current state — verified at S67 open

| Thing | State |
|---|---|
| Prod | **v2.0.11**, LNA **out**, gain 372, ~70–80%. Restarted 08-06 07:24 EDT. Emitting live |
| Live-config deviations | `timeout = 30` **and** `[[[pragmas]]] journal_mode = DELETE` both confirmed present in the running `weewx.conf` (DEC-0070/0071). Table in `CONSTANTS.md` |
| Branches | steady state: exactly `dev` + `main`, local and remote. `dev` 80 ahead of `main` |
| `:v2.0.12` image | S62's local build is **gone**. Rebuild from the merged tip at launch |
| Campaign B apparatus | schedule shifted in-repo; **NOT on the NAS** (its `rx_experiment.sh` is still campaign A's, mtime Jul 29) |
| Campaign A | **STOPped, sentinel in place.** Do not clear it |
| USB watchdog | ⛔ **NOT RUNNING since 2026-05-22** — deployed and byte-correct, but hand-started once and never supervised. Blocker 4 |
| hyperlocal-forecast | ✅ recovered. Container recreated 08-06 with HLF PR #286 merged (the reader-side 30 s busy timeout). ops#141 relabelled `repo:hlf` — **nothing further owed by this repo** |

### The two gates, as one-liners (full reasoning in the DECs — do not re-derive)

- **Metric is freeze-aware — DEC-0069.** `ops/campaign_analyze.py` reads per-minute `rxCheckPercent`
  from the archive DB and excludes freeze artifacts structurally. The gate was a *resolution*
  problem: at per-minute the real correction is **±0.03 pts against a 2.0-pt bar**. Read B with
  `--campaign B`; campaign A needs `--since 1785384300`.
- **DB lock BOUNDED, not cured — DEC-0070.** `timeout = 30` is live, so a slow reader costs ~30 s
  instead of 5–10 min. *New behaviour:* weewx now **blocks** rather than erroring, and such a stall
  is indistinguishable from a DEC-0067 freeze — correctly excluded by `campaign_analyze.py`, **not a
  bug to chase**. Watch for it recurring *despite* the cap: that would mean a reader holding the lock
  >30 s, a different problem.

**⛔ Do not retry WAL (DEC-0071).** Tried 08-06, rolled back in 28 min. A Docker `:ro` bind makes the
**files** read-only and SQLite creates `weewx.sdb-wal` mode `0555`, so a non-root reader can never
join the WAL — the mount was never the only blocker. `timeout = 30` gives most of the benefit. The
`journal_mode = DELETE` pragma stays **on purpose**, re-pinning `delete` every start.

## Blockers

1. **The weewx process freezes ~once a day, 2–4 min. Cause not fully explained (DEC-0067/0068).**
   Six logged; last three have thread captures, all `S`, never `D`. Coffee-radar (shares this NAS)
   was running during one at loadavg 12.39 vs 0.3–0.7 baseline — **a real contributor, not the sole
   cause**; n=1 of 3. `ops/freeze_watch.sh` is the catcher. **Gates nothing** — DEC-0069 bounds the
   campaign impact at ±0.03 pts. Detail: DEC-0068, `docs/ROADMAP.md` P0.
2. **ERR-0005 unexplained** — but a **single incident**, not a pattern (21 driver detections that
   day, 0 on every other). A container recreate fixed it, a `kill`+`start` 20 min earlier had not,
   and nobody knows why — which is why DEC-0065 declined to automate the recreate. Doesn't block B.
3. **`ppm`/`fc` still unmeasured**, deliberately unchanged for B (measuring now would confound the
   LNA contrast).
4. **The USB watchdog is NOT RUNNING in prod, and has not been since 2026-05-22** (established S67;
   evidence in `BACKLOG.md`). Hand-started once, never supervised. Three stalls on 08-06 went
   unhandled (**RF/USB, not the process freeze**: gap *with* the stall line = RF, silent = freeze);
   reception recovered to 81%, nothing degraded now. **Design: DEC-0073 — read it first.**
   ✅ **Built at S67:** PID guard + heartbeat in `ops/usb_watchdog.sh` (paths env-overridable),
   `tests/test_usb_watchdog.sh` (8 tests, positive-controlled), and `soak_check.sh` asserts the
   heartbeat — correctly red against prod today. **Still open, GATES campaign B:** (1) **deploy** +
   install the 5-min task (Class C; until then prod runs the dead pre-DEC-0073 copy); (2) reset-rate
   alerting — needs a `weewx_monitor.py` change, since the monitor reads `weewx.log`, not the
   watchdog log; (3) `campaign_analyze.py`'s fourth gap class, best written once real reset lines
   exist to test against.

## Ordered backlog

1. **Launch campaign B** (above) — or decide not to, deliberately.
2. ✅ **Doc hygiene — ops#145 closed at S67 (DEC-0072).** Standing obligation it leaves: a new
   `ops/`/`scripts/` file must ship with a header saying why it exists and when to load it — the
   MANIFEST class row promises that, and nothing fails if it's missing. ✅ `docs/ROADMAP.md`
   reconciled at S66; next check due
   **by S76**.
3. **WeatherLink Live backfill for ERR-0005** — approved, not applied. ~7 records at `interval = 15`
   + `backfill = 1`, ERR-0003's path. Back up the DB first.
4. Post-campaign: **LNA-in vs LNA-out grand comparison (A × B)** — run `ops/campaign_analyze.py` over
   both windows so the contrast is one metric on both sides. Then the final prod-config decision:
   whether the LNA goes back in, and whether it was ever worth anything.
5. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten (DEC-0060's recipe is minutes-long).
6. **`WU_RF_MIN_PCT = 60` may need retuning for the no-LNA regime** — it fired on a dew dip at 03:15.
   Wants B's data, not a guess.
7. **Consider `.claude/transient-state`** (ops#113). Opt-in is this repo's call.
8. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

**Standing watches now live in `BACKLOG.md`** — read-only, none block anything, and a watch is not
in-flight work.

## Gotchas that survive here because they are NOT in the canonical docs

The non-negotiables (public repo · prod is sacred · `docker kill` not `stop` · pause before every
commit · No-Rewrite · pyc cache) live in **`CLAUDE.md`**; gates, interpreter and git workflow in
**`docs/CONVENTIONS.md`**; the deploy-layer table in **`CONSTANTS.md`**. What is left is only what
those files do not say:

- **The secret gate also exits 0 with `nothing to scan` when nothing is staged.** A green run proves
  nothing until you `git add` first (DEC-0039/0045), and it wants a planted-payload positive control.
- **Ask "which layer wins in prod?" per file, every time** (DEC-0046) — a previous session's answer
  about a *different* file proves nothing. A shipped config change must also patch the live NAS copy
  and be verified in the **running system**.
- **`~/.claude/hooks/secret-read-guard.sh` matches by basename**, so it blocks reads of the repo's
  own clean `ops/wxcheck.sh` (which uses `${WU_API_KEY}`, no literals) because the *NAS* copy once
  held a key. Use `readconf <path>` to read it. Guard-side fix is ops-owned, not this repo's.
- **A sha match proves the FILE, never the PROCESS.** "Deployed and live — NAS copy matches repo
  byte-for-byte" was true about the bytes and false about liveness for ~2.5 months (blocker 4). For
  anything long-running, liveness needs its own evidence: a pidfile, a heartbeat line, or a start
  line in its own log.
- **This file is the single source of truth for the session number and the handoff** (DEC-0023);
  prefix cross-repo refs (`weewx S67` vs `dash S151`).

_Last updated: 2026-08-06 (S67) — HLF recovered (ops#141 → `repo:hlf`); ops#145 doc diet closed
(DEC-0072): both tier files under cap, MANIFEST on class rows. Then `EXPECT_IMAGE`/`EXPECT_DRIVER`
reset to prod's real values, which surfaced blocker 4. Campaign B is cleared — the question is when._
