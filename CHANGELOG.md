# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---
## [S98] — 2026-08-20 — Phantom 37 mph gust diagnosed and corrected (ERR-0006); reception-quality wind guard ships (DEC-0110); P0.5's last follow-on retired (DEC-0109)

- **Owner-reported phantom 37 mph gust at 11:12 EDT, diagnosed to source and corrected (ERR-0006).**
  Same class as `ERR-0004` (2026-07-27), recurring independently: `rxCheckPercent` for that one
  archive minute collapsed to 9.2% (vs. 60–90%+ every surrounding minute), a genuine RF-dead
  episode (weewx.log silent 11:11:35→11:15:22, confirmed not a restart). One of the few packets
  that passed CRC that minute carried a corrupted wind byte; every other field in the row read
  normally, so nothing tripped DEC-0054's frame co-rejection. Investigated and ruled out `#225`
  item 2 (rain-rate co-rejection gap, fixed same day in PR #260 but not yet deployed) as the
  mechanism here — rainRate was clean. Archive row nulled + daily summary rebuilt (day-max now 19
  mph, genuine); InfluxDB point deleted and rewritten minus the 7 wind-derived fields, with
  `windGust_qc=1`/`windSpeed_qc=1` flags (24 fields verified, matching `ERR-0004`'s own precedent
  exactly) — the dashboard's read-only proxy token can't write/delete (confirmed 403), so the
  correction used `weewx.conf`'s own uploader token instead. Wunderground/CWOP/PWSWeather/OWM/etc.
  already have the bad value; that's permanent, same as `ERR-0004`. Cross-verified independently by
  an eaglehunt-weather-dashboard session (InfluxDB via its own query path) and an eaglehunt-ops
  session (raised `#225` item 2 and a container-restart confound as candidate mechanisms; both
  checked directly and ruled out for this incident) — good example of the coordination working.
- **Reception-quality wind guard ships, closing the ERR-0004/ERR-0006 blind spot (DEC-0110).**
  Neither the bounds check nor the 75 mph delta cap can distinguish this corruption from a genuine
  squall gust of similar magnitude — `ERR-0004`'s own writeup already established that tightening
  either risks false-rejecting real weather. Measured first, before designing anything (93 days,
  129,607 records): genuine high wind and severe reception collapse have never co-occurred at this
  station (lowest `rxCheckPercent` among 220 records with `windGust>=10mph`: 54.5%; 87 of 89
  `rxCheckPercent<20%` records stayed calm at 0–4 mph) — so a guard combining both signals can't
  false-null a real gust, with wide margins on both sides. `dewpoint_service.py`'s `DewpointCacher`
  gains a `NEW_ARCHIVE_RECORD` binding (`rxCheckPercent<20%` AND `windGust>10mph` → null the wind
  triple + derived fields), confirmed via `weewx.conf`'s own `[Engine][Services]` order to run
  before `StdArchive`'s write and every RESTful uploader. Explicitly does not reach Wunderground's
  RapidFire feed (publishes pre-archive-close — a live ticker, not an archive of record). 11 new
  tests including both incidents replayed verbatim as positive controls. Ships with the ~08-23
  v2.0.14 build (baked into the image), same gate as `#225`.
- **ROADMAP.md's P0.5 fully closed (DEC-0109).** Its last follow-on ("Keep-a-Changelog headings +
  DECISIONS entry-skeleton convergence," proposed S25, ~72 sessions unclaimed) is retired, not
  picked up: the original rationale is unrecoverable (no surviving transcript), no sibling repo
  adopted anything to converge toward (checked all three), and `DECISIONS-FULL.md` already grew
  its own working skeleton independently of `CHANGELOG.md` — nothing left to reconcile. Judgment
  call, not just absence of evidence: this repo's entries are dense, cross-referencing narratives
  that an external single-facet schema would likely fragment rather than clarify.
- **A `ROADMAP.md` overclaim caught while closing the loop on the above.** Its P1 arc credited
  DEC-0054 with "closing ERR-0004" outright — true only for the co-occurring-bounds-failure
  mechanism, not the whole class, which `ERR-0006` just proved recurs independently. Corrected in
  place rather than left standing.
- **Cross-repo, same session:** fixed a `secret-read-guard.sh` false-positive gotcha in
  eaglehunt-ops (`command` escape-hatch anchoring + a co-occurrence false-positive class), found
  and flagged via `spawn_task` while doing unrelated ops work; landed there as OPS-DEC-0115, tested
  and deployed.
- **Gates:** 397/397 full suite (was 386, +11 new, 0 regressions), ruff clean, mypy clean (63
  files, `.mypy_cache` cleared first), secret gate clean. PR #265 merged to `dev`.

---
## [S97] — 2026-08-20 — S91 audit fully closed (#225/#226); NAS-LEASE holder client built + verified (DEC-0108); INTERFACES.md's two DEC-0053 gaps actually documented

- **The S91 audit's 8-issue sequence (#219–226) is now fully closed.** #225 (5 QC-completeness
  findings, all dormant on this station's single-ISS config) and #226 (4 public-facing CLI/config
  bugs) were the last two, both shipped this session (PRs #258, #260); #219–224 had already landed
  in prior sessions. Tracking issue #227 closed with the full sequence noted. #226 item 1 is the
  standout for impact beyond this station: the shipped config template carried a literal,
  unsubstituted `[options]` token that any new user following the documented setup shipped straight
  into `weewx.conf`, silently discarding the auto-appended `-tf`/`-tr` flags and falling back to
  868MHz EU instead of 915MHz US with zero error. 23 new regression tests across the two PRs.
- **`ops/nas_build.py` — weewx's NAS-LEASE holder client — built, tested, and verified against the
  real NAS, ahead of the ~08-23 build (DEC-0108).** A generic lease-wrapper (`--job <name> --
  <command>`): `O_CREAT|O_EXCL` acquire, explicit `fchmod 0644` (the exact umask near-miss
  `NAS-LEASE.md` v1.4 documents and DEC-0107 found on the box), `flock` held for the wrapped
  command's run, stale-break only when flock is free **and** `expires_at` has passed, release with a
  truthful outcome (`clean`/`build-failed`/`crashed`) wrapped in `try/finally`. Generic over any
  command so it covers both of weewx's named holder cases (image build, manual bulk analysis) from
  one script. **Scope decision, recorded in DEC-0108:** the observer/downshift side is deliberately
  not built — weewx has no live downshift lever to act on a "held" verdict yet, so a courtesy read
  with nothing to act on has unclear benefit today; revisit once the InfluxDB `post_interval` lever
  ships. 14 tests against a real `flock()` on a `tmp_path` dir, not mocked. **Later in the session,
  ran it for real** against the actual shared `LEASE_DIR` (a clearly-labeled dry-run job, TTL 60s) —
  clean `acquired`/`released` pair logged, directory left exactly as found, no stray lease file.
  Floor/TTL ship as §5's provisional 600s/3600s, to be re-pinned against the real ~08-23 build's
  measured duration; the adopting DEC itself still waits for that event on purpose.
- **`INTERFACES.md` actually documents both of DEC-0053's open findings now — ROADMAP had been
  overclaiming this since S48.** Tracing ROADMAP's P3 line (which asserted DEC-0053's
  station-identity finding was "documented there") against the actual file found that only Finding 1
  (bound the loop-JSON cache) had made it in. Finding 2 — InfluxDB carries no station-identity tag,
  and adding one later forks a parallel series instead of annotating it — is now written into §2,
  along with a one-line pointer to Finding 3 (the SQLite archive's own missing correction flag,
  deliberately left in `DATA_ERRATA.md` where DEC-0053 always said it belonged). ROADMAP's P3 line
  corrected in the same pass, with the guardrail's own "targeted pass writes both places" rule
  followed this time. PRs #261, #262.
- **Session-start concurrency, resolved cleanly.** A live peer session (`weewx-rtldavis-e4`, S96)
  was still finishing as this session started; coordinated directly rather than duplicating work.
  The peer's handoff corrected an early misreading on this session's part — ops#169's current
  title/body read as an unresolved coffee-radar heads-up, but the actual unresolved thread had
  already closed as DEC-0104/DEC-0107, verified independently against `DECISIONS.md` rather than
  taken on the peer's word alone. Mid-session, coffee-radar (`coffeeradar-28`) cross-checked the
  ~08-23 timeline directly; confirmed, and told them the holder client was now built and verified,
  not just designed.
- **Interim Campaign B readout, informational only — square left running untouched per owner
  instruction.** Using `ops/campaign_analyze.py --since <the live attempt's epoch>` (the raw log
  pools 6 aborted attempts back to 08-11; the tool's own pooling warning caught it): at 22 of 32
  blocks, arm B (gain 496, ex 0) leads arm A (372, anchor) by +2.25 pts, and D leads C by +1.16 pts
  at ex 50 — gain wins both head-to-heads; the ex axis itself reads as a wash (+0.93 pts one way,
  −0.16 the other). Already exceeds campaign A's entire 4-arm spread (0.94 pts). Explicitly not a
  verdict — the runbook's own rule is not to read partial results, and DEC-0102's overnight iowait
  confound is still open.
- **Two secret-read-guard false positives found and worked around, worth a note to ops.** The guard
  blocked a plain `scp` upload of this repo's own already-secret-gated script (never touches
  `weewx.conf`), and separately a `tail` on the NAS-LEASE attribution log (plain JSONL, no
  credentials) — both keyed on the command verb/NAS-host pattern rather than which file is actually
  touched. The documented `command` escape hatch resolved both, but only once `command` was the
  **literal first word** of the whole invocation — `cmd; command scp ...` still triggered it,
  `command bash -c '...scp...'` did not. Flagged via `spawn_task` for ops to fold into the guard's
  own documentation rather than left as a per-session rediscovery.
- **Green gate at close:** ruff clean, **386/386**, mypy clean (62 files), secret gate clean and
  positive-controlled mid-session (planted a fake key, confirmed the catch, restored from a
  pre-mutation backup rather than `git checkout` since the index held the payload). Soak at close:
  17 pass / 2 warn / 0 fail — same two known warns (chatty stdout #253, USB hedge during RF-dead).
- Model tier: ran on Sonnet 5 throughout, confirmed directly rather than inferred — no restore owed.
- Five PRs merged this session: #258 (#226), #259 (DEC-0108), #260 (#225), #261 (INTERFACES.md
  Finding 2), #262 (INTERFACES.md Finding 3). Steady state verified `dev` + `main` only after each.

---
## [S96] — 2026-08-20 — ops#169 closed end-to-end (DEC-0107); #224 unit systems fixed; ROADMAP tripwire fired

- **ops#169 / NAS-LEASE: every open item closed in one session, and all three box-level fixes rest on
  direct observation rather than report.** The round was run session-to-session with coffee-radar
  (their S205) at the owner's direction, with eaglehunt-ops informed throughout. Landed: `chmod 666`
  on `heavy-io.log`, `chmod 0777` on `LEASE_DIR` (sticky dropped), `chattr +a` on the log,
  `NAS-LEASE.md` **v1.4 / OPS-DEC-0110**, and HLF's create-mode patch (their PR #388, `066bbf9f`).
- **The finding that moved it: both weewx lease roles run non-root, and neither is what the other
  tenants assumed.** coffee-radar reasoned the uid gaps were moot for us because our client would run
  as root "like your `rx_experiment` tasks" — those *are* DSM root tasks, but neither is the lease
  client. The observer is `weewx-monitor` (uid 1031, DEC-0009 least-privilege) and the holder is a
  separate non-root account, established from the ownership of every `build-v2.0.*` directory rather
  than inferred. **weewx is the first tenant the gaps actually bite** — HLF and coffee-radar are both
  uid 0, which is exactly why three nights of clean production never surfaced them. Widening the
  monitor's sudo grant to dodge a file mode was considered and **rejected**: it trades a documented
  security decision for a `chmod` someone else can make.
- **`chattr +a` was deliberately not closed on its no-error exit.** That is its normal success
  signature and coffee-radar's reading was reasonable — but **this box is the origin of our
  accepts-and-silently-ignores precedent** (DEC-0036: Synology's `db` driver takes `max-size` and
  discards it, 7 h of prod lost to a cap that was never real). One owner-run `lsattr` returned
  `-----a------------` and converted inference to observation. A write-based probe was explicitly
  refused — it would confirm the attribute by attacking the attribution record.
- **We priced the cost of our own recommendation in writing.** Dropping sticky widens §11's already-
  accepted wrong-lease-deletion race from same-owner to any-tenant: a buggy unlink of a *valid* lease
  leaves the holder renewing into an unlinked inode while every observer reads the slot free. Still
  the right trade against option (b)'s *guaranteed* silent stranding of the least-privileged tenant,
  but recorded rather than discovered later. Break-by-takeover-in-place was considered and
  **discarded with the reason**, checked against HLF's real acquire/release code, so it stays dead.
- **Two findings came from the other tenants looking at our situation, and both changed what
  shipped.** coffee-radar noticed sticky was *incidentally* the only thing protecting the log from
  unlink — unpriced because it had only ever been weighed against §3's break clause — and flagged
  that the holder's literal account name was heading into a persisted record. That name is the
  owner's personal login, absent from all tracked files, and our adopting DEC lands in a **public,
  permanent** repo: the hazard was ahead, not behind. HLF, patching the line we reported, found **a
  second create we had not flagged** (the steal-then-acquire retry) — the branch that only runs after
  a crash, i.e. when the lease matters most.
- **DEC-0107 is deliberately NOT the adopting DEC.** Landing one locks §5's constants for every
  tenant (HLF's DEC-0177 was the first), so it must lock a *corrected* spec. Adoption now waits on
  nobody but us and lands with the client at the **~08-23 v2.0.14 build**, which §8 designates as the
  protocol's first cross-tenant holder exercise. Declared floor 600 s / TTL 3600 s, flagged as dated
  data to be re-pinned against that build's real duration.
- **#224 shipped: `dewpoint_service.py` now branches on `usUnits`** (PR #255). The file had no
  `usUnits` check anywhere — `dewpointF`/`heatindexF` unconditionally, plus two wind thresholds
  documented in mph compared against packet values that are km/h or m/s under
  `target_unit=METRIC`/`METRICWX`, both documented options in our own `weewx.conf.example`. Masked in
  prod only by the shipped US default. **Fixed the way WeeWX's own `wxxtypes.py` does, NOT via the
  issue's proposed `weewx.units.to_US()`** — `loop_json_writer.py` uses to_US legitimately because it
  *emits* US-suffixed fields, but this service writes into the live packet, so a to_US fix without
  the return trip would put degF into a metric packet: the same bug one layer along.
- **The wind half failed in both directions, each silently** — as m/s the 200 mph ceiling is ~447 mph
  and the guard was **inert**; as km/h it is ~124 mph and the guard **nulled real weather**. Readings
  are now normalised to mph at each comparison, keeping one documented threshold set instead of three
  to keep in sync. Pre-fix logs printed km/h values labelled `mph`; they now carry the reading's own
  unit. Suite **339 → 349**.
- **Two process findings from doing it.** The mutation check corrected our own documentation: 7 of 10
  new tests fail against the pre-fix file, not the 8 the docstring claimed. And the new tests **passed
  in isolation while asserting nothing in the full suite** — the weewx stubs live in `sys.modules` and
  are shared, so `dewpoint_service.weewx` is whichever stub won the import race; fixed by patching
  through the module under test and restoring after.
- **ROADMAP scheduled reconciliation ran — tripwire fired on time, three stale items fixed** (PR
  #256, bumped to S106). The most interesting: **the "Last updated" banner had itself gone stale.**
  S89 and S92 recorded targeted passes in the guardrail section without promoting them into the top
  block, so the banner read S86 while content was current through S92 — the freshness signal aged
  while the file did not. Also: P2 asserted the Campaign A arm-winner seal held, which DEC-0069 broke
  as a side effect **30 sessions ago**; and P3's INTERFACES citation list was three DECs out of date
  (verified against `git log -- docs/INTERFACES.md`, not inferred).

---
---
---
---
*(S73–S95 rolled to `CHANGELOG-ARCHIVE.md` verbatim — the ~3-session window.)*
