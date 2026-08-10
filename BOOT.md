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

## ▶ Resume here (S72)

### ▶▶ THE JOB: GATE 2 — Campaign B pilot readout (Tuesday daytime), then apply DEC-0080

**Campaign B is LIVE — deployed and armed 2026-08-10 morning (S70), unchanged since.** Prod swapped
to **v2.0.12/ws.4 with `BIAS_TEE=0`**, verified in the running system (banner, bias-tee-off line,
DEC-0062 redaction, loop flowing, reception back at 70% after the swap dip); `install` clean at
09:40. **Pilot 08-11T00:35–04:20, then H hold; square 08-12 → 08-20T00:05.** GATE 2 = the pilot
readout with the owner, Tuesday daytime (settle rule: drop each block's first 2 samples). Track
via tick log + `rx_experiment_data.log`; read results **only** with `ops/campaign_analyze.py
--campaign B`; A's anchor is arm A **74.81%** on that tool. Abort floor 50%; every failure path
restores baseline and emails. An unattended run still has **no working dongle recovery** — don't
expect a rescue. **Hub carries `:v2.0.12`** (config digest verified = NAS build). `:latest` stays
on v2.0.11 **on purpose** — move it once the station proves the release; decide at GATE 2.

**Radiation floor: DECIDED (DEC-0080), NOT YET APPLIED.** Option A — exact-code `StdCalibrate`
zero, versioned in `weewx.conf.example` §Corrections (full rationale + declined option B:
DEC-0080, S71 handoff). **Apply on the first post-GATE-2 prod touch:** copy the `radiation =`
line into the live `weewx.conf` `[StdCalibrate][[Corrections]]`; `docker kill` + `start` (mounted
config — no rebuild); add the third DEC-0070 deviations row to `CONSTANTS.md` same session;
verify the first dark hours read 0 — if 3.516 (`sr_raw=2`) shows, extend per-code, never a loose
window; file the ops note that the dashboard's `eh-ui.js` filter is now vestigial (retirement =
dashboard repo, DEC-0010). NOT applied before the pilot on purpose — unattended night, no dongle
recovery, config-typo crash-loop precedent.

Two things not to re-derive: **`weewx_monitor.py` IS the watchdog** (DEC-0074), and **every reset
line before 2026-08-07 19:28 names `syno_vbus_reset`, an operation that never ran** — prod is right
now, the *history* still lies, and that is what sent S67 down the wrong path.

`docs/CAMPAIGN-B-RUNBOOK.md` governs the night and carries the release mechanics, if a relaunch is
ever needed — already armed, not needed right now.

### Current state (S72)

| Thing | State |
|---|---|
| Prod | **v2.0.12**, driver **ws.4**, `BIAS_TEE=0`, LNA **out**, gain 372. Swapped + verified 08-10 09:05; emitting live |
| Live-config deviations | `timeout = 30` + `[[[pragmas]]] journal_mode = DELETE`, both verified in the running `weewx.conf`. Table in `CONSTANTS.md`. DEC-0080's correction joins them **at apply, post-GATE 2** |
| `weewx_monitor.py` | **alive, supervised, current** — pid 8810 era continued through the swap; soak "monitor alive" green 08-10. It **is** the USB watchdog (DEC-0074) |
| Branches | steady state: exactly `dev` + `main`. `main` = `7b6fd42` = prod; `dev` ahead (S71/S72 doc closes) |
| `:v2.0.12` image | **DEPLOYED + on Hub** (config digest = NAS build `9db5c1ddaac3`). `:latest` still v2.0.11 pending pilot proof |
| Campaign B | **ARMED** — installed 08-10 09:40, baseline snapshotted, first tick starts it. Pilot **08-11T00:35** |
| Campaign A | **archived** — five artifacts under `.campaignA` suffixes (incl. the STOP sentinel), 08-10 |
| Reset forensics | **LIVE, armed** (DEC-0075); awaiting a stall |

### DEC-0066 gates — closed; reasoning lives in the DECs

- **Metric freeze-aware (DEC-0069)** — `ops/campaign_analyze.py`, per-minute `rxCheckPercent`,
  structural exclusion. Read B with `--campaign B`; **A needs `--since 1785384300`**.
- **DB lock bounded, not cured (DEC-0070)** — `timeout = 30` live. weewx now *blocks* rather than
  erroring, which looks like a DEC-0067 freeze and is correctly excluded. **Not a bug to chase** —
  only a recurrence *despite* the cap means a new problem.
- **⛔ Never retry WAL (DEC-0071).** A `:ro` bind means SQLite creates `weewx.sdb-wal` mode `0555`,
  so a non-root reader can never join. The `journal_mode = DELETE` pragma stays **on purpose**.

## Blockers

1. **The weewx process freezes ~once a day, 2–4 min. Cause not fully explained (DEC-0067/0068).**
   Six logged; last three have thread captures, all `S`, never `D`. Coffee-radar (shares this NAS)
   ran during one at loadavg 12.39 vs 0.3–0.7 — **a contributor, not the sole cause**; n=1 of 3.
   `ops/freeze_watch.sh` catches it. **Gates nothing** — DEC-0069 bounds it at ±0.03 pts.
2. **ERR-0005 unexplained** — a **single incident** (21 driver detections that day, 0 on every
   other). A recreate fixed it, a `kill`+`start` 20 min earlier had not, nobody knows why — why
   DEC-0065 declined to automate the recreate. Doesn't block B.
3. **`ppm`/`fc` unmeasured**, deliberately unchanged for B (measuring would confound the LNA contrast).
4. **USB resets FIRE but do not WORK — the live defect (DEC-0074).** 08-06: three stalls, three
   resets, all three failed; **11/11 failed on 08-02** (count per DEC-0077). The watchdog works and
   is reporting that **the remedy doesn't**. `soak_check.sh` carries `USB RESETS INEFFECTIVE`.
   Unexplained, and ERR-0005 says a reset can make things *worse*. **Apparatus LIVE (DEC-0075);
   blocked on a live stall alone.** DEC-0073 superseded — it claimed these stalls went unhandled.
5. ✅ **CLOSED (DEC-0077)** — reset gaps do **not** contaminate campaign A; exclusion is structural
   on *any* gap. Don't re-open when reading B.

## Ordered backlog

1. **Read the first stall capture** (blocker 4) — apparatus live and verified; **the event is the
   only thing left.**
2. Post-campaign: **LNA-in vs LNA-out grand comparison (A × B)** via `ops/campaign_analyze.py` over
   both windows, one metric on both sides. Then the final call on whether the LNA goes back in.
3. **`ppm`/`fc` measurement-by-value** — deferred, not forgotten (DEC-0060's recipe is minutes-long).
4. **`WU_RF_MIN_PCT = 60` may need retuning for the no-LNA regime** — fired on a dew dip at 03:15.
   Wants B's data, not a guess.
5. Keep-a-Changelog headings + DECISIONS entry-skeleton convergence (proposed S25, never picked up).

**After GATE 2** (Campaign B's pilot readout takes the next session; this queue does not compete
with it), first the **DEC-0080 apply** (steps above), then two sessions of non-campaign,
cross-repo focused work, in order:

6. **`#144`** — console pressure +0.03 inHg vs METAR; `pressure_service.py` writes SLP into all
   three pressure fields; hourly staleness. Full brief + execution notes **on the issue**.
   **Design discussion before coding**; the service is **baked** → NAS rebuild to ship; item 1 is
   owner-only.
7. **`ops#141`** — mount the weewx archive **directory**, not the single `.sdb`. **Scope first,
   don't execute:** the issue's WAL framing is stale vs DEC-0071 and the shape was tried + rolled
   back once — caution recorded as a comment **on the issue**. Check HLF's *current* mount state
   first.

ROADMAP reconciled at S66; next check **by S76**. Standing watches live in `BACKLOG.md`.

## Gotchas that survive here because they are NOT in the canonical docs

Non-negotiables live in **`CLAUDE.md`**; gates and git workflow in **`docs/CONVENTIONS.md`**; the
deploy-layer table in **`CONSTANTS.md`**. Only what those do not say:

- **A file match proves the FILE, never the PROCESS — and never that a capability is absent**
  (DEC-0074; both halves cost a session). Liveness needs process evidence — a **startup line in the
  log after the file mtime**, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, **new pid + old pid
  gone**; never `/proc/<pid>` mtime, which is ACCESS time (#147). Absence needs you to check what
  *else* provides the function.
- **`secret-read-guard.sh` matches by basename**, so it blocks the repo's clean `ops/wxcheck.sh`
  (which uses `${WU_API_KEY}`). Read it with `readconf`. Guard fix is ops-owned.

_Last updated: 2026-08-10 (S72 close) — DEC-0080 decided (**apply post-GATE 2**, steps above),
PR #155 merged, ops#148 closed. Campaign B and blocker 4 unchanged from S70/S69._
