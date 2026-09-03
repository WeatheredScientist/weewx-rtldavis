# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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

## [S114] — 2026-09-02 — Spectrum capture finds wideband RFI, not a clean 925.5–926.5 MHz interferer (DEC-0132); ops#253 fully closed; PR #305 merged

- **Merged PR #305** (Foundation's stopped weewx container decommissioned).
- **ops#253 closed, both stages.** Marvin's `exec_devices` grant (`0bda:2838` via a per-device
  udev rule, owner-ratified S114) had only been smoke-tested with `rtl_test` before this session.
  Ran the real thing: `weewx.service` stopped (~6 min outage, self-service), a 5-min `rtl_power`
  sweep of 924.5–927.5 MHz through `marvinctl exec-ro`, prod restarted clean.
- **DEC-0132: the capture's noise floor was flat and stable all 5 minutes** (no rolloff shape —
  evidence against a static gain rolloff or fixed antenna null), **but 16 of 60 ten-second windows
  carried transient bursts (5–34 dB above floor) spanning 925.15–927.48 MHz** — nearly the whole
  capture band, not confined to DEC-0130's flagged 925.5–926.5 MHz channels 46–48 (only 7 of 16
  fall there; the single largest, +34.5 dB, hit 927.34 MHz, well outside it). Reading: RFI
  strengthens as the mechanism, but the exclusive tie to channels 46–48 weakens. Blocker 6 stays
  open — free next step (cross the spike frequencies against DEC-0130's histogram) queued for
  S115, explicitly on Fable per the owner's call, since it's open-ended analysis, not execution.

---
