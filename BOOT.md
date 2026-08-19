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

## ▶ Resume here (S94 → S95)

### What's settled (do not re-derive)

**#227's sequence: #223 fixed, tested, shipped — 5 of 8.** The frontier item, and its four defects
really were one design gap. **DEC-0103 records both open calls, decided:** (1) the **bounds vs delta**
split is the convention — a bounds reject (impossible reading, or gust < its own speed) is proof of
corruption so the baseline stays untouched, while a delta reject may be a genuine gust front so the
baseline **always resyncs, even on reject**; that resync plus a 300 s TTL is what kills the permanent
deadlock. (2) **Ported locally, NOT imported** from `rtldavis.py` — `dewpoint_service.py` keeps its
zero coupling to the driver, because `docs/INTERFACES.md` commits it to being re-pointable at
non-Davis WeeWX; the small duplication is the cheaper cost and is deliberate. Also: `windDir` now
co-nulled in every reject branch (the one consumer-visible change — a bare heading used to reach
loop-JSON, InfluxDB and every uploader), warmup samples bounds-checked before seeding, `windGust`
bounds-checked independently. 10 tests. **PR #241, merged (`592064b`); #223 closed on GitHub with an
explanatory comment.** 339/339, ruff/mypy clean (57 files), secret scan positive-controlled.

**`dewpoint_service.py` is BAKED, not mounted** — verified by `nasctl inspect` + positive control,
not assumed from `pressure_service.py`. `CONSTANTS.md`'s deploy-layer table was missing the file
entirely (the S85 `loop_json_writer.py` omission again) and now carries the row. **Nothing deployed
this session** — ships on an image rebuild behind v2.0.14.

**Model tier: nothing to restore — and that answer came from the files, not from the rule.** S94
escalated to Opus for #223's design work with a bare `/model claude-opus-5`. OPS-DEC-0010 says that
form persists as the new-session default, so the reflex is to declare a restore owed. **That reflex
was already wrong once here (S89): asserted three times from the rule, shipped into this very footer,
and corrected only when ops reported back.** So it was checked instead — all five scopes:
`~/.claude/settings.json` = `sonnet`; `~/.claude/settings.local.json` absent; `.claude/settings.json`
and `.claude/settings.local.json` carry no `model` key; canonical
`eaglehunt-ops/global/settings.json` = `sonnet`. **In this client that switch touched no floor file.**
Answer closeout step 6 from the files every time — a wrong tier claim in a tier-1 doc of a public
repo propagates to other repos' sessions within the hour. *(Read with a LEADING `command jq -r
'.model' <file>`; nested in a subshell or loop the read-guard still blocks.)*

### ▶▶ S95 JOB LIST

1. Daily square watch (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
2. **[ops#169] — OWNER-RAISED PRIORITY (S94): act within the next few sessions.** Read
   `eaglehunt-ops/NAS-LEASE.md` (the spec, OPS-DEC-0107) before planning — **it already answers most
   of what a session would otherwise re-derive, and it contradicts DEC-0099's framing.**
   - **The "two strands" are one strand.** coffee-radar's disk-contention handshake IS NAS-LEASE:
     their DEC-0181 Stage 2 (the handshake) landed *as* OPS-DEC-0107. Stage 1 (`--blkio-weight`
     caps) is coffee-radar-unilateral and needs nothing from weewx. There is no second protocol to
     wait for.
   - **⚠ The v2.0.14 mount is NOT a gate on adoption — S94's earlier claim here was wrong.** §9 has
     already decided weewx's client's *"natural home is host-side"* **precisely to avoid the
     container recreate.** The HOLDER role (wrap the NAS image build, `docker build`, DEC-0078) runs
     on the host; the OBSERVER half (read the lease, append to the log) is `weewx_monitor.py`, which
     is already resident, polls 30 s, and sees the volume natively. **Neither needs any container
     change.** Only the InfluxDB `post_interval` downshift — one optional yield lever — needs
     `LEASE_DIR` inside the container, and that is the *only* thing the v2.0.14 mount buys.
   - **§8 already designates weewx's ~08-23 v2.0.14 image build as the protocol's FIRST CROSS-TENANT
     EXERCISE** ("a weewx-held lease coffee-radar and HLF can observe"), ranked #3 of 3. That is the
     real deadline, and it is a holder-side job needing no mount.
   - **★ Governance consequence nobody has flagged: §5's constants LOCK when the SECOND adopting DEC
     lands.** HLF's DEC-0177 was the first. **weewx's would be the second — so weewx's adoption
     freezes the protocol constants for every tenant.** Treat that as a deliberate act, not a side
     effect; any amendment weewx wants must be raised on ops#169 *before* its own DEC lands.
   - **Pre-flight, verified S94:** `LEASE_DIR` = `/volume1/docker/nas-lease/` **exists**, mode
     `drwxrwxrwt` (1777, as specified) — the one-time owner step is DONE; `heavy-io.log` is live and
     HLF is actively renewing (held ~8.7 h on 08-19, released `outcome: step-failures`). A weewx
     client is Python `fcntl.flock()`, no binary needed (§9). **Still unverified:** that weewx's
     runtime user can create/rename in `LEASE_DIR`, `O_CREAT|O_EXCL` atomicity on the btrfs mount,
     and a cross-tenant-visible log append. **weewx has NO declared renewal floor** (§5 lists it
     "none declared") — wrapping the build requires declaring one.
   - **Red lines the spec already records for us:** SQLite archive commit is **never** deferred, and
     `loop-data.txt` has a **hard 30 s ceiling** (the eh-proxy 503s past it and the dashboard treats
     that as station-down). Any lease write is in-place (seek+write+truncate), **never**
     `loop_json_writer.py`'s tmp+`os.replace` idiom — §3, and DEC-0051 is our local record of why.
3. Continue #227's sequence: **#224 next** (tier:mid, same file as #223 — `dewpoint_service.py` — so
   it pairs naturally and DEC-0103's context is fresh). **#223 widened its surface:** #224 already
   flagged `MAX_WIND_DELTA = 75.0` as documented-mph and therefore miscalibrated under
   `target_unit=METRIC`, and S94 added `MAX_PLAUSIBLE_WIND_SPEED = 200.0` in the same units — fix
   both constants in the same pass as the `dewpointF`/`heatindexF` unit branch. #225/#226 are lower
   priority (confirmed dormant / cheap-tier) and can ride v2.0.15+.
4. **v2.0.14 prep is DONE for code**, now also carrying #223's fix. One optional addition to decide
   before the cut (not a blocker on job 2, see there): whether to mount `LEASE_DIR` read-only into
   the container while it is being recreated anyway. That mount buys **only** the InfluxDB
   `post_interval` yield lever; skipping it costs that one lever until the next recreate, and costs
   adoption nothing.
5. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
6. **[ops#173] BOOT.md over cap — TRACKED, do not re-derive or open a second issue.** Diet at the
   square's close (~08-23), still deferred on purpose.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173
[weewx#227]: https://github.com/WeatheredScientist/weewx-rtldavis/issues/227

### Current state (S94 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b |
| Campaign B | **Live and on schedule — arm C since 08-19T12:07:28.** Square through `08-23T00:05`. STOP/PAUSE/lock absent. Soak (S94 start): 16 pass / 2 expected-WARN, reception 71%/62% |
| Swap settle time | n=10 (unchanged since S90): 82/139/198/137/197/79/136/196/144/84 s — not a trend |
| Retention | **BOTH halves SETTLED** (DEC-0095/DEC-0100), unchanged since S90 |
| `dev` beyond prod | Everything for v2.0.14 **plus** DEC-0102, #219–#222, and **DEC-0103 / #223** |
| Freeze rate | DEC-0088-corrected (1.31/day); DEC-0102 adds the overnight-window confound number |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Branches | **Steady state restored: exactly `dev` + `main`.** S94's feature branch merged and deleted, remote + local, same session |
| Trackers | **#227: 5/8 done, merged and closed on GitHub.** #233 open (follow-up from #219, tier:mid) · #172/#144 open until v2.0.14 · #204 open (current.json cadence). Recently-closed issues audited at close: all carry an explanatory comment, no silent closes. Remember `Closes #N` does NOT auto-fire here (PRs land on `dev`, not the default branch) — S93 found #219/#220/#221 silently unclosed for exactly that reason |
| Cross-repo (S94) | Swept. **[ops#169] — the owner raised its priority at S94 close: "must prioritize more highly very soon, next few sessions for sure."** Promoted out of this row into **job 2**, where the v2.0.14 hard gate is spelled out. coffee-radar found live shared-NAS disk contention (~41% iowait) naming weewx's InfluxDB ingestion an unconfirmed contributor; weewx's S92 probe measured 11.80x overnight iowait into the same thread. Everything else unchanged |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected), separate phenomenon**
   from DEC-0081's RF-dead episodes. Still hard-aborts. Root cause unproven (thread blocking on the
   bind-mounted log volume is the leading hypothesis, DEC-0067/0068). Evening 18:00–21:00 carries
   the signal (DEC-0094). Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds a timing
   signature (clusters 00:00–04:00); DEC-0102 adds the first kernel-level number on the leading
   confound (11.80x iowait) but does NOT close it. Next real step is multi-night minute-level
   correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; not fully closed, its 21-stall episode remains the
   largest on record. Unchanged.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B. Unchanged.

## Gotchas that survive here because they are NOT in the canonical docs

- **A failing test proves nothing if it fails for the wrong reason** — the mirror of DEC-0045's
  positive-control rule, and it looks *identical* to real evidence. S94's first pre-fix proof had all
  10 new tests failing against the stashed old file; every one died on
  `TypeError: unexpected keyword argument 'now'` — the signature change, not the defects. **When a
  fix changes a signature AND behavior, shim the signature so only behavior is under test**, then
  re-run. Post-shim: 6 of 8 failed for the right reason, 0 after the fix.
- **Write the BOOT handoff AFTER the merge, not before.** S94 wrote it while the PR was still open,
  so it shipped telling the next session to delete a branch already gone and close an issue already
  closed — needing a second doc-only PR to correct. The closeout ritual's step order (BOOT at 2,
  commit/push at 7) reads as if BOOT comes first; for anything whose truth depends on the merge
  landing (branch state, tracker state, merge commit sha), it does not.
- **A `grep -o 'DEC-0[0-9]*' | tail` to find the next DEC number returns OTHER REPOS' numbers** —
  cross-repo references (HLF DEC-0177, ops DEC-0107) are quoted verbatim inside this repo's own DEC
  bodies and sort highest. Read the index table's last row instead. Same false-signal family as the
  zero-from-a-look-alike-tool rule below.
- **A SessionStart concurrency FYI can name a session that does not exist.** Seen twice now (S93
  post-crash, S94 clean start): the hook flagged a "live peer" that `ListAgents` did not list at all.
  Do the check — `git status` + `ListAgents` — but treat the FYI as a claim, not a fact.
- **Adding a new driver-state read to `parse_raw` breaks every test fixture that predates it,
  silently, until the FULL suite runs** (#222). Any change making shared decode code read one more
  field from a driver-shaped object needs a full-suite run before trusting one new test file's green.
- **A tool's "control" set silently absorbs a second named window's data unless BOTH are excluded
  from each other** (`ops/proc_probe.py --analyze`, S92, fixed). Adding a second measurement target
  to an existing analysis tool needs the window/control partition re-examined explicitly.
- **`/code-review ultra`'s cloud launcher wants a base branch, not a path target** — the local
  `/code-review <target> <level>` is the one honoring a path/PR/branch argument. Paths passed to
  `ultra` are read as a free-text note and it diffs `dev`→`main` instead (S91, cost a free slot).
- **Campaign clocks are LOCAL (EDT); most tool output is UTC — convert before comparing.** Check the
  actual process/log evidence, don't compute (S83, S91/DEC-0068, S92/DEC-0098).
- **A file match proves the FILE, never the PROCESS** (DEC-0074) — liveness = startup line after
  file mtime, `/proc/<pid>/stat` field 22 vs `/proc/uptime`, new pid + old gone.
- **`secret-read-guard.sh` trips every NAS `scp` deploy** (S81/S82/S82b) — settled fallback: hand the
  owner the single command, saying explicitly it runs on the Mac.
- **A guard block can be a MISFIRE — check before going near the mint path** (S85, ops#176). Rung 0:
  re-spell it (`Write`/`Edit` instead of a shell heredoc). **The `ssh nas` alias is genuinely
  read-only at the KEY level** (forced command, ops#82) — a refusal there is server-side, not a
  Claude guard, and is not the signal to start the mint dance; `ssh nas-admin` is the mutation-capable
  alias that actually triggers the Class C hook.
- **`gh pr merge`'s output is never trustworthy either way** — silent/empty stdout can mean success,
  an explicit error can mean a transient state. Only `gh pr view --json state,mergedAt` is
  trustworthy, every time (re-confirmed S93 on #238).
- **A freshly-opened PR reads `BLOCKED`/`UNKNOWN` before CI reports — a timing state, not a problem.**
  `land` says "no checks reported (yet)"; a GET seconds later shows them QUEUED/IN_PROGRESS
  (re-confirmed S94 on #241, which went CLEAN shortly after).
- **A second same-session PR branched before the first merged sits BLOCKED by branch protection**
  ("3 of 3 required status checks are expected", or `mergeStateStatus: BEHIND`). Fix:
  `gh api -X PUT repos/<r>/pulls/<n>/update-branch`, wait for the rerun, then merge.
- **Merging several same-session PRs in sequence: re-`git fetch`/`git pull` before every merge-into.**
  And **never `git checkout -- <file>` to unplant a staged positive-control payload** — it restores
  the planted version from the index; edit the lines out instead (re-confirmed S94).
- **`rx_experiment.lock` exists only during a pass's critical section** — absence at rest is correct;
  a holder older than 1800s is broken automatically and loudly.
- **Driver re-inits log `startup process`, never `Starting up weewx`** — a boot-marker grep that
  misses this reads respawns as absent.
- **`nasctl` is read-only** — NAS mutations need the Class C mint path (mint and re-run as TWO
  separate calls, never chained with `&&`).
- **`due_arm()` never returns `NONE` once the pilot block has run** — check `current_arm()`/state +
  STOP/PAUSE directly, not log silence. *(An EMPTY schedule does return `NONE` — the DEC-0096
  stand-down state; `install` refuses it before it can matter.)*
- **`rx_experiment.sh` the SCRIPT lives flat at the NAS project root, its LOG output does not**:
  `.state`/`.STOP`/`.PAUSE`/`.lock` flat at the root; `.log`/`_data.log` under `logs/`. **So does
  `weewx.log`** — `logs/weewx.log`, not `weewx-data/weewx.log`.
- **`nasctl grep` takes `<pattern> <file>`, pattern first, single-word patterns only** — multi-word
  patterns silently return a FALSE ZERO through the ssh quoting layer. **Positive-control any zero
  count** (used again S94 to prove the mount grep). `nasctl cat`/`tail` need **absolute** paths.
- **GitHub's API can degrade on WRITES while READS stay fine** — verify with a GET before assuming a
  mutation failed either way.
- **zsh reserves `$status` as an alias for `$?`** — a loop variable named `status` fails to assign.

_Last updated: 2026-08-19 (S94 close — escalated to Opus for #223's frontier design work; **the
floor was verified intact across all five scopes at close, nothing to restore** — see above, and
note the S89 precedent for why that is checked rather than inferred). Green gate run on the
branch: ruff clean, mypy clean (**57 files**, up from 56 — the count is the only proof the new test
file was not silently skipped), **339/339 tests**, secret gate positive-controlled with a planted
payload and the file verified byte-identical afterward. #223 shipped end-to-end: design discussed and
both open calls decided before any code, implemented, proven against pre-fix code through a signature
shim after the naive attempt proved nothing, landed as PR #241. DEC-0103 written (index + full body,
same session). CONSTANTS.md gains the `dewpoint_service.py` deploy-layer row. ROADMAP.md checked:
DEC-0103 ships/closes no P0–P3 line — nothing to reconcile, tripwire unchanged at S96. CHANGELOG.md
entry written; S91 rolled to `CHANGELOG-ARCHIVE.md` verbatim (64 lines, byte-identical, verified
before write), keeping the ~3-session window (S92/S93/S94). Campaign B checked at session start,
healthy, untouched by any of this session's work._
