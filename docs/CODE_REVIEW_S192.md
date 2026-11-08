# Code review — S192a cruft audit, dev @ 8260094 (v2.4.0 in prod), 2026-11-08

**Status:** findings only; no code, doc or git object was changed or removed by this session. Filed
2026-11-08 as #550 to #564: 3 high (#550, #551, #552), 8 medium (#553 to #560), 4 low (#561 to
#564); items 17 and 18 are information only. The issue map is at the end. The coordinator (S192)
triages. Predecessors: `docs/CODE_REVIEW_S145.md` (DEC-0205, 39 findings, all
reported closed by S181), the S112 public-maturity audit (DEC-0127, `BACKLOG.md` "Public-maturity
push"), the S91 security audit (DEC-0101). Those findings are not re-derived here; where a piece of
one is still present it is listed under "Prior findings still open", not as new.

**Scope.** Cruft: anything the repo carries that no longer earns its place. (a) runtime code and
tests, (b) `ops/` and `scripts/`, (c) docs and the tier files, (d) git. Reference points: the NAS
era ended 2026-09-05 (`CONSTANTS.md` Infra); campaigns A to D are untested results (DEC-0135);
DEC-0072 makes a script's header its manual; STANDARD rule 5 makes a second copy of a fact a defect;
DEC-0014 (No-Rewrite Rule) decides whether a removal needs a DEC.

Method: six read-only enumerators (Sonnet, low effort: driver+extensions, monitor+services, tests,
ops+scripts, root docs+CI, docs/), every finding below re-verified by the main thread (Fable 5.1) with
the command shown or named. Gates green at start: pytest 833 passed / 24 skipped, ruff clean, mypy
clean on 104 files. The ops hub's `checks/boot-cap-check.sh` and `checks/tier-sweep.sh` were run
against this tree for the cap figures. Nothing remote was touched: no ssh, no marvin, no NAS.

Legend: [V] verified directly by the main thread. Severity is the cost of leaving it. "Chore" means
no DEC is needed under DEC-0014; "DEC" means removal changes a subsystem or a published contract.

## HIGH — loaded or run every session, or a latent exposure path

1. [V] `CONSTANTS.md` is ~9,000 tokens against a ~1,000-token member cap. `boot-cap-check.sh` reads
   36,010 chars (~9,002 tok) and fails it even against the hub's own 2,500 cap (OPS-DEC-0237 gives
   members STANDARD §1's ~1,000). Section bytes: Release / rollback 15,756; Deploy layers 11,552;
   Infra 4,782. Two table rows carry 9.4 KB between them: "Prod image" (line 106, 4,479 B) and
   "Docker Hub" (line 107, 4,968 B) are per-release narratives back to v2.0.15, each release's
   digests, build host, cutover time and first-record time, which `CHANGELOG.md` and the DEC bodies
   already hold (DEC-0204/0206/0208/0209/0227/0228/0229). `tier-sweep.sh` only measures BOOT and
   MANIFEST, so this never fired. No weewx DEC accepts a CONSTANTS carry
   (`grep -n CONSTANTS docs/DECISIONS.md | grep -i 'cap\|tok'` → DEC-0063 and DEC-0070 only). It is
   loaded at every session start. Chore (move text, never delete), recorded as a DEC-0063 addendum
   row since it changes what the tier file holds. `tier:mid`.
2. [V] The main checkout's local `main` points at pre-rewrite history. `git branch -vv`: `main`
   `8d4fd05` "[origin/main: ahead 328, behind 849]", dated 2026-08-11; its subject "Merge pull
   request #161" exists on `origin/main` as `0265621`, the DEC-0127 / DEC-0144 rewritten twin.
   `git log origin/main..main | wc -l` = 328. Those 328 commits are the pre-scrub objects both
   rewrites were made to remove, still reachable from a branch ref in the working clone (not in
   this worktree's checkout; the ref is shared). A plain `git push origin main` from it is refused
   as diverged; a forced one would re-publish the scrubbed history. Fix is a one-line owner chore in
   the main checkout (`git branch -f main origin/main`, then a prune), under DEC-0127's rule that
   history mutation is the owner's pen. `tier:cheap`.
3. [V] `tests/go/` (7 files, 984 lines) and the Go halves of `test_timegate_patch.py`,
   `test_burstgate_patch.py` and `test_crcstats_patch.py` run nowhere automatically. `ci.yml:47-51`
   installs only pytest and configobj; `grep -n 'golang\|librtlsdr\|setup-go' .github/workflows/ci.yml`
   → 0; `grep -n 'go test\|tests/go' Dockerfile` → 0. The three tests skip with "librtlsdr
   development files not installed (the Docker build covers this)", but the Docker build compiles
   the patched decoder, it does not run these tests. CI run 42435425331 on `dev` (2026-11-08):
   `860 passed, 24 skipped`, the same 24 that skip locally. The four Go gates DEC-0135, DEC-0216,
   DEC-0223 and DEC-0229 rest on tests that cannot fail in CI. Chore (a CI job with `golang` +
   `librtlsdr-dev`, or a test stage in the Dockerfile). `tier:mid`.

## MEDIUM — misleading to a reader, or carried weight with no reader

4. [V] The campaign apparatus contradicts itself. `ops/rx_experiment.sh:3` carries the RETIRED banner
   (#455) while `ops/weewx-rx-experiment.service:81-82` still launches it (`ExecStart=... rx_experiment.sh
   tick`) and :68 overrides `RX_BASE=/srv/docker/weewx`; the script's own :70 says "Production always
   uses the default" over :73's `/volume1/docker/weewx-rtldavis` default (S145 item 12, still present);
   its header :8 says "CURRENTLY LOADED: campaign B". `weewx-rx-experiment.service:35-41` is an
   `install -m 0644 ... /etc/systemd/system/` recipe with no "reference copy, lagging; heartofgold
   owns the deployed unit" label, unlike the three sibling units (S145 item 13, still present), and
   the timer's :4 sends readers to it. `tests/test_rx_experiment.py` (1,278 lines, 66 tests) skips 17
   of them permanently: `_require_campaign()` at :141-146 skips whenever the schedule table is empty,
   and it has been empty since DEC-0096. Deliberately kept in part: BOOT job 3 keeps the hot-swap
   driver code for a future gain campaign that would use this script converted (DEC-0117), so
   retiring the apparatus is a DEC. Fixing the headers to tell the truth is a chore now.
   `tier:mid`.
5. [V] `MANIFEST.md` and `docs/handoffs/`. The hub check reads MANIFEST at 4,906 chars (~1,226 tok),
   past the 1,094 OPS-DEC-0102 accepted as a carry (and the 1,000 cap). Line 5 says "Check size with
   `boot-cap-check.sh`", a script that exists only in the private ops repo
   (`~/Projects/eaglehunt-ops/checks/`); a public reader has nothing to run (`docs/GOTCHAS.md:100`
   has the path, MANIFEST does not). Line 42 says `docs/handoffs/` holds "retired handoffs that live
   docs cite by path": `grep -rl` over tracked `*.md`/`*.py`/`*.sh` excluding the archives finds
   S38 cited by MANIFEST only, S37 by S38 only, S36 by nothing live (one `history_scan_known.txt:7`
   secret-scan row), S71 by nothing. Three of four are orphans. Chore. `tier:cheap`.
6. [V] `docs/GOTCHAS.md` §3 "NAS and campaign operations" (:230-372) carries about ten NAS-only
   traps with no historical marker: `nasctl` read-only semantics (:232-240), "`rx_experiment.sh` reads
   hardcoded NAS-only paths ... verify with `nasctl cat`" (:248-253), the NAS project-root file
   layout (:254-256), the Synology ACL `chmod` trap (:302-306). `grep -n -i 'historical\|retired' docs/GOTCHAS.md`
   → one hit (:291, unrelated). MANIFEST loads §3 "before any NAS, marvin or campaign task", so the
   retired half is read with the live half. DEC-0105 created the file as the home for durable traps;
   a "NAS era (retired 2026-09-05)" subsection or an ARCHIVE move is within that design. Chore.
   `tier:cheap`.
7. [V] `BACKLOG.md` (935 lines) carries resolved and demoted material in full. 17 lines carry ✅
   (`grep -c`), their blocks total about 190 lines (the longest :673-702, 30 lines); the NAS-era USB
   watchdog evidence (:176-255, about 50 lines) and "Durable RF findings ... DEMOTED S116" (:752
   onward, about 140 lines) are kept whole; it cites `ops/reception_service.py` (:38),
   `ops/usb_watchdog.sh` (:202, :228, :233) and `docs/STATUS.md` (:9), none of which exist, each
   narrated as removed. STANDARD rule 1: a conclusion survives as one line. Chore: move the bodies
   to `CHANGELOG-ARCHIVE.md` or `ARCHIVE/` verbatim (`scripts/check_secrets.sh` over anything
   rehomed). `tier:cheap`.
8. [V] Adopter-facing staleness. `README.md:141` "Data contract `loop_json_writer/1.0.0`" and :142
   "`loopjson-v1.0.0`" while `loop_json_writer.py:80` is `1.1.0` and `git tag -l 'loopjson-v*'` has
   `loopjson-v1.1.0`; :149 "v2.0.x runs Ubuntu 26.04, Python 3.14 and WeeWX 5.5" as the current
   statement for a v2.4.0 image on 5.5.2; :112 "Python 3.12+". `CONTRIBUTING.md:33-34` says a `lint`
   job runs "`ruff check` + `ruff format --check`; `mypy` runs advisory-only" (ci.yml:74 says there is
   no format gate, DEC-0027; `.pre-commit-config.yaml:6` says mypy is required) and :29 offers
   `for f in tests/test_*.py; do python3 "$f"; done`, which runs nothing since S178 removed the
   `__main__` blocks; `AGENTS.md:47-51` explains that the gate list lives once in CONVENTIONS for
   exactly this reason, and this is the surviving drifted copy (S112 session A item, still open).
   `docs/QUICKSTART.md:39` links `DEPLOY.md#host-preparation`; DEPLOY.md's headings are systemd,
   Synology NAS, Monitoring. `docs/DATA_ERRATA.md:4` and :53 link `DECISIONS.md#dec-0025-…` and
   `#dec-0021-…`; those headings are in `DECISIONS-FULL.md:420` and :234, DECISIONS.md has table
   rows. `docs/INTERFACES.md:137` "lands in prod with v2.0.14" in the future tense. Chore.
   `tier:cheap`.
9. [V] The NAS-LEASE courtesy yield is a permanent no-op that still ships. `influx.py:266-300` and
   :483-510 (about 40 lines, 24 `lease` hits) implement it behind `lease_dir`; `CONSTANTS.md`'s
   `lease_dir` row says "moot since DEC-0141: weewx has no NAS I/O left to yield ... a permanent
   no-op", and `BACKLOG.md:660` says "the cross-host wiring this item asked for will never be
   built". `ops/nas_build.py` (RETIRED banner) is the holder side; `tests/test_nas_build.py` (14
   tests) and `tests/test_influx_lease_yield.py` (12 tests) pin both. The code is in the public
   `extensions/influx` release and in a mounted prod file, so removal is a DEC (DEC-0014), with
   the `lease_dir` key dropped from the live conf in the same change. `tier:frontier`.
10. [V] `ops/wxcheck.py` and `ops/wxcheck.sh` have no header at all (DEC-0072: the header is the
    manual; `grep -c '^#' ops/wxcheck.py` → 1, the SPDX line). `wxcheck.py:4` opens
    `/opt/weewx-data/archive/weewx.sdb`, an in-container path, but nothing copies it into the image
    or the tree (`grep -rn wxcheck Dockerfile docker-compose.yml entrypoint.sh` → 0). The shell
    wrapper runs `docker exec weewx-rtldavis-v2` directly, which does not reach marvin from the
    laptop (`marvinctl --tenant weewx exec` is the route), and reads `WU_*` env that no example
    declares. Only citer: `docs/DATA_ERRATA.md:355`, historical. The shell file is name-protected by
    the secret-read guard (its 2026-07 history), so this session did not read its body; the
    enumerator did. Chore: header plus a `marvinctl` route, or retire. `tier:cheap`.
11. [V] Stale status framing in on-demand docs. `docs/INSTALL-RESEARCH.md:5-6` "written as it would
    read once the proposals below ship", :8 "Not touched: v2.1.1 release prep", :190 "Scope of
    v2.2.0: ... or A plus G first?" (answered by v2.2.0 and v2.3.0, DEC-0227/0228); MANIFEST still
    calls it "the ranked v2.2.0 proposal". `docs/ASSESSMENT.md` is stamped 2026-07-05 (S23) and
    still says the handoff is "trapped in Claude-private memory" (:42) against a STATUS.md-era
    table (:25); MANIFEST loads it for "weighing a decision". `CHANGES-FROM-UPSTREAM.md:4` "Last
    updated: 2026-10-18 (S158)" beside rows dated 2026-10-29 (:237, :254, :277-278); :68 "2571
    lines" and :70 "2494" against `wc -l rtldavis.py` = 2703 (S145 item 10 residual).
    `docs/CAMPAIGN-B-RUNBOOK.md` (RETIRED) and `docs/INFLUXDB-MIGRATION.md` (EXECUTED) sit in
    MANIFEST's row "any ops task, swap night, InfluxDB cutover", and `GOTCHAS.md:10` calls the
    runbook a doc that "describes what things are". `docs/UPSTREAM-THREADS.md` has no "Last
    updated" line though BOOT job 1 requires it kept current. `docs/ARCHITECTURE.md:119` gives the
    restart as "`docker kill` + `docker start`"; marvin's is `marvinctl restart weewx.service`.
    Chore: an INFLUXDB-MIGRATION-style status line on each. `tier:cheap`.

## LOW — cosmetic, or harmless until someone reads it

12. [V] Version ledger in the driver header. `rtldavis.py:43` "It reports itself as DRIVER_VERSION
    '0.20+ws.7'" while :233 is `'0.20+ws.10'` (BOOT job 6 confirmed). The changelog at :57-129 has
    no `ws.7 -> ws.8` row: :123 `ws.6 -> ws.7` is followed by :126 `ws.8 -> ws.9`; ws.8 landed in
    `f621946` (2026-10-28, #496). Chore. (Filed with 13.)
13. [V] Small code cruft. `seed_config.py:21` `ENV_VARS` is defined and never read
    (`grep -rnw ENV_VARS --include='*.py' .` → the definition). `rtldavis.py:1294` and :1320
    `if self.frequency in ['EU', 'US', 'NZ']` are always true after :1557's `raise ValueError`, so
    the `else:` at :1337 (`dbg_rtld(3, "Don't store freqErrors ...")`) and its twin cannot run (S145
    item 18: the comment was fixed, the branches kept). `Dockerfile:164-166` comment ends "v2.0.4"
    above the COPY of today's driver (S112 session B item, still open). `weewx.conf.example:261`
    "To enable this uploader, set enable = True below" sits under `enable = true` at :253, and :258
    cites "weewx-5.2.0"; `[Rtldavis]` shows no `hotswap_control_file`/`hotswap_ack_file`,
    `log_humidity_raw`, `sensor_map`, `path` or `ld_library_path` though `rtldavis.py:1534-1607`
    reads them (S145 item 17 residual on the hotswap keys). `weewx_monitor.py:631` and :705 tell
    the escalation-email reader not to use "the NAS docker-compose.yml"; :1435 logs "set
    REMEDY_MODE=usb_reset to keep the USB reset on Synology" at every start without the variable;
    :162-163 keeps Synology's `/usr/local/bin/docker` as the `DOCKER_BIN` last resort. Chore.
    `tier:cheap`.
14. [V] `ops/` and `scripts/` literals and headers. `ops/proc_probe.py` has no RETIRED banner while
    `proc_probe_nas.sh:3` and `proc_probe_watch.sh:3` do, and exits at :179 unless `NAS_PORT`/
    `NAS_USER`/`NAS_HOST` are set. `ops/soak_check.sh:21` example `v2.0.17`, :52 and :58 fallback
    `v2.0.20` (the stamp-derived default is live, S145 item 7 fixed; the literals lag).
    `ops/marvinctl_util.py:28` docstring example `v2.0.16`. `ops/campaign_analyze.py:132` "`nasctl
    grep` prefixes a line number" where :355 reads through `marvinctl`. `ops/backfill_influx.py:7`
    usage shows `--token YOUR_TOKEN` as the way in; :113 defaults it from `INFLUX_TOKEN`.
    `ops/find_duplicate_frames.py:51` usage names `/var/log/weewx/weewx.log`, a path no deployment
    has, and :20-35 describes pre-DEC-0135 decoder behavior under a STATUS note. `ops/nas_build.py:16`
    and :19 `v2.0.14` (RETIRED file; listed for completeness). Chore. `tier:cheap`.
15. [V] Git hygiene. `git branch --merged dev` lists 14 merged local branches (`s179-*` ×2,
    `s180-closeout`, `s183-*` ×2, `s184-*` ×7, `claude/s180*` ×4; sampled PRs #504, #506, #517, #521
    are merged); `git branch -r --merged origin/dev` lists 30 merged origin branches (the same plus
    `s181-*` ×3, `s185-*`, `s186-*`, `s187-*` ×5, `s189-timegate`, `s190-*` ×3; #515 and #543
    merged). Tags are identical local and remote; `backfill-v2.0.20` persists on both although
    `image-publish.yml:18-20` says "delete it once the image is published" (done 2026-10-17) and
    `CONSTANTS.md:107` says the trigger tag "is gone". `git worktree list` shows
    `.claude/worktrees/s189-timegate` still checked out at `d97de63` on the merged `s189-timegate`
    branch; the `s180c-…` directory BOOT job 6 flagged is live again as this session's worktree, so
    it is no longer stale. `git count-objects` warns of garbage at
    `.git/worktrees/s180c-audit39-uploader-tests-0d3322/refs` (64 B). Chore, owner-run in the main
    checkout (never from a worktree): delete merged branches local and remote, drop the backfill
    tag, prune the worktree. `tier:cheap`.
16. [V] Test boilerplate residuals (S145 item 37). `def _make_driver` is re-defined in
    `tests/test_slot_count_denominator.py:45` (wraps conftest's `make_driver`) and
    `tests/test_reception_layer_b.py:26` (its own); `_make_driver = make_driver` aliases in three
    files and three cross-test imports of the alias (`test_burst_gate_counter.py:13`,
    `test_crc_stats.py:12`, `test_dup_time_gate.py:24`); the `--test-alert` `sys.argv` hack is in
    17 files (`grep -l test-alert tests/*.py`, up from 14); `sys.path.insert` outside conftest in
    `test_doctor.py:15` and `test_seed_config.py:15`; "on the NAS" wording in `test_nas_build.py:12`
    and `test_usb_forensics.py:74`, :210 (item 38 residual). `test_issue_226_cli_fixes.py:90, :96,
    :137, :150` and `test_loop_json_writer.py:435` have no assert (call-only "must not raise";
    legitimate, listed as info). 24 skips are permanent in CI: 17 campaign stand-down (item 4), 3
    librtlsdr (item 3), 4 "real weewx not installed" in `test_loop_json_extra_names.py`. Chore.
    `tier:cheap`.
17. [V] `.gitignore` and local debris. `.gitignore:57-60` "OS / Synology cruft" (`@eaDir/`,
    `#recycle/`), :46-51 dashboard-artifact patterns, :26-28 NAS-era conf backup patterns; all
    harmless. This worktree's ignored `.claude/settings.local.json.bak-20260715`. Info; no issue.
18. [V] Tier shape. `BOOT.md` is at 92% of its cap (9,295 chars, ~2,323 tok), fine. The hub check
    also wants a `## Style` section; OPS-DEC-0207 makes section shape per-repo, so advisory. Info.

## Deliberately kept — looks dead, is not cruft

- **Hot-swap driver code** (`rtldavis.py:941-1044`, :1604-1625, :1983-2073, :2135-2149; about 230
  lines). No in-repo producer of the control file (`git ls-files | xargs grep -nEi 'hotswap|control_file'`
  outside the driver, tests and docs → prose only); kept by BOOT job 3 for the gain campaign
  `BACKLOG.md:566` carries, pending the owner's DEC either way.
- **#475** (portable QC) parked on purpose (BOOT "What's settled").
- **`influx.py` Python 2 shims and unused imports** (:164-193 `try/except ImportError`, `base64`,
  `socket`, `sys`, `http_client`, `Request`, `URLError`, `accumulateLeaves`, `BadStatusLine`):
  `ruff.toml` ignores `E402`/`F401` for this file on purpose "so a mounted file's bytes do not change
  for a lint rule" (#455, S158). Same for `wcloud.py`'s lint exclusion (upstream's file).
- **weewx API entry points with no in-repo caller**: `rtldavis.py:640` `confeditor_loader`, :1976
  `closePort`, :1980 `hardware_name`; `check_weewx_version(minimum_major=3)` at :246 and
  `influx.py:204-208` `REQUIRED_WEEWX` (upstream conventions, always pass on 5.x).
- **Synology adopter path**: `docs/DEPLOY.md:73-89` and :108-135, `REMEDY_MODE=usb_reset`
  (`weewx_monitor.py:123`), `usb_reset.sh`, `monitor.env.example:11-13`. Not this station's path
  since DEC-0118, but a documented alternative for a Synology adopter; DEPLOY says the non-root form
  is "untested on DSM".
- **`CAMPAIGN_INHIBIT`** reader with no writer (`weewx_monitor.py:143`): `ops/weewx-monitor.service:119-122`
  says so explicitly (S145 item 13 fixed).
- **`prod-baseline-*` and `v2.0.7`+ tags that are not ancestors of `dev`**: they point at `main`'s
  merge commits, which is the branch model (DEC-0011), not drift.
- **The s180c worktree directory**: reused by the coordinator for this session; live, not stale.

## Prior findings still open (not re-filed as new; residuals the S145 status line "Nothing open" overstates)

S145: 10 (CFU stamp and line counts, in 11 here), 12 (`rx_experiment.sh:70`, in 4), 13
(`weewx-rx-experiment.service` recipe, in 4), 16 (`monitor.env.example` documents 4 of the 23 env
keys `weewx_monitor.py` reads: `ALERT_FROM`, `ALERT_TO`, `GMAIL_PASS`, `REMEDY_MODE`; 17 undocumented
including `WEEWX_LOG`, `WEEWX_ARCHIVE_DB`, `WU_RF_EXPECTED`, `INPUT_STALE_S`), 17 (hotswap keys, in
13), 18 (dead else branches, in 13; DEC-0024 still cited for Layer B at `rtldavis.py:1373, :1600,
:1752, :1761, :1923, :2201` and `loop_json_writer.py:58` cites DEC-0006 for the DEC-0053 cache bound),
31 (pre-commit mypy `v1.11.1` vs CI `2.3.0`, BOOT job 6; dependabot pip-only), 37 and 38 (in 16).
S112 session A: CONTRIBUTING's CI description (in 8). S112 session B: upstream `/home/pi/work/bin/rtldavis`
defaults in `rtldavis.py:146, :265, :267, :1397` (:267 is the live `DEFAULT_CMD`); `Dockerfile` "v2.0.4"
(in 13).

## Dropped after verification (enumerator claims that did not hold)

- "No `backfill-v*` tag exists": `git tag -l` and `git ls-remote --tags origin` both list
  `backfill-v2.0.20` (item 15). A false zero.
- "`S38-cross-repo-architecture.md` is not in the repo": it is, at `docs/handoffs/`.
- "`docs/INFLUXDB-MIGRATION.md` links a wrong path `influx/README.md`": the text says "dashboard
  `influx/README.md`", a file in the dashboard repo. Not broken.
- "`image-publish.yml:114` `tools/scripts/smoke_image.sh` may not exist": the workflow checks the
  repo out twice, at `tools` (:67) and `src` (:74). Resolves.
- "`loop_json_writer.py` docstring default disagrees with the code": the docstring says a relative
  path resolves against `WEEWX_ROOT`; `:198` joins `root` with `loop-data.txt`. Consistent.
- "`ops/marvinctl_util.py` has zero references": imported by module name in `campaign_analyze.py:101`,
  `stall_baseline.py:75`, `freeze_baseline.py:89` (the enumerator caught its own false zero).

## Verified clean

- Version literals agree where they are meant to: image `v2.4.0` (Dockerfile:3, docker-compose.yml:18,
  `examples/systemd/weewx-rtldavis.service:8, :32`, `scripts/host-setup.sh:26`), `DRIVER_VERSION`
  `0.20+ws.10` (:233), `influx.py` `0.20+ws.2` (:12, :203, `extensions/influx/install.py:13`),
  writer `1.1.0` (`loop_json_writer.py:80`, `extensions/loopjson/install.py:10`), `weewx==5.5.2`
  (`requirements.txt:10`, `weewx.conf.example:25`, `prove_*.sh:5`).
- Every Dockerfile ARG and COPY is used; the COPY set matches CONSTANTS' deploy-layers table.
- Every script a workflow calls exists; every `workflow_dispatch` input is read; tag patterns match
  real tags. `dockerhub-description.yml` and `ci.yml` reference nothing retired.
- No `if False`/`if 0`, no commented-out code blocks, no line-number citations in any scoped Python
  file. No `/volume1`, `synousb`, `nasctl` or `docker stop` in runtime code (`weewx_monitor.py`,
  `usb_reset.sh`, `entrypoint.sh`, `doctor.py`, `seed_config.py`, the uploaders, the services).
- `QUICKSTART.md`, `DEPLOY.md` and `INTERFACES.md`: zero hits for marvin, tenant, `t-weewx`,
  `marvinctl`, `nasctl`, `/srv/docker`, Foundation (Synology appears as an adopter option only).
- Tests: no stale imports or monkeypatched names against the modules under test (0 of the attribute
  names patched are missing); no `xfail`; no `__main__` runner blocks (item 36 fixed); one
  `sys.path.insert` in conftest as designed.
- Local tags equal remote tags (`comm -3` empty).

## Not verified

- `ops/wxcheck.sh`'s body (name-protected by the secret-read guard; enumerator evidence only).
- Docker Hub's live tag list (out of scope; the repo's own claims were checked against git only).
- Test order dependence (S145 item 34): the default-order run is green; reverse order not re-run.
- Whether the 328 pre-rewrite commits on local `main` contain the scrubbed identifiers themselves
  (not read on purpose; DEC-0127 and DEC-0144 say that history was rewritten to remove them).

## Issue map

| Items | Issue | Number | Tier |
|---|---|---|---|
| 1 | CONSTANTS.md nine times its cap | #550 | mid |
| 2 | local `main` on pre-rewrite history | #551 | cheap |
| 3 | Go tests run nowhere automatically | #552 | mid |
| 4 | campaign apparatus contradictions, 17 permanent skips | #553 | mid |
| 5 | MANIFEST past its carry, orphan handoffs | #554 | cheap |
| 6 | GOTCHAS §3 NAS-only traps unmarked | #555 | cheap |
| 7 | BACKLOG resolved and demoted bodies | #556 | cheap |
| 8 | adopter-facing staleness (README, CONTRIBUTING, anchors) | #557 | cheap |
| 9 | NAS-LEASE yield, a permanent no-op that ships (DEC) | #558 | frontier |
| 10 | the two `ops/wxcheck` scripts: no header, unreachable | #559 | cheap |
| 11 | stale status framing in on-demand docs | #560 | cheap |
| 12, 13 | driver header ledger and small code cruft | #561 | cheap |
| 14 | ops/ literals and headers | #562 | cheap |
| 15 | git hygiene | #563 | cheap |
| 16 | test boilerplate residuals | #564 | cheap |
