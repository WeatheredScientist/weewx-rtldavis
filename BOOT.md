# BOOT — weewx-rtldavis

**Always-load, tier 1.** Rewritten each session, never appended (STANDARD rule 1). Resolved items
are deleted; a conclusion survives as one line. Load with `CONSTANTS.md` + `MANIFEST.md` — nothing
else at start. Everything else is pulled by name from `MANIFEST.md`, on demand.

**What this repo is.** The driver + Docker build for a Davis 6263 / VP2+ ISS *passively intercepted*
at 915 MHz via an RTL-SDR Blog v3 — the "escape the WeatherLink lock" tool. A public, published
WeeWX extension (Docker Hub + GitHub releases), GPLv3. Its real contract is the **data it emits**
(loop-JSON + InfluxDB line-protocol schema), not any one consumer. The dashboard that consumes it
is a **separate repo** — don't make dashboard changes here.

---

## ▶ Resume here (S73)

### ▶▶ THE JOB (next session = S74): stall-forensics deep-read — the mechanism is captured, read it

**GATE 2 passed (S73, 2026-08-11).** Pilot aborted at 02:11 after 2 of 5 arms on a stall (not
reception): P496 **75.56%** ≥ P449 **72.65%** → **arms {372, 496} confirmed**, **square runs
08-12T00:05 → 08-20T00:05**. DEC-0080 radiation fix **applied** (live conf **and**
`weewx.conf.rx-baseline` — a live-only apply gets wiped by `restore_baseline`; hazard found at
apply, now in `CONSTANTS.md` deviations). `:latest` → v2.0.12 on Hub, config digest `9db5c1…`
verified identical across tags. **Three** ABORT emails on 08-11 are expected — two overnight,
one at 08:58 (see below).

**The 08:55 re-arm exposed a second budget bug, fixed same session:** the H re-swap aborted at
08:58:14 as "no records" while the driver was **alive and publishing** — `health_ok`'s 180 s
budget (S57) never modeled **RF acquisition** (~0 s for P449 vs ~127 s measured on this boot:
main loop 08:55:17, first decode 08:57:24, first archive record due ~08:58:15 — missed by
seconds). `HEALTH_TRIES` 36 → 60 (~300 s vs the corrected ~245 s worst case), arithmetic pinned
in `tests/test_rx_experiment.py`. The 02:11 P402 abort probably had the same mechanism under the
guard race (S74 Sub-B confirms). **Deploy the fixed script + re-clear STOP before 08-12T00:05**
— with the old budget, every square swap is a coin flip against acquisition variance.

**The S73 capture (2026-08-11 01:52) answered DEC-0075's question with a third mechanism:**
`rtldavis` was a **zombie** — `Z`, `wchan=do_exit`, zero fds, **no replacement process**. The child
died mid-block; the parent (weewx driver) neither reaped nor respawned it; USB resets "fail"
because a device reset cannot resurrect a dead consumer; a container `kill`+`start` is what clears
it. Three full capture sets banked in `logs/usb-forensics/` incl. an **effective** reset at 23:56
(during the HLF-promotion + coffee-radar load spike, 15-min loadavg ~25 — DEC-0068's contributor
pattern) vs two ineffective at 01:52/01:59. Reset #2 **timed out after 15 s** — new failure mode.

### Staged plan (S74 → S76+), tiered per AGENT-ECONOMY / OPS-DEC-0004; Class C never in subagents (OPS-DEC-0034)

**S74 — stall deep-read (tier:frontier — escalate; main thread does the differential):**
- **Sub-A (Sonnet, read-only):** collate all 9 `logs/usb-forensics/` files + the 08-09 baselines
  into one normalized table (per phase: devnum, fd targets, container view, rtldavis pid/state).
- **Sub-B (Haiku, read-only):** exact night timeline from `weewx_monitor.log` + `weewx.log` +
  `rx_experiment.log` — child death time, driver-watchdog silence (did `rtldavis process stalled`
  ever log?), bad-window counts, both reset attempts, recovery instant, the 15 s timeout.
- **Sub-C (Sonnet, read-only, cross-repo):** HLF hlf#154 promotion + maintenance-tick timeline +
  coffee-radar schedule vs our two stall windows; extends DEC-0068's load-contributor record.
- **Main thread (frontier):** differential — why did the child die; why didn't the driver's 150 s
  watchdog respawn (its silence resembles a DEC-0067 freeze); does the zombie retroactively
  explain ERR-0005 (recreate-fixed-what-restart-didn't); mint the DEC.
- Also in S74 (cheap, main): **verify DEC-0080's first dark hours read 0** (3.516 ⇒ extend
  per-code, never a loose window); confirm square swaps clean in the tick log.

**S75 — remedy build (tier set by S74's verdict; design first with owner — PRINCIPLES §8):**
candidates: monitor escalation → auto-recreate (re-opens DEC-0065's decline, now with mechanism
evidence); driver child-respawn fix (upstreamable to lheijst); tick/guard lockfile (the 02:05
race). After design: **Sub-D (Sonnet)** tests + **Sub-E (Sonnet)** implementation in parallel;
NAS deploy main-thread, owner-gated. Monitor changes are host-side — deployable mid-square
without touching the campaign.

**Daily square watch (S73→S80, tier:cheap, ~5 min, any session's start):** STOP absent · state
matches schedule · `soak_check.sh` · reception plausible. Local-only (NAS creds don't reach cloud).

**Post-campaign (08-20+), in order:** ① A×B grand readout, `campaign_analyze.py` both windows,
LNA verdict (tier:frontier, owner present; adoption bar ≥2.0 pts, DEC-0059). ② `#144` console
pressure — design with owner, then Sub tests+impl split; service is **baked** → NAS rebuild
(tier:frontier design, mid build). ③ `ops#141` directory-mount **scope-only** comment (Sonnet;
WAL framing is stale vs DEC-0071). ④ `WU_RF_MIN_PCT` retune from B's data (cheap). ⑤ `ppm`/`fc`
measurement-by-value (mid, DEC-0060 recipe). ⑥ Keep-a-Changelog + DECISIONS skeleton convergence
(cheap Sonnet doc pass). Cross-repo, unscheduled: ops#153 (MANIFEST cap — awaits ops-side call),
ops#147 (weewx instances already fixed), ops#110 (winter 2027).

Two things not to re-derive: **`weewx_monitor.py` IS the watchdog** (DEC-0074) — its escalation
tops out at *emailing* a recreate command, it never runs one (DEC-0065); and **every reset line
before 2026-08-07 19:28 names `syno_vbus_reset`, an operation that never ran** — the history lies
even though prod is right (S67's wrong path).

### Current state (S73)

| Thing | State |
|---|---|
| Prod | **v2.0.12**, driver ws.4, `BIAS_TEE=0`, LNA out, gain 372. Healthy — recovered 02:11, verified publishing 08:32 |
| Live-config deviations | **three** now: `timeout = 30`, `[[[pragmas]]] journal_mode = DELETE`, **DEC-0080 radiation zero (also in the rx-baseline snapshot)**. Table in `CONSTANTS.md` |
| Campaign B | **square scheduled** 08-12T00:05 → 08-20T00:05; **STOP present after the 08:58 false-positive abort** — re-clear after the HEALTH_TRIES deploy, then the next tick swaps P449→H. Guard floor 50%, abort restores baseline + emails |
| Hub | `:v2.0.12` + `:latest` = same config digest `9db5c1…` (manifest digests differ — push-path compression, S70c vs S73; not drift) |
| Stall forensics | **CAPTURED** — 3 sets banked, zombie mechanism, S74 reads it. Apparatus stays armed |
| `weewx_monitor.py` | alive, supervised; fired 2 resets + captures overnight exactly as built |

## Blockers

1. **weewx process freezes ~once/day, 2–4 min, cause not fully explained (DEC-0067/0068).** Load
   is a contributor (n=1 of 3 then; last night's 23:56 stall during loadavg ~25 strengthens the
   pattern — S74 Sub-C extends the record). Gates nothing (±0.03 pts, DEC-0069).
2. **The stall remedy doesn't exist yet.** Mechanism now captured (zombie child, S73) but until
   S75 lands a remedy, a stall night can still trip the guard and abort a square block —
   recoverable: clear STOP next morning, `due_arm()` self-heals, structural exclusion covers the
   gap. **Do not treat an overnight abort as a campaign failure.**
3. **ERR-0005 unexplained** — single incident; the zombie finding may explain why the recreate
   worked where kill+start didn't (S74 question). Doesn't block B.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Gotchas that survive here because they are NOT in the canonical docs

- **A file match proves the FILE, never the PROCESS — and never that a capability is absent**
  (DEC-0074). Liveness needs process evidence: startup line after file mtime, `/proc/<pid>/stat`
  field 22 vs `/proc/uptime`, new pid + old pid gone — never `/proc/<pid>` mtime (ACCESS time).
- **`secret-read-guard.sh` matches by basename** — read `ops/wxcheck.sh` and any `weewx.conf`
  with `readconf`. Guard fix is ops-owned.
- **`rx_experiment_data.log` rows tagged P449, 01:23→08:55 on 08-11, are contaminated** (stall +
  baseline morning harvested under one tag). `campaign_analyze.py` is immune — it reads swap-time
  blocks from the apparatus log, never harvest tags. Don't hand-read the datalog for pilot numbers.
- `campaign_analyze.py --campaign B` will warn "multiple attempts pooled" once the square runs
  (the pilot abort split the log into two attempts) — for B this pooling is **correct**, the arms
  are label-distinct; the warning is informational here.

_Last updated: 2026-08-11 (S73) — GATE 2 passed, DEC-0080 applied both files, `:latest` moved,
zombie mechanism captured; S74 staged with subagent fan-out above._
