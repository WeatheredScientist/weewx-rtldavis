# Decision Log (INDEX) — weewx-rtldavis

**Status:** Source of truth (index) · **Tier 1 session read** (DEC-0030)
**Last updated:** 2026-07-09 (S35 — DEC-0030 docs diet: this file became the index; full bodies in DECISIONS-FULL.md)

One row per decision — scan this at session start; **do not re-litigate** anything listed. The
complete append-only bodies live in `docs/DECISIONS-FULL.md`; grep the DEC id there whenever a task
touches a settled decision's actual text (*"working near it" means read it*). New decision = append
the full body there + add a row here. A decision is never edited in place — it is **superseded** by
a later entry.

> **Provenance note:** entries DEC-0001…DEC-0009 are *reconstructed* from project history (the
> pre-governance chat sessions, roughly Apr–Jun 2026); their dates are approximate. DEC-0010 and
> up were made live under governance (S16 onward) and are exact. This log covers the
> **weewx-rtldavis driver/Docker** only; dashboard decisions belong to `eaglehunt-weather-dashboard`'s
> own log. **DEC-0018–0020 were never assigned** (numbering gap, no bodies exist).

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| DEC-0001 | Passive 915 MHz interception via RTL-SDR | Accepted | ~2026-04 (S1) |
| DEC-0002 | Ubuntu 26.04 / Python 3.14 multistage Docker build | Accepted | ~2026-05 |
| DEC-0003 | Same-repo tags for versioning (Option 2) | Accepted | ~2026-05-26 |
| DEC-0004 | Volume-mount extensions for hot iteration; bake stable code | Accepted · **driver half superseded** by DEC-0031 | ~2026-06 |
| DEC-0005 | Custom `loop_json_writer.py`; weewx-loopdata rejected | Accepted | ~2026-06 |
| DEC-0006 | Null-on-rejection filter philosophy (**runtime only** — see DEC-0032) | Accepted · **clarified** by DEC-0032 | ~2026-06 |
| DEC-0007 | Upload services use the WeeWX RESTThread pattern | Accepted | ~2026-05 |
| DEC-0008 | `docker kill`, never `docker stop` | Accepted | ~2026-05 |
| DEC-0009 | Dedicated limited user for the NAS-side monitor | Accepted | ~2026-06 |
| DEC-0010 | Adopt Eagle Hunt nine-file governance model | Accepted | 2026-07-04 (S16/S17) |
| DEC-0011 | Branch model: `main` = production truth, `dev` = work | Accepted | 2026-07-04 (S16) |
| DEC-0012 | Public repo: structural secret hygiene | Accepted | 2026-07-04 (S16) |
| DEC-0013 | Session numbering continues the shared lineage at S16 | **Superseded** by DEC-0023 | 2026-07-04 (S16) |
| DEC-0014 | No-Rewrite Rule | Accepted | 2026-07-04 (S16) |
| DEC-0015 | Graft Python tooling from hyperlocal-forecast | Accepted | 2026-07-04 (S17) |
| DEC-0016 | Claude Opus 4.8 at high/xhigh as the Claude Code driver | Accepted | 2026-07-04 (S16) |
| DEC-0017 | Gain held at 372 pending an averaged re-test | Accepted (interim) · **OPEN** | 2026-07-04 (S16) |
| DEC-0021 | Rain-counter glitch filter (the false-rain fix) | Accepted · released v2.0.3 | 2026-07-04 (S18) |
| DEC-0022 | Sensor-QC hardening deferred to a dedicated pass | **Resolved** by DEC-0029 (S33) | 2026-07-04 (S18) |
| DEC-0023 | Independent per-repo session counter | Accepted · **supersedes** DEC-0013 | 2026-07-04 (S20) |
| DEC-0024 | RF-reception metric ~150%: freqError channel packets published as loop packets | Monitor fixed (S27/S31); driver **Layer B OPEN**, deferred → v2.0.5 (S34) | 2026-07-04 (S21; upd. S22/S31) |
| DEC-0025 | Known-bad data: preserve-and-flag, never delete | Accepted | 2026-07-05 (S29) |
| DEC-0026 | v2.0.3 confidence gate waived: cut on tests + live evidence | Accepted | 2026-07-05 (S29) |
| DEC-0027 | Lint scope: enforce `ruff check`, not `ruff format`; exclude vendored uploaders | Decided | 2026-07-08 (S31) |
| DEC-0028 | Leaked credential in pushed public history: rotate immediately, don't rewrite | Decided | 2026-07-08 (S32) |
| DEC-0029 | Decode-layer sensor plausibility filter (temp/humidity/wind/UV/radiation) | Accepted · **resolves** DEC-0022 · cause **confirmed** by DEC-0033 | 2026-07-08 (S33) |
| DEC-0030 | Docs diet: tiered session read, DEC index+full split, CHANGELOG roll, STATUS prune | Accepted | 2026-07-09 (S35) |
| DEC-0031 | The driver is BAKED into the image, never bind-mounted (supersedes DEC-0004's driver half) | Accepted | 2026-07-12 (S36) |
| DEC-0032 | Retrospective correction: correct to the KNOWN value, flag it in-band (`rain_qc`) | Accepted · **clarifies** DEC-0006 | 2026-07-12 (S36) |
| DEC-0033 | Glitches are CRC-valid multi-bit corruption from spurious duplicate frames (upstream #15) | Accepted · **confirms** DEC-0029 · **confirmed locally** by DEC-0035 | 2026-07-12 (S36) |
| DEC-0034 | State the fork honestly: modification notices, `+ws` version, CHANGES-FROM-UPSTREAM | Accepted | 2026-07-12 (S37) |
| DEC-0035 | Duplicate-frame mechanism CONFIRMED here (~722/day); the test that said otherwise was broken | Accepted · **confirms** DEC-0033 | 2026-07-12 (S37) |
| DEC-0036 | The 7h18m freeze: trigger known (bare `docker logs` wedged the daemon), **mechanism OPEN**; mitigations banked | Accepted · **mechanism open** | 2026-07-13 (S37) |
| DEC-0037 | A retrospective correction must propagate to every derived field | Accepted · **extends** DEC-0032 | 2026-07-13 (S37) |
| DEC-0038 | An image tag denotes exactly one tree: publish **v2.0.5**, don't rebuild "v2.0.4" | Accepted · **extends** DEC-0031/0034 · *prod deliberately one patch behind* | 2026-07-13 (S38) |
| DEC-0039 | Secret gate: every allow term **anchored or positioned**; a gate ships with its planted-payload test | Accepted · **extends** DEC-0012 · adopts dash DEC-0063/0100 | 2026-07-13 (S38) |
| DEC-0040 | The cross-repo gap is an **enforcement** gap, not a documentation gap — **no master repo** | Accepted · owner-confirmed (S38) | 2026-07-13 (S38) |
| DEC-0041 | **StdPrint removed** — the v2.0.5 console-handler fix was necessary but NOT sufficient | Accepted · **completes** DEC-0036 · corrects DEC-0038 | 2026-07-13 (S38) |

## Open / deferred

- **DEC-0017** — gain 372 is interim; needs the 24 h averaged no-preamp sweep vs 207.
- **DEC-0024 Layer B** — driver stops publishing dataless freqError packets + persists raw
  `count`/`missed`; deferred to v2.0.5 (S34); No-Rewrite applies, needs its own design + approval.
