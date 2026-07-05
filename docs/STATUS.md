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

> **Current session: S27** (2026-07-05) — tied up the S23–S26 PR backlog (five open, nothing merged).
> **Secret gate landed and now blocking** (#6 → `dev`, #7 → `main`, + `secret-scan` required in branch
> protection); **the whole review stack collapsed onto `dev`** via #5 (`2c75c5e`) — rain fix + reception
> Layer A + S23 governance docs + S24/S25 code-quality fixes, one clean gated merge. `main` untouched
> beyond the gate. No prod/driver code touched. Governed lineage: S16→…→S25→S26→**S27**. Next session = S28.

_Last updated: 2026-07-05 (S27 — backlog closeout. **P1 secret gate:** merged #6 → `dev` (`90ef51b`) +
#7 → `main` (`490e776`); `main` previously had zero secret scanning. Set **`secret-scan` as a required
status check** on both branches (keyring token — the PAT 403 was a scope issue; `enforce_admins: false`,
no required reviews) → the DEC-0012 gate is no longer advisory. **P2 review stack:** the predicted
`ci.yml`/`check_secrets.sh` conflict never happened — the stack's S20 gate fix (`2a6327c`) is
byte-identical to dev's #6 fix, so it auto-merges. Retargeted **#5** to base `dev` and merged the whole
stack (`2c75c5e`): all S18–S26 work now on `dev` (secret-scan green, 34/34 tests). Closed #3/#4 as
merged-via-#5. Folded the retired root `cleanup_backlog.md`'s 8 open items into `BACKLOG.md` + deleted
`logging.additions` (`7025afa`). `main`-promotion (v2.0.3) stays parked for rain wild-validation +
dewpoint rebuild. Prior: S26 — secret-gate audit + the two draft PRs.)_

---

## Active thread

> **▶ Resume here (→ S28).** As of S27 the whole S18–S26 backlog is **merged onto `dev`** (via #5,
> `2c75c5e`) and the secret gate is **on `main` + `dev` and blocking**. `main` is otherwise untouched.
> Two things gate the `dev`→`main` v2.0.3 release, plus one owner deploy:
> 1. **Deploy reception Layer A (DEC-0024)** — code is now in `dev`; the deploy is monitor-restart-only
>    (owner action): scp `weewx_monitor.py`, `sudo kill <pid>` (pidfile `logs/weewx_monitor.pid`);
>    confirm the next RF-Reception email reads ≤100% (was ~150%). Independent of the release.
> 2. **Watch for the first real rain glitch in the wild** — confirms the S18 fix + alert together (log
>    "rejecting implausible counter delta" + clean archive + the email). Calendar-bound (~1 glitch/2–3 wk).
>    Checked 2026-07-05 (S22, read-only): **none fired yet.** The fix is live in prod via hot-swap; this
>    watch gates only the formal release.
> 3. After the glitch rides clean: **promote `dev` → `main` + tag v2.0.3** (release on GitHub + Docker
>    Hub), folding in the pending baked honest-null dewpoint rewrite (needs an image rebuild — bigger
>    deploy than the hot-swap; plan it). `dev` already carries rain + reception + governance + the
>    S24/S25 code-quality fixes, so v2.0.3 is a `dev`→`main` promotion, not a branch-by-branch merge.
> 4. Then, in a later session, **DEC-0022 sensor-QC hardening** (below).
>
> _Numbering note (DEC-0023): the "shared lineage with the dashboard" (DEC-0013) never held — the
> sibling runs its own S1→S40 counter and never shared one. This repo counts **independently**:
> S16→…→**S25**→**S26**→**S27** (this session). Cross-repo refs are prefixed (`weewx S27` vs `dash S40`)._

## Open threads (not yet shipped)

- **Reception metric ~150% — Layer A merged to `dev` (via #5, S27), PENDING DEPLOY.** Root cause: the
  daily RF-Reception email over-counts because `weewx_monitor.py` counted raw `Wunderground-RF:
  Published` log lines, but the driver publishes freqError freq-hop packets as duplicate publishes of
  the SAME record epoch (~1.66×; live 2026-07-05 sample showed a clean 2× — same epoch posted twice).
  **Layer A fix** (`feature/reception-dedup`, commit `20bf7c0`): a pure `wu_record_key()` helper dedups
  on the trailing `(<epoch>)`; the window counts unique epochs. 6 offline tests, driver + alert logic
  untouched. **Deploy = monitor restart only** (`sudo kill <pid>`, pidfile `logs/weewx_monitor.pid`;
  the respawn loop reloads on-disk code ≤5 min). Reversible. **Layer B** (driver stops publishing
  dataless freqError packets + disable `RAW_*` debug logging; also fixes 15 MB `weewx.log` bloat) is
  deeper, No-Rewrite applies — still deferred. Doc-vs-reality flag stands: the running binary **does**
  emit `ChannelIdx`/`FreqError` (BACKLOG said it didn't). See DEC-0024 + BACKLOG.
- **Rain fix** deployed live and now **merged to `dev`** (via #5, S27); **`main` still untouched**.
  Promote to `main` + tag v2.0.3 once it's proven in the wild (see Active thread).
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
  real key still live on the NAS). Non-urgent, owner-acknowledged 2026-07-04.
- **Remote URL casing** — origin is lowercase; GitHub redirects to canonical `WeatheredScientist/`.
- **Stale public branch** `origin/feature/influxdb-grafana` (11 commits) — may carry dashboard JSON +
  a driver-relevant wind-warmup fix; review, cherry-pick driver bits, delete from remote.

## Next session actions (→ S28)

**This section is the repo-visible handoff.** Read it first when resuming.

**✅ Done in S27 (the S23–S26 PR backlog is cleared):** secret gate merged to `dev` (#6) + `main` (#7)
and made a **required** status check on both; the whole review stack collapsed onto `dev` via #5
(`2c75c5e`); #3/#4 closed as merged-via-#5; S23 tail folded into BACKLOG. All open PRs resolved.

**Now the standing queue (owner/calendar-gated first):**

1. **Deploy the reception Layer A fix** (owner action; monitor-restart-only, DEC-0024) — code is in
   `dev`: scp the new `weewx_monitor.py`, `sudo kill <pid>` (pidfile `logs/weewx_monitor.pid`);
   confirm the next RF-Reception email reads ≤100% (was ~150%).
2. **M-A (monitor incremental read) + L-B (double-read race) — do AFTER the Layer A deploy lands.**
   Both edit `weewx_monitor.py`; L-B is resolved for free by M-A's byte-offset `seek()`. Sequencing
   avoids stepping on the just-deployed Layer A file. (The S24 review itself is **done** — S25.)
3. **Watch for the first real rain glitch** (still not fired, checked S22). The fix is live in prod;
   this gates only the formal release.
4. **v2.0.3 release** once the glitch rides clean: **promote `dev` → `main`, tag, release on GitHub +
   Docker Hub.** `dev` already carries rain + reception + governance + the S24/S25 code-quality fixes,
   so it's a `dev`→`main` promotion (not a branch-by-branch merge). Fold in the baked honest-null
   dewpoint rewrite (needs an image rebuild) and the **S24 driver fixes** (H1/H2/M3, branch-only —
   need the same rebuild + hot-swap). When H2 ships, **live-confirm rxCheckPercent starts populating**
   (`SELECT rxCheckPercent FROM archive ...` — expected all-NULL now). See ROADMAP P1.
5. **Housekeeping (P0/P4):** remote URL casing (→ `WeatheredScientist/`); clean stale
   `origin/feature/influxdb-grafana` (cherry-pick the driver-relevant wind-warmup fix first); rotate
   the exposed WU API key; delete the now-merged remote stack branches (`feature/s24-code-quality-review`,
   `feature/s23-governance-alignment`, `feature/reception-dedup` — all fully in `dev`; keep
   `feature/rain-spike-filter` until v2.0.3).

**Live access (read-only used in S21/S22):** `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` (real values in
gitignored `docs/LOCAL_INFRA.md`); logs at `.../logs/{weewx.log,weewx_monitor.log}`. Use
`env -u GH_TOKEN` for any `git push` (keyring token, not the PAT).
