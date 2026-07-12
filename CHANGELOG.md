# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

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
