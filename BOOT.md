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

## ▶ Resume here (S96 → S97)

### What's settled (do not re-derive)

**ops#169 / NAS-LEASE is CLOSED end-to-end — `DEC-0107` holds the whole record.** Every item landed
in one session and **all three box-level fixes rest on direct observation, none on report**:
`LEASE_DIR` is `drwxrwxrwx` (sticky dropped), `heavy-io.log` is `0666`, `chattr +a` reads
`-----a------------`. Spec is **`NAS-LEASE.md` v1.4 / OPS-DEC-0110**; HLF patched their create mode
(their PR #388). Do not re-measure any of it.

**Both weewx lease roles run NON-ROOT** — observer `weewx-monitor` (uid 1031, DEC-0009), holder a
**separate** non-root account whose name lives **only in the gitignored local-infra doc**: it is the
owner's personal login, absent from every tracked file, and this repo is public and permanent.
Describe it by function, never by name. Widening the monitor's sudo grant to dodge a file mode was
considered and **rejected** — it trades DEC-0009 for a `chmod` someone else can make.

**★ DEC-0107 is deliberately NOT the adopting DEC.** Landing one **LOCKS §5's constants for every
tenant** (HLF's DEC-0177 was first), so it must lock a corrected spec. Adoption is now blocked on
**nobody but us**.

**#224 shipped** (PR #255): `dewpoint_service.py` branches on `usUnits` per WeeWX's own
`wxxtypes.py` — *not* `to_US()`, which is right for `loop_json_writer.py` only because that service
*emits* US and never converts back. Suite **339 → 349**.

### ▶▶ S97 JOB LIST

1. **CONFIRM THE MERGES FIRST — three PRs were left open at S96 close, all CI-green:** **#254**
   (DEC-0107), **#255** (#224), **#256** (ROADMAP). Steady state is exactly `dev` + `main`; if the
   branches survived, delete them. `Closes #N` does **not** auto-fire here — PRs land on `dev`.
2. **Daily square watch** (~5 min): `ops/soak_check.sh` + a direct `rx_experiment.state` read.
   **Campaign B ENDS 08-23T00:05 — imminent.** Rotation-artifact WARNs after midnight are #252, not
   findings; the `stdout is chatty` WARN is #253 and is permanent until the next container recreate.
3. **★ The ~08-23 v2.0.14 build is now a THREE-purpose event — plan it as one.**
   - It carries **#224** (baked in the image, so this is how it reaches prod).
   - It is the lease protocol's **first cross-tenant holder exercise** (§8): wrap `docker build`
     with acquire → flock → release. **Red lines:** lease writes **in place** (seek+write+truncate),
     **never** tmp+`os.replace` — that strands the flock on an unlinked inode (§3, DEC-0051); SQLite
     archive commit **never** deferred; `loop-data.txt` hard 30 s ceiling.
   - It is when **weewx's adopting DEC lands and LOCKS §5 for every tenant.** Take the next free DEC
     number then. Declared floor **600 s / TTL 3600 s** — dated data from DEC-0078's ~10 min
     v2.0.12 build, **to be re-pinned against this build's measured duration**.
   - Optional call: mount `LEASE_DIR` read-only while the container is being recreated anyway. Buys
     **only** the InfluxDB `post_interval` yield lever; skipping costs adoption nothing.
4. **Continue #227's sequence: #225/#226 remain** — lower priority, can ride v2.0.15+.
5. **Watch for HLF's ~08-23 floor re-measure.** Their blend-refresh ran 88 min → 155m31s → 275m33s.
   We read the near-identical ratios (1.767, 1.772) as compounding; **they explained it better** —
   the three points bracket exactly two feature landings (their DEC-0173, DEC-0178), so two
   similarly-shaped layers give two similar multipliers as *steps*. Their re-measure with no new
   layer is the discriminating test. **Either way their 8 h TTL goes out of spec the moment they
   declare honestly** (3 × 275 min = 13.8 h), and **a raised TTL is a cross-tenant cost** — the slot
   is single, so a wedged holder blocks our build for the entire TTL. We argued for lowering the
   floor (intra-step heartbeat) over raising the TTL; they noted, correctly, that this changes the
   declared floor's meaning from "longest step" to "heartbeat cadence".
6. **Gain/receive-window hot-swap: filed, deliberately NOT started** — `BACKLOG.md` §Open ideas +
   [ops#179]. Revisit once the square closes **and** the gated queue clears.
7. **[ops#173]** — diet done at S94; left open on purpose for the automated sweep to close. Nothing
   to do unless it re-flags.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179
[ops#173]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/173

### Current state (S96 close)

| Thing | State |
|---|---|
| Prod | **v2.0.13**, driver **ws.5**; NAS-resident `rx_experiment.sh` + `weewx_monitor.py` unchanged since S82/S82b |
| Campaign B | **Live, arm B since `08-20T00:07:30` EDT.** Square through **08-23T00:05**. Soak at S96: **17 pass / 2 warn / 0 fail** — both warns known (#253 chatty stdout; USB hedge 4/4, expected during RF-dead per S73) |
| Restart rate | DEC-0106 baseline: 4/day during a campaign (all at HH:05), **0/day between**. A real loop is 7 starts in 7 min |
| Retention | **BOTH halves SETTLED** (DEC-0095/DEC-0100), unchanged since S90 |
| `dev` beyond prod | Everything for v2.0.14 **plus** DEC-0102/0103/0104/0106 and, once #254–#256 merge, **DEC-0107 + #224 + the ROADMAP pass** |
| Freeze rate | DEC-0088-corrected (1.31/day); DEC-0102 adds the overnight-window confound. Unrelated to DEC-0106 |
| Live-config deviations | unchanged: `timeout=30`, `[[[pragmas]]] journal_mode=DELETE`, DEC-0080 radiation zero. Table in `CONSTANTS.md` |
| Hub | `:v2.0.13` pushed; `:latest` still `:v2.0.12` until the square proves ws.5 |
| Trackers | **#252/#253** open (soak follow-ups) · #233 open · #172/#144 open until v2.0.14 · #204 open · #227 at 6/8 (#224 done, #225/#226 left). **ops#184 open on purpose** (HLF redirect). ops#169 **CLOSED** |
| Cross-repo (S96) | ops#169 closed with coffee-radar + ops + HLF; nothing owed to anyone. HLF's floor re-measure is the only live thread (job 5) |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven
   (thread blocking on the bind-mounted log volume leads, DEC-0067/0068); evening 18:00–21:00 carries
   the signal (DEC-0094). Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds 00:00–04:00
   clustering; DEC-0102 the 11.80x iowait confound, which does **not** close it. Next real step is
   multi-night minute-level correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; its 21-stall episode remains the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Model tier — ACTION OWED

**S96 ran on Opus 5, escalated mid-session via a bare `/model claude-opus-5`, which PERSISTS as the
new-session default (OPS-DEC-0010).** In the desktop app the floor is inert and every switch persists
in app state that `settings.json` does not reflect (OPS-DEC-0036/0062) — so a file check will look
clean while sessions still start on Opus. **Restore to Sonnet in the app by hand.** A repo session
may not edit the machine-wide floor itself (OPS-DEC-0060).

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-20 (S96 close). Green gate: ruff clean, **349/349**, mypy clean (57 files),
secret gate clean **and positive-controlled** (harness 54/54; `scripts/.identifiers` confirmed
present, without which the personal-identifier half silently skips). Shipped **DEC-0107** —
ops#169 closed end-to-end, all three box fixes on direct observation — plus **#224** and the
**S96 ROADMAP reconciliation** (tripwire → S106). Three PRs left open and green: **#254, #255,
#256**. Full narrative in `CHANGELOG.md`._
