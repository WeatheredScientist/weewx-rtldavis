# Changelog Archive — weewx-rtldavis

**Append-only archive · read on demand (DEC-0030).** Older session entries moved here **verbatim**
from `CHANGELOG.md`, which keeps only the last ~3 sessions live (the Tier 1 session read). Same
format: most recent first, session-tagged (`[S16]`, `[S17]`, …), release tags called out inline.
Nothing here is rewritten — text moves, history stays greppable.

---

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



## [S33] — 2026-07-08 — Bad-packet root cause + decode-layer sensor plausibility filter (DEC-0029, on `feature/s33-sensor-qc`, off `dev`)

The owner-priority bad-packet session. Evidence-first (owner: "pull the raw packet logs first;
let's be methodical"), then design approval, then code. **Not yet merged or deployed** — the driver
is baked, so this ships with the next image rebuild (v2.0.4).

- **Post-release health check (read-only): clean.** Container on `:v2.0.3`, `RestartCount=0`
  (expected post-reboot start 07:02 EDT), 0 rain rejections ever, monitor WINDOW 21/21 (100%).
- **Evidence dead end that matters:** the `RAW_CHANNEL_PAYLOAD` log lines never contained packet
  payloads — only frequency-hop metadata — and the v2.0.3 upstream-default binary silenced even
  those (weewx.log 16.6 → 7.5 MB/day). **No bit-level packet capture exists**; the archive DB
  (68,877 records, 2026-05-19→07-08) became the evidence base.
- **Root cause CONFIRMED from the archive** (details in DEC-0029): 18 one-minute **outHumidity**
  glitch spikes under flat radiation + flat temp, deviations clustering at 25.6/3 and 12.8/2 —
  the bit-7/bit-8 flip signature of the raw %×10 field; a physically impossible **UV 16.29** under
  overcast; midday-only pattern shown to be a **selection effect** (night glitches land >100% RH →
  StdQC nulls → carry-forward masks). **outTemp/wind archives clean** — dashboard temp + 201 mph
  wind spikes ride the unfiltered loop-JSON path (`LoopJsonWriter` runs before all QC). S30's
  suspected `MAX_WIND_DELTA` unit bug **disproven** (post-StdConvert = mph, correct).
- **Fix (DEC-0029): `SensorQC` decode-layer filter in `rtldavis.py`**, applied in `_data_to_packet`
  (rain's choke point): Davis-spec bounds (temp −40..65 °C, hum 0..100%, wind 0..89.4 m/s, UV 0..16,
  rad 0..1800 W/m²) + per-reading delta with baseline-resync (temp 4 °C, hum 10%, wind 20 m/s, UV 8;
  **no delta for radiation** — cloud edges are genuine). Honest null on rejection (DEC-0006), logs
  `"rejecting implausible value"`, rejected wind also nulls same-packet `wind_dir`. Config:
  `sensor_qc` master switch + `qc_<field>_max_delta` overrides (documented in `weewx.conf.example`).
- **DEC-0022 closed: `dewpoint_service.py` carry-forward → timeout-null.** The temp/hum/rad/UV cache
  still bridges the message-type rotation but expires after 300 s of sensor silence; dewpoint/
  heatindex computed only from fresh values. Failed sensors now read null, not frozen.
- **Tests:** `test_sensor_qc.py` (16, recorded signatures: +25.6% humidity flip, UV 16.29, 201 mph)
  + `test_dewpoint_timeout_null.py` (6). **Suite 85/85**; `ruff check` clean; secret scan green.

## [S32] — 2026-07-08 — v2.0.3 RELEASED (`v2.0.3` + `prod-baseline-20260705`); S31 monitor live; Gmail app-password rotation

**v2.0.3 released end-to-end.** Soak day 4 = clean, so the S30 hold cleared: 24 h `rxCheckPercent`
avg **75.4%** (1427/1429 records populated, min 50 / max 105 — the known floor-division cosmetic),
**0** rain-glitch rejections since the Jul-5 deploy, `RestartCount=0`, and the container rode out an
*unplanned NAS reboot* (~06:57) with a clean dongle handoff — the strongest soak evidence we could
have asked for. Only third-party upload blips (Windy/WOW 429s, a transient OWM outage). Steps:

- **PR #15** — `main`'s independent S26 secret-gate commits (PR #7) conflicted with `dev`'s (PR #6) on
  `ci.yml`, making the promotion PR un-mergeable; merged `main` into `dev` once, keeping `dev`'s
  DEC-0027 `ci.yml` (no `ruff format` gate). *(First attempt took the wrong side of the conflict —
  caught by CI's lint job doing exactly what DEC-0027 built it for, fixed before merge.)*
- **PR #11 merged** — `dev` → `main` (`f64f8d8`); `main` = production truth again.
- **Tagged `v2.0.3` + `prod-baseline-20260705`**; **GitHub release** published with the S30-drafted
  notes; **Docker Hub push `:v2.0.3` + `:latest`** (same digest `9dfd9b57…`, 281 MB) — the first
  public image that actually contains the driver fixes (rain filter, `rxCheckPercent` H2, honest-null
  wind, clobber fix).

**S31 monitor deployed + verified live — after diagnosing a reboot-broken boot task.** The morning's
NAS reboot restarted the `weewx_monitor` esynoscheduler task as a **non-root user**: its
`/etc/sudoers` append got Permission-denied and `sudo -u weewx-monitor` failed every 5 min ("a
terminal is required"), so the monitor was **down 06:56→17:28** with sudo-spam filling its log. Owner
reset the task user to root. Since the monitor was down, the S31 deploy needed no kill: scp'd `dev`'s
`weewx_monitor.py` (sha `23dfa03d…` verified; backup `weewx_monitor.py.bak-20260708-105410`), owner
ran the task, and the new code came up clean — pidfile written, incremental byte-offset polling,
startup email delivered ("Eagle Hunt PWS": `STATION_NAME` is now set, closing that housekeeping
item). First 6 h dropped-packets summary due at the next 00/06/12/18 boundary.

**Security — Gmail app password exposed in public history; rotated same-day (DEC-0028).** Found the
monitor's Gmail app password hardcoded in the legacy NAS `weewx_monitor.sh` *and* in two public-repo
history commits of `weewx_monitor.py` (`d2fb080` May 22, `eff3f56` May 24 — reachable from `main`+
`dev`, exposed ~6 weeks; the DEC-0012 gate scans trees/diffs, not history, so it never fired). Owner
revoked the credential, issued a replacement into the NAS `monitor.env` (via a clipboard-pipe
one-liner after interactive-prompt approaches failed through the `!` runner), and the monitor's
startup email verified SMTP auth on the new value. Legacy script's copy neutered to a placeholder.
**No history rewrite** — rotation kills the credential's value; force-pushing a public repo's history
doesn't un-leak it (DEC-0028).


---

*Older entries (S31 and earlier, back to [Pre-S16]) live in `CHANGELOG-ARCHIVE.md` — moved
verbatim, append-only (DEC-0030). Roll the oldest live entry there at session close once this file
exceeds ~3 sessions.*
## [S31] — 2026-07-08 — RF reception metric audited; daily email re-sourced from rxCheckPercent

**Audit finding:** the daily RF-reception email measured publish *liveness*, not reception. It counted
`Wunderground-RF: Published` log lines ÷ expected/min — a count padded by the freqError freq-hop
publishes (DEC-0024) so it reads ~100% even during real ~25% packet loss. Live proof: 14 straight
minutes pinned at "100%" while the driver's own `rxCheckPercent` ran 59–95% (median 75%); the metric's
only movement off 100% is a crash to 0% during a total stall. That bimodal 100↔0 behaviour, plus the
denominator churn (24→dedup→21) and the old ~150% reading, is why the numbers had been "all over the
place." The honest metric — the driver's `rxCheckPercent` (good CRC-decoded packets / theoretical max
per archive period) — was already in the archive DB; the email just wasn't using it.

**Layer A (monitor-only, no image rebuild):** re-source the daily summary from the archive's
`rxCheckPercent`. The email now reports packets **transmitted / received / dropped** plus hourly mean +
min — not "windows above a threshold." Verified against the live DB: 2026-07-06 = mean **75%**, 30,720
transmitted, **~7,701 dropped**. Read-only DB access with a safe fallback to the legacy scrape summary
on any hiccup; real-time `WINDOW` logging + outage alerting left unchanged (No-Rewrite, DEC-0014).
`tests/test_reception_db_summary.py` (+7); **suite 61/61**. Refines DEC-0024 (its epoch-dedup fixed the
*count*; this fixes the *source*). **Deploy = monitor restart (owner-run scp + `sudo kill`), not yet
done.** Driver-side follow-up (persist raw packet counts; fix the ~1–2 pt floor-division optimism)
folds into a later driver build.

**Reception summary cadence: daily → every 6 h (env-tunable).** A once-a-day midnight report was being
read the next morning — too late to act. The summary email now fires every `RF_REPORT_INTERVAL_HOURS`
(default **6** = 00/06/12/18 local; set 12 for twice-daily or 24 for the old daily cadence), aligned to
local-midnight blocks and reporting the window that just closed. Generalized `db_reception_summary` to
explicit epoch bounds + added `period_floor`/`period_label`; the formatter now labels the window and
lists only its hours. Verified live (mean 75%, ~1,900 dropped per 6 h window). `+2` tests, **suite
63/63**. Ships with the same monitor deploy as Layer A above.

**Also this session — CI lint made honestly green (DEC-0027).** The `lint` job had been red on every
branch (incl. `dev`) — a broken check erodes the "`main` = production truth" signal. Audited the debt:
27 `ruff check` findings (17 in vendored code, 10 ours) + `ruff format --check` wanting to reformat 25
files incl. the baked driver. Decision: lint what we maintain, don't police style or vendored code —
(1) dropped the `ruff format --check` CI gate (the codebase uses deliberate column alignment; the
driver is baked → reformatting it is No-Rewrite churn), (2) excluded vendored uploaders (`influx.py`,
`wcloud.py`, `ogoxeUploader.py`) via new `ruff.toml`, (3) fixed the 10 findings in our code
(`rtldavis.py` unused imports + bare `except`; `weewx_monitor.py` import split; test ambiguous `l`→`ln`;
`ops/*` unused imports). `ruff check .` now passes; driver logic + formatting untouched. Merged via PR #13.

---

## [S30] — 2026-07-05 — v2.0.3: driver fixes finally go live (clobber fix + build)

**Built (native amd64 on the NAS) and deployed to prod.** After deploy, `rxCheckPercent` went
NULL→real (**70–82%**) within two archive cycles — the driver's honest reception metric alive for the
first time since 2026-06-18, proving the clobber fix baked the patched driver. Packets flowing, clean
dongle handoff (no USB reset), old `rw250-test` image kept for rollback. *Still owner-gated: promote
`dev`→`main` + tag `v2.0.3`, GitHub release, Docker Hub push.*

The image folds in H1/H2/M3 (already on `dev`) plus:

- **Dewpoint service — wind honest-null (ported from the reviewed Jun-16 draft).** `_filter_wind` no
  longer substitutes the last cached `windSpeed` into a packet whose `windSpeed` is `None`. The Davis
  ISS transmits wind in **every** anemometer packet (`rtldavis.py:1122`), unlike temp/humidity/rain/UV
  which rotate across message types — so `windSpeed` is `None` only when the reading is genuinely absent
  (a "no sensor" raw `0,0` packet) or was just delta-rejected as a corrupt spike. In both cases an honest
  null is correct; a stale carried-forward value looks like live wind when there is none (e.g. a failed
  vane) and is harder to diagnose. Calm air still writes an explicit `0.0`, so charts stay continuous.
  Archive records aggregate many LOOP packets, so an occasional null packet does not blank the record;
  uploads omit nulls rather than sending bad data. **Temp/humidity/radiation/UV keep the carry-forward**
  for now — those rotating sensors legitimately miss most packets (DEC-0022 sensor-QC hardening, later).
  New `tests/test_dewpoint_wind_honest_null.py` (5 tests); **suite 54/54**.
- **receiveWindow reconciled (ARCHITECTURE §6).** Dropped the `Dockerfile` `sed 300→350` patch so the
  build ships the **upstream-default receiveWindow** — v2.0.3 carries only the proven software fixes, not
  the unproven rw350 experiment (its 24 h sweep stays backlogged). `main.go` is left unpatched.
- **Dockerfile clobber fixed — the driver fixes actually ship now (major).** `Dockerfile:101` did
  `cp /opt/weewx-data/bin/user/rtldavis.py …/site-packages/user/rtldavis.py`, overwriting the patched
  driver `COPY`'d one step earlier with the **stock** driver that `weectl extension install` lays down
  from upstream `src.tgz`. Since weewx imports `user.*` from the venv `site-packages/user/` (confirmed on
  the running container three ways: the weewx path resolver, `.pyc` presence only in that dir, and a
  content grep showing the live driver has **no** `rain_delta_tips` and the deadlocked H2), **every built
  image has shipped the stock driver** — no rain filter, no H1/H2/M3. This explains both open mysteries at
  once: `rxCheckPercent` NULL (stock's `pct_good_all` deadlock) *and* the July-4 phantom rain entering the
  archive (no live rain filter). Driver hot-swaps were landing in `data/bin/user/` — a path weewx does not
  import. Removed the clobbering `cp` (kept the `__init__`/`extensions` touches). With this, the v2.0.3
  rebuild bakes the patched driver → weewx imports it → the **rain filter, H1/H2/M3, and dewpoint
  honest-null go live for the first time**, and the public Docker Hub image finally contains them. *(The
  reception-metric fix and ERR-0001 were the NAS monitor + a DB edit, not the driver — those were already
  live.)*
- Bumped the `Dockerfile` header `v2.0.2 → v2.0.3` and refreshed the stale rtldavis `COPY` comment.
- **Committed `logging.additions` — the build was not reproducible from a clean clone.** `Dockerfile:80`
  `COPY logging.additions` referenced a file that was **untracked** (present only in the owner's checkout,
  never committed, not gitignored), so `docker build` from a fresh `git clone` failed at that step. Found
  when the v2.0.3 image was built on the NAS from the `dev` tarball. Also de-duplicated its contents (the
  `[Logging]` block had been accidentally appended twice). Now tracked → the image builds from a clean
  checkout on any host.

## [S29] — 2026-07-05 — RF-metric honesty, rxCheckPercent root cause, ERR-0001 correction

Turned the "how is reception really doing?" question into trustworthy answers, and reconciled the
July-4 rain glitch. Two owner-run prod steps deployed live (agent-guided, read-only-verified).

- **Reception "91%" was a denominator artifact — fixed + deployed.** The monitor divided the WU-publish
  count by a hardcoded **24**, but this ISS (Transmitter 4) transmits every ~2.8125 s → only ~**21.3**
  records/min are physically sent. Live measurement: **21.75/min**, ~2.78 s mean spacing, no multi-second
  gaps → **~100% reception**, not 91%. Set `WU_RF_EXPECTED` → **21** (env-overridable per station) and
  added `wu_pct()` (single source of truth, capped at 100). New `tests/test_reception_pct.py` (9 tests);
  **suite 49/49**. Merged **PR #10 → `dev`** (also carries the S28 M-A/L-B incremental read) and
  **deployed** (monitor restart); live log flipped `WINDOW: 22/24 (92%)` → **`WINDOW: 23/21 (100%)`**.
- **`rxCheckPercent` root-caused (dead since 2026-06-18).** The driver's own honest reception metric
  populated the archive 2026-05-26 → 2026-06-18 18:42 UTC (avg **67.5%**, the pre-LNA baseline), then
  went NULL. Traced to a **weewx engine reload at 2026-06-18 14:44 EDT** whose code carries the S24 "H2"
  `pct_good_all` deadlock (`rtldavis.py:1006` guards the assignment with `… and pct_good_all is not None`,
  but it's reset to `None` every period → can never pass). **Fix already on `dev`** (`:1011`,
  regression-tested); ships with the v2.0.3 image rebuild. (Reception genuinely improved ~70% → ~100% via
  the LNA between June and July — right when both honest metrics were dark.)
- **DEC-0025 — known-bad data: preserve-and-flag, never delete.** New public append-only
  **`docs/DATA_ERRATA.md`** + the reconciliation model (as-transmitted / errata / corrected best-estimate).
- **ERR-0001 applied — July-4 phantom honest-nulled.** The +1.28" 3 AM glitch (old driver, `rain_count=-64`
  → +128) was confirmed baked into the archive **and** the Weather Underground record (day total **1.84"**;
  MADIS almost certainly too — precip is barely QC'd downstream). Owner nulled the two 3 AM records
  (`dateTime IN (1783148640, 1783148700)`) + `weectl database rebuild-daily --date=2026-07-04`; July-4 rain
  **1.84" → 0.56"** — surgical (the day's genuine 0.56" evening rain preserved). InfluxDB copy still carries
  it (cross-repo follow-up); external WU/MADIS immutable, reconciled by the errata.
- **DEC-0026 — v2.0.3 confidence gate waived.** Cut the release with the rain fix baked in rather than wait
  weeks for a live glitch; the fix is already protecting prod, is tested, and the pipeline was validated
  end-to-end this session.
- **Housekeeping:** merged PR #10 (branch deleted). `dev` now carries rain + reception (metric + denominator)
  + governance + S24/S25 code-quality. **Next session ships v2.0.3** (image rebuild on Mac Docker Desktop →
  redeploy → promote `dev`→`main` + tag → GitHub/Docker Hub → live-confirm `rxCheckPercent` repopulates).

## [S28] — 2026-07-05 — Monitor incremental read (M-A/L-B) + branch cleanup

Release still calendar-gated (no real rain glitch yet); this session cleared the unblocked follow-ups.

- **P1 verified (read-only, live).** Rain wild-watch: **0** `rejecting implausible counter delta`
  events across the full log range (2026-06-05 → now) — the first real glitch still hasn't fired, so
  v2.0.3 stays parked. Reception Layer A confirmed live: WINDOW **88–100%**, 5-window avg **91–92%
  [OK]**, 0 bad windows; monitor healthy (PID alive under the esynoscheduler wrapper). Layer B
  signature still present live (driver emits `RAW_CHANNEL_PAYLOAD`/`FreqError` + double-publishes the
  same record epoch — exactly what Layer A dedups; weewx.log ~10 MB/day).
- **M-A + L-B: monitor incremental byte-offset read (PR #10 → `dev`, draft).** Replaced
  `get_linecount()` + `get_new_lines()` — which each re-read the whole (~10 MB/day, growing)
  `weewx.log` on every 30 s poll — with a single byte-offset read: `get_log_size()` +
  `get_new_lines(offset)` → `(lines, new_offset)` via one `seek()`. Fixes the O(n)-per-poll re-scan
  (**M-A**) and the double-open size/read race that double-counted appended lines (**L-B**, resolved
  for free by the `seek()`). Rotation (`get_log_size() < offset` → reset) + partial-line (hold back a
  line with no trailing newline) guards. New `tests/test_monitor_incremental_read.py` (6 tests);
  **suite 40/40**; secret-scan green; `lint` red (known pre-S24 ruff baseline, non-blocking).
  **Not yet deployed** — owner-gated (scp + `sudo kill`, same as Layer A).
- **Branch housekeeping.** Deleted merged remote branches `s20-governance-hardening` and
  `feature/influxdb-grafana` (moved off Grafana to Influx; its only driver-relevant bit — the
  wind-warmup one-liner `3f5470f` — was already in `dev`). `s27-p3-deployed` was already
  auto-deleted on PR #9's merge (stale local ref pruned). Remote-URL casing was already correct
  (both no-ops). Remote now: `dev`, `main`, `feature/rain-spike-filter` (kept for v2.0.3),
  `feature/s28-monitor-incremental-read`.
- **Still owner/calendar (→ S29):** review + merge + deploy PR #10; watch for the first real rain
  glitch → then cut v2.0.3; rotate the exposed WU key; set `STATION_NAME` in the NAS `monitor.env`
  (emails currently fall back to "My PWS").

## [S27] — 2026-07-05 — Land the secret gate + collapse the review stack onto `dev`

Tied up the S23–S26 PR backlog (five open, nothing merged). No prod/driver code touched; all the
review work landed on `dev`, and `main` got only the secret gate.

- **Secret gate now blocking (P1).** Merged **PR #6 → `dev`** (`90ef51b`) and **PR #7 → `main`**
  (`490e776`) — `main` previously had zero secret scanning. CI on both merge commits: `secret-scan` =
  pass, `lint` = fail (expected pre-S24 ruff, non-blocking to the gate). Then set **`secret-scan` as a
  required status check** in branch protection on `dev` + `main` (via the keyring token — the PAT's 403
  was a scope problem; `enforce_admins: false`, no required reviews). The DEC-0012 gate is no longer
  advisory.
- **Governance/review stack collapsed onto `dev` (P2).** The whole stack merges clean — the predicted
  `ci.yml`/`check_secrets.sh` conflict never materialized because the stack's S20 gate fix (`2a6327c`)
  is byte-identical to dev's #6 fix. Retargeted **PR #5** (`feature/s24-code-quality-review`, whose tip
  already carried reception-dedup + s23-governance + s24/s25) to base `dev` and merged it (`2c75c5e`),
  bringing all S18–S26 work — the rain fix, reception Layer A, the S23 governance docs (LICENSE/AGENTS/
  ASSESSMENT), and the S24/S25 code-quality fixes — onto `dev` in one gated merge (secret-scan green,
  34/34 tests). Closed **#3** and **#4** as merged-via-#5.
- **S23 tail closed.** Folded the 8 still-open items from the retired root `cleanup_backlog.md` into
  `BACKLOG.md` (dedup'd against what it already carried) and deleted `cleanup_backlog.md` + the
  duplicated `logging.additions` fragment (`7025afa`).
- **`main` untouched beyond the gate.** The `dev`→`main` v2.0.3 promotion stays parked pending the rain
  fix's first wild glitch + the dewpoint rebuild.
- **Reception Layer A DEPLOYED live (DEC-0024).** scp'd the dev `weewx_monitor.py` to the NAS (backup
  `weewx_monitor.py.bak-20260705-141508`), `sudo kill`ed the monitor; the esynoscheduler `sleep 300`
  wrapper respawned it on the new code. **Confirmed**: the RF WINDOW metric dropped from a steady
  ~150–162% to **92%** (`22/24`) on the first post-restart window — same packet volume, correct
  epoch-dedup. Reversible via the backup.
- **Still owner/calendar actions (→ S28):** watch for the first real rain glitch; rotate the exposed WU
  key; the influxdb-grafana cherry-pick + stale-branch cleanup; remote-URL casing; set `STATION_NAME`
  in `monitor.env` (emails currently fall back to "My PWS").

## [S26] — 2026-07-05 — Fix the secret gate's mainline coverage (draft PRs #6 → dev, #7 → main)

A dashboard (dash) cross-repo note flagged the ported DEC-0012 secret gate as neutered and warned this
repo's gate "almost certainly has the same hole." Verified empirically — the concern is real, but not
where the note assumed. **No prod/driver code touched; two draft PRs, nothing merged.**

- **Diagnosis (empirical).** The neuter bug — the `grep -n` `<lineno>:` prefix matched the docstring
  allow-rule's bare `:` and silently whitelisted real `ident = secret` lines — was **already fixed** on
  the governance feature-stack in S20 (`2a6327c`, `:` → `[A-Za-z]:`); the current gate catches a planted
  secret assignment (a real-looking `api_key` value) that the old gate passed clean. But the fix
  never reached the mainline:
  - **`main`/`origin/main`** — **no `check_secrets.sh` and no `ci.yml` at all.** A fresh clone of the
    public default branch had zero secret scanning.
  - **`dev`/`origin/dev`** — the **neutered S17 gate**, *and* its secret-scan was the last step of a
    single CI job behind `ruff check`, which fails on the pre-S24 tree (32 errors) — so the whole job
    went red at ruff and the scan never ran. Doubly dead.
- **PR #6 → `dev`** (`s26-secret-gate-dev`) — replaced `check_secrets.sh` with the fixed version; split
  `.github/workflows/ci.yml` into an independent **`secret-scan`** job + a `lint` job so a lint failure
  can never skip the gate.
- **PR #7 → `main`** (`s26-secret-gate-main`) — added `check_secrets.sh` (fixed) + the two-job `ci.yml`
  + `.pre-commit-config.yaml` (main had none of the apparatus).
- **Verified.** On both PRs, CI **`secret-scan` = pass** (clean tree) and **`lint` = fail** (expected,
  pre-S24 ruff; non-blocking to the gate). Locally: planted secret caught (exit 1); the fixed gate scans
  each whole tracked tree clean (exit 0, no false positives).
- **Open (→ S27):** (1) mark **`secret-scan`** a **required** status check in branch protection on `dev`
  + `main` (needs repo admin; PAT 403'd) — until then CI is advisory, not blocking. (2) Reconcile the
  s20→s24 governance stack's old single-job `ci.yml` to this two-job structure when it merges. (3) Review
  + merge #6 then #7. Cross-repo finding recorded; the corrected takeaway for dash: verify against the
  branch that actually carries the fix, and confirm its own gate uses the `[A-Za-z]:` guard.

## [S25] — 2026-07-05 — Finish the S24 review fixes (on `feature/s24-code-quality-review`)

Completed the S24 review's deferred tail. **Branch-only, not deployed;** the driver changes still ride
the next rebuild + hot-swap. No-Rewrite honored — every change is surgical. Full offline suite green
(34/34: the prior 29 + 5 new `owm` tests).

- **U1/U2 (`owm.py` rebase)** — the uploader overrode `RESTThread.run_loop` with a hand-rolled
  `queue.get`/`urlopen` loop, silently discarding every resilience knob it was constructed with
  (`post_interval`/`max_backlog`/`stale`/`max_tries`/`retry_wait`/`skip_upload`) — a transient network
  failure dropped the record with no retry. Re-based on the standard hooks: kept `format_url`, moved the
  JSON body to `get_post_body(record) → (body, 'application/json')` (the same contract `influx.py`
  uses), deleted `run_loop`/broken `post_request`/`import time`/unused `urllib.request`. RESTThread now
  owns retry/backoff. New `tests/test_owm_post_body.py` (5 tests: kwargs forwarded, hooks not
  overridden, body shape + km/h→m/s conversion, None-field omission, appid URL).
- **U4 (`influx.py` TLS)** — `post_request` unconditionally used `ssl._create_unverified_context()` for
  any `https://` endpoint (silent MITM exposure). Added a `verify_ssl` option (**default `True`** =
  verifying context; explicit opt-out restores unverified for self-signed/internal endpoints), wired
  through the service `__init__` + `InfluxThread`, documented in the docstring. Moot for the current
  local `http://` Influx; drop-in.
- **M4 (dead code)** — deleted `_fmt` (py2-only `ord()`) and `parse_readings` from `rtldavis.py`; both
  had zero callers repo-wide.
- **L6 (driver nits)** — fixed the per-transmitter debug guard to test the list *element*
  (`stats['pct_good'][i] is not None`) instead of the always-truthy list; hoisted `_stderr_sample_count`
  init out of the hot read loop into `__init__`; annotated the unreachable `elif lines:` branch. **L5:**
  documented the `@staticmethod`-that-takes-`self` convention at `parse_raw` rather than restructuring.
- **Nit sweep** — `weewx_monitor.py`: narrowed three bare `except:` → `except OSError:`, and made the
  three hardcoded `/volume1/...` paths env-overridable (`WEEWX_RTLDAVIS_DIR`/`MONITOR_LOG`/
  `MONITOR_PIDFILE`/`WEEWX_LOG`) for parity with the env-sourced credentials. `windy.py`: replaced the
  `__import__('queue')` wart with a normal `import queue`. `influx.py __main__`: `os.environ[...]` →
  `.get(...)` so `--version`/`--help` no longer `KeyError`, and fixed the `InluxDfB` typos.
  `ogoxeUploader.py`: reconciled the contradictory `server_url` comments and logged the real
  hardcoded URL instead of `None`.
- **SPDX** — added per-file `SPDX-License-Identifier: GPL-3.0-or-later` headers to the driver + all
  reviewed satellites (`rtldavis`, `weewx_monitor`, `owm`, `windy`, `influx`, `ogoxeUploader`, `wcloud`,
  `loop_json_writer`).
- **Deferred (still, → S26):** **M-A** (monitor incremental read) and its coupled **L-B** (double-read
  race) — both wait for the DEC-0024 Layer A monitor deploy so they don't step on the queued
  `weewx_monitor.py`. The S24 driver fixes (H1/H2/M3) + these still need the rebuild/hot-swap.
- Verified: `py_compile` clean on all 8 touched modules; offline suite **34/34 green**; secret-scan
  passes on every changed file.

## [S24] — 2026-07-05 — Code-quality review + first fixes (on `feature/s24-code-quality-review`, stacked on S23)

Reviewed the driver and its satellites, then fixed the two real bugs plus the log-bloat source. **Fixes
are branch-only; the driver ones need a rebuild + hot-swap and are NOT deployed.** No-Rewrite honored —
every change is surgical.

- **`docs/CODE_REVIEW_S24.md` (new)** — deliverable-of-record: ranked findings across `rtldavis.py`
  (1506 ll), `weewx_monitor.py`, and all uploaders (`owm`/`windy`/`ogoxe`/`wcloud`/`influx`) +
  `loop_json_writer.py`. Draft **PR #5**, based on the S23 branch. Records a verification note: a
  candidate `setDaemon`/`setName` finding was **dropped** after testing against the live Python 3.14.5.
- **H1 (`0929952`)** — `parse_raw` unknown-channel branch referenced an undefined `raw` (param is
  `pkt`) → `NameError` inside `genLoopPackets` instead of the intended log line. One-line fix +
  `tests/test_parse_raw_channel.py` (proven to fail with the exact NameError pre-fix).
- **H2 (`970c47e`)** — `pct_good_all` bootstrap deadlock: `_update_summaries` only set it under a guard
  that also required it to be non-`None`, but `_init_stats`/`_reset_stats` null it every period, so the
  driver's own `rxCheckPercent` was **never populated** (likely why the log-scraping monitor exists).
  Dropped the self-defeating clause + `tests/test_reception_stats.py` (drives two archive periods +
  `new_archive_record`; fails pre-fix). Live-confirm `rxCheckPercent` on deploy.
- **M3 + U3 (`8872947`)** — the `weewx.log` bloat (DEC-0024 Layer B family): gated the driver's
  per-packet `RAW_CHANNEL_PAYLOAD`/`RAW_RTL_HOP`/`RAW_RTL_STDERR_SAMPLE` INFO logging behind
  `debug_rtld`, and dropped `influx.py`'s per-record `loginf` → `logdbg` (also fixed the "Bindding"
  typo). Pure log-level changes, no behavior change.
- **Deferred (in STATUS handoff → S25):** M-A (monitor incremental read — waits for the Layer A deploy
  to avoid stepping on it), U1/U2 (`owm.py` RESTThread rebase for retry/backoff), U4 (`influx.py` TLS
  verification), and the M4 dead-code + minor-nits + SPDX-header sweep.
- Verified: full offline suite **29/29 green** (H1 2, H2 2, plus the existing 25); secret-scan passes
  on every changed file; both edited modules `py_compile` clean.

## [S23] — 2026-07-05 — Cross-project governance alignment (on `feature/s23-governance-alignment`)

Docs-only, **no driver or prod code touched, not deployed.** Piloting a shared governance standard
across the three-repo Eagle Hunt family (this repo is the pilot; ASSESSMENT.md §2/§5).

- **`docs/ASSESSMENT.md` (new)** — cross-repo governance audit (weewx vs `eaglehunt-weather-dashboard`
  vs `hyperlocal-forecast`), the "isolate content / harmonize form" alignment model, a draft
  **Governance Standard v1** (shared core + per-repo profiles), ranked recommendations, and the
  pilot→harvest→propagate roadmap toward a generic project template.
- **`LICENSE` (new)** — GPLv3, verbatim canonical text (reused from `hyperlocal-forecast` for
  guaranteed-correct text + cross-repo consistency). Fills the gap of a public, published tool with no
  license; ecosystem-standard for a WeeWX-derived work. Per-file SPDX headers deferred to the S24 review.
- **`AGENTS.md` (new)** — cross-agent entrypoint (the `AGENTS.md` convention) pointing at CLAUDE.md +
  STATUS.md, so a non-Claude agent or human can pick the repo up from GitHub alone.
- **ROADMAP restructured** — shared `P0–P4` vocabulary mapped to short/medium/long horizons; folded to
  post-S22 reality with ✅ done-markers and a "vision" preamble; added the P0.5 governance-alignment
  workstream. P0 governance bootstrap marked done.
- **STATUS.md made the single source of truth** for the session number (DEC-0023) and the
  **next-session handoff moved into the repo** (out of Claude-private memory, now a pointer) — the
  north-star fix so handoff state is visible on GitHub. Doc-map reordered to put STATUS at slot #2.
- Verified: secret-scan gate (DEC-0012) passes on all changed files; docs-only diff.

## [S22] — 2026-07-05 — Merge PR #2 + reception metric Layer A fix (on `feature/reception-dedup`, off `feature/rain-spike-filter`)

Picked up the S21 handoff. No driver or prod code touched; not yet deployed.

- **Merged PR #2** (`s20-governance-hardening` → `feature/rain-spike-filter`): the S20 governance work
  (independent numbering DEC-0023 + two `check_secrets.sh` gate fixes) now rides with the rain fix
  toward v2.0.3. Resolved three append-conflicts keeping both S20 and S21 content (CHANGELOG S21→S20,
  DECISIONS DEC-0023 above DEC-0024, STATUS last-updated). Merge commit `1a265e7`.
- **Reception-metric Layer A fix (DEC-0024, `20bf7c0`):** `weewx_monitor.py` counted raw
  `Wunderground-RF … Published` log lines, but the driver publishes freqError freq-hop packets as
  duplicate publishes of the **same record epoch** — over-reading reception to ~150%. A live read-only
  sample (2026-07-05) showed a clean 2× (same `(epoch)` posted twice). Fix: a pure `wu_record_key()`
  helper dedups on the trailing `(<unix_epoch>)`; the window now counts **unique epochs**.
  `close_reception_window` + the driver are untouched. 6 offline tests
  (`tests/test_reception_dedup.py`). **Deploy = monitor restart only** (respawn loop reloads on-disk
  code); reversible. **Layer B stays deferred.**
- **Live read-only check (SSH):** confirmed no rain glitch has fired in the wild yet (v2.0.3 promotion
  still calendar-bound); verified the live `weewx_monitor.py` was byte-identical to the repo copy
  (md5 match) before patching.

## [S21] — 2026-07-04 — Reception metric ~150% root cause (DEC-0024) + numbering made independent (on `feature/rain-spike-filter`)

Investigation + governance, **no driver or prod code touched**. (The S20 governance-hardening
CHANGELOG entry rides in separately via draft PR #2 — see below.)

- **Reception-metric ~150% — root cause confirmed (DEC-0024, OPEN).** Live read-only diagnosis: the
  daily RF-Reception emails over-count because `weewx_monitor.py` counts `Wunderground-RF: Published`
  *log lines* ÷ `WU_RF_EXPECTED`(=24), but the driver publishes freqError freq-hop `CHANNELPacket`s as
  extra **dataless loop packets** (~1.66×; live sample 1605 publishes / 968 unique record epochs,
  single Transmitter:4). True reception was ~90%. Cosmetic — real weather data + the rain fix are
  unaffected. Documented Layer A (monitor counts unique epochs — safe, monitor-restart-only) vs
  Layer B (driver stops publishing dataless freqError packets + disable `RAW_*` debug logging; also
  fixes the 15 MB / 122 k-line `weewx.log` bloat). Fix **deferred** (diagnosis + docs only).
- **Doc-vs-reality flag:** BACKLOG claimed the Go binary emits no `ChannelIdx`/`FreqError`; the running
  binary emits **both** — the likely trigger. BACKLOG finding corrected.
- **Session numbering made independent per-repo (DEC-0023, supersedes DEC-0013).** A forensic audit
  showed the "shared lineage with the dashboard" premise never held (the dashboard runs its own
  continuous S1→S40 counter and never referenced a shared one). Each repo now counts its **own**
  sessions; number from *this repo's* CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S21` vs
  `dash S40`); this repo's line is contiguous S16→…→**S20**→**S21**. The prior draft PR that tried to
  *reunify* into a shared counter (mislabeled "S40") was reworked into the **S20** governance-hardening
  session and now rides as **draft PR #2** (`s20-governance-hardening`; PR #1 auto-closed by the branch
  rename). That branch also carries two real `check_secrets.sh` fixes.

## [S20] — 2026-07-04 — Governance hardening: independent session numbering + fix secret-scan gate (on `s40-governance-hardening`, off `feature/rain-spike-filter`)

Governance audit ("does our governance make sense, is it robust, is it aligned with the sibling
repos") + the fixes it surfaced. No driver/prod code touched.

- **Session numbering made independent (DEC-0023, supersedes DEC-0013):** a forensic audit showed the
  "shared lineage with the dashboard" premise never held — the dashboard runs its own continuous
  S1→S40 counter and never referenced a shared one; this repo's DEC-0013 invented a parallel counter
  that re-used numbers (S16–S19) the dashboard had long passed. Resolution: **each repo counts its own
  sessions**; number from *this repo's* own CHANGELOG/STATUS +1; prefix cross-repo refs (`weewx S20`
  vs `dash S40`). This repo's line stays contiguous **S16→S17→S18→S19→S20**. (An earlier draft of this
  session tried to *reunify* into the shared counter and relabel this session "S40"; reversed before
  merge so `main` never sees the detour.) Updated `CLAUDE.md`, `docs/STATUS.md`.
- **Secret-scan gate hardened (`scripts/check_secrets.sh`)** — the load-bearing DEC-0012 gate, two bugs:
  1. **False-negative (serious, latent since S17):** the generic assignment-style detector (branch b)
     was effectively **dead**. Its allow-list runs against `grep -n` output, and the docstring-param
     rule `:[[:space:]]*[A-Z][a-z]` matched the `<lineno>:` prefix (e.g. `1:api_key = "…"` → the `:a`),
     silently whitelisting virtually every real `ident = "secret"` line. Tightened to `[A-Za-z]:…`
     (require an alpha char before the colon) so the numeric prefix no longer matches. Verified: a
     planted fake credential (an `sk_live_…`-style token assignment) is now caught; the whole tracked
     tree still scans clean (no new false positives); genuine docstring params still allowed. (This
     very reword was itself flagged by the fixed gate — dogfooding. The S16 leaks were caught by the
     *identifier* branch, which skips this filter — so the hole went unnoticed.)
  2. **Empty-array crash:** threw `files[@]: unbound variable` under `set -u` when run by hand with no
     staged files (bash-3.2 empty-array expansion). Added a clean-pass guard so the manual whole-tree
     audit path fails safe. CI (`git ls-files | xargs`) and pre-commit were already unaffected by both.
- **Doc note (`docs/CONVENTIONS.md`):** the macOS dev box has only `python3` (no bare `python`); the
  prescribed `python -m …` validation commands don't run verbatim locally — noted, plus how to run
  the secret gate standalone.
- **Audit verdict:** governance is coherent and well-aligned with the dashboard's nine-file model
  (intentional, documented divergences: `INTERFACES.md` ← `DATA-MODEL.md`, added `BACKLOG.md`); the
  one real drift was STATUS.md going stale after the S18 deploy — already reconciled in `689b12c`.

## [S18] — 2026-07-04 — False-rain fix (on `feature/rain-spike-filter`, off `dev`)

Confirm-first diagnosis then fix for the phantom-rain bug. Not yet deployed (pending a dry-window
live hot-swap) or merged. Target release v2.0.3.

- **Diagnosis (read-only):** root cause confirmed from code + archive DB + driver logs — the driver
  treated *any* negative rain-counter delta as a 127→0 wraparound and added 128, converting an
  RF-decode glitch into phantom rain. Two events found in 63k archive records: 2026-05-25 (1.28",
  exceeds the world 1-min rainfall record) and 2026-07-04 (0.64"×2, `rain_count=-64` in the log),
  both flat-zero-bracketed and false vs the WeatherLink Live console. Corrected two prior
  assumptions: the counter is 7-bit (not 8-bit), and the recent event was −64→+64 (not a single +128).
- **Fix (`rtldavis.py`):** extracted the pure `rain_delta_tips()` helper (DEC-0021) — only near-−128
  deltas are wraparounds; small-negative and >60-tip (0.60") deltas → `None` (null-on-rejection,
  DEC-0006). Self-documenting docstring explains the bug for future readers.
- **Tests (`tests/test_rain_filter.py`):** 13 offline cases against the exact recorded signatures
  (both glitches reject; real −127 wraparounds and normal rain pass); stubs weewx so it runs with no
  install, wired for CI.
- **Backstop (`weewx.conf.example [StdQC]`):** `rain 0,10 → 0,1.0`; added `rainRate 0,16` — the
  live-config edit happens at deploy time.
- **Audit found (deferred to S19, DEC-0022):** `dewpoint_service.py` still substitutes stale
  temp/humidity/radiation/UV (DEC-0006 violation); minor windGust/radiation/UV StdQC gaps.
- **Email alert (`weewx_monitor.py`):** watch the weewx log for the driver's rejection line and
  email on each caught glitch (reusing the monitor's existing Gmail + log-tail; the driver stays
  pure I/O-free). Reports the counter values and the false rainfall the old code would have
  recorded. `--test-alert` sends a sample email for verification. Detection unit-tested
  (`tests/test_rain_glitch_alert.py`, 6 cases — no false positives on real wraparounds/uploads).
  DEPLOYED (rain driver + StdQC) to the live container 2026-07-04 via reversible hot-swap with an
  in-container import pre-flight; verified healthy. Monitor file staged; alert activates on the next
  monitor restart.

## [S17] — 2026-07-04 — Documentation governance bootstrap (on `dev`)

- Authored the nine-file governance package modeled on `eaglehunt-weather-dashboard` (DEC-0010):
  `CLAUDE.md` + `docs/{PRINCIPLES, CONVENTIONS, DECISIONS, ARCHITECTURE, INTERFACES, ROADMAP,
  STATUS}` + `CHANGELOG.md` + `BACKLOG.md`.
- `DECISIONS.md`: backfilled genesis ADRs DEC-0001…0009 (reconstructed, approximate dates) and
  recorded the governance-era decisions DEC-0010…0017 (governance model, branch model, secret
  hygiene, session numbering at S16, No-Rewrite, hyperlocal tooling graft, Opus 4.8 driver, and the
  interim gain-372 amendment).
- `INTERFACES.md`: documented the two consumer contracts — the loop-JSON real-time surface (field
  table + units + sparse-field caching) and the InfluxDB 2.x line-protocol schema — so the driver
  stays re-pointable toward non-Davis / CumulusMX producers (PRINCIPLES §1).
- Added Python tooling grafted from the hyperlocal-forecast repo (DEC-0015): `.pre-commit-config.yaml`
  (ruff, ruff-format, secret-scan) and `.github/workflows/ci.yml`.
- All authored on `dev`; `main` untouched.

## [S16] — 2026-07-04 — Reconcile repo with production reality → `prod-baseline-20260704`

The published repo had drifted badly from the live NAS system; the drift ran in *both* directions
(GitHub missing runtime files, but also GitHub *ahead* with corrupted uploaders). Captured what is
actually running as the truth on `main`. Commit `7e79d15`, tagged `prod-baseline-20260704`.

- **Added** runtime/driver files missing from the repo: `rtldavis.py` (the driver), `influx.py`,
  `loop_json_writer.py`, `ogoxeUploader.py`.
- **Fixed corrupted uploaders**: GitHub's `owm.py`/`windy.py` had stale duplicate class definitions
  appended that shadowed the clean RESTThread classes (Python uses the last definition) — a latent
  regression for anyone deploying from the public repo. Reconciled to the running versions.
- **Synced infra** stale v2.0.1 → live v2.0.2: `Dockerfile` (rtl-sdr pkg, `receiveWindow` patch,
  influx2 install, COPY steps) and `entrypoint.sh` (dropped syslogd, added `rtl_biast -b 1` bias-tee).
- **Regenerated `weewx.conf.example`** from the live config with maximum scrub (all credentials,
  station IDs, `station_url`, coordinates, and the InfluxDB org name → `YOUR_*` placeholders).
- **Curated `docker-compose.yml`** to driver-only; documented the hot-swappable extension mounts and
  treated downstream consumers (InfluxDB, dashboards) as external (DEC-0010, INTERFACES).
- **Expanded `.gitignore`** (secrets, backups, logs, data, dashboard artifacts, vendored deps).
- **Versioned `ops/`** RF/operational tooling under clean canonical names (dropped version-numbered
  sweep iterations); `wxcheck.sh` scrubbed of a hardcoded WU API key + PWS id.
- **Secret hygiene:** three real leaks caught and scrubbed pre-commit (a hardcoded WU API key + the
  PWS id in `wxcheck.sh`; a station-location chart title in `gain_sweep_analyze.py`; the InfluxDB
  org name). Verified the tracked tree carries zero personal identifiers.
- Resolved the four verify-at-start items: gain is live at **372** (not 207); the v2.0.3 dewpoint fix
  never shipped; the `rw250-test` Dockerfile exists (no reconstruction needed) but diverges toward
  rw350; live `weewx_monitor.py` matches GitHub.
- Discovered `v2.0.2` was never git-tagged (DEC-0003 gap); the vestigial `loopdata.py` mount.

---

## [Pre-S16] — pre-governance history (reconstructed, approximate)

- **v2.0.2** (~2026-05-31, built, never git-tagged): baked-in `rtldavis.py` windDir patch,
  `rtl_biast -b 1` bias-tee in `entrypoint.sh`, `rtl-sdr` package added.
- **v2.0.1** (~2026-05-29): RF reception monitoring in `weewx_monitor.py`, wind-filter iterations,
  elevation fix, StdCalibrate wind offset, STATION_NAME de-personalization.
- **v2.0-ubuntu26** (~2026-05-26): Ubuntu 26.04 / Python 3.14 multistage build (979 MB → 278 MB).
- **v1.0-ubuntu22** (~2026-05): original working image, Ubuntu 22 base.
- Extensive RF tuning (gain/fc/ppm/receiveWindow sweeps), the custom `loop_json_writer.py`, and the
  11-service upload chain were built across these sessions. See BACKLOG.md for the durable RF findings.
