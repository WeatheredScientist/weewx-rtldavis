# Campaign B swap-night runbook — LNA removal + no-LNA RX campaign

**Design: DEC-0064** (campaign A was DEC-0059/0061). This is the checklist version: the swap
night is executed from chat, step by step, with two explicit owner gates. Everything here was
built and dry-run in advance so the night is execution, not derivation.

**The one hard rule: nothing touches the container or the bias tee until the owner's GO in
chat.** The owner is physically at the hardware for a 20–40 s SMA swap; the gate exists so the
antenna-disconnected window is that short, not minutes.

## Timeline at a glance

| When (local) | What | Who |
|---|---|---|
| Thu 08-06 daytime | Pre-flight complete (below) | agent + owner merge |
| Fri 08-07 00:05 | Campaign A self-terminates to baseline, completion email | automatic |
| Fri 08-07 ~00:10 | Archive A's artifacts; deploy new `rx_experiment.sh` | agent |
| Fri 08-07 ~00:15 | **GATE 1: owner GO in chat** → v2.0.12 deploy, bias tee off | owner → agent |
| Fri 08-07 ~00:17 | Physical LNA removal (SMA swap, 20–40 s) | owner |
| Fri 08-07 ~00:20 | Health check; redaction + bias-tee-off log verify; `install` | agent |
| Fri 08-07 00:35–04:20 | Overnight pilot: P496 → P449 → P402 → P372 → P328 | automatic |
| Fri 08-07 04:20 | H hold (baseline settings) through the day | automatic |
| Fri 08-07 daytime | Pilot readout; **GATE 2: confirm/adjust square arms** | agent + owner |
| Sat 08-08 00:05 | Campaign B first block (H → A swap) | automatic |
| Sun 08-16 00:05 | Campaign B self-terminates to baseline, completion email | automatic |

## Pre-flight (Thursday 08-06, all in daylight)

- [ ] `v2.0.12` image built on the dev machine and pushed to Docker Hub (`:v2.0.12` + `:latest`).
      Carries: DEC-0062 `pressure_service.py` redaction, `BIAS_TEE` env in `entrypoint.sh`
      (default `1` — published image behavior unchanged for existing users).
- [ ] Release PR merged by owner; `main` promoted per the branch model.
- [ ] `pytest` green, including the pilot/hold schedule assertions in
      `tests/test_rx_experiment.py`.
- [ ] `DRY_RUN=1` pass of the new `ops/rx_experiment.sh` recorded.
- [ ] Campaign A still healthy (no STOP sentinel, swaps clean) — if A aborted late, the swap
      night still works: A's abort already restored baseline; skip the "completion email" check.
- [ ] Owner knows the night's two gates and has the SMA wrench (if needed) staged.

## Swap night (Friday 00:05 → 00:35)

**Step 0 — confirm A ended.** Completion email received; `rx_experiment.state` reads
`BASELINE|…`; live config back on the baseline cmd. The DSM tick/guard tasks keep firing —
they are idempotent no-ops against a completed campaign and are REUSED for B (no DSM work).

**Step 1 — archive campaign A (agent).** On the NAS project root, rename aside:
`rx_experiment.log`, `logs/rx_experiment_data.log`, `rx_experiment.state`,
`weewx.conf.rx-baseline` → same names + `.campaignA` suffix. This resets block counting for B
(the un-rotated log carried phantom blocks through all of A) and clears the way for `install`
(which refuses to run over an existing snapshot).

**Step 2 — deploy the new apparatus (agent).** `scp` the campaign-B `rx_experiment.sh` to the
NAS project root; sha-verify against the repo copy. The old script's ticks between steps 1 and
4 will log "not installed" — cosmetic, expected.

**Step 3 — GATE 1 (owner).** Agent asks in chat; owner answers GO **only when physically at
the dongle, ready to swap**. Nothing before this touches the running container.

**Step 4 — container swap to v2.0.12 (agent, on GO).** `docker kill` → `rm` → `run` with the
prior container's exact mounts/devices/env (derive from `docker inspect` — the NAS
`docker-compose.yml` is stale/decorative) **plus `-e BIAS_TEE=0`**. This is the night's one
Class C command; the in-chat GO covers its token mint. From this moment the LNA is unpowered
and reception craters — expected, it is an unpowered amplifier acting as an attenuator.

**Step 5 — physical swap (owner, immediately after step 4).** Unscrew LNA, connect antenna
directly to the dongle. 20–40 s. Reception recovers to no-LNA levels.

**Step 6 — verify (agent).**
- [ ] Container startup log shows `Bias-tee disabled (BIAS_TEE=0), driving it off...`
- [ ] DEC-0062 verify: startup log shows the redacted `present`/`MISSING` form, no key fragment.
- [ ] New archive record lands (the health_ok criterion: proof the driver is producing).
- [ ] First RECEPTION samples are plausible no-LNA numbers (see Expected numbers).

**Step 7 — install (agent).** `rx_experiment.sh install` — snapshots the new baseline,
writes fresh state. First pilot row fires at **00:35**. A late start self-heals: `due_arm()`
swaps late rather than skipping, shortening pilot block 1 only.

**Owner goes to bed.** The pilot and the guard run unattended; every failure path restores
baseline and emails.

## If the night goes sideways

- **Abort overnight** (STOP sentinel + email): prod is already back on baseline — nothing to
  do until morning. A low pilot arm finding the reception cliff IS a pilot result; the
  high-to-low ordering means the upper arms were already harvested. Read the data, clear the
  STOP, adjust arms if needed, and the square still starts 08-08T00:05.
- **Health check fails after the v2.0.12 swap**: roll back the container to `:v2.0.11`
  (same run line, old tag, `BIAS_TEE` unset) — the LNA can stay physically out either way;
  bias tee defaults ON in v2.0.11 but an unloaded tee into a DC-open antenna is harmless for
  a diagnostic interval. Diagnose in daylight.
- **A did not self-terminate at 00:05**: do not improvise at midnight. Manual
  `rx_experiment.sh abort` restores baseline; postpone the swap night 24 h (schedule dates
  regenerate dev-side; that is a 15-minute daytime task).

## Friday daytime — pilot readout (GATE 2)

Drop the first 2 samples of each pilot block (settle rule), average the rest per arm, plot the
five-point gain curve. Decision, made with the owner:

- Curve peaks inside {372, 496} → square arms confirmed, nothing to deploy.
- Peak clearly at/below 402 → shift the high arm (496 → 449 or 434); edit arm literals +
  tests, re-run pytest, re-`scp`, sha-verify — all before ~23:00 Friday.
- The pilot is **arm-selection input only** (sequential, hour-confounded — pre-registered in
  DEC-0064). It never adopts anything into prod.

Also close out during the hold: does the daylong H window sit inside the expected no-LNA band?
Does the hour-07/19 notch present without the LNA? (Both go into the DEC-0064 record.)

## Saturday 00:05 — campaign B starts

- [ ] Tick log shows `swapping H -> A` and `arm A live and healthy`.
- [ ] `rx_experiment_data.log` shows H-tagged samples harvested (the hold's own tag — arm A's
      square samples start clean).
- Campaign B: 32 blocks, 8/arm, self-terminates **08-16T00:05**. Track exactly as A was
  tracked; do not read partial results (DEC-0059's adoption bar applies: ≥2.0 pts over the
  incumbent without a duplicate-frame regression).

## Expected numbers (pre-established, DEC-0064)

| Era | Config | Mean | sd (5-min) | Source |
|---|---|---|---|---|
| Jun 2–18 plateau | gain 207, **LNA in** (owner-confirmed, S61) | 67.45 | 3.22 | archive forensics, n=4321 |
| Jul 5–27 plateau (campaign A baseline) | gain 372, LNA in | 74.83 | 4.13 | archive forensics, n=5948 |
| No-LNA expectation | gain 372 | *set by the pilot* | — | first honest measurement 08-07 |

**There is no honest no-LNA telemetry anywhere** — the no-LNA evaluation era (gain 372, late
June) sits entirely inside the metric-dark gap. The pilot is the first real measurement; treat
Friday's first samples as discovery, not verification against a known band. Plausibility check
only: meaningfully below the 74.83 LNA-in baseline, meaningfully above the 50% floor.

Abort floor for the whole campaign-B era: **50%** (30-min mean) — ~5 SE below even a
pessimistic 62% baseline; forgiving on purpose while the no-LNA level is unmeasured.
