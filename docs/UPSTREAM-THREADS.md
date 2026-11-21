# Upstream — open contribution threads

**Last updated:** 2026-11-21 (S210d: every row re-read with `gh`; times US Eastern)

**Needs a reply from us today: none owed.** One optional: jbonzey's 2026-11-19 suggestion on
[weewx-packages#15](https://github.com/weewx-packages/weewx-rtldavis/issues/15) (reject early frames
relative to the expected arrival time) is what our Go gate already does; a draft with our figures is
in `docs/upstream/weewx-packages-15-relative-gate.md`, the owner's call to post.

**Tier 2 — pull by name from `MANIFEST.md`.** Live state for our contributions back to the projects
this fork descends from. `BOOT.md` carries only the one-line "four open threads" reminder; the
detail lives here so it doesn't cost a session start.

**Watch for replies.** `lheijst` has not commented on any of our threads (last seen 2026-07-09; no
reply to the 2026-11-18 close offer on #15). `weewx-influx2` has been quiet since 2023, so that one
may simply sit. As of 2026-11-21 the open PRs below show no lheijst or david-lutz activity at all;
the only movement upstream is hilman2's 2026-10-21 comments and the weewx-packages test threads.

**Etiquette (DEC-0034, and the S38 litmus test):** state the fork honestly — modification notices,
the `+ws` version suffix, `CHANGES-FROM-UPSTREAM.md`. Drafts are owner-reviewed before posting and
**never posted without an explicit go**. Credit other people's diagnoses by name and number. Any
internal-only detail (our own version numbers, session/DEC references) stays out of the posted text
entirely — an upstream reader has no context for either. **Draft structure (S126 feedback):** put
the actual postable text first, set off with a loud banner (`>>>>> ONLY THIS GETS POSTED <<<<<`),
then a second loud banner before any internal status notes — a small heading after a long preamble
isn't enough; it cost a round-trip when the owner assumed the whole draft was going out.

**Drafts live in `docs/upstream/` — a gitignored directory, deliberately not tracked.** This file is
the tracked *state* of the threads; that directory is the untracked *prose* awaiting review. Don't
conflate them, and don't commit the drafts.

## Open

- **[lheijst/rtldavis#7](https://github.com/lheijst/rtldavis/pull/7)** — the byte-only duplicate
  filter drops the ISS's genuine repeat packets and books each as a miss (DEC-0134). Measured 80 of
  81 misses in 15 min; real loss 0.3%. Fix is a time gate on `lastRecMsg`, deployed on our own
  hardware since v2.0.15 (DEC-0136). **POSTED 2026-09-06** (owner-approved, trimmed to ~70 words
  from an over-long first draft) via a fork (`WeatheredScientist/rtldavis`, branch
  `fix/time-gate-duplicate-filter`) — issues are disabled on this repo, so a PR was the only option,
  no existing thread to reply into. **OPEN.** hilman2 commented 2026-10-21: the weewx-packages
  continuation (v0.21.1) accepts repeats at ISS intervals with a per-transmitter two-second guard,
  tests included, credit in their `docs/credits.md`. No word from lheijst (checked 2026-11-21: still
  OPEN, nothing newer than hilman2's comment; the repo's other open PRs are equally untouched).
  LloydR's [`#2`](https://github.com/lheijst/rtldavis/pull/2)
  sits in the same function, still open since 2023-02-11, fixes a different failure mode
  (content-agnostic near-duplicates) — complementary, not conflicting; credited in the PR body. Repo
  is much quieter than `weewx-rtldavis` (last push before this PR: 2023-12-22) — may sit a while.
- **[lheijst/weewx-rtldavis#23](https://github.com/lheijst/weewx-rtldavis/pull/23)** — the temp-sign
  + `0xFF8` companion PR (S55, owner-reviewed before posting). Credits LloydR's #19 for the
  diagnosis; offers the masked 12-bit two's complement as an alternative (#19's 16-bit-signed ÷16
  leaks the `pkt[4]` flag nibble, a +0.05 °F constant). **OPEN** (checked 2026-11-21). Our side shipped as DEC-0055. hilman2 commented 2026-10-21: the
  signed-field and sentinel fixes are in the continuation's v0.21.1, credited in their
  `docs/credits.md`. No word from lheijst.
- **[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22)** — the
  rain-counter wraparound fix: the handler treated *any* negative delta as a 127→0 wrap and added
  128, producing phantom rain. **OPEN.** Our side shipped as DEC-0021 (v2.0.3). hilman2 commented
  2026-10-21: the continuation's v0.21.1 keeps the previous baseline after a rejection, with
  regression tests for 115 to 49 to 115 and a transmitter reset. No word from lheijst (checked
  2026-11-21: still OPEN). We posted on the issue #15 thread 2026-11-18 offering to close this PR if
  the continuation is where the fix lives; awaiting lheijst's word.
- **[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1)** — TLS
  verification on by default (it was a **silent** verification bypass) plus four more fixes.
  **OPEN**; that repo's first-ever PR. The only review is CodeRabbit's (a bot, 2026-07-13), two
  valid points: `influx.py:501` still `loginf`ed per record, and `verify_ssl` was undocumented.
  **Both fixed and replied 2026-10-29** (S181, owner's go): commit `0c5d394` on the fork branch
  `fix/tls-verification-and-py312-compat` (`logdbg`, plus a `verify_ssl` line in the readme's option
  list), then the reply as a PR comment. The maintainer has not commented (checked 2026-11-21: still OPEN, last activity our 2026-10-29
  reply).
- **[matthewwall/weewx-wcloud#6](https://github.com/matthewwall/weewx-wcloud/issues/6)** — **POSTED
  2026-10-29** (S181, owner's go, after DEC-0226). The repo ships no license file or license wording, so
  our vendored `wcloud.py` is tagged `NOASSERTION`; the issue asks him to add one (GPLv3 suggested).
  **OPEN.** On an answer, change the tag to match and drop the header note. Of his 63 `weewx-*`
  repos, 39 carry a GPLv3 license file and 24 none (checked 2026-10-29). Checked 2026-11-21: still OPEN, zero comments, no answer.
- **[weewx-rtldavis#514](https://github.com/WeatheredScientist/weewx-rtldavis/issues/514)** (this
  repo, opened by hilman2, the continuation's author) — asks us to test their Python port of the Go
  receiver (weewx-packages release 0.22.x, simulated transmitters only so far) and to join
  weewx-packages as a maintainer. **Holding reply POSTED 2026-10-30** (owner's go, S184): we test in
  early December on the second dongle beside the Go decoder, post numbers either way, and decide on
  maintaining after the test. Asked them for Pi CPU figures and option stability. **OPEN** (checked 2026-11-21: last comment is cdavis289's 2026-11-10 pointer to the results
  thread; nothing owed, the December test is ours to run). Test
  plan in `BACKLOG.md` "Open ideas"; the hardware request is eaglehunt-ops#440.
  **cdavis289's first results, 2026-11-10**
  ([weewx-packages/weewx-rtldavis#15](https://github.com/weewx-packages/weewx-rtldavis/issues/15)):
  Go v0.21.2 beside Python v0.22.2 on a VP2 Plus, one Ubuntu 26.04 x86_64 host, two Nooelec NESDR
  SMArt v5 dongles, 1,186 matched five-minute intervals. Mean reception 99.558% Go, 99.851%
  Python; intervals under 100%: 420 Go, 65 Python; no missing archive record on either. Python
  lost sync twice (11-08 and 11-10, about 45 s to reacquire; its worst interval was 33%, Go's
  95%). Average CPU 27.2% Go, 18.9% Python, not an identical workload. Anomalous gusts appear on
  both. Each receiver had its own dongle, so receiver and dongle are confounded: their next test
  swaps the dongles and adds sync and USB diagnostics. **For our A/B:** swap dongles between
  arms; record sync losses and the worst interval, not the mean alone; check whether their Go arm
  has an arrival-time gate like ours (DEC-0229) before comparing figures. Their diagnostics fork
  ([cdavis289/weewx-rtldavis-py](https://github.com/cdavis289/weewx-rtldavis-py), branch
  `feature/gust-anomaly-diagnostics`) logs frames around a gust anomaly plus sync and USB events.
  **Replied 2026-11-10** (S198, owner's go,
  [comment](https://github.com/weewx-packages/weewx-rtldavis/issues/15#issuecomment-6785518922)):
  ERR-0012 as a CRC-valid phantom gust, and the message-9 `windGust10` cross-check as a flag that
  discards nothing. No further reply owed on that. **Since then (read 2026-11-21, thread still OPEN):** cdavis289 posted
  the crossover results (dongles swapped: routine reception follows the dongle and RF path, not the
  language), then a Phase C update 2026-11-17 (Python lost sync for 114 s after 52 missed frames,
  11% interval while Go held 100%; diagnostics widened), then 2026-11-18 evening ET a Phase C2
  update: a CRC-valid frame 822.7 ms early at about -6.15 kHz preceded a 52-frame loss and a 27.5 s
  recovery, and an experimental 300 ms early-arrival guard (commit `eb9306c`, branch
  `feature/phase-c-receiver-diagnostics`) is now under test. jbonzey (2026-11-19) noted 0.22.2's
  fixed 2.0 s burst guard (BURST_GUARD) lets a 2.18 s frame through, reported 7 early-frame
  rejections in about 11 days from a 0.5 s Go patch (173,789 accepted frames since 11-14, none more
  than 0.2 s off the 2.5625 s rhythm), and suggested a guard relative to expected arrival, about
  0.2 s. Related: weewx-packages
  [#18](https://github.com/weewx-packages/weewx-rtldavis/issues/18) (jbonzey's V4 results) and
  [#19](https://github.com/weewx-packages/weewx-rtldavis/issues/19) (a failed tune is never
  retried), both open; weewx-packages v0.23.0 released 2026-11-17 (adds fractional wind speed). This
  is the same mechanism as our DEC-0229 gate (100 ms off schedule, three drops in prod, none with a
  gap), so we have figures they lack: **optional reply, draft ready**, owner's call. Relevant to the
  December A/B: the Python arm should be tested with and without an early-frame guard.

## Posted / closed

- **[weewx-contrib/weewx-rtldavis#2](https://github.com/weewx-contrib/weewx-rtldavis/issues/2)** —
  **POSTED 2026-10-29** (S180, owner's go), **CLOSED by vinceskahan 2026-10-29** as "not interested
  in implementing it but thank you for the info". His reply: not interested in patching the upstream
  code, the repo exists to make the whole stack installable by mortals in one place; suggests the
  two forks of Luc's code agree on one active one, and a scripted build/install; offers an
  AI-generated Python port tarball and its spec; saw phantom rain in the past, not in his latest
  two-day test; sees the duplicate packets. No reply owed; a reply is the owner's call.
- **[weewx-packages/weewx-rtldavis#6](https://github.com/weewx-packages/weewx-rtldavis/issues/6)** —
  **POSTED 2026-10-29** (S180, owner's go), **CLOSED by hilman2 2026-10-29**: fixed in their #7,
  released in 0.22.0; the version check is gone, the receiver now runs in Python inside WeeWX, and
  `--action show-packets` became `python3 -m user.rtldavis`. Credits two changes taken from this
  fork: dropping frames with a message type no transmitter sends (DEC-0203) and the EU frequency
  offsets riding on the observation packet. 0.22.0 is the version the December A/B (#514) tests.
- **[lheijst/rtldavis#2 comment](https://github.com/lheijst/rtldavis/pull/2#issuecomment-6499785445)**
  — **POSTED 2026-10-29** (S180, owner's go). DEC-0223's mechanism (preamble offsets straddling a
  512-sample block; copies 1 to 13 samples apart) and our sample-position gate, placed next to
  LloydR's wall-time gate and hilman2's per-transmitter one; points at
  `patch/rtldavis-burstgate.patch`. No field result claimed (the watch was 1 h 42 min).
- **[Issue #15 comment](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128)**
  — **POSTED 2026-07-13** (owner-approved). The first comment on that thread since **2022-11-14**.
  Explains the duplicate-frame mechanism (DEC-0033/0035), the wraparound bug, and — the part that
  mattered most to that thread — that the phantom **`rainRate` is ISS-side, not a driver bug**
  (DEC-0042). Three people there had been hunting it in software.
