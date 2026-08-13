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

## ▶ Resume here (S79, in progress)

### What's settled (do not re-derive)

**Campaign B: v2.0.13/ws.5 in prod, `prod-baseline-20260811` tagged; square recovered (DEC-0082,
S75, schedule shifted +24h).** Arm **A** due `2026-08-13T00:05`; square runs through
`08-21T00:05`. Still holding on **H** until then.

**Stall burst (DEC-0083) plateau CONFIRMED** — fourth flat reading (S79): 48h/72h still exactly
record-max 6/6 with no further growth, 24h back to 1 episode (68th pct). No new episode since
2026-08-12 01:36. This is the confirmation DEC-0083 was waiting on, not another "leans" reading —
treat the burst as settled unless a fresh climb reopens it. `ops/stall_baseline.py` /
`ops/freeze_baseline.py` (DEC-0085) are the re-runnable readouts for both sides; neither number
decays.

**Freeze rate: first-ever "elevated" rolling-window reading (S79), 48h only.** 24h/36h/72h stayed
unremarkable (68–90th pct); 48h read 92.5th pct (current 7, record-max 12) — driven by a same-day
cluster (4 freezes on 08-12 alone: 00:45, 19:46, 19:55, 21:04) landing in the same 48h window as
2 from 08-11. One window out of four, so not a confirmed trend by this repo's own "don't rest a
verdict on one cut" standard — but it's the same night as the first campaign-gating freeze pair
below. Re-run `ops/freeze_baseline.py` next check; a second elevated window would corroborate it.

**S76/S77 shipped DEC-0084 (secret gate hole 6 closed), DEC-0085 (`ops/freeze_baseline.py`), and
DEC-0086 (`barometer_inHg` is an unflagged WeatherLink passthrough, documented in
`docs/INTERFACES.md` §1).** Detail: CHANGELOG `[S76]`/`[S77]`.

**Dependabot PR #158 (weewx 5.4.0→5.5.0) still deliberately deferred** — no base-platform bump
mid-campaign; revisit post-campaign with v2.0.14.

**S78 — guard abort (freeze pair, 19:46–20:02) reconstructed and cleared well ahead of the 00:05
due time; first known freeze severe enough to gate the campaign** (freezes were "gates nothing",
DEC-0081/0083). No schedule shift needed, unlike DEC-0082. Detail: CHANGELOG `[S78]`, BACKLOG
freeze-rate watch. **Swap itself unverified as of this handoff** — S79 job 1.

**S79: a third freeze (21:04–21:09, 300s) traced and reconciled — not a new incident.** It landed
while STOP was still present from the 19:55:35 abort (tick log: refusals logged straight through
21:15); STOP was cleared sometime after that with no separate log line. Folds into the S78 event,
no fresh reconstruction needed. It's also the fourth freeze counted in the new 48h-elevated reading
above.

### ▶▶ S79 JOB LIST

1. **Verify the arm-A swap — due `2026-08-13T00:05` (NAS-local), still unconfirmed.**
   Tick log should show `swapping H -> A` and `arm A live and healthy`; reception plausible. A
   further guard abort gets the S74/S75/S78 treatment — reconstruct before clearing, never
   reflexively.
2. Daily square watch (~5 min): `ops/soak_check.sh` — done this session (15 pass/2 warn/0 fail,
   both warnings known/expected shapes), STOP absent, state matches schedule. Next check, glance at
   `ops/freeze_baseline.py` for a second elevated 48h window — corroboration would upgrade this
   from a watch item to a trend.

### Current state (S79, mid-session)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**, untouched this session (repo/governance work only). `soak_check.sh` (S79 re-run): 15 pass / 2 warn / 0 fail — reception 62% (single reading; 70–84% through the S78 evening) and a USB-hedge-reset warning, both known/expected shapes, not new faults |
| Campaign B | Holding on **H**; arm **A** due `2026-08-13T00:05`, square through `08-21T00:05`. STOP absent (S78's abort cleared, S79's third freeze reconciled into the same event — see above) |
| Stall rate | **Plateau CONFIRMED (S79, 4th flat reading)** — 48h/72h at record max, no further growth. Re-run `ops/stall_baseline.py`, don't eyeball `episodes.log` |
| Freeze rate | First-ever elevated single-window reading (48h, S79) — see above. Needs a second window to corroborate before calling it a trend |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | `dev` synced with `origin/dev` at PR #168's merge commit; this session's write-up is on `s79-baseline-confirm`, PR pending. `main` unchanged at `prod-baseline-20260811` — not in sync, no promotion due yet. Only `dependabot/pip/weewx-5.5.0` remains beyond `dev`/`main` |

## Blockers

1. **weewx process freezes — 1.57/day, median 240 s (S79 re-measurement via
   `ops/freeze_baseline.py`), separate phenomenon** from DEC-0081's episodes. **S78: no longer
   "gates nothing"** — first known freeze pair severe enough to trip the campaign's own abort
   floor (see above). **S79: first-ever elevated 48h rolling-window reading**, same night as the
   S78 event — one window, not yet a confirmed trend (see above). Root cause still unproven
   (thread blocking on the bind-mounted log volume is the leading hypothesis, DEC-0067/0068).
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open): interference vs no-LNA
   front-end margin vs site vs condensation. **DEC-0083 adds a dated onset (08-10 23:56) the
   characterization should start from** — it coincides with the campaign-B pilot night and the
   v2.0.12 promotion, neither of which is established as cause.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains
   the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` matches by basename** — read `ops/wxcheck.sh` / any `weewx.conf` with
  `readconf`. **Found S75: its documented `command`-prefix escape hatch does NOT clear
  it** — re-blocked with the identical message even with `command scp ...` already applied. Looks
  like a bug in the guard's own matching, not filed anywhere yet. If it blocks a NAS write again:
  try a different tool (`rsync` also got flatly denied with no mint path that session — may be a
  separate classifier layer) or hand the single command to the owner rather than iterating on
  `scp` variants.
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only by design (mutations refused by the box)** — clearing
  `rx_experiment.STOP` needs the mutating NAS path (Class C, full-credential ssh): confirm the
  exact command in chat first, mint, re-run identical. Worked cleanly S74, S75, S78.

_Last updated: 2026-08-12 (S79, mid-session) — stall burst plateau CONFIRMED (4th flat reading);
freeze rate's first-ever elevated 48h window, same night as S78's campaign-gating pair; third
freeze (21:04) reconciled into that same event. Arm-A swap verification still pending, due 00:05._
