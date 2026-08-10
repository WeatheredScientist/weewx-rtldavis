# Upstream — open contribution threads

**Tier 2 — pull by name from `MANIFEST.md`.** Live state for our contributions back to the projects
this fork descends from. `BOOT.md` carries only the one-line "four open threads" reminder; the
detail lives here so it doesn't cost a session start.

**Watch for replies.** `lheijst` was active as recently as 2026-07-09; the `weewx-influx2` repo has
been quiet since 2023, so that one may simply sit.

**Etiquette (DEC-0034, and the S38 litmus test):** state the fork honestly — modification notices,
the `+ws` version suffix, `CHANGES-FROM-UPSTREAM.md`. Drafts are owner-reviewed before posting and
**never posted without an explicit go**. Credit other people's diagnoses by name and number.

**Drafts live in `docs/upstream/` — a gitignored directory, deliberately not tracked.** This file is
the tracked *state* of the threads; that directory is the untracked *prose* awaiting review. Don't
conflate them, and don't commit the drafts.

## Open

- **[lheijst/weewx-rtldavis#23](https://github.com/lheijst/weewx-rtldavis/pull/23)** — the temp-sign
  + `0xFF8` companion PR (S55, owner-reviewed before posting). Credits LloydR's #19 for the
  diagnosis; offers the masked 12-bit two's complement as an alternative (#19's 16-bit-signed ÷16
  leaks the `pkt[4]` flag nibble, a +0.05 °F constant). **OPEN.** Our side shipped as DEC-0055.
- **[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22)** — the
  rain-counter wraparound fix: the handler treated *any* negative delta as a 127→0 wrap and added
  128, producing phantom rain. **OPEN.** Our side shipped as DEC-0021 (v2.0.3).
- **[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1)** — TLS
  verification on by default (it was a **silent** verification bypass) plus four more fixes.
  **OPEN**; that repo's first-ever PR.

## Posted / closed

- **[Issue #15 comment](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128)**
  — **POSTED 2026-07-13** (owner-approved). The first comment on that thread since **2022-11-14**.
  Explains the duplicate-frame mechanism (DEC-0033/0035), the wraparound bug, and — the part that
  mattered most to that thread — that the phantom **`rainRate` is ISS-side, not a driver bug**
  (DEC-0042). Three people there had been hunting it in software.
