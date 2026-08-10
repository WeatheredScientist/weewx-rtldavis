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

## ▶ Resume here (S70)

### ▶▶ THE JOB: read the first stall capture (blocker 4)

The apparatus is **deployed, verified and armed** (DEC-0075) — `usb_forensics.sh` `dc7912ae`,
root-owned, re-verified on the box 08-09 after the `/proc`-mtime fix. Do **not** re-deploy — that
is the S60b/S63 trap, BOOT telling the next session to redo finished work. Design, hypothesis and
the two predicted signatures: **DEC-0075** — don't re-derive them.

**Wait for the event.** ~1/day, unpredictable; none since 08-07 19:28 (checked S69 — only the
smoketest + verify files in `logs/usb-forensics/`). Read the `pre`/`post` pair together. **Both
clean means the stall is not a USB fault at all** — a real answer, not a null result.

**Campaign B is GO — launch in flight (S70).** v2.0.12 promoted (#151, `main` = `7b6fd42`); image
**built natively on the NAS** (`9db5c1ddaac3`, explicit `BUILD-EXIT=0`) — the arm64 laptop can no
longer cross-build it (tar ENOSYS under emulation); NAS-native is the v2.0.3-precedent path. The
08-09 night was **scrubbed at 00:58** (VPN died with the 00:35 row passed — the runbook's
postpone-24h contingency, prod untouched). Schedule regenerated +1 day: **pilot 08-11T00:35,
square 08-12 → 08-20T00:05**. Remaining: archive A artifacts (incl. root-owned STOP) → deploy B's
`rx_experiment.sh` from the **merged** dev tip → swap to v2.0.12 with `BIAS_TEE=0` (one nohup'd
batch, VPN-drop-safe) → verify → `install` before 00:35. Hub push of `:v2.0.12` deferred
(docker save → laptop → push from home); `:latest` only after prod proves it. `EXPECT_*` in
`soak_check.sh` still v2.0.11/ws.3 **on purpose** — the bump rides the deploy. An unattended run
still has **no working dongle recovery** — not a gate, but don't launch expecting a rescue.

Two things not to re-derive: **`weewx_monitor.py` IS the watchdog** (DEC-0074), and **every reset
line before 2026-08-07 19:28 names `syno_vbus_reset`, an operation that never ran** — prod is right
now, the *history* still lies, and that is what sent S67 down the wrong path.

### ▶▶ Campaign B — the launch sequence

**`docs/CAMPAIGN-B-RUNBOOK.md` governs the night and carries the release mechanics.** The one thing
worth repeating because it has bitten twice: **take the build sha from `git rev-parse origin/dev`,
never one written down** — a remembered sha ships a green checkmark on a silently incomplete image.

### Current state (S69)

| Thing | State |
|---|---|
| Prod | **v2.0.11**, driver **ws.3**, LNA **out**, gain 372, ~70–80%. Emitting live |
| Live-config deviations | `timeout = 30` + `[[[pragmas]]] journal_mode = DELETE`, both verified in the running `weewx.conf`. Table in `CONSTANTS.md` |
| `weewx_monitor.py` | **alive, supervised, current** — NAS matches merged tip `ad7e5a4`, pid **8810** since 08-09. It **is** the USB watchdog (DEC-0074) |
| Branches | steady state: exactly `dev` + `main`. `dev` ~90 ahead of `main` |
| `:v2.0.12` image | **BUILT on the NAS 08-10** (`9db5c1ddaac3`, from `7b6fd42`). NOT on Hub yet — save→push deferred |
| Campaign B apparatus | schedule regenerated (pilot **08-11T00:35**); script **NOT on the NAS yet** (its `rx_experiment.sh` is still campaign A's) |
| Campaign A | **STOPped, sentinel in place.** Do not clear it |
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

_Last updated: 2026-08-10 morning (S70, in flight) — campaign B GO: v2.0.12 merged + built on the
NAS, first night scrubbed on a dead VPN (runbook contingency, prod untouched), schedule +1 day.
Tonight: deploy + swap + install before 00:35. Blocker 4 unchanged — no stall capture yet._
