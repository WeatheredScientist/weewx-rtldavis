# Roadmap — weewx-rtldavis

**Status:** Direction (what next, in what order). For *why* see DECISIONS.md; for *how* see
ARCHITECTURE.md; for *what's on the bench right now* see `BOOT.md` (the single source of truth for
the current session + active thread).
**Last updated:** 2026-08-06 (S66 — **full reconciliation**, see the guardrail below for what it
caught). Prior structural change: 2026-07-28 (S56 — split: P4 + "Longer horizon" moved out to BACKLOG.md's new
"Long-term direction" section, per DEC-0058 — this file is now P0–P3 only, the actively sequenced
plan, so it doesn't get cluttered by uncalendared/aspirational items. Earlier same-session pass:
folded the old P1 + P1.5 sections into one continuous data-integrity arc covering v2.0.3–v2.0.11;
collapsed P0.5's mostly-done checklist to a pointer; added the staleness guardrail below.)

`BOOT.md` holds what's *in motion right now*; this holds the ordered, actively-sequenced plan
(P0–P3 only, per DEC-0058). BACKLOG.md holds unordered near-term ideas **and** long-term/
uncalendared direction — see its "Long-term direction" section for anything horizon-scale.

## Keeping this current (staleness guardrail)

This file went 20 sessions / 8 releases (S35 → S55c, v2.0.3 → v2.0.11) without being updated —
a user-asked audit found it, not anything structural. Two rules to not repeat that:

- **When a DEC lands that ships, closes, or reprioritizes a line item here, update that line in
  the same session** — the same discipline CLAUDE.md already requires for DECISIONS.md ("same
  session, not deferred"). Don't wait for a docs-diet pass or an audit to notice.
- **Next scheduled reconciliation check: by S76** (~10 sessions out). If the session counter is
  at or past S76 and this line still says S76, that itself is the signal it's overdue — run the
  same pass as S56 and S66 did (diff every open/pending item here against DECISIONS.md,
  CHANGELOG.md and `BOOT.md`).
- Last full reconciliation: **S66, 2026-08-06** — all 8 open items diffed. Four were stale and
  fixed: the tiering migration was still unchecked *while its own body said "Executed S60"*; the
  v2.0.12 row had read "BUILDING 2026-08-02" for four sessions when that build no longer exists;
  campaign B's gates were listed as open after DEC-0069/0070/0071 cleared them; and the DB-lock row
  still said "flip WAL once ops#141 lands" **after DEC-0071 had abandoned WAL** — a same-session
  DEC-0057 update that was missed the day before, and exactly what this pass exists to catch. Also
  corrected: the P2 heading still announced "CAMPAIGN A RUNNING", and the archive-DB reader list
  still named the dashboard.
- Earlier: full pass **S56, 2026-07-28**. Targeted DEC-0057 passes at **S63** (DEC-0067) and
  **S66** (DEC-0069).

## The vision

**Own your weather data and let others own theirs.** An RTL-SDR passively intercepts the same
915 MHz Davis broadcast the console hears, so the readings become locally owned and re-pointable —
the "escape the WeatherLink lock" tool. The durable deliverable is not "a Davis driver" but a
**stable, documented data contract** (loop-JSON + InfluxDB schema, INTERFACES.md) that non-Davis
WeeWX, other sinks, and eventually CumulusMX can satisfy (PRINCIPLES §1). Published free under GPLv3
so the community can use and extend it.

## Priority vocabulary (shared across the Eagle Hunt family)

`P0` critical path / do first · `P1` important soon · `P2` later / measured · `P3` modularity ·
`P4` housekeeping / community. Horizon mapping: **short-term = P0–P1**, **medium-term = P2–P3**.
**This file stops at P3 (DEC-0058)** — P4 and anything uncalendared/aspirational lives in
BACKLOG.md's "Long-term direction" section instead, so the active plan doesn't get buried under
long-horizon items. ✅ = done; annotations mark items *found stale during an audit* rather than
deleting the history.

## Guardrails

Full operating rules live in CONVENTIONS / CLAUDE.md. The ones that bite most often: this repo is
**PUBLIC** (secret-scan gate, DEC-0012), **prod is sacred** (one dongle/receiver, deploy-to-dev-first,
DEC-0011), **hot-swap what you iterate / bake what you trust** (DEC-0004), discuss design before
coding, and the **No-Rewrite Rule** (DEC-0014).

---

# SHORT TERM (P0–P1) — foundational work, all ✅ DONE

Nothing below is the current focus — everything in this section has shipped. Current focus (watches,
open threads) lives in `BOOT.md`, not here.

## P0 — Governance bootstrap (S16–S20) — ✅ DONE
Prod-truth reconcile + `prod-baseline-20260704`, nine-file governance, CI/pre-commit + secret gate,
independent session numbering. See CHANGELOG-ARCHIVE `[S16]`–`[S20]`, DEC-0010…0017, DEC-0023.

## P0.5 — Governance alignment across the family (S23–S56) — ✅ DONE except one follow-on
Brought this repo's *form* into line with the sibling repos and external best practice, keeping
content isolated (ASSESSMENT.md §2): `docs/ASSESSMENT.md` cross-repo audit + Governance Standard v1,
GPLv3 `LICENSE`, `AGENTS.md` cross-agent entrypoint, ROADMAP restructured to shared P-tiers,
STATUS.md promoted to single source of truth for the session number, `cleanup_backlog.md` folded
into BACKLOG (S27), docs diet (DEC-0030, S35 — the family-wide pattern: dash DEC-0081 → hyperlocal
DEC-0095 → here), remote URL casing + stale-branch cleanup (S56). See CHANGELOG-ARCHIVE `[S23]` and
ASSESSMENT.md for detail — not re-narrated here.
- [ ] **Keep-a-Changelog headings + DECISIONS entry-skeleton convergence** (proposed S25, never
      picked up).
- [x] ~~**Session-context tiering migration — DEC-0063, decided S59, execute S60.**~~ **DONE S60**
      (this row said so in its own body while staying unchecked — caught by the S66 full pass). The third
      generation of the docs-diet idea (dash DEC-0081 → hyperlocal DEC-0095 → DEC-0030 here →
      ops `STANDARD.md`): `BOOT.md`/`CONSTANTS.md`/`MANIFEST.md`/`ARCHIVE/` replace the DEC-0030
      Tier-1 set. Adopted on measurement against ops#130's own recommendation to defer — Tier-1
      accretes **~1.1K tokens per session close**, so leanness here is a moment, not a trajectory.
      Both siblings already migrated. **Executed S60** — see CHANGELOG `[S60]`.

## P0.6 — Code-quality review + fixes (S24–S25, M-A S28) — ✅ DONE
Ranked findings in `docs/CODE_REVIEW_S24.md`; all fixes landed with regression tests — H1/H2/M3/U3
(S24), U1/U2 owm rebase, U4 TLS, M4 dead code, nits + SPDX headers (S25), M-A/L-B monitor
incremental read (S28). See CHANGELOG-ARCHIVE `[S24]`, `[S25]`, `[S28]`. Driver fixes shipped in
v2.0.3 (S30/S32).

## P1 — Data integrity & Sensor-QC hardening (S18–S55c) — ✅ DONE, watch-only
One continuous arc, not several separate efforts: RF/decode corruption that passes CRC has produced
impossible values (rain, wind, humidity, temperature) since S18, and each release below closed one
corruption class. Full decision trail in DEC-0021/0022/0024/0026/0029/0033/0037/0042/0044/0049/
0054/0055/0056 and CHANGELOG-ARCHIVE `[S18]`–`[S52]` / CHANGELOG `[S55]`–`[S55c]` — not re-narrated
here.

- **False-rain fix → v2.0.3** (S18–S32): DEC-0021 root cause (wraparound handler), StdQC tightening
  + driver spike filter + email alert; reception-metric Layer A (S22/S27) rebased on
  `rxCheckPercent` (S31, DEC-0024); honest-null dewpoint + clobber fix. Wild-glitch gate consciously
  waived on live evidence (DEC-0026).
- **Sensor-QC decode filter → v2.0.4** (S33–S34): DEC-0029, decode-layer `SensorQC` bounds filter +
  DewpointCacher timeout-null, closing DEC-0022.
- **Reception-metric over-count fixed → v2.0.8** (S43): both layers of DEC-0024 closed (monitor
  counts unique record epochs; driver stops publishing dataless freqError packets).
- **Frame-level co-rejection → v2.0.9** (S52): DEC-0054 — a bounds failure now nulls every field of
  its frame instead of just the failing one, closing ERR-0004 (issues #74/#76).
- **Signed temp decode → v2.0.10** (S55): DEC-0055, fixes negative-temperature encoding and the
  `0xFF8` flag-nibble leak.
- **Cap-16 tuning → v2.0.11** (S55c): DEC-0056, decided on an evidence pass (R1/R2); monitor
  tripwire verified live end-to-end.

**Still open — ordinary watches, not a new arc.** Current status (co-rejecting grep, humidity-spike
signature DEC-0044, first-frost test of the signed-decode negative branch, DEC-0056's
rain-rejection revisit trigger) lives in `BOOT.md`'s standing watches — not duplicated here, and not
evidence this P1 item is still "in progress." **`#74` calm-windDir left this list at S59**, closed
on five consecutive clean days with a positive control (`BOOT.md` §Standing watches).

**Blocker discipline (DEC-0011):** no drop-in dev receiver — RF-dependent verification is calendar-
bound and done via reversible live hot-swap with an instant rollback path.

---

# MEDIUM TERM (P2–P3) — after v2.0.11

## P2 — RF optimization, done honestly (PRINCIPLES §3) — **A COMPLETE, B READY BUT HELD**
DEC-0048 (S41) deferred this into one designed experiment; the apparatus (`ops/rx_experiment.sh` +
`tests/test_rx_experiment.py`, S56/DEC-0059) is now deployed and executing. The seven
pre-governance sweep scripts are deleted; two of them were silently broken.
- [x] **Phase 0: `FreqError` telemetry CONFIRMED TO EXIST** (S57) — found within 13s of a restart
      once a logger-level gotcha was fixed (DEC-0060). `ppm`/`fc` measurement-by-value is a
      deliberately deferred follow-up, not done this campaign (arms run unmeasured `0`/`0`).
- [x] **Campaign A — LNA in circuit — ENDED EARLY 2026-08-02, 12 of 32 blocks.** Ran clean
      07-30 00:05 → 08-02 00:05 (12/12 swaps healthy, zero aborts), then aborted on the B→D swap
      when the receiver went silent for reasons unrelated to the arm — a 105-minute total RF
      outage (**ERR-0005**). The abort was **correct**: `health_ok()` waits for an archive record
      and none existed in the window (last 00:04:20, next 01:24:24), so DEC-0061's budget
      arithmetic is upheld, not implicated. STOP sentinel left in place deliberately; A is not
      resuming. Its surviving value is what DEC-0064 always said it was — the LNA-in
      characterization (922 samples, mean 72.4) and the multi-day drift error bar. **Arm winner
      stays sealed until after B.** Settles DEC-0017 (**absorbed**). Tracked at
      [ops#114](https://github.com/WeatheredScientist/eaglehunt-ops/issues/114).
- [ ] **v2.0.12 release carrying DEC-0062 + `BIAS_TEE` env — BUILT, NOT PUBLISHED.** *(Status
      corrected S66: this said "BUILDING 2026-08-02" for four sessions. S62's local build is **gone**,
      Docker Hub still carries `:v2.0.11` + `:latest`, and prod runs v2.0.11. **Rebuild from the
      merged tip when campaign B launches** — the build is a launch step, not a pending task.)*
      `entrypoint.sh` reads `BIAS_TEE` (default 1 — published image unchanged; all
      four branches verified S62). Also carries S62's driver stderr fix (**`0.20+ws.4`**, ERR-0005)
      and the README version banner, which was three releases stale. Push `:v2.0.12`, deploy with
      `-e BIAS_TEE=0`, then move `:latest` only after our own station proves it. Carry DEC-0046
      into the release: verify in the **running system**, never in the artifact — and the DEC-0031
      canary in `ops/soak_check.sh` now actually fails on a version mismatch (S62), which is what
      makes that verification real.
- [ ] **Campaign B — LNA physically removed — PREPARED, then HELD (DEC-0066).** The LNA came out at
      ~01:33 on 08-02 during the ERR-0005 diagnosis, so the swap night's physical step is done, and
      the schedule was shifted −4 days to launch 08-03. **Held instead:** prod went deaf three times
      that day (105 min, 3 min, 10 min) and two remain unexplained. An 8-day unattended reception
      experiment run across intermittent unexplained deafness yields data that *looks* like results,
      and B's 32 swaps each expose it to the abort that already killed campaign A. Apparatus, tests,
      runbook and image are all ready; only the timing is open. **Schedule dates are now in the past
      — regenerate before any `install`.**
      **ALL GATES NOW CLEARED (S66) — the hold is a judgment call, not a work item.**
      *Explain the outages* — substantially met at DEC-0067: the recurring class is **process
      freezes, not RF loss**, bounded (~1/day, ~3.5 min) and pre-dating the LNA removal, while
      ERR-0005 is a **single incident**. *Watchdog* — done (S63). *Metric freeze-aware* — **done
      (DEC-0069)**, and the gate turned out to be mostly a **resolution** problem: the old 5-minute
      aggregate let one frozen minute wreck four good ones (~0.8 pts), while per-minute
      `rxCheckPercent` puts the real correction at **±0.03 pts against a 2.0-pt bar**. *DB lock* —
      **bounded (DEC-0070)**, outages ~30 s not ~10 min, and **WAL was tried and abandoned
      (DEC-0071)**, so there is nothing further to wait for. **Nothing remains to build before B
      launches.**
      **First honest no-LNA telemetry already accruing** — ~14 h at gain 372 gave mean 72.6% with
      no hour-07 notch, against campaign A's pooled 72.4%. Treat that as suggestive only: A's
      figure pools all four arms including gain 207, so it is biased low, and the clean comparison
      is B's 372 anchor against A's — which is exactly why 372 is in both campaigns.
- [x] ~~**Deploy the escalating watchdog (DEC-0065) to the NAS**~~ — **DONE**, verified live at the
      S63 open: the NAS `weewx_monitor.py` matches the repo tip byte-for-byte, with zero resets or
      escalations since. It was deployed between sessions, outside a session, which is why S62's
      handoff still listed it as pending.
- [x] ~~**P0 — explain the two unexplained 08-02 outages**~~ — **substantially answered by DEC-0067
      (S63).** They were two different phenomena filed under one name. The driver's own 150 s
      watchdog is the discriminator and had been reporting correctly all along: it fires only when
      the main thread is executing, so a >150 s output gap **with** `rtldavis process stalled` is
      RF loss and a **silent** one is a process freeze. ERR-0005 fired it 21 times → genuine RF
      outage, and **0 detections on every other day measured** → a single incident, not a pattern.
      The 13:47 dropout fired nothing → **the receiver was fine and the process was frozen.**
      **Still open, tracked below: why it freezes.** ERR-0005's own root cause also remains
      unestablished, but it no longer gates campaign B on its own.
- [ ] **P0 — why does the weewx process freeze? (DEC-0067, DEC-0068)** ~2-4 min, roughly once a
      day; seen 07-30 08:04 (**LNA in**), 08-02 13:46, 08-03 02:59, 08-03 23:23 (262 s, S64), and two
      more caught S65 (08-04 17:48 and 19:13 EDT). All threads stop together and nothing is logged;
      `weewxd`'s own main thread reads `S`, never `D`, across every capture so far — leans against
      the original "blocked on the bind-mounted log volume" hypothesis. **DEC-0068 (S65): this NAS
      also runs coffee-radar, and it was confirmed running (via `nasctl inspect`, not a name match —
      its scheduled job never sets `--name`) during one freeze, with loadavg spiking to 12.39 against
      a 0.3–0.7 baseline — a real contributor, not a full explanation.** The other S65 freeze, same
      night, had neither coffee-radar nor elevated load. n=1 correlated out of 3 captured freezes;
      not a settled base rate. `ops/freeze_watch.sh` (S65, now committed — no longer a scratchpad
      rebuild every session) is the tool for any further capture. **Root cause is not fully
      explained, but campaign B does not need it to be** — and as of **DEC-0069 (S66) the metric gate
      is CLOSED**, leaving the line below as B's sole remaining gate. DEC-0069 also bounds how much
      these freezes were ever worth to the campaign: **±0.03 points** on a pooled arm mean against a
      2.0-point adoption bar, once the metric is read at the resolution it is actually stored at.
      Ruled out already: NAS-wide stall, the S37 stdout wedge,
      CPU-quota throttling, `pressure_service`. Upstream hit this and worked around it without
      diagnosing it (`get_stderr()`'s 10 s cap).
- [x] ~~**P0 — make the campaign metric freeze-aware**~~ — **CLOSED by DEC-0069 (S66).** Two parts,
      and the larger one was a *resolution* problem, not a freeze problem: `harvest()` read the
      monitor's **5-minute** `RECEPTION:` aggregate, where one frozen minute drags a whole bucket
      (measured 16 % / 27 % against ~72 %) — that is where the ~0.8-point estimate came from. The
      same measurement is stored **per minute** in the archive DB as `rxCheckPercent`, where a freeze
      damages one record. Exclusion is **structural** (drop the record either side of any gap, plus
      NULL, plus non-physical `rx > 100`), never magnitude-based — a threshold would discard genuine
      deep fades and bias every arm upward. Net effect on a pooled arm mean: **±0.03 points** against
      a 2.0-point bar. New tool `ops/campaign_analyze.py` (+14 tests); `ops/rx_experiment.sh`
      deliberately untouched. Campaign A recomputed: spread **0.94 pts**, no arm near adoption.
- [ ] **P0 — the `database is locked` defect** — **BOUNDED at S66 (DEC-0070); no further work
      planned.** Stays open because the defect is capped rather than eliminated, not because
      anything is queued — WAL was the remaining idea and DEC-0071 abandoned it. Root
      cause is a pair of untouched defaults: `journal_mode=delete` (a reader's SHARED lock blocks the
      writer) plus weedb's **5 s** SQLite timeout (`weedb/sqlite.py:136`), so six seconds of reader
      cost a CRITICAL + weewx's hardcoded 120 s wait + restart ≈ **5–10 min**. **Shipped `timeout = 30`
      in the live `weewx.conf`** — outages now capped at ~30 s, verified in the running system.
      **⛔ WAL WAS TRIED AND ROLLED BACK — do not retry it (DEC-0071, S66).** HLF shipped the
      directory mount (ops#141); WAL went live 06:56 EDT on 08-06 and HLF **froze on a stale
      snapshot within minutes**. Two blockers, both missed by DEC-0070: a Docker `:ro` bind makes the
      **files** read-only (DEC-0070's test chmod'd only the *directory*, so it never reproduced the
      condition — structurally blind, DEC-0035 again), and SQLite creates `weewx.sdb-wal` mode
      **0555**, so even a read-write mount leaves a non-root reader unable to write it. Rolling back
      cost a **~6 min crash loop**. `journal_mode = DELETE` is now pinned by a `[[[pragmas]]]`
      subsection so an accidental flip cannot recur. **`timeout = 30` is the fix, not an interim** —
      it delivers most of WAL's practical benefit at none of this risk. Remaining detail below
      **pre-dates the LNA removal**
      (08-01 15:08, 08-02 19:45; earlier S59) — and **independent of the freezes above**. DEC-0067
      decomposed the 10-min outage: ~106 s of hung uploader threads + **120 s of weewx's own
      hardcoded wait** + ~5 min restart, so the thread hang is only ~18 % of it — the identical
      lock on 08-01 cost 4 min because the threads exited in 0.26 s. **Lead fix: the archive DB is
      not in WAL mode**, the standard cause of exactly this contention — *tried, see above*. If this
      ever recurs **despite** the 30 s cap, that means a reader held the lock >30 s and is a
      different problem; bound the uploader-thread joins then. **Archive DB readers (corrected S66,
      DEC-0070 — this row previously named "the dashboard"):** scanning every container that mounts a
      weewx path finds only `hyperlocal-forecast-api`, `eh-proxy` (parent dir, read-only), and weewx
      itself. Plus the NAS monitor (read-only, 6-hourly) and `weectl`.
- [x] ~~24 h **receiveWindow sweep**; reconcile image tag ↔ Dockerfile~~ — **dissolved by DEC-0059.**
      `-ex N` ≡ `receiveWindow 300+N` (upstream sums them), so the window is a mounted-config knob,
      no rebuild, and it is simply the second factor of the campaigns above. The `rw*` image tags
      were redundant, not merely misnamed.
- [ ] Confirm the running binary's `receiveWindow` (ARCHITECTURE §6) — **narrowed, still open.** It
      cannot be read from logs: the deployed binary is older than upstream master and lacks master's
      startup settings line (absent from both `weewx.log` and container stdout, checked S56). Needs
      the deployed `src.tgz` read directly, or a rebuild. No longer blocks the campaigns.
- [x] ~~Investigate rebuilding `rtldavis` from newer Go source for `FreqError`/`ChannelIdx`
      telemetry~~ — **moot.** S57 confirmed the *currently deployed* binary already emits it; no
      rebuild needed for this purpose.

## P3 — Modularity toward multi-source (PRINCIPLES §1)
- [ ] Harden INTERFACES.md as the stable contract; document it well enough for a non-Davis WeeWX or
      CumulusMX producer to satisfy it. (Partial progress: DEC-0032's `rain_qc` flag and DEC-0053's
      station-identity/correction-flag findings are already documented there — this item is about
      closing the remaining gaps, not starting from zero.)
- [x] Remove the vestigial `loopdata.py` mount + `[LoopData]` section (DEC-0005) — done S47.

---

**P4 and long-term/uncalendared direction moved to BACKLOG.md's "Long-term direction" section
(DEC-0058, S56)** — credential hygiene follow-ups, multi-source adaptability, the governance
template harvest, and the winter-2027 sky-state instrumentation (ops#110) all live there now,
not here.
