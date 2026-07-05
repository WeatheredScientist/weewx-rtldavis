# Status — weewx-rtldavis

**In-flight working state (what's on the bench right now).** Read first at the start of a session,
update last before finishing. ROADMAP.md holds the full prioritized plan; this file holds only what
is actively in motion, parked, or needs a check.

- DECISIONS.md records *settled* decisions. **This file records open ones.**
- CHANGELOG.md records *shipped* work. **This file records work not yet shipped.**
- **This file is the single source of truth for the current session number and the next-session
  handoff** (DEC-0023). Every other doc — and Claude memory — points *at* this; none carries its own
  copy. Handoff state lives here (in the repo, visible on GitHub), never only in private memory.

When something here becomes permanent (a decision is made, a feature ships), move it to
DECISIONS.md / CHANGELOG.md and delete it here. Keep this file short.

> **Current session: S30** (2026-07-05) — shipping v2.0.3, and found the reason the driver fixes never
> took. **Major finding: weewx imports the driver from the BAKED venv `site-packages/user/`, and
> `Dockerfile:101` was clobbering the patched `rtldavis.py` with the STOCK `weectl extension install`
> copy** — so every built image shipped the stock driver (no rain filter, no H1/H2/M3), and driver
> "hot-swaps" to `weewx-data/bin/user/` never took effect (that path isn't imported). Confirmed on the
> running container three ways (weewx path resolver, `.pyc` only in the venv dir, content grep: live
> driver lacks `rain_delta_tips` + carries the deadlocked H2). **This single bug explains both open
> mysteries: `rxCheckPercent` NULL (stock `pct_good_all` deadlock) AND the July-4 phantom rain (no live
> rain filter).** Fixed the clobber (1-line). **v2.0.3 build inputs now committed to `dev`:** dewpoint
> **wind honest-null** (ported from the reviewed Jun-16 draft; wind is in every Davis packet so no dropout
> — temp/hum/rad/UV keep carry-forward per DEC-0022), **receiveWindow reverted to upstream default** (drop
> the unproven rw350 patch), Dockerfile **clobber fix** + v2.0.3 header, +5 tests (**suite 54/54**), docs
> corrected. **✅ Built (native amd64 on the NAS), deployed to prod, and CONFIRMED:** `rxCheckPercent`
> went NULL→**70–82%** within two archive cycles (alive for the first time since 2026-06-18 — the clobber
> fix works). Packets flowing, clean dongle handoff, old `rw250-test` image kept for rollback. **Remaining
> (owner-approval-gated): promote `dev`→`main` + tag v2.0.3 → GitHub release → Docker Hub push.** Governed
> lineage: S16→…→S28→S29→**S30**.
>
> **Owner priority (S30):** root-cause temp/humidity/radiation/UV spikes as **bad RF packets** (same class
> as the rain glitch) rather than StdQC/carry-forward bandaids — a dedicated future session (after v2.0.3),
> with a model suited to deep RF-decode debugging (BACKLOG §Data integrity; DEC-0022).

_Last updated: 2026-07-05 (S30 — v2.0.3 assembly + the clobber discovery. Committed to `dev`: dewpoint
wind honest-null, receiveWindow→upstream default, **Dockerfile clobber fix** (weewx imports the baked
venv driver; `Dockerfile:101` was shipping the STOCK driver over the patched one → rain filter + H1/H2/M3
never live → explains rxCheckPercent NULL + the July-4 phantom), v2.0.3 header, +5 tests (suite 54/54),
ARCHITECTURE §3 corrected (driver is BAKED not mounted). Build/deploy/promote/release remain owner-run.
**Correction to prior S28/S29 notes:** the driver fixes were NOT actually live — the rain-fix "hot-swap"
targeted `weewx-data/bin/user/`, a path weewx does not import; the rebuild makes them live for real.)_

_Prior S28: unblocked follow-ups. **P1 verified (read-only, live):** rain-watch
grep = **0** `rejecting implausible counter delta` events across the full log range (2026-06-05 → now),
so v2.0.3 stays parked; reception Layer A confirmed live (WINDOW 88–100%, 5-window avg **91–92% [OK]**,
0 bad windows), monitor healthy. Layer B signature still live (driver emits `RAW_CHANNEL_PAYLOAD`/
`FreqError` + double-publishes the same epoch). **M-A + L-B:** rewrote `weewx_monitor.py`'s log read as a
single byte-offset `seek()` (`get_log_size()` + `get_new_lines(offset)`), killing the twice-per-poll
whole-file re-read (M-A) and the double-open race (L-B) — **draft PR #10 → `dev`**, suite 40/40,
secret-scan green, **not yet deployed** (owner-gated scp + `sudo kill`). **Housekeeping:** deleted merged
remote branches `s20-governance-hardening` + `feature/influxdb-grafana` (Grafana retired for Influx; its
wind-warmup fix `3f5470f` was already in `dev`); `s27-p3-deployed` was already auto-deleted on #9's merge;
remote-URL casing already correct. Prior: S27 — secret gate landed + required, review stack collapsed onto `dev`.)_

---

## Active thread

> **▶ Resume here (S30 → S31).** v2.0.3 build inputs are committed to `dev` (see **"Next session actions"**
> below for the remaining owner-run build/deploy/release steps + the exact NAS run config). **Key S30
> correction:** the driver fixes (rain filter, H1/H2/M3) were **never actually live** — weewx imports the
> baked venv driver, `Dockerfile:101` clobbered it with the stock copy, and the "hot-swaps" went to a
> non-imported path (`weewx-data/bin/user/`). The v2.0.3 rebuild makes them live for the first time. The
> older items below are retained for history (some describe the pre-correction understanding):
> 1. **Review + merge + deploy PR #10 (M-A/L-B).** Same monitor-restart deploy as Layer A (owner): scp
>    `weewx_monitor.py`, `sudo kill <pid>` (pidfile `logs/weewx_monitor.pid`); the esynoscheduler wrapper
>    respawns on the new file (≤5 min). Independent of the release. Confirm "Poll: N new lines" keeps
>    flowing and reception stays ~90%.
> 2. **Watch for the first real rain glitch in the wild** — confirms the S18 fix + alert together (log
>    "rejecting implausible counter delta" + clean archive + the email to `ALERT_TO`). Calendar-bound
>    (~1 glitch/2–3 wk). Checked 2026-07-05 (S28, read-only): **0 to date** across the full log range.
>    The fix is live in prod via hot-swap; this watch gates only the *formal* release — an optional
>    confidence gate, not a safety one (could cut v2.0.3 now on tests + live evidence if desired).
> 3. After the glitch rides clean (or if the confidence gate is waived): **promote `dev` → `main` + tag
>    v2.0.3** (release on GitHub + Docker Hub), folding in the pending baked honest-null dewpoint rewrite
>    **and the S24 driver fixes H1/H2/M3** (both need an image rebuild — bigger deploy than a hot-swap;
>    plan it). When H2 ships, **live-confirm `rxCheckPercent` starts populating** (`SELECT rxCheckPercent
>    FROM archive …` — expected all-NULL now).
> 4. Then, in a later session, **DEC-0022 sensor-QC hardening** (below).
>
> _Numbering note (DEC-0023): the "shared lineage with the dashboard" (DEC-0013) never held — the
> sibling runs its own S1→S40 counter and never shared one. This repo counts **independently**:
> S16→…→**S26**→**S27**→**S28** (this session). Cross-repo refs are prefixed (`weewx S28` vs `dash S40`)._

## Open threads (not yet shipped)

- **Reception metric ~150% — Layer A DEPLOYED + CONFIRMED (S27, DEC-0024).** Root cause: the daily
  RF-Reception email over-counted because `weewx_monitor.py` counted raw `Wunderground-RF: Published`
  log lines, but the driver publishes freqError freq-hop packets as duplicate publishes of the SAME
  record epoch (~1.66×). **Layer A fix** (`wu_record_key()` epoch-dedup) merged to `dev` via #5 and
  **deployed live 2026-07-05**: scp'd the new `weewx_monitor.py` (backup `weewx_monitor.py.bak-20260705-141508`
  on NAS), `sudo kill`ed the monitor; the esynoscheduler wrapper respawned it (`sleep 300` loop) on the
  new code. **Confirmed working**: WINDOW dropped from a steady ~150–162% to **92%** (`22/24`) at the
  first post-restart window — same packet volume, correct dedup. **Layer B** (driver stops publishing
  dataless freqError packets + disable `RAW_*` debug logging; also fixes 15 MB `weewx.log` bloat) is
  deeper, No-Rewrite applies — still deferred. Doc-vs-reality flag stands: the running binary **does**
  emit `ChannelIdx`/`FreqError` (BACKLOG said it didn't; re-confirmed live S28). See DEC-0024 + BACKLOG.
- **M-A/L-B — monitor incremental byte-offset read (S28, PR #10 → `dev`, draft, NOT deployed).** The
  monitor re-read the whole ~10 MB/day `weewx.log` twice per 30 s poll (`get_linecount()` +
  `get_new_lines()`). Rewrote it as a single byte-offset `seek()` (`get_log_size()` +
  `get_new_lines(offset)`) — kills the O(n) re-scan (M-A) and the double-open race (L-B) in one change;
  rotation + partial-line guards; `tests/test_monitor_incremental_read.py` (6 tests), suite 40/40.
  **Deploy is owner-gated** (scp + `sudo kill`, same as Layer A). Merge PR #10, then deploy.
- **Rain fix — where the code actually lives (S28 clarification).** Three distinct states, easy to
  conflate: **(1) live in prod on the NAS** via the S18 hot-swap; **(2) on GitHub, PUBLIC `dev` branch**
  (`rain_delta_tips` + `MAX_PLAUSIBLE_TIPS` in `rtldavis.py`, merged via #5 in S27; also on
  `feature/rain-spike-filter`); **(3) NOT on `main`** — the tagged production-baseline branch — which is
  exactly what the v2.0.3 promotion gates. **There is no private repo:** this driver has one repo,
  `WeatheredScientist/weewx-rtldavis`, and it is public (the dashboard is the separate
  `eaglehunt-weather-dashboard`). So the fix is already public on GitHub (on `dev`), just not released
  on `main`. Promote `dev` → `main` + tag v2.0.3 once it's proven in the wild (see Active thread).
- **Reception %% denominator fixed — honest metric still owed (S29).** The monitor's "91%" was a
  denominator artifact (divided by 24; the ISS physically sends ~21.3/min at the 2.8125s Tx-4 period).
  Fixed on the PR #10 branch (`WU_RF_EXPECTED` 24→21, env-overridable, `wu_pct()` capped at 100, +9
  tests). Deploys with the M-A/L-B monitor change. This is the *interim* honest number; the *real* metric
  is the driver's `rxCheckPercent` (next thread).
- **`rxCheckPercent` dead since 2026-06-18 — ROOT CAUSE FOUND (S29); fix already on `dev`.** The
  driver's honest reception metric populated the archive 2026-05-26 → **2026-06-18 18:42 UTC (avg
  67.5%)**, then went NULL. **Cause:** at `2026-06-18 14:44 EDT` the weewx engine reloaded the driver
  (`Main loop exiting … Loading station type Rtldavis`), and the reloaded code carries the **S24 "H2"
  `pct_good_all` deadlock** — live `rtldavis.py:1006` reads `if total_max_count > 0 and
  self.stats['pct_good_all'] is not None:`, but `pct_good_all` is reset to `None` every period (`:966`),
  so the guard **can never pass** → `pct_good_all` stays None → `rxCheckPercent` never set (`:1023`) →
  NULL forever. (Not the `curr_cnt` parse — sensor data still flows, so the DATA `PATTERN` still matches;
  no signal/restart anomaly at the transition, records kept coming every 60s.) **Fix already on `dev`:**
  `rtldavis.py:1011` is `if total_max_count > 0:` (the `and … is not None` removed), regression-tested in
  `tests/test_reception_stats.py`. **Ships when the v2.0.3 image is rebuilt** (driver is baked; needs the
  same rebuild as H1/M3 + the dewpoint rewrite). On ship, live-confirm `rxCheckPercent` repopulates and
  then point the monitor at it instead of scraping WU-publish lines. *Bonus finding:* a pre-June-18
  `user.reception_service` (`ReceptionMonitor: received N/24`) was a 2nd honest-ish signal; it's since
  been removed (0 lines today, not in `weewx.conf`) and also used the wrong /24 denominator.
- **ERR-0001 local honest-null — ✅ APPLIED 2026-07-05 (S29, DEC-0025).** Nulled the two 3 AM phantom
  records (`dateTime IN (1783148640, 1783148700)`) + `weectl database rebuild-daily --date=2026-07-04`
  (owner-run; backup `weewx.sdb.bak-err0001-20260705-165813`). Verified: July-4 daily rain **1.84" →
  0.56"** — the honest-null was surgical (the day's genuine 0.56" evening rain, ≤0.05" increments
  ~20:31–22:39 EDT, is preserved; only the 1.28" 3 AM phantom removed). **Still open:** the **InfluxDB**
  copy (dashboard's source) still carries the phantom — cross-repo (DEC-0010), tracked in DATA_ERRATA.md;
  external WU (day total 1.84") / MADIS copies are immutable, reconciled by the errata.
- **Sensor-QC hardening (DEC-0022, a later session):** the stale-substitution DEC-0006 violation in
  `dewpoint_service.py` (temp/humidity/radiation/UV — real 6263 sensors get stuck if they fail) +
  minor windGust/radiation/UV StdQC bounds. Ties into the pending dewpoint rewrite. Do after v2.0.3.
- **Pending v2.0.3 dewpoint rewrite** — the honest-null Jun-16 host version is written but undeployed
  (dewpoint is baked → needs a rebuild). Fold into the v2.0.3 release; may also address DEC-0022 #1.
- **Gain 372, interim** (DEC-0017) — awaiting a 24 h averaged no-preamp sweep to settle vs 207.
- **rw250 vs rw350** (ARCHITECTURE §6) — running binary likely rw250, committed Dockerfile patches
  rw350; needs a rebuild + receiveWindow sweep to reconcile.
- **Vestigial `loopdata.py`** — mounted + `[LoopData]` section present but not in any active service
  list; safe to remove, not urgent (don't touch prod casually).

## Needs a check / housekeeping

- **Rotate the exposed WU API key** (was hardcoded in NAS `wxcheck.sh`; scrubbed from the repo in S16,
  real key still live on the NAS). Non-urgent, owner-acknowledged 2026-07-04. **Owner action.**
- **Set `STATION_NAME` in the NAS `monitor.env`** — alert emails currently fall back to "My PWS".
  **Owner action** (edit `monitor.env` + monitor restart).
- ~~Remote URL casing~~ — **resolved (no-op, S28):** origin is already canonical `WeatheredScientist/`.
- ~~Stale branch `origin/feature/influxdb-grafana`~~ — **deleted (S28):** Grafana retired for Influx;
  its only driver-relevant bit (wind-warmup `3f5470f`) was already in `dev`. Also deleted merged
  `s20-governance-hardening`; `s27-p3-deployed` was already auto-gone on #9's merge.

## Next session actions (S30 remaining → S31 if unfinished)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S30 (committed to `dev`, pushed):** dewpoint **wind honest-null** (ported byte-identical
from the reviewed Jun-16 draft; `_filter_wind` no longer substitutes stale `windSpeed` — wind is in every
Davis packet so no per-packet dropout; temp/hum/rad/UV keep carry-forward, DEC-0022), **receiveWindow →
upstream default** (dropped the unproven rw350 `sed`), **Dockerfile clobber fix** (`:101` was shipping the
stock driver over the patched one), v2.0.3 header + doc corrections, `tests/test_dewpoint_wind_honest_null.py`
(+5, **suite 54/54**), secret-scan clean. Commits `5486de8`, `8085504`, `8c06817` on `dev`.

**✅ Done in S30 (build + deploy):** Built the image **native amd64 on the NAS** (Mac is arm64; native
build avoids a QEMU cross-compile of the from-source C+Go — cleaner). Flushed two more latent build bugs:
the `Dockerfile:101` clobber (shipped stock driver) and an **untracked `logging.additions`** (Step-7
`COPY` failed from a clean clone — now committed + de-duplicated). Verified the baked image contains the
patched driver (rain filter + H2, 71988 B — not the 67256 B stock) + honest-null dewpoint. Deployed
(`docker rm -f` + re-run on `:v2.0.3`, identical binds; old `rw250-test` kept for rollback). **Confirmed
live:** `rxCheckPercent` NULL→**70–82%** within two 60 s archive cycles; packets flowing; clean dongle
handoff (no USB reset).

**Remaining = release (owner-approval-gated — outward-facing/hard-to-undo):**

1. **Promote `dev` → `main`** (explicit approval — never force-push/merge to main) + **tag `v2.0.3`** so
   `main` = what's actually running. 8 S30 commits on `dev` (`5486de8`→ the CHANGELOG/STATUS closeout).
2. **GitHub release** (v2.0.3 notes) + **push image to Docker Hub** (`weatheredscientist/weewx-rtldavis`
   `:v2.0.3` + `:latest` — first public image that actually contains the driver fixes). Image built on the
   NAS; `docker login` + `docker push` are owner creds. *(Old `rw250-test` tag is a misnomer now —
   receiveWindow ships at the upstream default.)*
3. **Keep watching the first archive cycles** — first time the rain filter + QC actually run in prod;
   verify no regression in rain/wind/reception over the next day.

**Also open (not blocking v2.0.3):**
- **ERR-0001 InfluxDB null** — the dashboard reads InfluxDB, which still carries the July 4 phantom;
  cross-repo (DEC-0010), no `influx` CLI on the NAS. Handle on the dashboard side or via the Influx API.
- **Owner housekeeping:** rotate the exposed WU API key; set `STATION_NAME` in the NAS `monitor.env`
  (alert emails fall back to "My PWS"). Keep `feature/rain-spike-filter` until v2.0.3 ships.
- **Snow / freezing / no heating tape** (parked, owner's future thread) — cold-weather failure modes
  (sensor freeze, stuck counters, DEC-0006 stale-substitution) we haven't designed for. 2026 = learning year.

**Live access (read-only used in S21/S22):** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in
gitignored `docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use
`env -u GH_TOKEN` for any `git push` (keyring token, not the PAT).
