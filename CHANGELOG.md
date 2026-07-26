# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S48b] — 2026-07-25 — Provenance audit (DEC-0053): loop-JSON cache bounded; #48 and #45 closed

**Issue #48 — closed, DEC-0042 upheld.** A dashboard-side reconciliation found WeatherLink's
install-to-date total only balances if the console *excludes* the 2.56″ of phantom rain we corrected,
and asked whether that undercuts DEC-0042's ISS-side mechanism. It does not — the premise conflates
two classes this repo's data model already separates into independent flags: the 2.56″ is `rain_qc`
(3 points, the **counter**, owned by DEC-0021/0033/0035), while DEC-0042 governs `rainRate_qc`
(33 points, `rain = 0.0` in every one, contributing 0″ to any total). Both classes independently
*require* the console's absence — ERR-0001 was our own wraparound handler adding 128 to a logged
`rain_count=-64` and ERR-0002 a bit-7 flip passing CRC (both downstream of the shared broadcast), and
DEC-0042's mechanism predicts no tip at all. Per INTERFACES §4 the console is our ground truth for
"did the bucket actually tip," and it says no — confirmatory, not contradictory. The reconciliation is
real value as **independent validation that the correction was right** (residual 0.01″), now recorded
in `DATA_ERRATA.md`. DEC-0042 gained a "Challenged and upheld" note so it isn't re-derived.

**Issue #45 — closed as DEC-0053.** Audited every artifact a consumer reads for whether the
assumptions it was produced under travel with it. One real bug, two documented gaps:

- **Fixed:** `loop_json_writer.py`'s cache was **unbounded** — it updated only on non-None values,
  never expired them, and stamped every write with the *current* packet's `dateTime`. A dead or
  SensorQC-rejected sensor emitted its last value forever, indistinguishable from a live reading, on
  the surface the dashboard reads. Same failure `dewpoint_service.py` fixed for the archive path at
  S33/DEC-0022 — learned in one artifact, never propagated to its sibling. Now bounded per-field:
  300 s default (matching DewpointCacher), **2 × `[DavisPressure] fetch_interval`** for
  `barometer_inHg`, since a flat 300 s would have blanked the hourly-fetched barometer for 55 min of
  every hour and regressed Cold-load Fix B. Expired fields are omitted, not frozen, and logged at
  WARNING. 6 new tests + a mutation check confirming they go red against the old cache (91 total).
- **Documented, not fixed:** InfluxDB carries no station identity — and the "one-line" `tags =` fix is
  a trap, since it forks the series key (interface break, needs dashboard coordination). The SQLite
  archive carries no correction flag, so the system of record is less provenanced than the derived
  store. Both in BACKLOG with the reasoning.

`INTERFACES.md` §1 updated — the staleness bound is part of the contract, and a missing field now
explicitly means "no current value," never "value unchanged."

**Deployed and verified in prod** (PR #69 merged, then hot-swapped — `loop_json_writer.py` is MOUNTED
per DEC-0046, so the merge alone would have been inert). Pre-flight drift check confirmed the live
file was byte-identical to the repo's pre-change version; scp'd with md5 matched both ways, pyc
cleared, container restarted (`kill` → `start`, DEC-0008). Live log: `cache TTL 300 s,
barometer_inHg 7200 s` — the barometer TTL correctly derived from the live `fetch_interval = 3600`.
Watched 453 s, past the default TTL: zero expiry warnings, all fields still served, values updating.
Rollback is `loop_json_writer.py.bak-pre-ttl-S48` + restart. No image rebuild; `:v2.0.8` unaffected.

---

## [S48] — 2026-07-25 — pytest hard-gated at commit time; closes issue #55

Investigated [#55](https://github.com/WeatheredScientist/weewx-rtldavis/issues/55) ("closeout
doesn't hard-gate on a green test suite"), filed 2026-07-16 before this repo's closeout skeleton
existed. Found the practical exposure already narrow: `dev` is a protected branch requiring the
`tests`/`lint`/`secret-scan` CI checks before any merge (verified directly this session via PR #65),
so a broken-test commit has no path onto `dev` regardless of whether an agent remembers to run
pytest locally. The one real remaining gap: pytest wasn't part of `.pre-commit-config.yaml` — only
ruff/mypy/secret-scan ran at commit time, which is what DEC-0015 originally intended but never fully
wired up. Added a `local` pytest hook (isolated pre-commit env, `additional_dependencies: [pytest]`,
`always_run: true`) — the suite is all-stdlib so it needs nothing from this repo's `.venv`. Verified
it fires on every commit and passes in isolation. Commented on and closed #55, citing the branch-
protection/CI structure as the actual hard gate, with this as the immediate-local-signal bonus.

(Caught, not fixed, as out of scope: running `pre-commit run --all-files` surfaced 19 pre-existing
mypy errors and trailing-whitespace fixes across `influx.py`/`ogoxeUploader.py`/`weewx.conf.example`
that normal per-commit runs never touch, since pre-commit only checks each commit's own diff.
Reverted those incidental changes — not this session's task.)

---

## [S47] — 2026-07-25 — Backlog + branch cleanup: loopdata.py / reception_service.py removed, rw350/400-test images deleted, stale worktree removed

Cleared four long-parked, "not urgent" backlog items in one session.

**`loopdata.py` (DEC-0005, open since S16).** `user.loopdata.LoopData` was confirmed still absent
from every active `[Engine][Services]` list. Removed the `[LoopData]` config section from the live
`weewx.conf` (backed up first as `weewx.conf.bak-pre-loopdata-cleanup-S47`; a small Python script
found the section by its top-level header and asserted on expected content before writing, rather
than a line-count sed). Recreated `weewx-rtldavis-v2` (`kill` → `rm` → 3 s settle → `run`,
reconstructed from `docker inspect`) without the `loopdata.py` bind mount. Verified live: container
`running`, 6 mounts (down from 7), `weewx.log` publishing archive records and RESTful uploads within
seconds, no `CRITICAL`/stall. `loopdata.py` renamed aside on the NAS to `loopdata.py.removed-S47`
rather than deleted, for rollback.

**`ops/reception_service.py` (found S43).** Confirmed unimported anywhere in the test suite (one
stale comment reference in `tests/test_reception_layer_b.py`, fixed), never `COPY`'d into the
Dockerfile, and its `ReceptionMonitor` service never listed in `weewx.conf`. Deleted from the repo;
the NAS copy renamed aside to `reception_service.py.removed-S47`.

**`rw350-test` / `rw400-test` Docker images (DEC-0048's last piece).** `rw250-test` was retired at
DEC-0048 (S41); the other two ad-hoc `receiveWindow`-sweep tags were left. Confirmed neither backs
any running container (`docker ps -a` showed only `weewx-rtldavis-v2` on `:v2.0.8`) and deleted both
from the NAS. DEC-0048 is now fully closed.

**Stale worktree.** `.claude/worktrees/s46-closeout-amendment` (branch
`worktree-s46-closeout-amendment`, merged via PR #64) removed — same pattern as the 8 worktrees
cleaned up at S41.

No driver/source code changed, no image rebuild, `:v2.0.8` unchanged. Docs updated: BACKLOG.md,
ROADMAP.md, docs/ARCHITECTURE.md, docs/DECISIONS-FULL.md (DEC-0005), docs/STATUS.md.

---

## [S46] — 2026-07-24 — Humidity-spike watch checked directly (still unfired); OPS-DEC-0019 rollout closed cross-repo; dev housekeeping

Ran the DEC-0044 humidity-spike check directly against the live NAS logs rather than deferring it:
fetched every `log_humidity_raw` packet captured since the capture went live (2026-07-13 15:27, S41)
through the current log — 11 days, 8,852 raw packets, ~3x the largest prior sample (S43's 2,056).
Decoded per the driver's own formula (`rtldavis.py:1543-1550`) and searched for a single-step raw jump
of 16-37 %RH (the DEC-0044 signature). **Zero matches.** Largest swing: -9.86 %/min (2026-07-17
13:16→13:17, 60.5%→51.3%) — larger than S43/S44's reported 7.5 %/min purely from sample size, still
ordinary midday humidity movement, clustered in the predicted 11:00-16:00 window. Watch remains open,
unfired.

Closed [eaglehunt-ops#37](https://github.com/WeatheredScientist/eaglehunt-ops/issues/37) (OPS-DEC-0019
env-twin rollout): confirmed all three Eagle Hunt repos had merged their portion (weewx-rtldavis#59 in
S45, hyperlocal-forecast#135, eaglehunt-weather-dashboard#102+#112) — commented and closed.

Housekeeping: local `dev` was 2 commits behind `origin/dev` (PR #61, `ops-53-settings-consolidation`)
— pulled forward; removed the resulting stale merged worktree
(`.claude/worktrees/ops-53-settings-consolidation`) and its local branch. Checked eaglehunt-ops' open
issues and both sibling repos for anything owed here: nothing tagged `repo:weewx`, nothing outstanding.

Opening this closeout as PR #62 surfaced a real CI break: the lint job's unpinned `pip install ruff`
had drifted to 0.16.0, whose new default rules flagged 295 pre-existing hits (139 in `rtldavis.py`,
the driver protected from reformatting churn by DEC-0014/DEC-0027) — `lint` is a required check on
`dev`, so this was silently blocking every PR. Fixed via PR #63 (pinned `ruff==0.5.7`, matching the
`.pre-commit-config.yaml` pin DEC-0027 already settled on; no source files touched). Merge order:
#63 merged first, then #62's branch was updated onto it so its own lint check went green. Both
merged 2026-07-24. The CI workflow file changed; no source/driver code did.

---

## [S45] — 2026-07-20 — PR #59 merged: OPS-DEC-0019 env-twin permission rules (cross-repo)

`.claude/settings.json` gained two ask-rule entries: `Bash(env * git merge * main)` and
`Bash(env * git merge * dev)`. Env-wrapping (`env -u GH_TOKEN git merge …`) defeats ask-rule
pattern matching, since `env` isn't stripped before the match runs — the existing `git merge * main`/
`git merge * dev` rules never fired for an env-wrapped call, which fell through to the auto-mode
classifier instead of resolving by rule. `git push` already carried its env-wrapped twin; this fills
in the same gap for the two protected-branch merge rules. Mechanical, no code touched, part of the
cross-repo OPS-DEC-0019 rollout (`eaglehunt-ops#37`) landing the same fix in all three Eagle Hunt
repos. CI green (lint/secret-scan/tests). The branch and commit were already staged when this session
started; this session's contribution was flipping draft PR #59 to ready and merging it to `dev`.

Humidity-spike watch and the DEC-0049 rainRate prediction: unchanged, still unfired (see [S44]).

---

## [S44] — 2026-07-19 — Soak-check phantom-rain false positive fixed; shared closeout skeleton adopted (DEC-0052)

`ops/soak_check.sh` on the still-running v2.0.8 (up 98h) flagged 49 archive rows as a possible
DEC-0049-predicted phantom-rainRate event. Cross-checked against the full 2026-07-18 archive: it
wasn't one — 3 real bucket tips that day, a falling barometer (29.93→29.78 in) and rising gusts (to
8 mph) confirm a real storm, and every flagged row is the ISS's own rain-rate message decaying after
a real tip (one decay tail ran 38 minutes, past the light-rain formula's nominal ~1022s ceiling).
**Fixed:** the detector now excludes any row with a real tip in the preceding hour. Re-verified
live: 49 → 0 false positives, all other soak checks unchanged. The DEC-0049 prediction itself (a real
condensation event, tip counter not advancing) remains unfired.

**DEC-0052:** adopted eaglehunt-ops' locked closeout skeleton (OPS-DEC-0016), adapted. `CLAUDE.md`'s
closeout ritual — previously split across two paragraphs ("Session ritual — End" and a separate
"Docs-diet ritual at close") — is now one 6-step numbered list; the docs-diet ritual and this repo's
stricter local commit/push rule are kept as addenda, per the template's own pattern. The only
genuinely new content is step 5, a model-tier restore check — the third repo (after
hyperlocal-forecast, coffeeradar) to independently land on that same assessment. Closes
weewx-rtldavis#56; outcome reported to eaglehunt-ops#22.

Both changes landed via PR #57 (`s44-ops-closeout-and-rain-fix` → `dev`), checks green
(lint/secret-scan/tests).

Humidity-spike watch: still negative, 894 samples this container lifetime, largest jump ~7.5 %RH/min
— same magnitude as S43, no qualifying spike.
