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

> **Current session: S29** (2026-07-05) — dug into RF-metric trust + the July 4 rain glitch. **Reception
> "91%" was a denominator artifact:** the monitor divided WU-publish count by 24, but this ISS (Tx 4)
> transmits every ~2.8125s → only ~21.3/min are physically sent; live measurement shows ~21.75/min with
> no gaps = **~100% reception, not 91%**. Fixed the denominator (env-overridable 21 + capped `wu_pct()`),
> +9 tests (suite **49/49**), pushed to **PR #10 branch** (rides the same monitor deploy). **The driver's
> *honest* metric `rxCheckPercent` has been NULL since 2026-06-18** (last real value 67.5%) — opened as a
> tracked investigation (below). **July 4 phantom +1.28" rain confirmed** in the archive (two 0.64"
> records) and in the WU/CWOP→MADIS external record; established **DEC-0025 (preserve-and-flag, never
> delete)** + `docs/DATA_ERRATA.md` (ERR-0001). Local honest-null is **owner-gated** (prod DB write,
> read-only boundary). Governed lineage: S16→…→S27→S28→**S29**. Next session = S30.

_Last updated: 2026-07-05 (S29 — RF-metric trust + July 4 glitch dig. **Reception fix** (denominator
24→21 physical TX rate, `wu_pct()` cap, +9 tests, suite 49/49) pushed to PR #10 branch. **rxCheckPercent
dead since 2026-06-18** → investigation opened. **DEC-0025 + docs/DATA_ERRATA.md** (ERR-0001: July 4
phantom +1.28", confirmed in archive + WU/MADIS). Local honest-null owner-gated. **S28 below still
holds:** rain-watch = 0 glitches since the fix, reception genuinely ~100% (was misread as 91%).)_

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

> **▶ Resume here (→ S29).** As of S28: reception Layer A is **deployed + confirmed live** (91–92% [OK]),
> and the M-A/L-B monitor rewrite is in **draft PR #10 → `dev`** (40/40, secret-scan green) but **not yet
> deployed**. `main` is untouched beyond the secret gate. Open gates for the `dev`→`main` v2.0.3 release,
> plus owner actions:
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

## Next session actions (→ S30)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S29:** Diagnosed the RF-metric trust problem — "91%" was a **denominator artifact** (monitor
divided by 24; the ISS physically sends ~21.3/min); **real reception is ~100%**. Fixed it on the **PR #10
branch** (`WU_RF_EXPECTED` 24→21 env-overridable + `wu_pct()` cap, +9 tests, suite **49/49**, pushed
`db5d82f`). Found the driver's honest **`rxCheckPercent` dead since 2026-06-18** → opened as an
investigation (Open threads). Confirmed the **July 4 phantom +1.28"** in archive + WU (+ almost certainly
MADIS); established **DEC-0025** (preserve-and-flag) + **`docs/DATA_ERRATA.md`** (ERR-0001).

**Now the standing queue (owner-gated first):**

0. **Owner prod steps (need a real terminal / write access — read-only boundary blocks the agent):**
   (a) **Deploy PR #10 + the reception fix** — one monitor restart carries both (scp `weewx_monitor.py`,
   `sudo kill <pid>`, esynoscheduler respawns ≤5 min). Then confirm WINDOW now reads ~100% (not ~90%) and
   "Poll: N new lines" keeps flowing. (b) **Apply ERR-0001 honest-null** — back up `weewx.sdb`; `UPDATE
   archive SET rain=NULL WHERE dateTime IN (1783148640, 1783148700)`; `weectl database rebuild-daily
   --date=2026-07-04`; verify Jul-4 total drops 1.28"; mark ERR-0001 ✅. InfluxDB null is cross-repo.
1. **Revive `rxCheckPercent`** — root cause found (S29): the S24 "H2" `pct_good_all` deadlock, deployed
   at the 2026-06-18 driver reload; **fix already on `dev`** (`rtldavis.py:1011`). No more investigation
   needed — just ship it in the v2.0.3 image rebuild, then live-confirm it repopulates and point the
   monitor at it instead of scraping WU-publish lines. (Open threads has the full evidence.)
2. **Merge PR #10 to `dev`** (secret-scan green, lint red-on-purpose; now also carries the reception fix).
3. **Watch for the first real rain glitch** (0 to date, re-checked S29). Confirms the S18 fix + alert
   together (log "rejecting implausible counter delta" + clean archive + the email to `ALERT_TO`).
   Calendar-bound (~1/2–3 wk). The fix is live in prod; this gates only the *formal* release, and it's
   a **confidence** gate, not a safety one — could be waived (cut v2.0.3 on tests + live evidence).
4. **v2.0.3 release** once the glitch rides clean (or the gate is waived): **promote `dev` → `main`,
   tag, release on GitHub + Docker Hub.** `dev` already carries rain + reception + governance + the
   S24/S25 code-quality fixes. Fold in the baked honest-null dewpoint rewrite (needs an image rebuild)
   and the **S24 driver fixes** (H1/H2/M3, branch-only — need the same rebuild + hot-swap). When H2
   ships, **live-confirm rxCheckPercent starts populating** (`SELECT rxCheckPercent FROM archive ...` —
   expected all-NULL now). See ROADMAP P1.
5. **Owner housekeeping:** rotate the exposed WU API key; set `STATION_NAME` in the NAS `monitor.env`
   (emails currently fall back to "My PWS"). Keep `feature/rain-spike-filter` until v2.0.3.

**Live access (read-only used in S21/S22):** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in
gitignored `docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use
`env -u GH_TOKEN` for any `git push` (keyring token, not the PAT).
