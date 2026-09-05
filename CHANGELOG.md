# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S124] — 2026-09-04 — DEC-0141 designed AND DEC-0142 executed the same night: InfluxDB serves from marvin since 22:35 ET; Foundation hosts no weather workload

- **Cutover (owner's call to go tonight, 22:08–22:43 ET):** stage 0 by marvin (MARVIN-DEC-0121);
  stage 1 dark-parallel from a live snapshot passed 22:07; Foundation `influxdb` TERM-stopped 22:13:35
  (`--restart=no`, retained as rollback); final stopped-server copy via `docker cp … -` to the
  marvin-data share; `weewx-influxdb.service` live 22:35:02; owner's four-file `sed` repoint; weewx
  restarted 22:40:42, first publish to marvin 22:43:16; dashboard repointed + `verify_archive_fresh.py`
  GO 22:46. Two Class C NAS mints, three owner-hands marvin lines. As-run record: runbook §8.
- **Open (S125 job 1):** 29-record `weewx`-bucket gap 22:14–22:42 (all in SQLite) — backfill deferred;
  `SuccessExitStatus=2` unit re-install; delete the two final tars from the share; pre-dump backup
  timer; ops/dashboard doc rows; drill section.
- **Deviations recorded (DEC-0142):** `docker cp` route instead of NAS `sudo tar`; `.rx-baseline` is at
  the tenant ROOT (runbook path was wrong — a `&&`-chained grep hid the fact the `sed` had worked);
  influxd exits 2 on SIGTERM; system buckets drop expired empty shards on first start; the 16 MB
  estimate was 9× low on bytes (152 MB tar) and right about the outage shape.
- `CONSTANTS.md` Infra + live-config rows rewritten for the new host (`server_url` row added, NAS rows
  say "nothing weewx runs"); `docs/INTERFACES.md` §2 drops the `weather-net` wording; ROADMAP P1.8
  stages 0–2 checked.

### Earlier the same session — the design (PR #334, merged 21:38 ET)

- **Why this session:** ops#260's sequencing put InfluxDB last; HLF (12:26 ET) and EHWD (~19:35 ET)
  both cut over today, ops posted the owner's ask for weewx's plan, and the owner opened this session
  on exactly that. Escalated Sonnet → Fable for the design.
- **`docs/INFLUXDB-MIGRATION.md`** (new): measured state (Foundation `influxdb:2.7` = engine
  v2.7.12, **16.4 MB / 64 shards** via the unauthenticated `/metrics`, 8086 LAN-published, data dir
  `0700 uid 1000`), the consumer table (all three already on marvin; HLF none), three stages, a
  ten-step cutover table with who-runs-what and what each step proves, rollback, what doesn't change.
- **`ops/weewx-influxdb.service`** (new): `weewx-influxdb` inside the weewx manifest globs,
  `influxdb:2.7.12` `--pull=never`, `--user 996:986`, `-p 8086:8086`, `weather.slice`, no secrets.
- **DEC-0141** — ten design points and their rejected alternatives (`backup`/`restore`, own tenant,
  uid 1000, floating tag, live pre-rsync, riders). Foundation's instance is retained stopped
  `--restart=no`; the store gets its first backup ever on marvin; the NAS-LEASE courtesy yield
  becomes moot on ship.
- **Two measurement traps recorded:** `nasctl ls` of the `0700 uid 1000` data dir returns an EMPTY
  listing (permission false-zero, GOTCHAS §1); the Foundation compose comment says "no host port" while
  `inspect` shows `8086 → 0.0.0.0`.
- `docs/ROADMAP.md` gains P1.8 (the decoupling's first roadmap line; tripwire still S126);
  `MANIFEST.md` ops/runbook row widened by one filename; `BOOT.md` rewritten S124 → S125 (job 1 = the
  move; ops#265 recorded as wired per the ops session's FYI).
- Cross-repo: [ops#270](https://github.com/WeatheredScientist/eaglehunt-ops/issues/270) filed as the
  move's ledger; ops#260's owner ask answered; marvin + dashboard sessions
  told directly (SOP).

## [S123] — 2026-09-04 — S122's closeout repaired; #320 fixed, #314 closed as overtaken (DEC-0140), #327 filed; BOOT.md back under cap

- **Closeout debt repaired first** (ops#218, third recurrence after S120): the `[S122]` entry
  below, `BOOT.md`'s pointer S122 → S123, and `docs/ROADMAP.md`'s P2 reconciliation line for
  DEC-0137→0139 (PR #326, `90797d1`). S122 gets no done-marker.
- **#320 fixed.** `CHANGES-FROM-UPSTREAM.md`'s Provenance row for the Go decoder said "unmodified"
  while the Dockerfile has applied `patch/rtldavis-dupgate.patch` since DEC-0135 — now "patched by
  us" with pointers (the `## rtldavis (the Go demodulator)` section already existed; the table row
  had drifted). `rtldavis.py` delta recounted per the file's own recipe: **+1204 / −166** (1422 →
  2460 lines), up from S97's +815 / −149; base tarball unchanged at 1422. Last-updated bumped from
  S54. The issue's "worth checking" question answered: the patched `main.go` carries **no GPLv3
  §5(a) notice** of its own — **#327** filed (Go source change, needs a build+deploy pass).
- **#314 closed as overtaken by #317 — DEC-0140, docstring-only.** The Sonnet first pass
  recommended raising the backstop to 150 + clamp; the owner escalated to Fable before
  implementation, and the re-read against `rtldavis.py:1684-1691` found #317's denominator already
  makes `rx <= 100` hold by construction *and* makes an absorbed multi-minute record read ~100, not
  200 — so the rule is correct on every campaign row, dormant post-v2.0.16, and over-excludes only
  in v2.0.15's ~13 h, where no campaign ran. Left as-is on purpose; `ops/campaign_analyze.py`'s
  docstring says why. (PR #328, `33fd982`.)
- **ops#264 remedied:** `BOOT.md` rewritten under STANDARD rule 1 — 2664 → **≈1993 tok** (chars/4
  under a UTF-8 locale, ops' `boot-cap-check` method), 80% of the 2,500 cap. Closes on the next
  green sweep; not closed by hand.
- ROADMAP: no line touched by DEC-0140 (`campaign_analyze.py` is not a P0–P3 item); tripwire at
  S126, not due.
- Gates, every commit: ruff clean · 475 passed / 17 skipped · mypy clean, 68 files · secret gate 0.
  Merges verified by `gh pr view --json state,mergedAt`, not by `gh pr merge`'s (silent) output.

## [S122] — 2026-09-04 — DEC-0139: #317 closed on production data; `v2.0.16` promoted to `main` (`prod-baseline-20260904`); README banner refreshed

- **#317 closed (PR #323, DEC-0139).** Read the 6-hourly `RECEPTION SUMMARY` log across the three
  windows spanning the `v2.0.16` cutover (20:29:06 EDT, 2026-09-03): 12:00–18:00 (fully pre-fix)
  197/360 (55%) over 100%, matching `BOOT.md`'s S121 figure exactly; 18:00–00:00 (spans the
  cutover) 86/358, already dropping; 00:00–06:00 (fully post-fix) **0 of 360** — every hour exactly
  100%, `dropped (est, lower bound)` 4 of 7,680. One clean window sufficed because
  `round((last − prev) / loop_time)` makes `count <= max_count` hold by construction — the fix is
  structural, not statistical. `docs/DATA_ERRATA.md`'s `DISC-0001` gets a second boundary.
  Completes the DEC-0135 → 0136 → 0137 → 0138 → 0139 verification chain.
- **`v2.0.16` promoted to `main` (PR #324), tag `prod-baseline-20260904`.** 267 commits (S75 → S122)
  of accumulated `dev` work promoted in one merge — the duplicate-decode fix (DEC-0134/0135/0136)
  and the slot-count denominator fix (DEC-0137/0138/0139).
- **`:v2.0.16` pushed to Docker Hub, 11:30 ET** *(backfilled by S123 from S122's transcript, marvin's
  S25 record and ops#266 — S122 wrote none of it down, and its BOOT pointer still said Hub was at
  `:v2.0.13`)*. Route: DEC-0078's own save/load/push, run once as a stopgap — owner `docker save`
  as root on marvin (`ssh marvin-sudo`; a raw `sudo -v` over ssh hung first, which became
  [ops#266](https://github.com/WeatheredScientist/eaglehunt-ops/issues/266)'s "no prompt means fail"
  SOP) → tarball to the laptop → `docker load` → `docker push` from the laptop. Digest verified by
  S122 via `manifest inspect` (`1a9daeb6…`) and re-verified by S123 against marvin's running
  container. `:latest` not moved. The durable self-service path is
  [ops#265](https://github.com/WeatheredScientist/eaglehunt-ops/issues/265) — filed the same
  morning, for the *next* release; ops' client half (OPS-DEC-0190) landed by 11:44 ET.
- **Public-release readiness audit ahead of the promotion** turned up two more findings, both
  filed rather than fixed inline: README.md had drifted three releases stale at `v2.0.12` (fixed
  same session, PR #325 — the version banner, driver tag, base-image weewx version, and
  changelog bullets for v2.0.13–v2.0.16, since `.github/workflows/dockerhub-description.yml`
  pushes this file to Docker Hub's public listing on every `main` push) and `BOOT.md` measured
  over its 2,500-token cap ([ops#264](https://github.com/WeatheredScientist/eaglehunt-ops/issues/264)).
- **Session never ran its own closeout** (ops#218 recurring pattern) — no CHANGELOG entry, stale
  `BOOT.md` pointer, no session title. Repaired retroactively by S123 (this entry); S122 gets no
  done-marker.
- Gate state not independently re-verified by S123 — S122's own PRs report clean gates (ruff,
  pytest, mypy, secret scan) at merge time; take that on the PR record, not re-run here.

## [S121] — 2026-09-03 — DEC-0138: `v2.0.16` built and deployed (31 s cutover); #317 stays open pending the metric-level proof

- **Closeout debt repaired** (ops#218): wrote DEC-0137, the `[S120]` CHANGELOG entry below, and moved
  `BOOT.md`'s pointer to S120 → S121 before starting new work (PR #321).
- **`v2.0.16` built and deployed.** Tree transport rode the same one-off owner-authorized path
  DEC-0136 used for v2.0.15 (`ops#257` is still open — no self-service checkout on the marvin
  tenant): local `git archive` of `dev`@`73acc3d` → `scp` to marvin (sha256-verified both ends) →
  owner `sudo tar` extraction (a second, distinct Class C wall — `marvin-admin` has no write access
  to the `t-weewx`-owned tenant root, found by hitting a plain `Permission denied` after the transfer
  step's own confirmation had already been spent). `marvinctl build` then ran self-service, no gate.
  Verified the artifact directly (`grep -n last_pkt_ts` inside the built image) before touching prod,
  not from the build pipeline's exit alone.
- **Cutover: 31 s** (`20:28:35` → `20:29:06` ET) — a same-host container recreate, not a rebuild
  wait. Container sha matches the build; driver banner unchanged (`0.20+ws.5`); `weewxd` published
  records within seconds; no `CRITICAL` since restart. DEC-0138 recorded.
- **#317 stays open** — deploy-verified, not yet metric-verified. Next: the 18:00/00:00 ET monitor
  email should show the pre-fix 55%-over-100% baseline reading ~0%; close #317 with that number and
  write `DISC-0001`'s second boundary in `docs/DATA_ERRATA.md`.

## [S120] — 2026-09-03 — DEC-0137: #317's fix lands on dev — rxCheckPercent denominates by ISS slots between received packets, not floor(wall-clock period / loop period); >100% becomes structurally impossible

- **#317 (driver).** `_update_stats` records each transmitter's last accepted-packet arrival time;
  `_update_summaries` denominates by `round((last − prev) / loop_time)` instead of
  `period // loop_time`, so `count[i] <= max_count[i]` holds by construction instead of relying on
  PR #315's after-the-fact clamp. Counter resets clear both timestamps so a discontinuity can't
  manufacture a spurious baseline. The 12:00–18:00 email measured the pre-fix scale directly: 197 of
  360 records (55%) read over 100%. `tests/test_slot_count_denominator.py` (new, 6 tests: the four
  synthetic cases from #317, the reset guard, a 500-period randomized invariant sweep);
  `test_reception_stats.py` + `test_issue_225_qc_fixes.py` reseeded to the new baseline. Squash-merged
  PR #319 → `dev`@`e158741`. Gate: ruff clean · 475 passed / 17 skipped (+6) · mypy clean, 68 files ·
  secret gate clean.
- **#317 stays open — deploy is the remaining half, not a formality.** A `dev` merge is a silent
  no-op in prod (driver is BAKED into the image). Remaining: tree transport to marvin (owner-run,
  `ops#257` — no self-service `git_branch`/checkout on the tenant yet) → `marvinctl build`
  (self-service) → unit image-tag flip (owner-run) → `v2.0.16` → confirm the 18:00/00:00 monitor
  emails on the new denominator → `DISC-0001`'s second boundary in `docs/DATA_ERRATA.md`.
- DEC-0137 recorded (owed since S119's clamp shipped tracker-only, no DEC).
- **Closeout debt (ops#218):** this session's code landed (PR #319, e158741) without running the
  closeout ritual — no BOOT/CHANGELOG/DEC update, no session title. Repaired retroactively by S121:
  this entry, DEC-0137, and the BOOT.md pointer rewrite below. S120 never wrote its own done-marker
  and does not get one now.

## [S119] — 2026-09-03 — #313: the reception summary clamps per-record rxCheckPercent at 100%, and the per-ID transmit interval is verified against Davis's own spec sheets

- **#313 (monitor).** `summarize_reception_rows()` clamps each record's rxCheckPercent at 100 before
  multiplying it out and counts the clamped records as `over100`; `format_reception_summary()`
  relabels `Packets dropped (est, lower bound)`, prints `Records reading over 100% (clamped): N of
  M`, and its footnote now says what the number is: the driver floor-divides the archive period by
  the loop period (60 s → 21, 59 s → 20) against 21.33 real transmissions/min, so a fully received
  minute reads 101–105% (~103% mean, measured since DEC-0135). The 06:00–12:00 email's "dropped
  −37" hours now read 0 and the total is a lower bound on real loss instead of pre-fix loss netted
  against post-fix over-count. Three new tests; the stale "applies no cap" claims in
  `ops/campaign_analyze.py` and its test docstring corrected. **Merged (PR #315, `bd499d3`, 13:46 ET)
  and deployed:** the merged file (sha `147f3eff…`) reached marvin at 16:10:38 ET by owner-run
  `curl` + `sudo install` (the tenant key is forced-command, so no agent transport exists), and the
  monitor restarted on it at 16:11:13 via self-service `marvinctl restart`. Verified by sha against
  dev's tip, process start after file mtime, and the S118 startup line appearing for the first time.
  The 18:00 ET summary is the first on the new format.
- **Per-ID transmit interval verified from primary sources** (the owner asked whether 2.8125 s could
  be a bad read of the docs). Davis's VP2 spec sheet (DS6152 Rev C, this station's product) states
  every sensor interval as N × (2.5 to 3.0 s) — temp/rain 10–12 s (4 slots), leaf wetness 15–18 (6),
  humidity/UV/solar 50–60 (20), soil moisture 62.5–75 (25) — ranges that exist only because the
  packet period runs 2.5–3.0 s across the eight IDs. (Davis's Vue sheet says outright "varies with
  transmitter ID code … (#1=shortest) … 3 seconds (#8=longest)", but it is a sibling product's
  document and its 2.25 s figure does not fit (41+ID)/16 — corroboration of the design, not this
  station's spec; owner correction via ops.) DeKay's RF-Protocol wiki
  (2.5 s at ID 0, +1/16 s per ID) and `lheijst/rtldavis` `idLoopPeriods` agree. Our S115 capture:
  303 receptions, all packet id 4, 292 single-slot gaps mean **2.8124 s, sd 1.0 ms**, span/2.8125 =
  294.00 = transmissions seen; a 2.5 s cadence would need 331 slots. (41+4)/16 = 2.8125 exactly; the
  ISS is on DIP ID 5 (`-tr 16` = "tr5"; "Transmitter 4" is the zero-based packet id). A period
  difference, not a phase offset: free-running transmit-only beacons cannot hold a phase, so only
  distinct periods bound collisions between co-sited stations.
- **DEC-0135's re-send model gets an independent check:** wind bytes changed in 33 of 213
  different-type consecutive pairs but 0 of 80 same-type pairs (fresh samples would have changed
  ~12), so the repeat is a verbatim copy, not a schedule coincidence.
- Filed **#314** (`campaign_analyze.py`'s `rx > 100` backstop now excludes most good minutes; split
  from #313, low priority). ops#256 closed on the ops side: the dashboard has no reception consumer,
  and HLF (measured locally) lists the field in a docs inventory only, no code reads it.
- **#316, found while locating the deploy target:** `ops/weewx-monitor.service:82` had
  `Environment=REMEDY_SYSTEMCTL=sudo systemctl` unquoted, which systemd parses as `sudo` and drops
  the second token (journal warning at every load since Aug 30, including the 07:58:59 start that
  armed `restart_unit`), so the armed remedy would have run `sudo restart weewx.service` and failed.
  Tracked file quoted in #315; live unit edited by the owner (`sed` + `daemon-reload`) and the
  monitor restarted at 16:20:49 ET. Before/after proof from one instrument: the startup line read
  `Remedy armed: sudo restart weewx.service` at 16:11 and `Remedy armed: sudo systemctl restart
  weewx.service` at 16:20, with no systemd warning at the second load. #316 closed.
  Also measured: marvin runs S107's `weewx_monitor.py` (sha `a6065f5f…`) — S118's #312 monitor
  change merged but never left the repo, so ops#257 limb 3 is closed-on-merge, not on-deploy.
- S118's entries sit under the [S117] heading below (its closeout was partial: `BOOT.md`'s resume
  header was left at "S117 → S118"); numbering resumes here at S119.

## [S117] — 2026-09-03 — DEC-0136: v2.0.15 deployed, `missed` 81 → 0 confirmed on production data, and the monitor's thresholds turn out not to be stale after all

- **DEC-0136 — DEC-0135 deployed.** `v2.0.15` built on marvin from `origin/dev`@`2fa80a4`. Prod cut
  over **07:17:53 EDT**, outage 07:01:44 → 07:17:53 (**16m09s**), gain unchanged at 372. Validation
  met every pre-registered number over a like-for-like 15:00 capture: `missed` 81→**0**, `repeat`
  0→**79**, `duplicate` 89→**6**, accepted 214→**274**, banner showing `dupWindow=500`.
- **Confirmed in production**, which S116 could not do. The prod instrument is the driver's own
  INFO frame counters — not `ARCHIVE_STATS`, which is DEBUG-level and absent at `debug_rtld=1`.
  Duplicate frames/period **6.23 → 0.57**, repeat frames appearing at **5.81**, population
  conserved (6.38 vs 6.23). So **91% of what the demodulator called a duplicate and discarded was
  a real re-send**, and 5.81 per 21.33 slots = **27.2% of transmissions**, against DEC-0134's ~27%.
- **`REMEDY_MODE` armed** `none` → `restart_unit` (07:58:59), in a second receiver-free step —
  together with removing a **stale `campaign.inhibit`** that had outlived its campaign by 2.5 days.
  `weewx_monitor.py` checks the inhibit at `:705` **before** the mode check at `:712`, so the flip
  alone would have been a **silent no-op**. The lifecycle documented at
  `ops/weewx-monitor.service:84` — "the campaign script creates this file for its duration" —
  **does not exist in any code**; nothing creates or removes it.
- **What `276` counts**, read from the upstream Go source rather than inferred: a hop is emitted
  only on an accepted packet or a loopTimer expiry, plus init. So **hops = accepted + missed +
  init**, reconciling both captures exactly (274+0+2 = 276; 214+81+2 = 297).
- **Two corrections to S116's own numbers.** (a) The apparent 85.6% slot-arithmetic shortfall was
  **cold-start acquisition**, not loss: 273 inter-arrival gaps, median 2.800 s, max 2.900 s, *zero*
  above 4 s, with **128 s** between `Init channels` and the first accepted packet. The steady-state
  window is 767.8 s, not 900 — 274 accepted against 273.0 expected is **~100%**. (b) A repeat falls
  through to the normal path and emits a `msg.ID=` line, so the 274 "decoded" **already include**
  the 79 repeats; unique payloads are **195**.
- **Reverses a standing assumption: the monitor's ~73% thresholds do NOT go stale.** Measured
  **15.38/21 (73.2%)** across the eight windows before vs **15.86/21 (75.5%)** across the seven
  after; a real +28% jump would read ~19.7 and be unmissable. The metric is `len(set(epochs))` —
  distinct one-second epochs, already counting freqError hop packets — so it saturates and is
  substantially **insensitive** to what was fixed (DEC-0024's mechanism from a new direction).
  `WU_RF_MIN_PCT = 60` stays valid. `DISC-0001`'s consumer list corrected accordingly; only
  `rxCheckPercent` consumers need re-keying, and prod computes that over a **wall-clock**
  denominator, never hops.
- **Four self-service gaps in the deploy path, all found by doing it:** no tree transport
  (`/srv/docker/weewx` is not a checkout, tenant has no `git_branch`; this release rode a one-off
  owner-authorized `scp -r` of a `git archive` export, 126 tracked files, sha256-verified on both
  ends), no image-tag control (a literal in a `0644 root:root` `ExecStart` — an `EnvironmentFile`
  carrying `IMAGE=` would fix it, deliberately not bundled since it hands a tenant control over
  what root launches), no config write, no ad-hoc archive read.
- **Verification note.** DEC-0078's `BUILD-EXIT` marker belongs to `ops/nas_build.py` and does not
  exist on the `marvinctl build` path, so the artifact was proven directly instead — `exec-ro`
  running `rtldavis -h` on the new image, at **zero outage**, printing `-dupwindow … (default 500)`.
  When the sanctioned proof does not cover the path taken, prove the artifact, not the pipeline.
- **`DISC-0001` given its real boundary timestamp** (2026-09-03 07:17:53 EDT) now that one exists.
- Gates: ruff clean · 466 passed / 17 skipped · mypy clean (67 files). Docs-only session — no
  production code changed in this repo.
- **Closeout tail:** PR #310 (this closeout, plus the ops#216 Finding-1 job filing) merged. ops#233
  (PWS alerting rebuild) closed on ops's recommendation — both asks demonstrated live during today's
  outage. ops#257 narrowed: limb 3 down to "no ad-hoc read" (S118 job 3 closes it); limb 2 blocked
  on marvin's own OPS-DEC-0159-class reading.
- **S118 issue triage.** `weewx_monitor.py` now logs `remedy_action()` at startup and `log()`s the
  reception-summary body it previously only emailed, closing ops#257 limb 3. `ops/soak_check.sh`
  excludes the six known entrypoint boot lines before counting `stdout_lines`, fixing #253's
  cry-wolf WARN — found in the process: the script still targets `NAS_HOST`, unverified against
  marvin since DEC-0118. `README.md` documents the DVB `dvb_usb_rtl28xxu` blacklist step (#216),
  in Quick Start and Troubleshooting. Repo #274 closed (fully resolved). Gates: ruff clean, 466
  passed / 17 skipped, mypy clean (67 files).

## [S116] — 2026-09-02 — DEC-0135: the duplicate filter is time-gated and the repeat suppressed one layer up; the fix unbiases the statistic, it does not improve reception

- **DEC-0135 — DEC-0134's fix, built (deploy pending).** Verified first the one alternative
  DEC-0134 had not ruled out: a stale buffer *replaying* a decode would have made the miss booking
  honest. Every decode carries its own correlation magnitude and 16-symbol vector — **80 of 80**
  long-gap duplicates have distinct ones, so they are fresh receptions on a different channel after
  a retune. The two populations sit at 2.1 ms and 2.8117 s (= `idLoopPeriods[4]`) with **nothing
  between 0.05 s and 2.5 s**.
- **Go** (`patch/rtldavis-dupgate.patch`, new): gate the byte comparison on `-dupwindow` (500 ms),
  advance `lastRecTime` only on acceptance, log survivors as `repeat packet:`. Ships as a tracked
  patch applied in the Dockerfile — not a fork, not a 3 MB vendor — so it is the smallest reviewable
  public diff, is the upstream PR verbatim, and **fails loud** if `weewx-contrib`'s unpinned
  `refs/heads/main` `src.tgz` moves.
- **Python**: `self._last_pkt` has been **dead code since it was written** — `data` carries
  `curr_cnt0..3`, cumulative counters that advance every packet, so the comparison was
  unconditionally true. Extracted as pure `dedup_key()` excluding them (metric untouched;
  `_update_stats` consumes them first), fixed the latent `NameError` in the `else` branch that
  becomes reachable now, added `repeat_count` so the suppression is measured rather than silent.
  **Suppress, not emit** (owner's call): the payload is byte-identical, so forwarding it would add
  ~37% loop packets/InfluxDB points/loop-JSON writes for no information.
- **It unbiases the statistic; it does not improve reception.** The data was always correct. The one
  candidate real benefit was checked and is not real — `chAlarmCnts` reached max 2 against a
  threshold of 51, so `maxmissed` re-inits are blocker 2, untouched.
- **Campaigns A–D demoted from settled-negative to untested**, and DEC-0134's "negative results
  remain valid as don't-re-sweep evidence" withdrawn as too strong: a flat result from an
  insensitive instrument is not evidence of flatness. Still not re-run — ~6 pts of headroom against
  DEC-0059's 2.0-pt bar, both mechanisms identified and neither gain-responsive. **Re-baseline by
  observation instead** (new standing watch); the real prize is that blocker 2 becomes measurable
  for the first time against a flat ~99% baseline.
- **ROADMAP tripwire pass (S116, next S126)** — heaviest since S66. P2's header rewritten to warn
  that every ~73–75% figure below it is a repeat fraction. Closed a ROADMAP item **open since S56 on
  a false premise**: `receiveWindow` "cannot be read from logs" was an inference from one verbosity
  level; it is 300, upstream default, confirmed three independent ways.
- **Build-host question answered:** `marvinctl build <path> -t <tag>` is a tier-2 own-resource verb —
  self-service, no NAS, no `docker save`/`load`.
- `docs/DATA_ERRATA.md` **DISC-0001** (not an `ERR`): `rxCheckPercent` steps ~73% → ~99% at the
  deploy — a metric-definition change, recorded so it is not later re-read as a real event. Names
  the stale-baseline consumers, including the wind guard proposed under `ERR-0004`/`ERR-0006`.
- `patch/` excluded from the whitespace-fixing pre-commit hooks — they rewrote the diff's context
  bytes on the first commit attempt and 1 of 5 hunks stopped applying.
- Gates: ruff clean · 466 passed / 17 skipped (+9) · mypy clean, 67 files (+1) · secret gate 0,
  self-test 54/54. Patched Go source **compiles** (real cgo build, positive-controlled); the 9 new
  tests are **mutation-tested 5/5**.
- PR #308.

## [S115] — 2026-09-02 — DEC-0134: the ~25% "loss" is the demodulator discarding the ISS's repeat packets as duplicates; real RF loss 0.3%. DEC-0133: RFI explains channels 46–48 (~2 pts); loss periodic in wall-clock time

- **DEC-0134 — blocker 6 RESOLVED.** Ran DEC-0133's designed capture (prod down 20:42–21:09 ET,
  26.5 min, self-service): `rtl_test` at the Go geometry — zero lost samples; the deployed
  `rtldavis` standalone with `-v` for 15 min — 295 hops, 81 misses (27.5%, prod's number with
  nothing but the binary in the loop) and **89 `duplicate packet` lines**, 89/89 byte-identical to
  the previous decoded packet, 84/89 one ISS interval later on the next channel, **80 of 81 misses
  preceded by one within 0.6 s**: the loop `continue`s on a duplicate without hopping and the
  pending timer books a miss 0.363 s later. Real loss 1/295. Explains every flat axis, the
  console's single-digit loss, the flat histogram, the wall-clock period. Fix = time-gated
  duplicate check (Go rebuild, S116). Full-band `rtl_power -i 1` kept for the RFI picture.
- **DEC-0133 (analysis).** Crossed S114's capture against DEC-0130's histogram with the ±134 kHz
  passband applied: exposure picks out exactly channels 46/47/48 (a ~400 kHz-comb FHSS neighbour);
  the cluster is ~2 pts; the other 48 channels sit flat. The 3,047 Sep-1 miss timestamps are
  periodic in wall-clock time (7.7495 s, z = 97; hop-locked alternative z = 4). Host stalls ruled
  out read-only. Owner confirmed the single-digit console receives this ISS at this property.
- Blocker 6 closed; `BACKLOG.md` ceiling item resolved and the fix queued as S116's lead;
  `docs/ROADMAP.md` line updated; GOTCHAS §1 (read `missed` with `duplicate`) and §3 (harvest a
  debug window whole — the Sep 1 received-packet lines had rotated away); upstream thread to draft
  logged in `docs/UPSTREAM-THREADS.md`. S111's entry rolled verbatim to `CHANGELOG-ARCHIVE.md`.
- PR #307 (this session's closeout).
