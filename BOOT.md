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

## ▶ Resume here (S68)

### ▶▶ FIRST — two cheap things S67 left ready

1. **Deploy the corrected monitor** (~5 min). `dev` has it, the NAS does not, so prod logs still
   print `RESET: triggering syno_vbus_reset` — an operation that does not happen. Log text only;
   deferred at S67 when the Class C mint was refused twice. **Do it before the reset investigation**,
   or that investigation reads the same lie that misdirected S67. `scp` from the merged tip →
   sha-verify → owner-run `sudo kill` on the pidfile → respawns ≤5 min.
2. **Then decide campaign B** (below). DEC-0066's gates are still handled; S67 added no formal gate.

**New at S67 — neither formally blocks B, but read both first:**
- **Resets fire but never work** (blocker 4). So an unattended multi-night run has **no working
  recovery from a stalled dongle**. True all along, so not a new gate — just don't launch believing
  the watchdog will save a bad night.
- **Reset gaps may already sit inside campaign A's published numbers** (blocker 5). This one affects
  the A-vs-B comparison, which is the entire point of B. Settle it before *reading* B, not before
  running it.

### ▶▶ Campaign B — the launch sequence, unchanged

`docs/CAMPAIGN-B-RUNBOOK.md` governs the night. In order:

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
| Prod | **v2.0.11**, driver **ws.3**, LNA **out**, gain 372, ~70–80%. Emitting live |
| Live-config deviations | `timeout = 30` + `[[[pragmas]]] journal_mode = DELETE`, both verified in the running `weewx.conf`. Table in `CONSTANTS.md` |
| `weewx_monitor.py` | **alive and supervised** — a Synology boot task re-checks its pidfile every 5 min. It **is** the USB watchdog; it handled every 08-06 stall (DEC-0074). ⚠️ NAS copy is **one commit behind `dev`** — see FIRST above |
| Branches | steady state: exactly `dev` + `main`. `dev` ~90 ahead of `main` |
| `:v2.0.12` image | S62's local build is **gone**. Rebuild from the merged tip at launch |
| Campaign B apparatus | schedule shifted in-repo; **NOT on the NAS** (its `rx_experiment.sh` is still campaign A's) |
| Campaign A | **STOPped, sentinel in place.** Do not clear it |

### The two DEC-0066 gates — closed. Reasoning is in the DECs; do not re-derive it

- **Metric freeze-aware (DEC-0069)** — `ops/campaign_analyze.py`, per-minute `rxCheckPercent`,
  structural exclusion. Read B with `--campaign B`; **A needs `--since 1785384300`**.
- **DB lock bounded, not cured (DEC-0070)** — `timeout = 30` live, ~30 s not 5–10 min. weewx now
  *blocks* rather than erroring, which looks exactly like a DEC-0067 freeze and is correctly excluded.
  **Not a bug to chase.** Only a recurrence *despite* the cap means a new problem.
- **⛔ Never retry WAL (DEC-0071).** A `:ro` bind makes the *files* read-only and SQLite creates
  `weewx.sdb-wal` mode `0555`, so a non-root reader can never join. The `journal_mode = DELETE`
  pragma stays **on purpose**.

## Blockers

1. **The weewx process freezes ~once a day, 2–4 min. Cause not fully explained (DEC-0067/0068).**
   Six logged; last three have thread captures, all `S`, never `D`. Coffee-radar (shares this NAS)
   ran during one at loadavg 12.39 vs 0.3–0.7 — **a real contributor, not the sole cause**; n=1 of 3.
   `ops/freeze_watch.sh` catches it. **Gates nothing** — DEC-0069 bounds it at ±0.03 pts. DEC-0068.
2. **ERR-0005 unexplained** — a **single incident**, not a pattern (21 driver detections that day, 0
   on every other). A recreate fixed it, a `kill`+`start` 20 min earlier had not, nobody knows why —
   which is why DEC-0065 declined to automate the recreate. Doesn't block B.
3. **`ppm`/`fc` still unmeasured**, deliberately unchanged for B (measuring now would confound the
   LNA contrast).
4. **USB resets FIRE but do not WORK — the live defect (DEC-0074).** 08-06: three stalls, three
   resets within seconds, **all three failed** (`RESET ineffective (1/3)`, bad windows 8 → 10 → 15);
   9/9 failed on 08-02 too. The watchdog works and is reporting that **the remedy doesn't**.
   `soak_check.sh` carries `USB RESETS INEFFECTIVE`. Unexplained — and ERR-0005 says a reset can make
   things *worse*. Hypothesis + the decisive test: `BACKLOG.md`. **DEC-0073 is superseded**; it
   claimed these stalls went unhandled, which was false.
5. **Reset gaps may already be inside campaign A's published numbers (DEC-0074).** Nine resets on
   08-02 — inside the 07-29 → 08-05 window `campaign_analyze.py`'s three-class gap taxonomy was
   validated against, so reset-adjacent gaps were sorted into freeze/swap/lock in the figures
   DEC-0069 published. **A question about an existing result, not a pre-launch nicety.**

## Ordered backlog

1. **Deploy the corrected monitor**, then **launch campaign B** — or decide not to, deliberately.
2. **Why the resets fail** (blocker 4) and **whether reset gaps skew campaign A** (blocker 5).
   Working material + the decisive test: `BACKLOG.md`.
3. **WeatherLink Live backfill for ERR-0005** — approved, not applied. ~7 records at `interval = 15`
   + `backfill = 1`, ERR-0003's path. Back up the DB first.
4. Post-campaign: **LNA-in vs LNA-out grand comparison (A × B)** via `ops/campaign_analyze.py` over
   both windows, one metric on both sides. Then the final call on whether the LNA goes back in.
5. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten (DEC-0060's recipe is minutes-long).
6. **`WU_RF_MIN_PCT = 60` may need retuning for the no-LNA regime** — fired on a dew dip at 03:15.
   Wants B's data, not a guess.
7. **Consider `.claude/transient-state`** (ops#113). Opt-in is this repo's call.
8. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

✅ **ops#145 closed at S67 (DEC-0072).** Standing obligation: a new `ops/`/`scripts/` file must ship
with a header saying why it exists — the MANIFEST class row promises it, and nothing fails if it's
missing. **A file in no class needs its own row** (`weewx_monitor.py` had none, which is how S67 went
wrong). ROADMAP reconciled at S66, next check **by S76**. **Standing watches live in `BACKLOG.md`.**

## Gotchas that survive here because they are NOT in the canonical docs

Non-negotiables live in **`CLAUDE.md`**; gates and git workflow in **`docs/CONVENTIONS.md`**; the
deploy-layer table in **`CONSTANTS.md`**. Only what those do not say:

- **The secret gate exits 0 with `nothing to scan` when nothing is staged.** Green proves nothing
  until you `git add` first (DEC-0039/0045); positive-control it with a planted payload.
- **Ask "which layer wins in prod?" per file, every time** (DEC-0046). A shipped config change must
  also patch the live NAS copy and be verified in the **running system**.
- **A file match proves the FILE, never the PROCESS — and never that a capability is absent.** Both
  halves cost a session: "matches byte-for-byte, zero resets since" was true and its conclusion
  wrong, and a dead script was read as a missing function while `weewx_monitor.py` did the job all
  along (DEC-0074). Liveness needs process evidence; absence needs you to check what *else* provides
  the function.
- **`secret-read-guard.sh` matches by basename**, so it blocks the repo's clean `ops/wxcheck.sh`
  (which uses `${WU_API_KEY}`). Read it with `readconf`. Guard fix is ops-owned.
- **This file is the single source of truth for the session number and the handoff** (DEC-0023);
  prefix cross-repo refs (`weewx S67` vs `dash S151`).

_Last updated: 2026-08-07 (S67 close) — ops#145 closed (DEC-0072); soak_check expectations reset to
prod's real values, which surfaced the watchdog thread; **DEC-0074 superseded DEC-0073** after the
monitor turned out to be the watchdog all along. Live now: resets that fire but never work, and
reset gaps possibly inside campaign A's figures. Lessons filed cross-repo as ops#147._
