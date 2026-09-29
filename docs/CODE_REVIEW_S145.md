# Code review — S145 audit, dev @ 7d06cbf (v2.0.17 in prod), 2026-09-28

**Status:** items 1–9, 33 and 34 (the HIGH set) are fixed in PRs #412–#417 and the docs PR, filed as
#402–#411 (item 5 as `eaglehunt-ops#358`, private). Items 10–32 and 35–39 are open; pick from here.
Predecessor: `docs/CODE_REVIEW_S24.md`. Decision record: DEC-0205.

Method: six read-only reviewers (Sonnet x5 by file set, Haiku x1 mechanical cross-ref), synthesized and
spot-verified by the main thread (Fable 5.1). No worktrees: nothing edited. Repo untouched; gates green
at start (pytest 535 passed/17 skipped, ruff clean, mypy clean).
Legend: [V] verified directly by the main thread · [R] reviewer evidence only (file:line + quote).
Per-reviewer detail was session-local; this file is the durable record (DEC-0205).

## HIGH — wrong behavior, wrong credit/licensing, or would mislead a maintainer

1. [V] rtldavis.py:1672-1720 — slot-count denominator (#317/DEC-0137) is off by one at seeding. The seed
   packet is counted in `count` but its slot never enters `delta`; the skipped first boundary does not
   advance `prev_pkt_ts`. First record after every start/counter reset misreads (22/21 = 104.8%, or ~half
   if the seed precedes the first boundary). Steady state is exact. Tests seed the baseline directly.
2. [V] weewx_monitor.py:1247,1293,1307,1487 — `wu_period_counts` is emptied every 300 s, but the FULL
   OUTAGE classifier and the alert average read it as "the last 5 windows". Both depend on phase; a
   single zero window can classify as FULL OUTAGE, and `sum/(5*EXPECTED)` understates with <5 entries.
3. [V] weewx_monitor.py:753 — any REMEDY_MODE other than exactly `none`/`restart_unit` runs `do_reset`
   (the Synology USB script) while `remedy_action()` logs "no automatic remedy". No validation, no test.
4. [V] owm.py:73,93 and windy.py:62,79 — both convert with `to_METRIC` (group_rain = cm) and send rain
   where the APIs document mm: 10x low if enabled. windy also sends per-interval `rain`, not last hour.
5. [V] scripts/test_check_secrets.sh:91-95 — planted "not real" private-range addresses: two appear
   verbatim in 6 and 15 files of the private estate repos. The gate exempts this file by path. Owner to
   confirm off-screen whether they are live hosts (MARVIN-DEC-0007 / DEC-0127 scrub).
6. [V] Versioning scheme out of step with its own rule. `DRIVER_VERSION = 0.20+ws.5` last bumped
   2026-08-11 (2a6f631); 13 driver commits and inventory items 14-18 landed since. README rule 1 says
   bump on every behavior change; README's table still says patch level `4`; influx.py is `ws.2` since
   8762efb while CHANGES-FROM-UPSTREAM:55 and README:111 say `ws.1`; influx.py:197 comment says rev 1.
7. [V] ops/soak_check.sh:44 — default EXPECT_IMAGE is `:v2.0.16`; prod is `:v2.0.17`, so an un-overridden
   run reports IMAGE MISMATCH on healthy prod.
8. [V] ogoxeUploader.py:67 — `weewx.engine.StdService.__init__` replaces upstream `super().__init__`,
   skipping StdWunderground's init. Not in the §5(a) notice or the inventory (only the log.debug fix is).
9. [V] scripts/check_secrets.sh vs test_check_secrets.sh — removing `passcode` from the key alternation
   leaves all 63 planted controls green (scratch mutation). Reviewer found the same for several classes
   and for the identifier check. History: the gate has been wrong six times (S26→S76).

## MEDIUM — misleading comment/doc, real duplication, stale-but-harmless

10. [V] CHANGES-FROM-UPSTREAM.md inventory lags the code: no rows for #219/#220/#221/#222/#233 fixes,
    Layer B hop caching, `dup_count`, DEC-0056; temp-sign fix "Not yet offered" though lheijst#23 has
    been OPEN since 2026-07-28; line counts stale; wcloud "SPDX only" but carries three `# type: ignore`
    (S49); influx notice omits S49 edits; "Last updated 2026-09-06" beside rows dated 09-28.
11. [V] ruff.toml:3-7 says vendored uploaders are unmodified, so our influx/ogoxe patches go unlinted.
    docker-compose.yml:57 cites DEC-0029 (SensorQC) for "bake the driver" (DEC-0031); calls Synology the
    monitor host; never says prod does not run from it.
12. [V] Retired NAS mechanics presented as current: rx_experiment.sh:70 "Production always uses the
    default" over `/volume1` defaults; loop_json_writer.py:28-33 scp-to-NAS deploy block; nas_build.py,
    proc_probe*.sh, freeze_watch.sh, backfill_influx.py NFS mode; weewx.conf.example:751 dead `[LoopData]`
    with `/volume1/web`; usb_reset.sh / usb_forensics.sh "this NAS"; README:362 "runs on the NAS host".
13. [V] ops/*.service copies lag heartofgold's deployed units (OnFailure, ExecStopPost, --cgroup-parent,
    bolt ExecStartPre) yet weewx-monitor.service:17-21 keeps an install recipe; :99 says the campaign
    script creates `campaign.inhibit` — nothing writes it.
14. [V] ops/tenant_mounts.py:18-21 says `sortedcontainers` is git-tracked; it is gitignored, no repo copy.
15. [V] Dockerfile:169-170 — `{a,b}` brace expansion under `/bin/sh` (dash, no SHELL directive): both
    `rm -rf` cleanups are silent no-ops.
16. [V] README monitor section vs code: "~24/min" vs WU_RF_EXPECTED 21; "daily summary" vs 6-hourly;
    GMAIL_PASS quoting contradicts monitor.env.example; the example documents 3 of the 23 env keys read.
17. [V] weewx.conf.example: 4 of 10 `qc_*_max_delta` keys; no `[LoopJsonWriter]` stanza; `hotswap_*`
    only in `default_stanza`; `version = 5.3.1` vs weewx 5.5.0; top-level [WeatherCloud]/[Windy]/[OWM]
    stanzas that no module reads (they read [StdRESTful] subsections).
18. [V] Driver comments that misstate the code: :2027 "`if packet:` was a NameError waiting" (packet =
    dict() at :1888 binds it; DEC-0135 body repeats it); dedup_key docstring says only the reading remains
    but merged freqError fields stay in the key (:1988 before :2019); :1156 "only for EU band" above an
    always-true EU/US/NZ test with dead else branches; DEC-0024 cited for S24 code-review findings
    (rtldavis.py:1741, weewx_monitor.py:436, influx.py:591); DEC-0006 cited for the S48 cache bound
    (DEC-0053); DEC-0116 cited for a config revert (DEC-0117).
19. [R] pressure_service.py:41 `int(station_id)` raises on the example's `YOUR_STATION_ID`, so the
    "missing credentials, not binding" path is unreachable; :121 injects inHg with no usUnits check.
20. [R] influx.py:486-507 lease JSON that is a list/null/number raises AttributeError outside
    run_loop's try and kills the thread; docstring promises any failure reads as "not held".
21. [R] weewx_monitor.py duplication: db_reception_summary/db_battery_summary are one function twice;
    main() is 221 lines threading 11 `wu_*` locals through an 8-arg/6-tuple helper; second RECOVERY
    block (:1541) looks unreachable; `wu_pct` "single source of truth" bypassed by three inline formulas.
22. [R] ops duplication: `_marvinctl`/`_resolve_image`/`DB_QUERY` copy-pasted across campaign_analyze,
    freeze_baseline, stall_baseline; FIELD_MAP + line-protocol builder duplicated in backfill_influx /
    backfill_container; /proc sampler duplicated in proc_probe.py vs proc_probe_nas.sh.
23. [R] owm.py/windy.py share ~half their lines; one site-service/thread base plus a field-map loop on
    `to_METRICWX` removes the duplication and fixes item 4. windy.py:27 `get_queue` is dead.
24. [R] rtldavis.py CONCISE: 47-line QC block in `_data_to_packet` (`qc_value` unused, reject format
    duplicated, `check()` re-runs bounds); genLoopPackets ~150 lines with a duplicated reset block;
    [V] :2089 `data['windBatteryStatus'] = data.get(...)` is a no-op; ~225 hot-swap lines have no
    in-repo producer (rx_experiment.sh still restarts per swap).
25. [R] ops/find_duplicate_frames.py:17-35 describes pre-DEC-0135 Go behavior; its "transmitter
    repeats" count is now always 0.

## LOW — cosmetic

26. [V] rtldavis.py:2 `# coding: latin-1` while five lines carry UTF-8; the :1817 docstring reads "Â§4".
27. [V] SPDX gaps: pressure_service.py, dewpoint_service.py, usb_reset.sh, entrypoint.sh, Dockerfile,
    ops/*, scripts/* carry none while the other root modules do; weewx.conf.example (Keffer-derived) has
    no modification notice.
28. [R] `GPL-3.0-or-later` SPDX on influx/wcloud/ogoxe beside upstream text saying GPLv3 without "or
    later"; upstream weewx-wcloud declares no license. Not legal advice; worth a look.
29. [V] tests/test_input_staleness.py:195 `assert ... or True` is vacuous.
30. [V] patch/rtldavis-dupgate.patch applies at offset 0 / fuzz 0 to today's upstream tarball (Apple
    patch dry-run; reviewer agrees). The build-time "fuzz 2" did not reproduce — BOOT job 2 may be moot
    or GNU-patch-specific. Hunk headers' new-start numbers are off by 6 (cosmetic).
31. [R] ci.yml:69 mypy unpinned while pre-commit pins 1.11.1; dependabot watches pip only;
    .pre-commit-config:5-7 says "non-blocking" though CI lint is a required check.
32. [R, unverified] rtldavis.py:830 "US init 133 s": the Go formula (maxFreq+2)*loopPeriod gives ~149 s
    for this station's channel, <1 s under the 150 s watchdog. Check against real startup logs.

## Dropped after verification
- "REMEDY_MODE armed to restart_unit, unrecorded" — both unit copies and BOOT say `none`.
- Cross-referencer's "zero issue citations" and "no missing DEC ids" — both false zeros; redone by hand:
  29 issue numbers and 88 DEC ids all resolve to matching subjects (upstream #15 and dashboard DEC-0266
  are labelled as foreign).

## Verified clean
- Dockerfile COPY set = CONSTANTS deploy-layers table = `.dockerignore` allowlist; labels v2.0.17;
  Ubuntu 26.04 / Python 3.14 / weewx 5.5.0 / ruff 0.5.7 consistent across Dockerfile, CI, README.
- Header credits (Wall, Heijst, kobuki, Skahan) and §5(a) notices present where the inventory claims,
  except items 8 and 10. Go source line refs (main.go ~L394, protocol.go ~L218) hold.
- Driver constants (150/240 s, 500 ms, 16 tips, loop_times = idLoopPeriods) and every log string the
  monitor, soak_check, rx_experiment and tests grep for still match.
- Monitor: no shell=True; sqlite closed in finally; flock guard coherent (DEC-0151); SMTP verifies TLS.

## Tests
33. [V] tests/test_reception_pct.py — zero asserts: `check()` appends and prints, so its 5 tests cannot
    fail; `wu_pct` has no other test. (H)
34. [V] tests/ order dependence — `pytest tests/test_sensor_qc.py tests/test_hotswap_control.py` fails 3;
    reverse-sorted full suite fails 3 (532 pass). Cause: `rtldavis.weewx` binds to the first importer's
    stub (9 stubs lack `WeeWxIOError`) and `WD['escalated']` leaks between files. (H)
35. [R] tests/test_dup_time_gate.py:55, test_duplicate_frame_counter.py:122 re-implement driver logic
    inline; deleting the driver's guard (:2020) and marker (:1962) leaves 14 tests green. (M)
36. [R] tests/test_loop_json_writer.py:301 `__main__` block mid-file: the advertised direct run skips
    the 8 DEC-0093 tests; test_soak_check.py:50 module-level `pytest.skip()` without allow_module_level
    aborts collection when only BSD `date` is on PATH. (M)
37. [R] Boilerplate: own weewx stub in 27 files (1,220 lines, 11% of the suite), `sys.path.insert` in
    47, the `--test-alert` argv hack in 14, hand-rolled `__main__` runners in 44; no conftest.py. One
    conftest (path setup, one superset stub, autouse reset of wm.WD/EP/BLIND) removes this and item 34.
    Helpers duplicated under different names: `_make_driver` x5, `channels` fake x6, `_cacher` x3,
    WD-reset dict x4. (M)
38. [R] Test MISATTR: test_reception_full_outage.py:1 cites DEC-0154 (USB view) for the FULL OUTAGE
    class (DEC-0199); test_usb_forensics.py:1 DEC-0074 → DEC-0075; test_freeze_baseline.py:1 DEC-0083 →
    DEC-0085; test_loop_json_writer.py:136 DEC-0006 → DEC-0053; stale rtldavis.py line numbers in 4
    docstrings; "on the NAS" wording in 5 files. (L)
39. [R] Zero test references: windy.py, wcloud.py, ogoxeUploader.py, entrypoint.sh, 9 ops scripts, 4
    unit/timer files. (info)
