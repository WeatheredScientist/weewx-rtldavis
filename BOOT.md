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

## ▶ Resume here (S69)

### ▶▶ THE JOB: read the first stall capture (blocker 4)

✅ **DEPLOYED AND VERIFIED 2026-08-09.** Do **not** re-deploy — that is the S60b/S63 trap, BOOT
telling the next session to redo finished work. Prod runs merged tip `ad7e5a4`; monitor 3870 →
**8810**; smoke-tested live on the NAS. Design, hypothesis and the two predicted signatures:
**DEC-0075** — don't re-derive them.

**Wait for the event.** ~1/day, unpredictable, none since 08-07 19:28. Captures land in
`logs/usb-forensics/`; read the `pre`/`post` pair together. **Both clean means the stall is not a USB
fault at all** — a real answer, not a null result.

⚠️ **One live wart:** the *deployed* `usb_forensics.sh` reports `started=` from `/proc/<pid>` mtime =
**access** time, so it will claim a days-old `rtldavis` just restarted. Fixed on `dev` (#146,
merged) — **re-install that one file** to clear it. Decisive signatures unaffected; a capture before
then is still worth having, just ignore `started=`.

✅ **Blocker 5 is CLOSED (DEC-0077)** — reset gaps do **not** contaminate campaign A. Measured: 11
resets (not nine), all on 08-02; the archive went normal → 105 absent rows → NULL → normal, the
documented lock/outage shape, already excluded because DEC-0069 drops the record either side of *any*
gap without consulting the class. No present-but-low rows, which was the only real exposure. Campaign
A's figures stand and B can be read against them.

Then **decide campaign B** (below). DEC-0066's gates hold and blocker 5 is closed, so nothing now
stands between B and being read against A. An unattended run still has **no working dongle
recovery** — true all along, so not a gate, but don't launch expecting a rescue.

Two things not to re-derive: **`weewx_monitor.py` IS the watchdog** (DEC-0074), and **every reset line
before 2026-08-07 19:28 names `syno_vbus_reset`, an operation that never ran** — prod is right now,
the *history* still lies, and that is what sent S67 down the wrong path.

### ▶▶ Campaign B — the launch sequence

`docs/CAMPAIGN-B-RUNBOOK.md` governs the night. In order:

1. **Promote + tag.** `dev` is ~90 ahead of `main`; `main` is the production-truth branch.
2. **Rebuild `:v2.0.12` from the merged tip.** ⚠️ **Take it from `git rev-parse origin/dev`, never a
   sha written down here** — S66's copy named `bdc4f9f`, 13 commits stale by S67 and predating
   DEC-0069/0070/0071. A remembered sha ships a green checkmark on a silently incomplete image.
3. **Push `:v2.0.12`.** `:latest` only after our own station proves it.
4. **Regenerate the `SCHEDULE=` dates** in `ops/rx_experiment.sh` — shift the block by a constant
   offset (S62's method: 39 substitutions; structure tests confirm the square survives). The 08-10 →
   08-19 dates are a placeholder. `install` **refuses** a schedule whose first row has passed
   (DEC-0066): a stale one joins mid-square with no pilot, or records the campaign complete without
   running it — both look like success.
5. **Bump `EXPECT_IMAGE` *and* `EXPECT_DRIVER` in `ops/soak_check.sh`** as part of the deploy —
   `:v2.0.12` and `ws.3` → `ws.4` together. Both were reset to prod's real values at S67 after being
   bumped early at S62; bumping them before the ship recreates exactly that.
6. **Class C deploy steps → `install`.**

### Current state (S68d)

| Thing | State |
|---|---|
| Prod | **v2.0.11**, driver **ws.3**, LNA **out**, gain 372, ~70–80%. Emitting live |
| Live-config deviations | `timeout = 30` + `[[[pragmas]]] journal_mode = DELETE`, both verified in the running `weewx.conf`. Table in `CONSTANTS.md` |
| `weewx_monitor.py` | **alive, supervised, current** — boot task re-checks its pidfile every 5 min; NAS matches merged tip `ad7e5a4`, pid **8810** since 08-09. It **is** the USB watchdog (DEC-0074) |
| Branches | steady state: exactly `dev` + `main`. `dev` ~90 ahead of `main` |
| `:v2.0.12` image | S62's local build is **gone**. Rebuild from the merged tip at launch |
| Campaign B apparatus | schedule shifted in-repo; **NOT on the NAS** (its `rx_experiment.sh` is still campaign A's) |
| Campaign A | **STOPped, sentinel in place.** Do not clear it |
| Reset forensics | **LIVE** (DEC-0075), deployed + verified 08-09 from `ad7e5a4`. Armed; awaiting a stall |

### The two DEC-0066 gates — closed. Reasoning lives in the DECs

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
   ran during one at loadavg 12.39 vs 0.3–0.7 — **a contributor, not the sole cause**; n=1 of 3.
   `ops/freeze_watch.sh` catches it. **Gates nothing** — DEC-0069 bounds it at ±0.03 pts.
2. **ERR-0005 unexplained** — a **single incident**, not a pattern (21 driver detections that day, 0
   on every other). A recreate fixed it, a `kill`+`start` 20 min earlier had not, nobody knows why —
   why DEC-0065 declined to automate the recreate. Doesn't block B.
3. **`ppm`/`fc` unmeasured**, deliberately unchanged for B (measuring would confound the LNA contrast).
4. **USB resets FIRE but do not WORK — the live defect (DEC-0074).** 08-06: three stalls, three
   resets, **all three failed** (bad windows 8 → 10 → 15); **11/11 failed on 08-02** (the DECs say
   nine — count corrected by DEC-0077). The watchdog works and is reporting that **the remedy
   doesn't**. `soak_check.sh` carries `USB RESETS INEFFECTIVE`. Unexplained, and ERR-0005 says a reset
   can make things *worse*. **Apparatus LIVE (DEC-0075); blocked on a live stall alone.**
   **DEC-0073 superseded** — it claimed these stalls went unhandled, which was false.
5. ✅ **CLOSED — reset gaps do NOT contaminate campaign A (DEC-0077).** They were sorted into
   lock/outage, and it changes nothing: exclusion is structural on *any* gap, never class-based. The
   one thing that would have mattered — present-but-low rows, which no rule excludes because
   magnitude thresholds are refused by design — **did not occur**. Taxonomy amended: complete for
   *shapes*, not *causes* (a USB reset is a fourth cause of the lock/outage shape). No analyzer
   change; don't re-open when reading B.

## Ordered backlog

1. **Read the first stall capture** (blocker 4) — forensics are live, just waiting on the event.
   Re-install `usb_forensics.sh` from the merged tip to clear the `started=` wart. ✅ Blocker 5 closed
   (DEC-0077), ✅ #147 closed.
2. **Launch campaign B** — or decide not to, deliberately.
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
  the function. ⚠️ **But DEC-0074's own probe is wrong — `#147`.** `/proc/<pid>` mtime is **access**
  time, measured 08-09 reporting 17 s for a 2.88-day-old process. Use a **startup line in the log**
  after the file mtime (what actually carried both the S67 and S68 verifications), `/proc/<pid>/stat`
  field 22 vs `/proc/uptime`, and **new pid + old pid gone**.
- **`secret-read-guard.sh` matches by basename**, so it blocks the repo's clean `ops/wxcheck.sh`
  (which uses `${WU_API_KEY}`). Read it with `readconf`. Guard fix is ops-owned.
- **This file is the single source of truth for the session number and the handoff** (DEC-0023);
  prefix cross-repo refs (`weewx S67` vs `dash S151`).

_Last updated: 2026-08-09 (S68d) — reset forensics **deployed, verified live and smoke-tested**;
the smoke test then caught a defect in them (`/proc` mtime is access time, not start — DEC-0074's
own probe had the same flaw, both corrected). **Blocker 5 CLOSED (DEC-0077)**: campaign A's figures
are uncontaminated, so B can be read against them. Also DEC-0075 (capture-only; a root-escalation
introduced and closed in the same commit) and DEC-0076 (secret gate's fifth hole). S69's job:
**read the first stall capture** — the event is the only thing left gating blocker 4._
