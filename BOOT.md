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

## ▶ Resume here (S73 → S74)

### What S73 settled (do not re-derive)

**GATE 2 passed; arms {372, 496} confirmed; square runs 08-12T00:05 → 08-20T00:05 on v2.0.13.**
Pilot gave P496 75.56% ≥ P449 72.65% (aborted at 2 of 5 arms on a stall — the abort became the
day's biggest win). DEC-0080 radiation fix applied (live conf **and** rx-baseline snapshot — a
live-only apply is wiped by `restore_baseline`), `health_ok` budget fixed (missing RF-acquire
term, 36→60 tries — the old budget would have coin-flipped every square swap), `:latest` →
v2.0.12 at GATE 2.

**DEC-0081 — the stall class is RF-DEAD EPISODES, not USB faults.** Same-day forensics
differential (3 capture sets, night timeline, HLF/coffee-radar correlation): the device never
re-enumerates, the driver's watchdog/respawns work, silent children recur across gain configs and
recovery is time-correlated, never action-correlated. Resets are theater (~17 attempts, 0 fixes);
ERR-0005's recreate-fix = episode-end coincidence; DEC-0065 vindicated. Shipped same day:
**v2.0.13/ws.5** (child reaping — three stacked zombies captured; `STALL DIAGNOSIS` mute-vs-
emitting at every 150s raise; paced `DATA DROUGHT` for the RF-quiet mode that never trips the
watchdog) + **monitor** (`RESET_MAX_TRIES` 3→1 hedge; `episodes.log` ledger, one row per
ALERT→RECOVERY — **the pre-registered LNA-verdict datum**). Soak criterion reframed FAIL→WARN.
Episode ROOT CAUSE deliberately open — post-campaign characterization with A×B + ledger.

### ▶▶ S74 JOB LIST (short, verification-shaped)

1. **DEC-0080 dark-hours verify**: overnight 08-11→12 `radiation` must read 0 (if 3.516 /
   `sr_raw=2` shows, extend per-code, never a loose window). First corrected night.
2. **Square health**: first blocks swapped clean under the 300s budget (tick log); reception
   plausible; any overnight guard abort = clear STOP in the morning and resume — **an episode
   abort is the system working, not a campaign failure (DEC-0081)**.
3. **ws.5 first-contact checks**: any `STALL DIAGNOSIS` / `DATA DROUGHT` lines overnight — each
   one self-classifies; a **mute-class** diagnosis (raw_stderr_lines=0) is the only signature
   that would re-open the USB theory. `episodes.log` gets its first rows on the next episode.
4. **Monitor respawn confirm** (if the owner's kill has run): new pid ≠ 8810 in
   `logs/weewx_monitor.pid` + fresh `Monitor started` line **after** the file mtime (DEC-0074:
   process evidence, never a sha). Until then prod runs the old monitor — new code sits staged.
5. **Promotion bookkeeping if not done at S73 close**: `dev` → `main` PR + `prod-baseline-20260811`
   (CONSTANTS release table flags it pending).
6. Daily square watch (cheap, ~5 min): STOP absent · state matches schedule · soak (now 15/2/0
   baseline) · reception plausible.

**Upstream follow-up staged (post-campaign, not urgent):** CHANGES rows 12–13 (reaping +
self-classification) → PR to lheijst alongside the existing open threads (`UPSTREAM-THREADS.md`).
**Dependabot PR #158 (weewx 5.4.0→5.5.0) deliberately open** — no base-platform bump
mid-campaign; evaluate post-campaign with the v2.0.14 cycle.

### Current state (S73 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**, `BIAS_TEE=0`, LNA out, gain 372 (H hold). Swapped 15:02 EDT mid-H, verified live (banner, canary, records 35s, soak 15/2/0) |
| Campaign B | **H hold live**, square starts 08-12T00:05, self-terminates 08-20T00:05. Guard floor 50%; every failure path restores baseline + emails |
| Live-config deviations | three: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero (also in rx-baseline snapshot). Table in `CONSTANTS.md` |
| `weewx_monitor.py` | **new code deployed + sha-verified (`f9e7d88d…`), respawn PENDING the owner's `ssh -t nas-admin 'sudo kill 8810'`** — uid-1031 process, path-scoped sudo. Old code keeps running (fires old-policy resets) until then — harmless |
| Hub | `:v2.0.13` pushed; `:latest` = v2.0.12 until the square proves ws.5 |
| Branches | `dev` + `main`; `main`/tag one release behind (item 5 above) |
| episodes.log | does not exist yet — created on the first episode close |

## Blockers

1. **weewx process freezes ~once/day (DEC-0067/0068) — unchanged, separate phenomenon** from
   DEC-0081's episodes. Load contributor pattern got a second instance (23:52 episode onset in
   the coffee-radar/HLF-maintenance window, loadavg ~25). Gates nothing.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open): interference vs no-LNA
   front-end margin vs site. Episodes predate LNA removal (08-02, 08-06 LNA-in). The ledger +
   self-classification + A×B campaign data are the instruments; characterization is
   post-campaign work.
3. **ERR-0005** — largely explained by DEC-0081 (same serial-respawn signature, 105-min episode;
   recreate coincided with episode end). Not fully closed: its 21-detection day remains the
   longest episode on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone. Applies to the
  pending monitor respawn (item 4 above).
- **`secret-read-guard.sh` matches by basename** — read `ops/wxcheck.sh` / any `weewx.conf` with
  `readconf`.
- **`rx_experiment_data.log` P449-tagged rows 01:23→08:55 on 08-11 are contaminated** (stall +
  baseline morning under one tag). `campaign_analyze.py` is immune (reads swap-time blocks).
- `campaign_analyze.py --campaign B` will warn "multiple attempts pooled" (the pilot abort split
  the log) — for B the pooling is correct; informational only.
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent (S73's own log-blindness, cost half a differential).

_Last updated: 2026-08-11 (S73 close) — GATE 2 passed, DEC-0080 applied, DEC-0081 decided +
shipped (v2.0.13/ws.5 + monitor demotion + episode ledger), health budget fixed, `:latest`
moved. Square starts tonight on the new stack._
