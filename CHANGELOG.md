# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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

## [S137] — 2026-09-13 — Adopted the cross-repo dispatch ring protocol (`eaglehunt-ops#321`, DEC-0197)

- **`eaglehunt-ops#321` answered.** `CLAUDE.md`'s Session ritual gains a **Cross-repo dispatch**
  bullet next to the existing inbox-pull step: after posting a tracker comment asking something of
  another repo, ring that repo's live session (`ListAgents`) with one line; receivers read, act
  within their own permissions, answer on the tracker, and ring back; nothing Class C rides a
  message. Wording mirrors hlf's/coffeeradar's/heartofgold's already-adopted text. PR #385, merged
  to `dev`. Logged as DEC-0197 — no ROADMAP line touched.
- **Session-start checks, nothing new found.** This repo's own tracker (#380/#373/#370/#337) and
  the ops `repo:weewx` inbox (#313/#312/#306/#265/#110) were already fully reflected in `BOOT.md`'s
  S137 job list. `estate-context-heartofgold` confirmed old/merged-away history, not a stranded PR.
  The closeout-debt hook's flag against `8111407` was a false alarm: that commit **is** the
  `BOOT.md` fold-in of S136's post-closeout cross-repo replies, not undocumented drift.
- Gate: ruff clean · 496 passed / 17 skipped · mypy clean, 70 files · secret gate 0.

## [S136] — 2026-09-09 — `backfill_container.py` fixed to run self-service against marvin (DEC-0196); `MANIFEST.md` trimmed (`eaglehunt-ops#306`); ROADMAP tripwire reconciliation

- **`ops/backfill_container.py` fixed (DEC-0196), closing the gap behind three separate ad hoc
  incident workarounds** (DEC-0151, DEC-0153, the ERR-0009 attempt near DEC-0155). It was broken
  as committed — a never-filled `INFLUX_ORG` placeholder, a dead compose-network hostname, and a
  read-write connection against the live production archive. Now reads
  `server_url`/`org`/`bucket`/`token` straight from the container's own mounted `weewx.conf` via
  `configobj` (the token never crosses a transcript), connects read-only, and requires
  `--start`/`--end` instead of defaulting to stale one-off incident dates. Verified live with
  `--dry-run` against the real running container — 870 records correctly batched, zero writes.
  `ops/backfill_influx.py` unchanged in behavior, docstring only. PR #382.
- **`MANIFEST.md` trimmed for `eaglehunt-ops#306`'s estate-wide tier-file sweep**: collapsed the
  one real rule-9 violation (`CHANGES-FROM-UPSTREAM.md`'s 9 enumerated filenames → a class
  description), dropped the header's stale S94-specific size arithmetic in favor of pointing at
  `boot-cap-check.sh`, and fixed a stale "NAS-side daemon" reference for `weewx_monitor.py` found
  in passing. Residual size is a coverage-beats-cap case per OPS-DEC-0101, not further
  compressible without cutting real load-when guidance. PR #381.
- **Incidental finding, filed not fixed:** `marvinctl conf`'s server-side redaction catches
  `token` but not `server_url` — a real marvin LAN IP reached this session's transcript while
  verifying the above. Filed as `eaglehunt-ops#308`; heartofgold's live session notified directly
  per the standing cross-repo SOP.
- **`docs/ROADMAP.md`'s own ~10-session reconciliation tripwire fired exactly on time (due "by
  S136").** Full pass: nothing stale found. The P0 freeze-rate line deliberately still reads
  DEC-0088's 1.31/day — S131's 4.03/day reading stays unconfirmed and un-DEC'd pending a
  quiet-window re-read (`BOOT.md` job 1), so it belongs in `BOOT.md`, not here. P3's
  INTERFACES.md line re-verified current through DEC-0093. Next check: S146.
