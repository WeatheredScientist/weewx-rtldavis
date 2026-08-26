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

## ▶ Resume here (S103 → S104)

### What's settled (do not re-derive)

**v2.0.14 remains prod, unchanged since S101** — DEC-0110/DEC-0111/#233/#224, weewx 5.5.0,
NAS-LEASE adoption locked (DEC-0114). Campaign B is CLOSED, gain 496 adopted (DEC-0115). Full
detail in `docs/DECISIONS.md` DEC-0114/DEC-0115 if this ever needs re-litigating — not repeated
here.

**S102 (DEC-0116): `dev`/prod were NOT fully in sync despite S101's claim** — `loop_json_writer.py`,
a MOUNTED file, was four weeks stale. Fixed live, #144/#172/#204 closed. **`ogoxeUploader.py`,
`sortedcontainers`, and `weewx.conf` — the deploy-layers table's other mounted files — remain
independently unverified**; don't assume current without checking (job 3).

**S103: the gain/receive-window hot swap is BUILT — DEC-0117.** The last open `BACKLOG.md` idea /
[ops#179], filed S89 and held until Campaign B closed. Watched control file (`hotswap_control_file`,
unset = off) carrying bounds-checked `gain`/`ex` integers only — never a command string, since `cmd`
reaches `shlex.split()` → `Popen`. Polled at the top of `genLoopPackets`, ~10 s, no thread.
**The non-obvious part, don't re-derive it:** `time_last_received` is a local in `genLoopPackets`
and a respawn does not reset it, while a fresh child is legitimately silent for the US 133 s init
period — so a swap must reset the four watchdog counters *and* widen the threshold to 240 s until
the first packet, or it trips the 150 s stall raise mid-init and tears the driver down. Plus
rollback, an atomic ack file recording the measured respawn gap, and init-time honoring so a restart
can't silently revert a swap. Mutation-verified. **Not in prod: `rtldavis.py` is BAKED — needs an
image rebuild — and the feature is off until the config key is set.**

**#233, #252 remain fully resolved** (via PR #271). **The S91 code audit remains fully closed**
(#219–226).

**Standing SOP (S101): for live inter-repo coordination, message the other repo's live Claude
session directly first (`ListAgents`/`SendMessage`), always loop `eaglehunt-ops` too.** Used again
this session (ops verification exchange) — process, not repo state, not repeated here.

**Marvin (new Debian hypervisor build) is targeting a Saturday 2026-08-29 host migration for
weewx + eaglehunt-weather-dashboard + hyperlocal-forecast, conditional on Marvin's network-link
soak surviving concurrent Win11-VM bring-up and coffeeradar's own move through the weekend.** Not
this repo's decision to track in detail — `~/Projects/marvin/STATE.md` is the source of truth — but
relevant context for anything infra-adjacent proposed before then.

### ▶▶ S104 JOB LIST

1. **`main` promotion for v2.0.14** — deliberately deferred (DEC-0114). Once v2.0.14 has proven out
   in prod for a reasonable stretch, promote per the usual release mechanics (`CONSTANTS.md`).
   **Docker Hub push follows the same gate** (DEC-0078) — Hub is still on `:v2.0.13`.
2. **Convert `ops/rx_experiment.sh` to the DEC-0117 control file** — the other half of the hot swap,
   deliberately left out of S103. Retires the 600 s settle window and the restart transient from
   campaign blocks. **Must not land mid-campaign** (ops#179 constraint 1); none is scheduled, so the
   window is open now. Needs the driver in prod first (job 3) or it has nothing to talk to.
3. **The hot swap is not in prod until an image rebuild** — `rtldavis.py` is BAKED. No urgency on its
   own (feature is off by default), so fold it into the next image cut rather than cutting one for it.
4. **Spot-check the other mounted files' live-vs-`dev` state** (`ogoxeUploader.py`,
   `sortedcontainers`, `weewx.conf`) — DEC-0116 established that an image bump says nothing about a
   mounted file unless specifically checked, and none of these three have been since before S101.

[ops#179]: https://github.com/WeatheredScientist/eaglehunt-ops/issues/179

### Current state (S103 close)

| Thing | State |
|---|---|
| Prod | **v2.0.14**, driver **ws.5** unchanged, `influx.py` **ws.2**, weewx **5.5.0**, gain **496** |
| Campaign B | **CLOSED.** Gain 496 adopted (DEC-0115). Nothing further scheduled |
| Soak | Not re-run since S101 — next session should confirm green before trusting anything downstream |
| Restart rate | DEC-0106 baseline (4/day during a campaign, 0/day between) — stale since there's no active campaign; watch for the new steady-state rate |
| `dev` vs prod | `dev` is now **ahead** of prod by DEC-0117 (baked layer — needs an image rebuild, job 3). `loop_json_writer.py` in sync since S102. Other mounted files unverified (job 4) |
| Hot swap (DEC-0117) | **Built, tested, merged to `dev`. Not in prod, and off by default.** Driver half only — `ops/rx_experiment.sh` still restart-based (job 2) |
| Data integrity | ERR-0006 correction unchanged; external copies still permanently carry the bad value |
| NAS-LEASE | Adopted and locked (DEC-0114) — `RENEWAL_FLOOR_S=420`, `TTL_S=3600` |
| Trackers | ops#179 closed this session (DEC-0117). #253 permanent until next recreate. #274 informational, no action |
| Marvin migration | Target **Saturday 2026-08-29** for this repo's host move, conditional on the soak — see above |

## Blockers

1. **weewx process freezes — 1.31/day, median 240 s (DEC-0088-corrected).** Root cause unproven
   (thread blocking on the bind-mounted log volume leads, DEC-0067/0068); evening 18:00–21:00 carries
   the signal (DEC-0094). Untouched this session.
2. **RF-dead episode root cause unknown** (DEC-0081, deliberately open). DEC-0097 adds 00:00–04:00
   clustering; DEC-0102 the 11.80x iowait confound, which does **not** close it. Next real step is
   multi-night minute-level correlation, not a re-run. Untouched this session.
3. **ERR-0005** — largely explained by DEC-0081; its 21-stall episode remains the largest on record.
4. `ppm`/`fc` unmeasured, deliberately unchanged for B.

## Model tier

**S103 escalated to Opus 5 for the DEC-0117 design work — via `/model claude-opus-5`, the
PERSISTING form (OPS-DEC-0010), not a session-only switch.** The Sonnet floor must be restored:
`"model": "sonnet"` in `~/.claude/settings.json`, or re-run `global/install.sh`. **If the next
session opens on Opus, this is why — restore it before doing anything else.**

## Gotchas — they live in `docs/GOTCHAS.md`

**Durable traps are NOT carried here** (DEC-0105/ops#173). **Read it when:** trusting any tool's
zero/empty/green result (§1) · any PR/merge sequence or handoff write (§2) · any NAS or campaign
task (§3) · judging a component live, dead, or shipped (§4). Indexed in `MANIFEST.md`. **New traps
are appended THERE, not here** — that is what keeps this file under cap.

_Last updated: 2026-08-26 (S103 close). Green gate: ruff clean, **428 passed / 8 skipped** (26 new),
mypy clean (65 files), secret gate clean. Shipped: the gain/receive-window hot swap (DEC-0117),
ops#179 closed — full narrative in `CHANGELOG.md`._
