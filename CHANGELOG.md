# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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
