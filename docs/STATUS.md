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

> **Current session: S28** (2026-07-05) — release still calendar-gated (no real rain glitch yet); cleared
> the unblocked follow-ups. **P1 verified live** (rain-watch: 0 glitches to date; reception Layer A
> confirmed 91–92% [OK]). **M-A + L-B** (monitor byte-offset incremental read) coded + tested (40/40) →
> **draft PR #10 → `dev`**, not yet deployed (owner-gated). **Branch cleanup done** (deleted
> `s20-governance-hardening` + `feature/influxdb-grafana`; `s27-p3-deployed` already auto-gone; URL casing
> already correct). No prod/driver code touched. Governed lineage: S16→…→S26→S27→**S28**. Next session = S29.

_Last updated: 2026-07-05 (S28 — unblocked follow-ups. **P1 verified (read-only, live):** rain-watch
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

## Next session actions (→ S29)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S28:** P1 verified live (rain-watch = 0 glitches to date; reception Layer A confirmed
91–92% [OK]). Coded + tested **M-A + L-B** (monitor byte-offset incremental read) → **draft PR #10 →
`dev`** (40/40, secret-scan green). **Branch cleanup done** (deleted `s20-governance-hardening` +
`feature/influxdb-grafana`; `s27-p3-deployed` already auto-gone; URL casing already correct — both no-ops).

**Now the standing queue (owner/calendar-gated first):**

1. **Merge + deploy PR #10 (M-A/L-B).** Review the draft PR; merge to `dev`; deploy the monitor the
   same way as Layer A (owner: scp `weewx_monitor.py`, `sudo kill <pid>`, esynoscheduler respawns ≤5
   min). Confirm "Poll: N new lines" keeps flowing + reception stays ~90%. Independent of the release.
2. **Watch for the first real rain glitch** (0 to date, checked S28). Confirms the S18 fix + alert
   together (log "rejecting implausible counter delta" + clean archive + the email to `ALERT_TO`).
   Calendar-bound (~1/2–3 wk). The fix is live in prod; this gates only the *formal* release, and it's
   a **confidence** gate, not a safety one — could be waived (cut v2.0.3 on tests + live evidence).
3. **v2.0.3 release** once the glitch rides clean (or the gate is waived): **promote `dev` → `main`,
   tag, release on GitHub + Docker Hub.** `dev` already carries rain + reception + governance + the
   S24/S25 code-quality fixes. Fold in the baked honest-null dewpoint rewrite (needs an image rebuild)
   and the **S24 driver fixes** (H1/H2/M3, branch-only — need the same rebuild + hot-swap). When H2
   ships, **live-confirm rxCheckPercent starts populating** (`SELECT rxCheckPercent FROM archive ...` —
   expected all-NULL now). See ROADMAP P1.
4. **Owner housekeeping:** rotate the exposed WU API key; set `STATION_NAME` in the NAS `monitor.env`
   (emails currently fall back to "My PWS"). Keep `feature/rain-spike-filter` until v2.0.3.

**Live access (read-only used in S21/S22):** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in
gitignored `docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use
`env -u GH_TOKEN` for any `git push` (keyring token, not the PAT).
