# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S42] — 2026-07-14 — the cross-repo round: DEC-0040's triggers fired, the identifiers were live on public dev, and pre-commit had never run (DEC-0050)

> **This was the scheduled `[Fable]` cross-repo coordination round** (dash S74 = this repo's S42),
> and this repo's share of it landed in one PR.
>
> **The identifier scrub was not hypothetical.** `ops/soak_check.sh` carried the real NAS
> user/IP/port as tracked shell defaults — **on `dev`, on a PUBLIC repo**, since S41. Our own
> `test_check_secrets.sh` tree check flags it (40/41 → the "1 FAILED" was this), but that check
> runs only where the gitignored `.identifiers` file exists — **CI is structurally identifier-blind
> by design**, so the only enforcement point was local pre-commit. And the hole under the hole:
> **pre-commit was configured but never installed** — `.git/hooks/pre-commit` did not exist, here
> or in either sibling repo. The load-bearing local gate for a public repo had never once executed.
> A configured control that nothing runs is prose (DEC-0040, one level down). Fixed: defaults are
> now placeholders that fail fast; real facts live in `~/.claude/nas.env` (also honored by the new
> eaglehunt-ops checks) / gitignored `docs/LOCAL_INFRA.md`; suite 41/41 with a clean tree; soak
> re-proven green end-to-end via `nas.env` and red on the placeholder path; pre-commit actually
> installed (owner-run). Per DEC-0028's precedent (identifiers, not credentials; LAN IP): fix
> forward, **no history rewrite**.
>
> **DEC-0050 — the station gets a master for its IDENTITY (and only that).** DEC-0040's own revisit
> triggers fired (five shared `~/.claude/` executables versioned nowhere; the same gate fix
> re-derived four times; the dashboard's DEC-0106 as the predicted casualty — 6.7 km of coordinate
> drift, a week of forecasts for the wrong town). The private **`eaglehunt-ops`** repo now holds:
> canonical `station-identity.env`, the drift check (**first run: 8/9 representations within 19 m —
> and the 9th finding was real**, see below), the NAS runtime contract, and the `~/.claude/` guards
> under version control with their tests (live copies = deployments via owner-run `install.sh`).
> Scope fenced by the S38 §Etiquette litmus test; deletion clause attached.
>
> **The identity check's first run caught a live outage in a sibling:** HLF's
> `/api/v1/forecast` hangs indefinitely for **every** coordinate pair (health/current fine,
> container "Up 8 hours" — *"Up" is not health*, our own DEC-0036 lesson, now on an API surface).
> Per §Etiquette: **filed in HLF's tracker with the evidence, not fixed from here.**
>
> **Also filed here (cross-repo asks from the dashboard's S73):** the loop writer emitting
> `cloudbase` (+`windchill`) — folds into the existing Cold-load Fix B thread; and a provenance
> audit (does the artifact a consumer READS carry the assumptions it was captured under — their
> DEC-0104/0106 twins of our DEC-0040/0045/0047 family). The dashboard's stale claim that our
> secret gate was "neutered" was **re-measured and retired** — 40/41 planted payloads pass; the
> one failure was the tree check doing its job on the identifiers above.
>
> **Read-guard field data (their `~/.claude/` DEC-0047 guard, now versioned in eaglehunt-ops):**
> S73/S74 logged five false positives — all token×verb string matches with no data flow (a commit
> MESSAGE containing "proxy.env" + the word "more"; the sanctioned `readconf` invoked by full path;
> a `.env` name inside an `echo` literal). Two mechanical fixes ride the eaglehunt-ops migration
> (readconf at a path boundary; a lone `git commit` exempted after heredoc-body stripping — chains
> and substitutions still block), proven 46/46 both directions. The wider class is documented as
> accepted: a false block costs a retype; a false allow costs a rotation.

---

## [S41] — 2026-07-13 — v2.0.7 shipped, and the config fix that would have missed prod entirely

> **v2.0.7 is on Docker Hub, prod runs it, and the raw-humidity capture is finally live.**
>
> The headline was meant to be routine: take S39's `[[root]]` logger fix (DEC-0043), which had been
> sitting merged-but-unreleased on `dev`, and ship it. That happened — `:v2.0.7` + `:latest`
> (digest `sha256:31cad4d2`), GitHub release, `main` == prod, `prod-baseline-20260713b` tagged.
>
> **The finding is what the deploy nearly missed.** The `[[root]]` fix lives in the image's *baked*
> config, protected by a Dockerfile build-time assertion so an image cannot be built without it. But prod
> bind-mounts `weewx-data/` over `/opt/weewx-data` — the mount covers the whole directory, so the live
> `weewx.conf` **shadows the baked config completely**. Deploying `:v2.0.7` and stopping there would have
> been, in prod, **a no-op with a green checkmark**: correct image, passing assertion, accurate release
> notes, and a station still emitting syslog tracebacks and still silently dropping every startup
> diagnostic. **DEC-0046.**

### Shipped — v2.0.7

- **Docker Hub:** `:v2.0.7` and `:latest`, both at digest `sha256:31cad4d2826b…`. Built on the NAS from
  `git archive v2.0.7` — the image is built from *exactly* the tagged tree (DEC-0038).
- **GitHub release** [v2.0.7](https://github.com/WeatheredScientist/weewx-rtldavis/releases/tag/v2.0.7);
  `dev` → `main` (PR #38, after PR #37's version bump); `main` and `dev` are identical trees.
- **Prod recreated on `:v2.0.7`** at 15:27 EDT. `docker kill`, never `stop` (DEC-0008); no `rtldavis.py`
  mount (DEC-0031). Rollback available: `:v2.0.6` (`e23cabd53591`) is still on the NAS.
- **`prod-baseline-20260713b`** tagged — the second baseline of the day (the first, `-20260713`, was
  v2.0.6). Not force-moved; the old tag still means what it meant. DEC-0011's *`main` = production truth*
  invariant holds.

### Found — DEC-0046: the baked config never reaches prod

- Caught by a **pre-flight `grep` of the live config**, which found **zero** `[[root]]` blocks while the
  image's baked config carried it and asserted it.
- **The exact mirror of DEC-0031.** There, the *driver* is baked and the bind-mount is the no-op, so an
  `scp` is silently ignored. Here, the *config* is mounted and the image is the no-op, so a rebuild is
  silently ignored. Inverses — which is precisely what makes the pair easy to get backwards. **Neither
  errors. Both accept the instruction and discard it.**
- Fixed in the same window: the live `weewx.conf` gained the `[[root]]` block (backed up first to
  `weewx.conf.bak-pre-v2.0.7`). Prod's version routes to `handlers = rotate,` — **file only, no console**,
  deliberately differing from the baked config, because prod declares no console handler and adding one
  would re-arm the DEC-0036 freeze hazard that DEC-0041 disarmed. **The fix must match; the text need not.**
- **The fifth member of the family**: an interface that accepts an instruction and silently discards it
  (DEC-0031's bind-mount, DEC-0036's `max-size`, DEC-0040's prose, DEC-0045's test that certified the
  hole). The build assertion was not wrong — **it was answering a question nobody was asking in prod.**

### Verified in prod — behaviorally, not by inspecting the artifact

- **`weewx.log` now contains `weewxd INFO Initializing weewxd version 5.4.0`**, plus the command line, the
  Python version, the platform and `WEEWX_ROOT` — **lines that had never once appeared in that file.** This
  is the S39 acceptance criterion, and it reads the running system. An image check would have said PASS.
- **Zero `--- Logging error ---` blocks** on stdout (was ~15 tracebacks / ~515 lines per start).
- `driver version is 0.20+ws.1 (patched by WeatheredScientist -- not stock upstream)`, `sensor_qc True`,
  **`log_humidity_raw True`**, 0 tracebacks, `RestartCount: 0`, and Wunderground (rapidfire + PWS), Influx
  and Windy all publishing.

### Armed — the raw-humidity capture is now live (DEC-0044)

`log_humidity_raw` had been sitting in the live config since S39 but weewx reads its config **only at
startup**, so it took this restart to activate. It is now running. **The next midday humidity spike logs
its raw `pkt[3]`/`pkt[4]`** and settles the nibble question deterministically — no averaging, no free
parameter. Spikes run ~2–3/week, clustered 11:00–16:00. The inversion method is in DEC-0044; do not
re-derive it.

### Security — DEC-0047: the secret gate guards commits, not reads

> **The transcript is an egress path, and nobody had modeled it as one.**

- **The gap.** Every secret control in this repo is a **commit-time** control — DEC-0012,
  `check_secrets.sh`, the CI secret-scan, the 41-payload proof suite. Four hardenings across S26 → S40, all
  of them guarding the **write** path to GitHub. **None says anything about reading.** Whatever a tool
  prints lands in `~/.claude/projects/*.jsonl` in plaintext and is transmitted to the model provider. The
  `.gitignore` entry feeds the blind spot: the live config is *deliberately* excluded from the repo, which
  makes it feel handled. **"Not in the repo" is not "not in the transcript."** DEC-0040 said *prose does not
  execute*; this is worse — **there was no prose.** No rule was broken because no rule existed.
- **What surfaced it:** a `sed -n "/^[Logging]/,+44p"` on the live config during this deploy. A fixed
  **line-count** window on a sectioned file: `[Logging]` is ~22 lines, so it ran off the end and printed the
  following sections into the transcript. **A line-count window on a sectioned config is a loaded gun —
  sections move, the window does not.**
- **Three mechanical controls, in `~/.claude/`** (global — DEC-0040's "no master repo"):
  `hooks/secret-read-guard.sh` (PreToolUse on Bash/Read/Grep; blocks *secret path* × *emitting verb*, sees
  through `ssh "…"`, **leaves editing alone** so the DEC-0046 release workflow still works — a guard that
  blocks the work gets switched off; matches **per-token**, so `cat weewx.conf.example && cat weewx.conf`
  cannot launder the live config through the `.example` carve-out);
  `bin/readconf` (**section-scoped — it structurally cannot take a line window**; values become stable
  `sha256` fingerprints while `handlers = rotate,` and `level = INFO` stay readable, because a DEC-0046
  deploy has to verify exactly those); and `bin/scan-transcripts` (the detection half).
- **Proven, not merely green.** The guard's suite asserts **both directions** (38/38 — the leaking command
  blocks; `cat weewx.conf.example`, `sed -i`, `cp`, `readconf` all still pass), and a **mutation test**
  turns it **red — 18 failures.** The scanner **self-tests before every run** and refuses to report "0" if
  the harvest returned nothing. **Verified live:** re-running the original command is now blocked by the
  hook.
- **A scanner that cries wolf is its own failure mode.** The first pass reported a real password sitting in
  `weewx.conf.example` on public `main` since S16 — which would have been a live exposure and a fifth gate
  hole. It was the example's own placeholder string. The evidence looked internally weird (the same
  "password" appeared as three different keys), and re-checking it is the only reason a five-alarm claim was
  not filed. DEC-0039: *a green exit code is not evidence.* DEC-0045: *a passing test is not evidence
  either.* **S41: a scan that finds nothing is not evidence unless you have proved the scanner can see.**
- **A full scan of all refs confirms no real credential has ever been committed to any of the three repos.**

### Housekeeping — the cleanup that found its own backlog item was stale

- **DEC-0049 — the ISS hardware is new and inspected, so the phantom rainRate is not a broken part.**
  DEC-0042 closed with *"next step is physical: inspect the bucket, the reed switch and its wiring."*
  **That action is now closed and it came back clean.** The owner reports the ISS hardware is **new**, was
  **recently inspected**, and has **no faults** — the one component that did fail, the **anemometer**, was
  **replaced ~16–17 June 2026**. A clean inspection does not falsify DEC-0042, it **sharpens** it: the two
  readings were always *defective part* or *working part reacting to the environment*, and **the first is
  now excluded.** Condensation bridging a **healthy** reed switch produces exactly the measured signature
  (94 % RH, 1.7 °F dewpoint spread, 0 mph wind, tip counter never advancing). **There is nothing to swap and
  no part to order** — anyone reading DEC-0042's "next step is physical" without DEC-0049 would order one
  for no reason. The anemometer date is also a **dating anchor**: wind data either side of mid-June comes
  from different physical hardware.

- **DEC-0048 — reception testing is a designed experiment, not a pile of image tags.** `rw250-test` is
  retired. It was a **misnomer within a day of being built** (`receiveWindow` ships at the upstream
  default), and it was **never published to Docker Hub** — verified against the live tag list, so the
  confusion was only ever ours. The deeper point: that sweep was never a controlled experiment, which is
  also **why DEC-0017 has sat open since S16** — gain is held at 372 pending an "averaged re-test" that
  never happened because no method was ever agreed. A proper RX test is **deferred, not abandoned**: when it
  runs it gets a hypothesis, a control arm, an averaged window, and a pre-registered metric — and it settles
  **gain 372-vs-207 and `receiveWindow` in the same run**, since they share the same apparatus and the same
  confound. Until then **neither parameter gets tuned by feel.**

- **Branch cleanup — and the backlog item was stale.** STATUS had been asking us to delete
  `feature/rain-spike-filter` and `s32-reconcile-main`; **neither still existed.** What *did* exist was **8
  merged `worktree-*` branches**, each verified at **0 unmerged commits** before deletion. The remote is now
  exactly **`dev` and `main`**. All three Eagle Hunt repos have **zero** open PRs, and the dashboard's
  long-flagged stranded draft PR is gone too.

## [S40] — 2026-07-13 — a comment is not an exemption: the gate's proof had certified the hole

> **The secret gate let commented-out credentials into a PUBLIC repo — and its own test said that was
> correct.**
>
> Carried over from the close of S39, where it was spotted and deliberately left as the owner's call.
> `scripts/check_secrets.sh` had an `ALLOW (1)`: *if the whole line is a comment, allow it.* So
> `# api_key = <a real credential>` shipped clean. `git push` does not strip comments, and neither does
> anyone reading the file on GitHub.
>
> **The part that made this a DEC and not a bug fix:** the rule was not a blind spot the test missed —
> **the test asserted it.** Two commented credentials sat in `test_check_secrets.sh` under *"must PASS"*,
> and they were part of DEC-0039's celebrated *"28/28 planted payloads, proven"*. DEC-0039's thesis is
> *"a green exit code is not evidence."* S40's correction: **a passing test is not evidence either, if
> the assertion is wrong.** The proof had certified the hole.

### Fixed — DEC-0045: comments are scanned exactly like code

- **`ALLOW (1)` deleted.** No comment rule at all. A comment earns no exemption; only its **value** can.
  `# api_key = YOUR_API_KEY_HERE`, `# token = "${INFLUX_TOKEN}"` and the `influx.py` docstring style still
  pass — via the placeholder / interpolation / prose rules, which test the value. Commenting a line out no
  longer changes the verdict **in either direction**.
- **No new exemptions.** The gate's own header had illustrated three past bugs with six real-looking
  credential literals, which the fix now flags. The tempting move — exempt `check_secrets.sh` by path, as
  the test file already is — was **rejected**: that is a 130-line blind spot in the one file that most
  needs scanning. The literals **moved into `test_check_secrets.sh`, where they execute as payloads**, and
  the header now points at them. DEC-0040 applied to the gate itself: *prose does not execute.* The gate
  scans 100 % of tracked files, including its own source.

### Evidence — because a green run proves nothing on its own (DEC-0039)

- **Blast radius measured before deciding:** deleting `ALLOW (1)` produced **6 hits across the entire
  tracked tree, all of them inside the gate's own header comments.** Every legitimate comment elsewhere
  (README's `YOUR_*` blocks, `influx.py`'s docstring, the handoff docs) already passed on its *value*. The
  exemption was doing **no legitimate work in this repo** — it was close to pure hole.
- **Planted-payload suite: 41 passed, 0 failed** (was 28). Seven new BAD payloads cover every comment
  marker form (`#`, `//`, `/* */`, ` *`, indented, no-spaces) plus a commented constructor line; six new
  GOOD payloads are the same placeholder/prose/empty values wearing a comment marker.
- **Mutation test:** re-adding `ALLOW (1)` turns the suite **red — 7 LEAKED**. The fix is load-bearing and
  the test can actually fail.
- **Full-history scan: 0.** Every blob that ever existed in this repo (**333 unique, all refs**) was
  scanned for a commented credential. None. **The hole was never exploited** — nothing needs revoking, and
  no history rewrite is warranted. Positive-controlled: the same scan with the gate's own files re-included
  finds the 11 known header examples, so the scanner demonstrably sees things. (The first version of that
  scan reported a false "0" because `git` was silently not running inside the loop and `2>/dev/null` ate
  the error — caught only *because* the positive control was run. Same lesson, third time in one session.)
- **The gate blocked this session's own ADR** on first draft (4 hits — it quoted the payloads verbatim).
  The literals were removed rather than exempted.

### Also

- **PR #34 merged** — S39's work (DEC-0043 root logger, DEC-0044 nibble theory) landed on `dev`. It had
  been sitting open and green since S39; the session-start hook flagged it.
- 72 pytest tests still green. **Prod untouched** — still `:v2.0.6`, `RestartCount: 0`. This session
  changed no runtime code, only the commit-time gate and its docs.

---

## [S39] — 2026-07-13 — the root logger nobody overrode, and a theory that did not survive its own test

> **Two findings, one shipped fix, and one filter deliberately NOT built.**
>
> A routine post-deploy health check on `:v2.0.6` found prod emitting **15 logging-error tracebacks
> (~515 lines) to stderr on every container start**. Root cause: weewx's own defaults point the **ROOT
> logger** at a syslog handler on `/dev/log` — a socket that does not exist in a container. Our
> `logging.additions` had always overridden the `weewx` and `user` loggers, but `weewxd` and
> `weeutil.*` are in **neither** namespace, so they fall through to root and blow up there.
>
> The louder half is cosmetic (bounded burst; steady state is still 0 lines/90 s, so DEC-0041 holds).
> **The quieter half is not:** `weewx.log` has *never* contained a single `weewxd` or `weeutil` line —
> no version banner, no config path, no group list. Those records were not noisy, they were **lost**,
> and the failure announced itself only on a stream nobody reads. Fixed with a `[[root]]` override plus
> a build-time assertion, and verified A/B inside the real container: with the fix, `weewxd INFO
> Starting up weewx version 5.4.0` lands in the file for the first time. **DEC-0043.** Ships in v2.0.7.

**The coupling filter was on the S39 plan. It is not being built, and that is the bigger result.**

The inherited task was a "cross-sensor consistency filter" from dashboard S69: *a humidity move
>6 %/min with temperature essentially flat is physically impossible*, reported 3-for-3 with 0 false
positives. Underneath it sat an unproven mechanism — the **nibble theory**: the ISS message-type nibble
(`pkt[0] >> 4`) takes a bit flip, so **another sensor's payload is decoded as humidity**. S69 proposed a
falsifiable arithmetic test and never finished it. S39 finished it. **DEC-0044.**

- **The theory's arithmetic contradicts its own story.** Humidity is `0xA` = `1010`. Its single-bit
  neighbours are `0x2` (supercap), `0x8` (temp), `0xB` (undefined), `0xE` (rain). **Solar is 2 bits
  away; UV is 3.** So "a misdecoded solar/UV payload — that's why it's always midday" is not reachable
  by a single bit flip, and midday was the theory's headline evidence.
- **Every testable variant fails.** UV: implied ≈ 2× actual on *every* spike. Temperature: implied
  200–400 °F. Supercap: fails where testable.
- **The solar "match" was fitted noise.** Recovering a raw reading from a 1-minute average needs
  `raw = n·spike − (n−1)·baseline` with `n` unknown; letting `n` float over {1,2,3} scored 12/28, but
  the winning `n` came out uniformly **{1:4, 2:4, 3:4}** — a meaningless parameter. Against **2000
  shuffled pairings**: true 43 % vs chance 35 %, **p = 0.248**.
- **This is structural.** The free parameter exists *because* the archive averages, and it is precisely
  what manufactures false matches. **No analysis of 1-minute data can settle this** — and InfluxDB
  stores the same 1-minute records (checked: bucket `weewx`, retention infinite).
- **The filter's own premise is weak too.** "Temperature essentially flat" describes **90 % of all
  minutes** (66,743 of 74,538 at |ΔT| ≤ 0.1 °F), so the flatness test discriminates almost nothing. And
  every spike visible in the archive implies a *raw* glitch of 16–37 %RH — **already rejected by
  DEC-0029's existing 10 %RH-per-reading cap**. The filter would have targeted a residual we never
  showed exists.
- **The cited false-positive test was not evidence.** The 2026-05-23 "gust front" shows a maximum
  humidity move of **1.0 %/min** in our archive (90 %RH, 50 °F, wind ≤ 2.5 mph — a calm, saturated
  day). Any threshold spares it.

**So: instrument, don't filter.** The decisive instrument was already in the code — **`log_humidity_raw`**,
an upstream option (Luc Heijst's) nobody had switched on. It logs `(pkt[4] << 8) + pkt[3]`: **both raw
payload bytes**. With a real `pkt[4]` there is no averaging and no free parameter, and the inversion
becomes deterministic. Armed in the live `weewx.conf` (INFO → file handler only; prod declares no
console handler, so it adds nothing to stdout and carries no DEC-0036 risk). It activates on the next
restart, and the next midday spike settles the question.

**Also:** `iss_channel = 5` with every other channel `0` — there is exactly **one** transmitter, so
"bleed from another *transmitter*" was never possible. A type-level misroute inside the ISS's own
packets is the only mechanism the hardware permits.

**Tests:** 67 → **72**. The five new ones assert the `[[root]]` override in both shipped configs and the
Dockerfile's build-time assertion; deleting the `[[root]]` block fails three of them (planted-payload
check, per DEC-0039).

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
public breaks. Prod deliberately stayed on `:v2.0.4` **at that point in the session** — the delta was
behaviorally nil here (prod's `weewx.conf` has no console handler at all — the config drift that spared
us), and redeploying prod unattended, hours after a seven-hour outage, to fix something that did not
affect prod, was the wrong trade. *(Resolved later the same day: once v2.0.6 existed and the owner was
present, prod was deployed to `:v2.0.6` in an attended window and `prod-baseline-20260713` was tagged —
see below.)*

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
- **[The issue-#15 comment is POSTED](https://github.com/lheijst/weewx-rtldavis/issues/15#issuecomment-4960224128)**
  (owner-approved, 2026-07-13) — **the first comment on that thread since 2022-11-14.** It explains the
  duplicate-frame mechanism, the wraparound bug, and that the phantom **rainRate is ISS-side, not a driver
  bug** (DEC-0042) — which the three people there had been hunting in software for four years.

**DEC-0042 — the phantom rainRate is ISS-side, and the rainRate thread is CLOSED.** Reconstructed from a
2026-05-29 DB backup that happened to predate our own S36 correction: no real rain that day at all; the
rate held **03:22–03:37 UTC, sharp on and sharp off** — exactly the ISS's ~15-min timeout; the implied tip
interval stayed in a tight **8.5–10.0 s** band; and **the tip counter never advanced** (`rain = 0.0000` in
all sixteen records). Decisive: reaching those raw values from the `0x3FF` "no rain" sentinel needs **~6
bit-flips in every packet for sixteen consecutive minutes** — RF corruption gives *one* bad packet, not a
coherent stream. **The ISS sent them.** Conditions both events: overnight, 94 % RH, 1.7 °F dewpoint
spread, 0 mph wind. **Condensation trips the reed switch enough to start the rate timer, never enough
water to tip the bucket.** So DEC-0033/0035 are now explicitly *bounded* — they explain the rain
**counter**, and no decode-layer filter will ever touch the rate. **The next step is physical, not
software.** Method lesson kept in the ADR: this was only answerable because a backup predated our own
correction — **snapshot the affected rows BEFORE a retrospective correction, not after.**

**Prod finished the session on `:v2.0.6`, and `main` == prod again.** Recreated 11:09 EDT; verified
`driver version is 0.20+ws.1 (fork of lheijst 0.20)`, `sensor_qc True`, `influx service version 0.20+ws.1`,
stdout **silent**, every uploader publishing, `RestartCount: 0`. `prod-baseline-20260713` tagged, which
restores DEC-0011's *`main` = production truth* invariant that S38 deliberately broke for a few hours.
Prod's bind-mounted `influx.py` also caught up with the repo (it had drifted — DEC-0031's class again:
the running copy still had `VERSION = "0.20"`, the unconditional `_create_unverified_context()`, and
per-record `loginf` spam; not a live exposure, since the endpoint is plain http).
