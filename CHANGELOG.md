# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S141] — 2026-09-27 — UV diode-floor correction: DEC-0080's exact-code zero extended to UV's two dark codes (DEC-0200, `eaglehunt-ops#343`)

- **Checked in with ops on `#343`.** The thread had closed 23 s after the owner put the UV fix on
  weewx. Posted the measurement and asked ops to confirm there was no later stand-down call
  ([comment](https://github.com/WeatheredScientist/eaglehunt-ops/issues/343#issuecomment-5860016912)),
  then rang the ops session.
- **Measured before designing (prod archive, 08-12 → 09-27).** UV's dark floor is two codes, not
  one: `uv_raw 2` (0.04) in 96.9% of rows, `uv_raw 1` (0.02) in 2.5%, in runs of minutes, and never
  0 or 3. The same pass re-verified DEC-0080's solar floor as clean: one code, with `sr_raw 2` only at
  twilight.
- **The owner chose the two-code exact window**
  `UV = UV if UV is None else (0 if 0.01 < UV < 0.05 else UV)` over the thread's one-code line.
  `weewx.conf.example` carries it. The new `tests/test_diode_floor_corrections.py` pins both
  diode-floor lines under weewx 5.5's own `StdCalibrate` eval semantics (10 tests,
  positive-controlled).
- **Applied live 2026-09-27 17:39:57 ET.** A container dry-run came first. The owner approved the
  Class C root-route `sed` over the live conf and the tenant-root `.rx-baseline`; the mint was refused
  once and succeeded on the ladder's retry. `weewx.service` restarted at 17:40:18 and booted clean.
  The dark-hours-read-0 check is still pending (`BOOT.md` job 1).
- Docs: DEC-0200; a `CONSTANTS.md` live-config deviations row; `docs/INTERFACES.md` now says the
  radiation/UV dark floors are zeroed by config, with this station's apply dates.
- Gate: ruff clean · 516 passed / 17 skipped · mypy clean, 72 files · secret gate 0
  (positive-controlled).

## [S139] — 2026-09-19 — `docs/ARCHITECTURE.md` re-verified against live marvin state (BOOT job 5)

- Doc hadn't been touched since S17 (2026-07-04) and had drifted across the DEC-0118 marvin move:
  stale weewx version (5.3.1 → 5.5.0, verified live), stale LNA/bias-tee claim (LNA is out,
  `BIAS_TEE=0`), a NAS-pathed mount table duplicating (and out of sync with) `CONSTANTS.md`'s own
  table, and a NAS-side monitor section describing a DSM-Task user that no longer exists. Section
  3's mount table is now a pointer to `CONSTANTS.md` instead of a second copy (STANDARD rule 5).
  Section 7 rewritten for `weewx_monitor.py`'s current shape: `weewx-monitor.service`,
  `User=t-weewx`, `REMEDY_MODE=none`, and why `usb_reset.sh` doesn't apply on marvin's topology.
  `CONSTANTS.md` itself checked out accurate on everything verifiable — no changes needed there.
  Two rows stay flagged unverified (marvin host tool availability, `LOCAL_INFRA.md`'s marvin
  entry) — both need either an interactive host shell or reading a secret-bearing file the
  read-guard rightly blocks. PR #392.
- Closeout ran late (this entry + the `BOOT.md` pointer rewrite land at S140's session start,
  per `ops#218`'s "closeout debt" recovery path — the session that did the work ended without
  running its own closeout).

## [S138] — 2026-09-14 — Tier-file conformance (`eaglehunt-ops#312`/`#313`); freeze-rate re-read confirms DEC-0088 (DEC-0198); `#373`'s full-outage alert class (DEC-0199)

- **`eaglehunt-ops#312`/`#313` fixed.** `BOOT.md` gained its three missing universal sections
  (`## Current state`, `## Files needed at session start`, `## Style`); `MANIFEST.md` gained the
  coverage row for 9 repo-root WeeWX runtime modules (`rtldavis.py`, `influx.py`,
  `loop_json_writer.py`, `ogoxeUploader.py`, `owm.py`, `pressure_service.py`,
  `dewpoint_service.py`, `wcloud.py`, `windy.py`). `MANIFEST.md`'s own cap stays over (4816 vs
  4000 chars) — the new coverage row is required content; coverage-beats-cap per OPS-DEC-0101 and
  S136's own precedent on this file (`eaglehunt-ops#306` commented, left open). PR #387.
- **DEC-0198: freeze-rate re-read confirms DEC-0088's 1.31/day; S131's 4.03/day was that
  session's own confound.** Checked `weewx.service`'s own uptime first (continuous since
  2026-09-07 23:42:48 EDT, zero restarts — a genuinely quiet window) before trusting the
  re-measurement. Fresh `ops/freeze_baseline.py` read: current 24h/36h/48h/72h rolling windows
  all 0 freezes, 0.0th percentile. Of 49 freezes over 17.6 d, 24 cluster on 2026-09-07 — the day
  S131 ran and ported this script to `marvinctl` (DEC-0152) — including one 8580s outlier;
  excluding that incident day, 25/~16.6d ≈ 1.51/day, matching DEC-0088/DEC-0083. `BOOT.md`
  blocker 1 reworded (mechanism itself, DEC-0068/DEC-0094, stays unproven); `ROADMAP.md`'s P0
  line reconciled. PR #388.
- **DEC-0199: `#373` closed — `weewx_monitor.py` gains a FULL OUTAGE reception alert class.**
  The driver-process side already had distinct escalating classes (DEC-0081/DEC-0120); the actual
  gap was narrower — `close_reception_window()`'s own alert treated every sustained sub-60%
  streak identically, which is what made the 09-07 incident's `WINDOW: 0/21 (0%)` log unreadable
  at a skim. New `classify_reception_alert()` cross-references two independent signals, either
  sufficient alone (same shape as `ops/freeze_baseline.py`'s RF-dead classification): every
  window in the sustain streak at literally zero packets, or the driver's own watchdog already
  escalated (`WD['escalated']`). Alert subject/log line say `DOWN`/`FULL OUTAGE` instead of `LOW`
  when either fires, naming which signal(s) tripped; recovery wording unchanged. 10 new tests —
  `close_reception_window()` had zero prior coverage. Not yet deployed to marvin (host-side
  daemon; needs `marvinctl pull` + a deliberate `weewx-monitor.service` restart). PR #389, DEC-0199
  writeup PR #390.
- **`eaglehunt-ops#326`/`#320` answered**, cross-repo dispatch ring received: probed the new
  `marvinctl notify-log weewx.service` verb (clean, "no page recorded" shape confirmed), posted
  verbatim, rang the live ops session back.
- **Session-start checks, nothing new found beyond the above.** `estate-context-heartofgold`/`-2`
  branches re-confirmed stale/local-only (neither on `origin`, both predate a large chunk of
  current `dev`); the closeout-debt hook's repeated flag was the same harmless shape each time —
  a BOOT.md-content commit and its own merge commit landing "after" it.
- Gate: ruff clean · 506 passed / 17 skipped · mypy clean, 71 files · secret gate 0.
