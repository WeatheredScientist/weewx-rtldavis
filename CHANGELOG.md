# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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

---

## [S43] — 2026-07-15 — v2.0.8 shipped, deployed and verified: Cold-load Fix B/DEC-0051, Reception Layer B/DEC-0024, duplicate-frame counter/DEC-0035

> **Soak check (v2.0.7, up 49h): green.** 11/15 pass, 4 expected startup-only warnings, 0 failures —
> archive current, stdout quiet, no tracebacks, no stalls, 100% reception, 45,190 records published, 0
> phantom-rain rows in 2,987 archive rows. **Humidity-spike check: no qualifying spike yet.** Decoded
> the full `humidity_raw=` series since the capture went live (2,056 samples, ~50h, including the
> rotated `weewx.log.2026-07-13`/`.2026-07-14` the live log had already rolled past) per the driver's
> real decode formula. Largest jump: 7.5 %RH/min, clustered in the predicted 11:00–16:00 window but
> well under the 16-37% DEC-0044 signature. Capture instrument confirmed working correctly.
>
> **Three backlog items shipped in code:**
>
> 1. **Cold-load Fix B + windchill (DEC-0051, closes issue #44).** `loop_json_writer.py` now writes an
>    identical snapshot to a second path (`current.json`, default `/opt/weewx-data/current.json`) on
>    every LOOP packet, atomic tmp+rename same as `loop-data.txt`; `windchill` added to `_FIELDS`
>    (`windchill_F`). `docs/INTERFACES.md` updated. **Deploy: mounted file — hot-swap (scp + clear-pyc
>    + restart), no image rebuild** (verified against `docs/ARCHITECTURE.md`'s mount table).
> 2. **Reception Layer B (DEC-0024 — now fully resolved).** The driver published channel-hop
>    (`freqError{n}`) packets as their own dataless loop packets, which every uploader (WU RapidFire
>    etc.) then published as if they were full weather updates — the ~1.6x overcount measured at S21.
>    Considered and rejected: dropping the packet outright (freqError is repurposed onto real archive
>    schema columns — `consBatteryVoltage`/`hail`/`hailRate`/`heatingTemp`/`heatingVoltage` — and
>    `ops/reception_service.py` logs non-zero freqErrors, so silently breaks both); tagging it dataless
>    and filtering in every consumer (broader blast radius for no benefit). **Chosen:** cache the
>    channel-hop packet's freqError fields and merge them onto the *next* real DATA packet instead of
>    ever yielding a standalone one (`_cache_pending_freq_fields` / `_merge_pending_freq_fields`, each
>    cached value rides exactly once). Side effect: also fixes `weewx_monitor.py`'s live `WINDOW:`
>    reception metric, which counted channel-hop packets as real readings via its epoch-dedup (S22)
>    never fully catching them (S31 confirmed it still pinned near 100%) — verified live post-deploy,
>    see below.
> 3. **Duplicate-frame counter (DEC-0035's own proposed instrument).** `genLoopPackets`'s stderr scan
>    now counts Go's `"duplicate packet:"` dedup line unconditionally (no `debug_rtld` gate) into
>    `self.stats['dup_count']`; `_update_summaries()` logs one INFO line per archive period (including
>    `N=0`, so a quiet period is distinguishable from the instrument not running); `_reset_stats()`
>    zeroes it for the next period — the same pattern already used for `pct_good_all`.
>
> Items 2+3 both touch the baked driver (`rtldavis.py`) — bundled for **one** image rebuild rather than
> two. +13 offline tests (`test_loop_json_writer.py`, `test_reception_layer_b.py`,
> `test_duplicate_frame_counter.py`); suite 72 → 85. **DEC-0051 added; DEC-0024 and DEC-0035 updated**
> with S43 sub-sections in `DECISIONS-FULL.md`.
>
> **Caught mid-commit: local pre-commit's `ruff-format` hook had silently contradicted DEC-0027 since
> S31.** CI dropped `ruff format` deliberately (it flattens `rtldavis.py`'s column alignment and
> reformats the baked driver — No-Rewrite); local `.pre-commit-config.yaml` still carried it. Never
> fired because pre-commit itself was never installed until S42 (DEC-0050) — its first real run
> attempted to mass-reformat `rtldavis.py` (3,213-line diff) on this session's commit. Caught (a second
> hook also blocked the same commit), reverted, `ruff-format` removed from the config. Checked both
> siblings for the same pattern: the dashboard already avoids it deliberately; `hyperlocal-forecast`
> carries it too but with no equivalent DEC and no known baked file, so no finding filed there.
>
> **Deployed and verified, same session.** PR #49 (the three items) and PR #50 (the `v2.0.8` version
> bump — Dockerfile header + README) merged to `dev`. Image built on the NAS in a fresh `build-v2.0.8/`
> checkout (`docker build`, zero errors in the build log), pushed to Docker Hub as `:v2.0.8` + `:latest`
> (digest `sha256:2c05493a...`). `loop_json_writer.py` hot-swapped into place (old copy preserved as
> `.bak-pre-v2.0.8`); production container recreated (`docker kill` → `rm` → `run`, DEC-0008 — replicated
> the *actual running container's* `docker inspect` config, not the NAS's own stale `docker-compose.yml`,
> which still said `:v2.0.4`). **Live-verified, not image-checked (DEC-0046 discipline):** driver banner
> `0.20+ws.1`; `current.json` writing real data including `windchill_F`; `duplicate frames this period: N`
> logging every archive period; **Wunderground-RF published-record count now matches unique record
> epochs exactly (53/53 over a 3-min window)** — the ~1.6x overcount DEC-0024 documented is gone;
> `soak_check.sh` 14/15 pass, 0 failures (1 warning: 71% reception, ordinary RF variance, not a
> regression). **`weewx_monitor.py`'s live `WINDOW:` metric confirmed fixed too:** post-deploy it reads
> `WINDOW: 14-17/21 (67-81%)`, `RECEPTION: 73-77% avg` — matching the driver's own trusted
> `rxCheckPercent` range (59-95%, median 75%, S31) for the first time, instead of the pre-fix pinned-
> near-100% pattern S31 documented. (Correction: `ops/reception_service.py` — a *different*,
> WeeWX-internal `ReceptionMonitor` service — turned out not to be wired into this station's
> `weewx.conf` at all, and per `git log` has sat untouched since S16; likely vestigial, like
> `loopdata.py`. It is not what generates the reception emails; `weewx_monitor.py` is.)
>
> **PR #51 promoted `dev` → `main`** (CI green on both source commits); tagged `prod-baseline-20260715`
> + `v2.0.8`; GitHub Release published. `docs/CONVENTIONS.md` and `CLAUDE.md` had stale `:v2.0.4`/`:v2.0.5`
> drift notes left over from S38 that were never corrected when S41 actually caught prod up — fixed now
> alongside this release. `ops/soak_check.sh`'s own `EXPECT_IMAGE` default bumped to `:v2.0.8`.
