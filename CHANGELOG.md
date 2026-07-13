# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S38] — 2026-07-13 — v2.0.5 → **v2.0.6** SHIPPED; the gates now execute instead of asking nicely

> **v2.0.5 was an incomplete fix, and v2.0.6 finishes it (DEC-0041).** v2.0.5 moved the console log
> handler to `WARNING` and I claimed that made weewx's stdout nearly silent. **It did not.**
> `report_services = weewx.engine.StdPrint` `print()`s **every LOOP packet straight to stdout**,
> bypassing the logging module entirely — no log level touches it. It was writing **~25 MB/day** into
> the very pipe that froze prod for 7h18m, and because it is a **weewx stock default** it was in the
> baked image *and* our `weewx.conf.example`, so **every downstream user had it too**.
>
> Found by finally checking the thing nobody had checked — the actual `log.db` sizes (needs root):
> `weewx-rtldavis-v2` had accrued **15 MB in 14 hours**. The mitigation had been *reasoned about from
> the architecture* instead of *measured at the source*. One `sudo du` would have caught it.
>
> **Fixed everywhere:** prod (`report_services =`, restarted — stdout growth now **0 lines/60 s**,
> was ~36); the baked image config, **with a build-time assertion that fails the build if the edit
> no-ops**; and `weewx.conf.example`. Shipped as **v2.0.6**. Also removed `/weewx`, a container **dead
> since 2026-05-04** still holding the **largest `log.db` on the box (47 MB)** — dead containers keep
> their log store forever.

**The headline: `v2.0.5` and `latest` are on Docker Hub.** Downstream users had been getting the
**stock driver** (DEC-0031) *and* the **console-handler freeze hazard** (DEC-0036) on every `docker
pull` since 2026-07-08. That stopped at 12:55 today. It is the only item in this session that had an
ongoing external cost, and it is closed.

**Why v2.0.5 and not v2.0.4 (DEC-0038).** The `v2.0.4` image on the NAS was built at **15:44 on
07-12 — eight hours before the freeze that produced DEC-0036**, so it never contained the fix the
release was being cut for. A rebuild was mandatory either way. Republishing different content under
`v2.0.4` would have made one tag name two different images, which is the *same* lie as DEC-0031 and
DEC-0034 — the artifact asserting one thing and being another. `v2.0.4` was never on Hub, so nothing
public breaks. **Prod deliberately stays on `:v2.0.4`** and `prod-baseline` has NOT moved: the delta is
behaviorally nil here (prod's `weewx.conf` has no console handler at all — the config drift that spared
us), and redeploying prod unattended, hours after a seven-hour outage, to fix something that does not
affect prod, is the wrong trade. **A catch-up deploy is owed.**

**S37 never landed, and that is its own lesson.** All of S37 — three ADRs, the fork-identity audit, the
duplicate-frame confirmation — was sitting in **draft PR #23** and had never merged to `dev`. CI green,
branch pushed, nothing shipped. Found and merged at the top of this session. It is the direct
motivation for the session-start hook below.

**The secret gate, hardened and PROVEN (DEC-0039).** The bug class, stated once: *an allow term that
can match anywhere on the line is not an allow-list, it is an escape hatch — the secret sits on the
left and the excuse on the right.* `token = REAL  # falls back to os.environ` passed the old gate
clean. Every allow term is now **anchored** or **positioned against the key the detector matched**, and
the `grep -n` prefix bug is fixed at the root (bash parameter expansion; the allow-list runs on raw
lines) rather than compensated for with `^[0-9]+:` anchors. Ships with
`scripts/test_check_secrets.sh`: **13 planted payloads that must be caught, 14 good lines that must
pass, plus a clean-tree check — 28/28.** It runs in CI *before* the scan. It earned its keep
immediately by catching a hole in **the fix being written to close the previous hole**, and then by
catching the ADR that described it. CI also now runs the **67 unit tests**, which it never did.

**The cross-repo question, answered (DEC-0040): the gap is an ENFORCEMENT gap, not a documentation
gap.** All three options on the table (shared ops repo / vendored fragment / status quo) distribute
*documentation* — and in the worst incident **the rule was already written down**. "`docker logs`
always with `--tail N`" was in `CLAUDE.md` *and* `CONVENTIONS.md` before the freeze; it was followed
for thirty-odd sessions and broken once, and once cost seven hours. **Prose does not execute.**
Decision: **no master repo.** Build a shared enforcement layer instead —
- `~/.claude/hooks/docker-guard.sh` (`PreToolUse`): blocks bare `docker logs` and `docker stop`.
  **19/19 tests**, including a `docker logs` hidden inside `ssh nas "..."` that beat the first draft.
  Verified live.
- `~/.claude/hooks/eaglehunt-status.sh` (`SessionStart`): reports draft PRs, stranded branches and
  uncommitted work **across all three repos**. **On its first run it found a live stranded draft PR in
  the dashboard (#22)** that nobody knew about.
- Branch protection: **`enforce_admins: true`** on `main` and `dev` (checks: `secret-scan`, `lint`,
  `tests`). The S36 bypass is now mechanically impossible, for everyone.

**The Synology `db` log driver cannot be capped — proven, not assumed.** A container run with
`--log-opt max-size=1m` emitted 200,000 lines and **kept all 200,000**. `db` is a proprietary Synology
driver with no published options; the cap is *unsupported*, not undocumented. The daemon accepts the
option and discards it — **the third time in one session** that "the configuration was accepted" did
not mean "the configuration does anything" (cf. the green secret gate, the silent compose clobber).
Also demonstrated, rather than inferred, the DEC-0036 mechanism: retrieving that log **hung for over
three minutes**, and that was a `--tail`-bounded read. Prod was never at risk.

**Provenance, outward half — SENT.** After three sessions of "the fork hasn't given anything back," it
has. Both upstreams forked separately (our distribution repo correctly stays a normal repo, not a GitHub
fork), both PRs **open**:
- **[lheijst/weewx-rtldavis#22](https://github.com/lheijst/weewx-rtldavis/pull/22)** — the rain-counter
  wraparound. Proven against LloydR's own numbers from issue #15: `115 → 49 → 115` now yields
  missing/missing instead of a phantom 1.28″, while genuine wraparounds still work (`127 → 0` = 1 tip).
- **[david-lutz/weewx-influx2#1](https://github.com/david-lutz/weewx-influx2/pull/1)** — five fixes, led
  by a **silent TLS-verification bypass** (`ssl._create_unverified_context()` applied unconditionally to
  every https endpoint, so every user posting to InfluxDB Cloud has certificate verification off and
  their token on an unauthenticated connection). That repo's first-ever PR.
- **The issue-#15 thread response is drafted and NOT posted** — `docs/upstream/issue-15-response.md`,
  awaiting the owner's review for tone. The PR needs nothing; this is the half that explains the
  mechanism to the three people who have been living with it since 2022.

**Prod finished the session on `:v2.0.6`, and `main` == prod again.** Recreated 11:09 EDT; verified
`driver version is 0.20+ws.1 (fork of lheijst 0.20)`, `sensor_qc True`, `influx service version 0.20+ws.1`,
stdout **silent**, every uploader publishing, `RestartCount: 0`. `prod-baseline-20260713` tagged, which
restores DEC-0011's *`main` = production truth* invariant that S38 deliberately broke for a few hours.
Prod's bind-mounted `influx.py` also caught up with the repo (it had drifted — DEC-0031's class again:
the running copy still had `VERSION = "0.20"`, the unconditional `_create_unverified_context()`, and
per-record `loginf` spam; not a live exposure, since the endpoint is plain http).

## [S37] — 2026-07-12→13 — A 7-hour prod freeze, the CRC question answered, and the fork finally admits it is one

Three unrelated things collided. In order of how much they matter.

### The outage: weewx froze for 7h18m (DEC-0036, ERR-0003)

At 23:53:45 weewx stopped doing anything and stayed that way until 07:12. **It did not crash** — both
processes alive, container reporting `Up`, and **no error or traceback ever written, because the thing
that was stuck was the logging.** `weewx_monitor.py` emailed at 00:15 (22 min in — the monitor worked);
the owner was asleep.

- **Established:** weewx's main thread blocked in `pipe_wait`; the Docker daemon's path for *that one
  container* was wedged (`logs`/`exec`/`kill` all hung, other three containers healthy); a **bare
  `docker logs` with no `--tail`** had been hung since the previous day against Synology's SQLite
  `log.db`. Only `synopkg restart ContainerManager` cleared it.
- **NOT established, and the first answer was wrong.** The initial diagnosis — "the INFO console handler
  filled the stdout pipe" — is **false for this station**: the live `weewx.conf` has *no console handler
  at all*. `pipe_wait` covers a blocked pipe **read or write**, and it was read as a write without
  checking. **Mechanism recorded as OPEN.** No causal story was invented to close the ticket.
- **But the console-handler finding is real for the image we publish.** `logging.additions` (baked in by
  the Dockerfile) *does* set the console handler to INFO. Prod escaped only because **the live config has
  drifted from the repo**. Every downstream user has the hazard we did not — the same shape as DEC-0031.
  Fixed to `WARNING`; it reaches users only when v2.0.4 is pushed.
- **Recovery + backfill (ERR-0003):** ~438 one-minute records were **never captured** (nothing was
  cached; the restart discarded nothing). Backfilled 29 records from the co-located WeatherLink Live
  console via the WU history API — same ISS, **different receiver, 15-min cadence** — into both stores,
  flagged in-band `backfill = 1`. The window was dry and dead calm, so the loss is small.

### The CRC question is answered — and the test that answered it first was broken (DEC-0035)

The S36 Lloyd test reported **0 suspicious pairs** over 1,863 frames, with gaps perfectly quantized at
the 2.8 s ISS period. It looked like a decisive null. **It was an artifact — the instrument was blind to
the thing it was built to detect**, twice over: it parsed the driver's `data:` lines, which are emitted
*after* `main.go` has already dropped every duplicate; and its stated premise ("we see spurious frames
even when they fail CRC") is false, because `protocol.go` L218 bails on CRC failure *inside the Go
binary*.

Counting Go's own `duplicate packet:` lines instead: **61 frames arriving 1.4–10 ms (median 2.0 ms) after
a byte-identical frame — ~722/day.** A Davis ISS transmits every 2.8 s and cannot transmit twice 2 ms
apart. **The receiver manufactured them.** DEC-0033 is confirmed on our hardware (LloydR's gap was
262 µs; ours ~2 ms). The 712 duplicates at 2.8 s are just the transmitter repeating an unchanged payload.

This **meets the owner's precondition for the upstream post** (he wanted local confirmation first). The
post is still **not sent** — what remains is prose, in his voice, on his explicit go.

### The fork admits it is a fork (DEC-0034)

We shipped four GPLv3 files with our patches on top and said so **nowhere**, while `rtldavis.py` reported
`DRIVER_VERSION = '0.20'` — stock upstream — carrying +263/−51 lines. Every other link in the chain had
done this properly: Luc documents his merge in the header, and Vince Skahan added a dated
`# 20-12-2025 patched by...` block to the very same file. We inherited the convention and skipped it.

- **GPLv3 §5(a) modification notices** on `rtldavis.py`, `influx.py`, `ogoxeUploader.py`, and `wcloud.py`
  (whose only change is an SPDX line — recorded honestly).
- **Versioned honestly:** `0.20` → **`0.20+ws.1`** (PEP 440 local version) in the driver and the influx
  uploader. The driver now logs `(fork of lheijst 0.20 … not stock upstream)`, which also replaces the
  ad-hoc `RTLDAVIS_DRIVER_MARKER` canary — stock upstream cannot print that line.
- **`CHANGES-FROM-UPSTREAM.md`** — the full inventory, built by diffing against the real upstream
  sources, not from memory. It turned up **more than expected**: `influx.py` carries **five** patches, not
  the one we thought — including `e.read.decode()` (missing parens: the HTTP error handler raises
  `AttributeError` instead of reporting the error) and an unconditional `ssl._create_unverified_context()`
  on https. `rtldavis.py` holds **four** real upstream bugs beyond the rain filter, including a windDir
  branch that never populates wind data and a `NameError` crash path.
- **README rewritten** — it read as though we ship Luc's driver. We don't.

### Also

- **ERR-0001 amendment / DEC-0037** — the phantom-rain correction never propagated to the *derived*
  fields. The dashboard's S70 handoff caught `dayRain_in` still at **1.84″** against a corrected 0.56″;
  auditing found **`rain24_in` (1.84″) and `hourRain_in` (1.28″ — entirely phantom) were wrong too.** All
  three recomputed from the corrected SQLite series and rewritten in InfluxDB (5,394 points, in place,
  idempotent). New rule: *a retrospective correction must propagate to every field derived from it.*
- **Debug state reverted** (`debug_rtld` → 1, `user` logger → INFO). `qc-capture` on the NAS is gone.
- **Cross-project handoff** written for the dashboard + HLF (advisory; **no changes made in their
  repos**), carrying the owner's open architectural question about harmonizing shared NAS-level assets.

*Two confident, internally-consistent, wrong conclusions were reached and retracted in this session — the
"decisive null" and the console handler. Both collapsed the moment the actual artifact was inspected.
Recorded because the pattern matters more than either error.*

---

## [S36] — 2026-07-12 — v2.0.4 SHIPPED: SensorQC live; the driver-clobber found and killed; rain errata closed

The deploy that three sessions had staged and never shipped. Triggered by a handoff from dashboard
session S69, which had walked into this repo's territory, changed the live station, and found that the
bug it was chasing was already fixed here and never deployed. **Prod is v2.0.4; the bad data flowing to
WU/CWOP → NOAA MADIS (where it is immutable) has stopped.**

- **The handoff's recommended deploy path was wrong, and finding out why was the session.** It advised
  hot-fixing the driver by `scp`-ing to the bind-mounted `weewx-data/bin/user/rtldavis.py`. That path is
  **not what weewx imports** — `weewxd` loads `user.*` from the baked venv — and the running container
  had **no `rtldavis.py` mount at all**. The "fix" would have been a silent no-op.
- **The real find: `docker-compose.yml` was mounting the STOCK driver over the baked one.** Line 33 (and
  line 47 of the **public**, committed compose) bind-mounted `weewx-data/bin/user/rtldavis.py` — the
  stock driver `weectl extension install` lays down — straight over the patched one. Prod escaped it only
  because the live container was hand-run without the mount; **every downstream user of the published
  image was running the stock driver** (no rain filter, no SensorQC), regardless of image contents. This
  is the run-time twin of the S30 build-time `cp` clobber. Removed, with a "do NOT re-add" note at the
  exact line. → **DEC-0031** (driver is BAKED, never mounted; supersedes DEC-0004's driver half).
- **v2.0.4 built + deployed** (native amd64 on the NAS, `docker kill` per DEC-0008). Verified against the
  **running process**, not the version tag: `import user.rtldavis` → `SensorQC: True`, `sensor_qc True` in
  the log, `RestartCount: 0`, no driver mount. Reception came back **75–80%** (up from 63–70%). `:v2.0.3`
  retained for rollback. The live `docker-compose.yml` now genuinely describes production (it still said
  `:rw250-test`, an image two releases stale — a loaded gun for any future `compose up`).
- **Rain errata closed — all three phantoms, both stores.** A full-history sweep of InfluxDB and the
  SQLite archive finds **exactly three** implausible rain points ever. ERR-0002 (**new**, 2026-05-25
  23:22 EDT, +1.28" — a bit-7 flip; S69 spotted it, re-verified from scratch here) is now logged and
  corrected; ERR-0001's long-pending InfluxDB correction is finally applied. Both stores now agree
  exactly (2026-07-04 = 0.56", 2026-05-25 = 0.06"), which fixes the public water-balance charts.
  The "no `influx` CLI on the NAS" blocker in STATUS was **false** — there is one in the container.
- **DEC-0032 — retrospective correction: correct to the KNOWN value, flag it in-band.** DEC-0006's
  null-on-rejection rule governs the **runtime filter**, not retrospective correction. The phantoms are
  bracketed by zeros for ±20 min, so `0.0` is a *known fact* and `NULL` would have understated what we
  know. Corrected points carry a sparse **`rain_qc = 1`** flag (3 points in all of history; InfluxDB is
  schemaless, so it costs ~nothing and normal queries never see it) — WMO/MADIS practice, and it gives
  the dashboard its "corrected" marker without a parallel list. `DATA_ERRATA.md` stays narrative truth.
  → **INTERFACES.md** documents `*_qc` as an optional sparse field + pins the `record,binding=archive`
  series key.
- **`scripts/check_secrets.sh` never worked — fixed.** The allow-list ran with `grep -viE`; the `-i`
  erased the `[A-Z]` terms that carry the whole constant-vs-literal distinction, so the ALL_CAPS rule
  (meant to allow `= FOO_KEY`) also swallowed any unquoted lowercase literal — i.e. essentially every
  real secret written without quotes. **The gate was green because it caught nothing.** Now
  case-sensitive (the secret pattern keeps `-i`), plus two further holes closed that were live here *and*
  upstream: `# ` matched a comment anywhere on the line, and the docstring rule passed a capitalized
  single token. Verified 6/6 planted forms blocked, whole tracked tree clean. (Ports the dashboard's
  DEC-0063.)
- **The CRC question answered — DEC-0033 (and a retraction).** Chasing the owner-wanted community bug
  report, we first concluded the corruption *must* be transmitter-side, reasoning that CRC-16 cannot
  miss a single-bit error (verified: 0 of 64 single-bit flips of a valid 8-byte message pass).
  **That inference was invalid** — "catches all single-bit errors" does not imply "catches all errors".
  Raw packets posted by user *LloydR* in upstream issue `lheijst/weewx-rtldavis#15` settle it: two frames
  **262 µs apart** (a Davis ISS transmits every ~2.5 s), differing in **4 bits**, **both passing CRC** —
  the error pattern is a valid codeword. So one transmission is being decoded twice: the *receiver*
  makes the second frame. Model: the rtldavis Go demodulator emits spurious near-duplicate frames; most
  fail CRC and are dropped silently, ~1 in 65,536 passes and delivers garbage. The driver's dedup
  (`data != self._last_pkt`) is **exact-equality**, so a *corrupted* near-duplicate is by construction
  not a duplicate and sails past it. DEC-0029's original stated cause was right; DEC-0033 **confirms**
  it. Both rtldavis.py comments that had propagated the retracted claim are fixed.
- **The upstream contribution is drafted but NOT posted, and held out of git** (public repo). Research
  found issue #15 open since **Oct 2022** with three users reporting this exact symptom class and no
  root cause — so this is a **comment on their thread, not a new issue**. Our analysis explains *their*
  data: LloydR's counter values (115→49→115) run through the upstream handler give 0.62" + 0.66" =
  **1.28"**, matching the "1.3 inches" he reported in 2022. (The handler is wrong twice: once on the
  corrupt jump, once when the sensor returns to the truth.) Maintainer is responsive (commented
  2026-07-09); LloydR's PR #19 covers wind/temps, not rain, so we complement it.
- **`ops/find_duplicate_frames.py` — the "Lloyd test"**, to confirm the mechanism on our own hardware.
  Key property: the driver logs the raw `data:` line **before** the CRC check, so spurious frames are
  visible **even when they fail CRC** — this answers in hours, not weeks. Prod temporarily runs
  `debug_rtld = 2` + `user` logger at DEBUG to feed it (**revert steps in STATUS**).
- **Cross-repo handoff written** — `docs/handoffs/S36-to-eaglehunt-dashboard.md`: answers all three of
  dashboard S69's open questions, documents the new `rain_qc` contract, and returns a reciprocal finding
  (their secret gate still has two live holes we closed here).
- **Doc staleness swept:** ARCHITECTURE §6 claimed the running image was `rw250-test` and the Dockerfile
  "an rw350 experiment" (both stale since S30); CLAUDE.md + CONVENTIONS named the same dead tag. All now
  state the real image and the baked-driver rule. `weewx.conf.example` reconciled with the live station
  (S69's service reorder + tightened StdQC bounds); the stale DEC-0029 comment in `rtldavis.py` fixed.

## [S35] — 2026-07-09 — Docs diet (DEC-0030): tiered session read, DEC index+full split, CHANGELOG roll

Docs-only; no code, no prod change. Ports the family docs-diet pattern — born on the dashboard
(dash S57, its DEC-0081; recipe at `eaglehunt-weather-dashboard:docs/reference/docs-diet-playbook.md`),
proven on hyperlocal (its S143, DEC-0095) — to this repo, closing the three-repo alignment loop.
Session boot drops from ~130 KB ≈ 32K tokens to ~33 KB ≈ 8K tokens. **Invariant honored: text moved
verbatim, nothing rewritten or deleted; all rehomed files passed `scripts/check_secrets.sh` (public repo).**

- **DECISIONS split:** `docs/DECISIONS.md` is now a one-row-per-DEC **index** (+ open/deferred
  list); full append-only bodies moved verbatim to `docs/DECISIONS-FULL.md`. New DEC = full body
  there + index row. Noted explicitly: DEC-0018–0020 were never assigned (numbering gap).
- **CHANGELOG roll:** this file keeps ~3 live sessions; `[S31]` and earlier (back to `[Pre-S16]`)
  moved verbatim to `CHANGELOG-ARCHIVE.md` (append-only, same format).
- **CLAUDE.md doc map → two tiers** (Tier 1 always ≈ 33 KB; Tier 2 on demand, anti-loophole rule:
  *"working near it" means read it*), plus the stale-checkout guard the S35 pickup itself tripped
  over: **current docs live on `dev`** — read from `dev`'s tip if the local checkout lags.
- **Session-close ritual extended:** STATUS prune (shipped → CHANGELOG pointer, settled → DEC
  pointer), CHANGELOG roll, and a secret scan over anything a doc move rehomes.
- **ROADMAP reconciled + collapsed:** P0/P0.6/P1 → DONE pointer summaries (v2.0.3 shipped S32;
  code-quality fixes landed S24–S28); P1.5 → resolved by DEC-0029, deploy rides v2.0.4.

## [S34] — 2026-07-08 — S33 sensor-QC merged to `dev` (PR #17); health check clean; parked stable on v2.0.3

Short close-out session; owner goal: end in a place that holds for days/weeks. No production change.

- **Health check (read-only): clean.** Container on `:v2.0.3`, up 16 h, `RestartCount=0`;
  `rxCheckPercent` 68–80% live (6 h mean 74.6%, min 50, **360/360** minute rows — no archive gaps);
  **0 rain rejections ever**; monitor polling normally.
- **PR #17 merged → `dev`** (merge `db763c8`, checks green: secret-scan + lint): `SensorQC`
  decode-layer filter (DEC-0029) + DewpointCacher timeout-null (closes DEC-0022). **Staged, not
  deployed** — the driver is baked; ships with the owner-run v2.0.4 rebuild.
- **Rebuild pre-verified:** the `dev` Dockerfile COPYs the patched `rtldavis.py` into the venv
  (L99) with the S30 clobber trap explicitly guarded (L101 note) — the v2.0.4 image will genuinely
  contain `SensorQC`.
- **Reception Layer B (DEC-0024) decided: waits for v2.0.5.** v2.0.4 stays single-purpose so its
  live-verification and rollback stay unambiguous; Layer B is cosmetic + log-bloat relief, still
  undesigned (No-Rewrite), and the S31 monitor fix already made the reception emails honest.
- **Backlog: tuning infrastructure idea captured** (owner, S34) — live-tuning control panel and/or
  a statistically sufficient sweep plan (ties into DEC-0017); framing deferred to a future session.

