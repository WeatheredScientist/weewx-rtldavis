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
| DEC-0017 | Gain held at 372 pending an averaged re-test | Accepted (interim) · open, but **absorbed into DEC-0048's designed RX experiment** | 2026-07-04 (S16) |
| DEC-0021 | Rain-counter glitch filter (the false-rain fix) | Accepted · released v2.0.3 | 2026-07-04 (S18) |
| DEC-0022 | Sensor-QC hardening deferred to a dedicated pass | **Resolved** by DEC-0029 (S33) | 2026-07-04 (S18) |
| DEC-0023 | Independent per-repo session counter | Accepted · **supersedes** DEC-0013 | 2026-07-04 (S20) |
| DEC-0024 | RF-reception metric ~150%: freqError channel packets published as loop packets | **Fully resolved** — Layer A (S22/S31) + **Layer B shipped (S43)**: freqError merged onto the next real DATA packet instead of yielded standalone | 2026-07-04 (S21; upd. S22/S31/S43) |
| DEC-0025 | Known-bad data: preserve-and-flag, never delete | Accepted | 2026-07-05 (S29) |
| DEC-0026 | v2.0.3 confidence gate waived: cut on tests + live evidence | Accepted | 2026-07-05 (S29) |
| DEC-0027 | Lint scope: enforce `ruff check`, not `ruff format`; exclude vendored uploaders | Decided · local pre-commit **brought back in sync** (S43 — `ruff-format` had silently contradicted this since S31) | 2026-07-08 (S31; upd. S43) |
| DEC-0028 | Leaked credential in pushed public history: rotate immediately, don't rewrite | Decided | 2026-07-08 (S32) |
| DEC-0029 | Decode-layer sensor plausibility filter (temp/humidity/wind/UV/radiation) | Accepted · **resolves** DEC-0022 · cause **confirmed** by DEC-0033 | 2026-07-08 (S33) |
| DEC-0030 | Docs diet: tiered session read, DEC index+full split, CHANGELOG roll, STATUS prune | Accepted | 2026-07-09 (S35) |
| DEC-0031 | The driver is BAKED into the image, never bind-mounted (supersedes DEC-0004's driver half) | Accepted | 2026-07-12 (S36) |
| DEC-0032 | Retrospective correction: correct to the KNOWN value, flag it in-band (`rain_qc`) | Accepted · **clarifies** DEC-0006 | 2026-07-12 (S36) |
| DEC-0033 | Glitches are CRC-valid multi-bit corruption from spurious duplicate frames (upstream #15) | Accepted · **confirms** DEC-0029 · **confirmed locally** by DEC-0035 | 2026-07-12 (S36) |
| DEC-0034 | State the fork honestly: modification notices, `+ws` version, CHANGES-FROM-UPSTREAM | Accepted | 2026-07-12 (S37) |
| DEC-0035 | Duplicate-frame mechanism CONFIRMED here (~722/day); the test that said otherwise was broken | Accepted · **confirms** DEC-0033 · **permanent counter shipped (S43)** | 2026-07-12 (S37; upd. S43) |
| DEC-0036 | The 7h18m freeze: trigger known (bare `docker logs` wedged the daemon), **mechanism OPEN**; mitigations banked | Accepted · **mechanism open** | 2026-07-13 (S37) |
| DEC-0037 | A retrospective correction must propagate to every derived field | Accepted · **extends** DEC-0032 | 2026-07-13 (S37) |
| DEC-0038 | An image tag denotes exactly one tree: publish **v2.0.5**, don't rebuild "v2.0.4" | Accepted · **extends** DEC-0031/0034 · *prod deliberately one patch behind* | 2026-07-13 (S38) |
| DEC-0039 | Secret gate: every allow term **anchored or positioned**; a gate ships with its planted-payload test | Accepted · **extends** DEC-0012 · adopts dash DEC-0063/0100 | 2026-07-13 (S38) |
| DEC-0040 | The cross-repo gap is an **enforcement** gap, not a documentation gap — **no master repo** | Accepted · owner-confirmed (S38) | 2026-07-13 (S38) |
| DEC-0041 | **StdPrint removed** — the v2.0.5 console-handler fix was necessary but NOT sufficient | Accepted · **completes** DEC-0036 · corrects DEC-0038 | 2026-07-13 (S38) |
| DEC-0042 | The phantom **rainRate is ISS-side** (condensation trips the reed switch, never tips the bucket) — not RF, not the driver | Accepted · **bounds** DEC-0033/0035 · closes the rainRate thread | 2026-07-13 (S38) |
| DEC-0043 | Override the **root** logger, not just `weewx`/`user` — weewx's default root points at a syslog socket a container does not have | Accepted · **completes** DEC-0036/0041 | 2026-07-13 (S39) |
| DEC-0044 | The **nibble theory is not supported** by the archive, and the archive can never settle it — **instrument, don't filter** | Accepted · **bounds** DEC-0029 · **parks** the coupling filter | 2026-07-13 (S39) |
| DEC-0045 | **A comment is not an exemption** — the secret gate scans comments like code. A commented-out credential in a public repo is still leaked, and the gate's *own test* had asserted it was fine | Accepted · **amends** DEC-0039 · **extends** DEC-0012 | 2026-07-13 (S40) |
| DEC-0046 | **The baked config is shadowed by the prod bind-mount** — an image-only config fix reaches downstream users and *never* reaches prod. The exact mirror of DEC-0031 (where the *image* wins and the mount is the no-op) | Accepted · **mirrors** DEC-0031 · completes the delivery half of DEC-0043 | 2026-07-13 (S41) |
| DEC-0047 | **The secret gate guards commits, not reads — the transcript is an egress path.** A `sed -n '…,+44p'` overran its section and dumped credentials into the transcript; no control existed because nobody had modeled reading as a path. Guard + redacting reader + transcript scanner, all in `~/.claude/`. *(Rotation specifics: gitignored local-infra doc.)* | Accepted · **extends** DEC-0012 · completes DEC-0039/0045 (write path only) · applies DEC-0040 | 2026-07-13 (S41) |
| DEC-0048 | **Reception testing is a designed experiment, not a pile of image tags.** The ad-hoc `rw*-test` images are retired; a proper RX test (hypothesis, control arm, averaged window) is deferred and will settle DEC-0017's gain question in the same run | Accepted · **absorbs** DEC-0017's pending sweep · applies DEC-0038 | 2026-07-13 (S41) |
| DEC-0049 | **The ISS hardware is new and inspected — the phantom rainRate is not a broken part.** DEC-0042's "inspect the bucket + reed switch" action is CLOSED and came back clean, which excludes a defective part and sharpens DEC-0042: it is working hardware reacting to condensation. Anemometer replaced ~16–17 Jun 2026 | Accepted · **bounds** DEC-0042 | 2026-07-13 (S41) |
| DEC-0050 | **The station gets a master for its IDENTITY (and only that): `eaglehunt-ops`** — DEC-0040's revisit triggers fired (5 shared executables versioned nowhere; the gate fix re-derived 4×; dash DEC-0106 = the predicted casualty). Private coordination repo per the S38 §Etiquette litmus test: canonical `station-identity.env` + drift check (first run 8/9 within 19 m, the 9th a real HLF finding), NAS runtime contract, the `~/.claude/` guards versioned with tests, issues as the cross-repo inbox. NOT a master repo; deletion clause. Also: `soak_check.sh` identifiers scrubbed to fail-fast placeholders (they were live on public `dev`; CI is structurally identifier-blind — `.identifiers` is gitignored), and **pre-commit was configured but never installed in ANY of the three clones** — now actually installed | Accepted · **executes** DEC-0040's revisit clause · owner-approved (cross-repo round, dash S74) | 2026-07-14 (S42) |
| DEC-0051 | Cold-load Fix B ships (`current.json` alongside `loop-data.txt`); `windchill` added — closes issue #44 | Accepted | 2026-07-15 (S43) |
| DEC-0052 | Adopt eaglehunt-ops' shared closeout skeleton, adapted — docs-diet + DEC log kept as-is, model-tier restore check added as step 5 | Accepted · **adapts** OPS-DEC-0016 · closes weewx#56 | 2026-07-19 (S44) |

## Open / deferred

- **DEC-0017** — gain 372 is interim; the averaged no-preamp sweep vs 207 is now **part of DEC-0048's designed RX experiment**, not a standalone errand.
