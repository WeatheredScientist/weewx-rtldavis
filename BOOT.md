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

## ▶ Resume here (S74 → S75)

### What's settled (do not re-derive)

**GATE 2 passed; v2.0.13/ws.5 shipped and promoted to `main` (`prod-baseline-20260811`).** DEC-0081
(RF-dead episodes, not USB faults) shipped with child reaping + stall self-classification + episode
ledger (`logs/episodes.log`). Monitor respawned clean: pid **22206** (was 8810), `Monitor started`
15:29:02 — confirmed via DEC-0074 process evidence, not a sha. DEC-0080 radiation fix live (both
live conf and rx-baseline snapshot).

**S74 — the day's second guard abort, root-caused and cleared.** (First was the pilot's zombie-child
stall, cleared 08:55 per S73.) This one tripped `30-min mean reception 46% < 50% floor (arm H)` at
09:55:03. Reconstructed the exact 6-sample mean from `weewx_monitor.log` — 70/30/70/71/20/16 → 46,
matching the abort message exactly. Traced to a real RF-dead episode (09:33–10:04, pre-ws.5): a USB
reset was attempted and logged **ineffective**; recovery was uncorrelated with the reset — the
DEC-0081 signature, not a new failure mode. STOP cleared (owner-confirmed in chat, Class C mint);
verified stable through a **second live episode** (17:52–17:59, also self-recovered, also non-mute:
`raw_stderr_lines=7`, "RF class") without re-tripping. Square proceeds on schedule, 08-12T00:05.

`ops/soak_check.sh`: 14 pass / 2 warn / **1 FAIL — repeated rtldavis stalls: 2** since the v2.0.13
container start (16:37, 17:52). Both non-mute, both self-recovered <7 min, both consistent with
DEC-0081's still-open characterization — but the frequency (2 in ~3h) is itself a new, unexplained
data point. Watch the rate as the square runs; don't re-litigate root cause mid-campaign over it.

Condensation floated as a candidate cause (humid, dewpoint spread 11.7°F at check time) — plausible
for the one **overnight** episode (01:50) only; doesn't explain the two daytime ones. Adds a fourth
candidate to DEC-0081's open list (interference / no-LNA margin / site / **condensation**), not an
answer.

**Dependabot PR #158 (weewx 5.4.0→5.5.0) reconfirmed deliberately open** — no base-platform bump
mid-campaign (the square hasn't run a single block yet); its `tests` check is also currently
failing regardless. Revisit post-campaign with the v2.0.14 cycle.

### ▶▶ S75 JOB LIST

1. **DEC-0080 dark-hours verify, for real this time**: S74 confirmed the correction is live but
   couldn't check results — dark hours hadn't happened yet at check time. Check last night's
   (08-11→12) archive data: `radiation` must read 0 across the dark window. If 3.516 / `sr_raw=2`
   shows, extend per-code, never a loose window.
2. **Square health, block 1**: A-arm swap at 08-12T00:05 — tick log shows `swapping H -> A` and
   `arm A live and healthy`; reception plausible. Any guard abort gets the same treatment as S74's
   (reconstruct from `weewx_monitor.log` before clearing, not reflexively).
3. **Repeated-stall rate watch**: 2 episodes in ws.5's first 3h. Is this settling toward DEC-0081's
   historical baseline or running hot? `episodes.log` has 2 rows now — read it directly rather than
   re-deriving from raw logs each time.
4. Daily square watch (cheap, ~5 min): `ops/soak_check.sh`, STOP absent, state matches schedule,
   reception plausible.

**ops#153 open**: this repo's own `MANIFEST.md` is over its documented cap (4,334/4,000) — not
addressed this session, owner's call on timing.

### Current state (S74 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**, up since 15:02 EDT 08-11. `soak_check.sh`: 14 pass / 2 warn / 1 fail (repeated-stall count, see above) |
| Campaign B | **H hold live, STOP cleared** — square starts 08-12T00:05 as scheduled. Sticky-abort-until-cleared behavior confirmed working as designed (tripped once this cycle, held ~8h until diagnosed + cleared) |
| Live-config deviations | three: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero (also in rx-baseline snapshot). Table in `CONSTANTS.md` |
| `episodes.log` | 2 rows (16:34–16:40, 350s; 17:52–17:59, 410s) — both self-recovered, both non-mute |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` + `main` in sync — promotion PR #161 merged, `prod-baseline-20260811` tagged |

## Blockers

1. **weewx process freezes ~once/day (DEC-0067/0068) — unchanged, separate phenomenon** from
   DEC-0081's episodes. Gates nothing.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open): interference vs no-LNA
   front-end margin vs site vs **condensation (new S74 candidate, unconfirmed)**. The ledger +
   self-classification + A×B campaign data are the instruments; characterization is post-campaign.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-detection day remains the
   longest episode on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` matches by basename** — read `ops/wxcheck.sh` / any `weewx.conf` with
  `readconf`.
- **`rx_experiment_data.log` P449-tagged rows 01:23→08:55 on 08-11 are contaminated** (stall +
  baseline morning under one tag). `campaign_analyze.py` is immune (reads swap-time blocks).
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only by design (mutations refused by the box)** — clearing `rx_experiment.STOP`
  needs the mutating NAS path (Class C, `nas-admin`): confirm the exact command in chat first, mint,
  re-run identical. Worked cleanly S74.

_Last updated: 2026-08-11 (S74 close) — day's second reception-floor abort root-caused and cleared,
square proceeding on schedule, soak_check flags a repeated-stall rate to watch, weewx 5.5 bump
reconfirmed deferred._
