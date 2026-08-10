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

## ▶ Resume here (S71)

### ▶▶ THE JOB: solar radiation diode-floor fix — design decision (suggested Fable / escalated session)

Full self-contained brief: **`docs/handoffs/S71-radiation-floor-design.md`** — written to be read
cold, no transcript needed. Problem is fully diagnosed (a real, quantized ~1.758 W/m² diode
dark-current floor, traced to a June 2026 dashboard fix that's since regressed at the chart layer).
Two designs are drafted and compared — a `StdCalibrate` magnitude-match (ready to apply, config-only)
vs. a `weewx.almanac`-based elevation-gated service (more correct at the dawn/dusk edge, costs new
code + tests + a rebuild). **Neither is implemented — the choice is the open work.** This is judgment
work, not execution of a locked design; the owner asked for it deliberately in a fresh, escalated
session.

Also open but event-driven, neither blocking the job above — the stall apparatus (blocker 4, detail
there) and Campaign B's GATE 2, which doesn't exist until the pilot runs tonight:

**Campaign B is LIVE — deployed and armed 2026-08-10 morning (S70), unchanged this session.** Prod
swapped to
**v2.0.12/ws.4 with `BIAS_TEE=0`**, verified in the running system (banner, bias-tee-off line,
DEC-0062 redaction, loop flowing, reception back at 70% after the swap dip); `install` clean at
09:40. **Pilot 08-11T00:35–04:20, then H hold; square 08-12 → 08-20T00:05.** GATE 2 = the pilot
readout with the owner, Tuesday daytime (settle rule: drop each block's first 2 samples). Track
via tick log + `rx_experiment_data.log`; read results **only** with `ops/campaign_analyze.py
--campaign B`; A's anchor is arm A **74.81%** on that tool. Abort floor 50%; every failure path
restores baseline and emails. An unattended run still has **no working dongle recovery** — don't
expect a rescue. **Hub carries `:v2.0.12`** (pushed at S70 close;
config digest verified = NAS build). `:latest` stays on v2.0.11 **on purpose** — move it once the
station proves the release; decide at GATE 2.

Two things not to re-derive: **`weewx_monitor.py` IS the watchdog** (DEC-0074), and **every reset
line before 2026-08-07 19:28 names `syno_vbus_reset`, an operation that never ran** — prod is right
now, the *history* still lies, and that is what sent S67 down the wrong path.

`docs/CAMPAIGN-B-RUNBOOK.md` governs the night and carries the release mechanics, if a relaunch is
ever needed — already armed, not needed right now.

### Current state (S69)

| Thing | State |
|---|---|
| Prod | **v2.0.12**, driver **ws.4**, `BIAS_TEE=0`, LNA **out**, gain 372. Swapped + verified 08-10 09:05; emitting live |
| Live-config deviations | `timeout = 30` + `[[[pragmas]]] journal_mode = DELETE`, both verified in the running `weewx.conf`. Table in `CONSTANTS.md` |
| `weewx_monitor.py` | **alive, supervised, current** — pid 8810 era continued through the swap; soak "monitor alive" green 08-10. It **is** the USB watchdog (DEC-0074) |
| Branches | steady state: exactly `dev` + `main`. `main` = `7b6fd42` = prod; `dev` slightly ahead (post-release docs) |
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
with it), two sessions of non-campaign, cross-repo focused work, in order:

6. **`#144`** — console pressure reads ~+0.03 inHg high vs METAR MSLP; `pressure_service.py`
   writes the sea-level value into all three fields (`pressure`/`barometer`/`altimeter`, bit-
   identical, should differ by ~0.6 inHg at 550 ft); hourly sample-and-hold staleness
   (`fetch_interval = 3600`, a 60-min staircase). File-don't-fix courtesy report from HLF
   (hlf#302) — item 1 (console/WeatherLink elevation setting) is **owner-only**, not
   automatable. Items 2–3 need a design decision first (inject-only-`barometer` vs. compute the
   inverse reduction; polling cadence within WeatherLink v2 rate limits) — `pressure_service.py`
   is **baked into the image** (CONSTANTS.md deploy layers), so any fix needs a NAS-native
   rebuild + prod deploy, not just a commit. Discuss the approach before coding.
7. **`ops#141`** (`hyperlocal-forecast-api`) — mount the weewx archive **directory**, not the
   single `.sdb` file. **Scope this before touching anything**, not mechanical execution: DEC-0071
   already tried this exact shape once — HLF shipped the directory mount, WAL went live, and it
   was rolled back 28 minutes later after HLF froze on a stale snapshot. The issue as currently
   written may already be partially done, partially reverted, or superseded — check HLF's
   *current* mount state first. WAL itself is separately blocked (`weewx.sdb-wal` mode 0555, no
   mount change fixes that), so "closing #141" may mean something narrower than the issue's own
   suggested order implies.

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

_Last updated: 2026-08-10 (S71 close) — ops#148 + DEC-0079 closed, ERR-0005 backfilled
(`DATA_ERRATA.md`), `#144`/`ops#141` sequenced for after GATE 2. **Next job: the radiation-floor
design handoff above.** Campaign B and blocker 4 unchanged from S70/S69._
