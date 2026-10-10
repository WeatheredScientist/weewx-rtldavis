# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S152] — 2026-10-10 — LoopJsonWriter's service placement and the deploy note corrected (`eaglehunt-ops#395`, #441)

- **`docs/ARCHITECTURE.md` §1 and §2 now put `LoopJsonWriter` last in `process_services`, with
  `data_services` empty.** That is what the live `weewx.conf` (read redacted, `marvinctl conf … Engine`)
  and `weewx.conf.example` both say, and has been since 2026-07-12; the docs had said `data_services`
  since S16 until the dashboard's public how-it-works audit found it. `loop_json_writer.py`'s DEPLOY
  docstring now describes the tenant-root checkout and `marvinctl pull` plus a restart (DEC-0150)
  instead of the NAS `scp`; the decoy-copy warning stays. Docs and a docstring only: no image, no
  deploy, prod untouched. `DRIFT_REPORT.md` Q3 keeps its S-early reading as a dated record.
- **Ops check-in (ops S77):** no cutover in flight, nothing Class C; `eaglehunt-ops#357` is HLF's to
  accept and ops's to close, `#358` waits on the owner's off-screen address check, `#110` stays
  deferred. `weewx#440` (the dashboard's ask to package `loop_json_writer.py` as an installable
  extension) is weewx's own; design first, no deadline.
- Watches: `soak_check.sh` 14 passed, 5 warnings (all expected), 0 failures; no `bar_absolute` fallback
  warning in `weewx.log`, and `station pressure` still arrives each fetch. The new small traps are in
  `docs/GOTCHAS.md` §3, with S151's, which had been sitting in `BOOT.md`. S149 and S148 rolled to the
  archive verbatim.

## [S151] — 2026-10-07 — the secret gate's four detector holes closed (#421, DEC-0210)

- **`scripts/check_secrets.sh` now scans quoted key names, knows `secret_key`/`access_key`/`private_key`,
  stops flagging `os.getenv(`, and judges the allow-list per match instead of per line.** Controls
  first, shown red against the old gate; 190 controls green; fourteen of fifteen mutations of the new
  alternates go red (the fifteenth is unkillable by construction). Three test fixtures took `YOUR_*`
  placeholders and `PASSWORD` joined the key list, because the quoted-key change made four tracked
  lines visible. Prod untouched; v2.0.20 soak 19/0/0, no `bar_absolute` fallback warning.

## [S150] — 2026-10-06 — WeatherLink's `bar_absolute` becomes weewx's `pressure` (DEC-0209, `eaglehunt-ops#357` option A); v2.0.20 in prod the same night

- **v2.0.20 is in prod since 2026-10-06 22:15:14 ET.** PR #433 moved the stamp; built on marvin
  from `dev`@`9a86c97` (image `f617c9ca…`); `exec-ro` sha of the seven baked modules against
  v2.0.19: only `pressure_service.py` differs, equal to `dev`'s. The first fetch (22:17:19) logged
  `station pressure 29.534`; the first record (22:18:00) carries `pressure 29.534`, `altimeter
  30.130` against the derived rows' 29.526 / 30.122 — a +0.008 inHg step, `barometer` unchanged
  (DISC-0002 filled). Zero WARNING/ERROR lines since the restart; three archive minutes lost to it.
  `soak_check.sh`: 19 passed, 0 warnings, 0 failures (an earlier run inside the acquisition gap
  flagged ARCHIVE STALLED, as expected). `:v2.0.20` pushed to Docker Hub with `marvinctl push` at
  22:19 ET, Hub's digest equal to prod's (`f617c9ca…`). Tagged `v2.0.20` on `9a86c97` with a GitHub
  release.
- **Docker Hub `:latest` moved from v2.0.13 to v2.0.20** (22:52 ET, owner route): `docker buildx
  imagetools create` from the laptop, registry-side, same index digest as prod. The first attempt
  failed `insufficient_scope` on the stored Hub credential; a fresh `docker login` by the owner
  fixed it. Recorded in CONSTANTS as the measured shape of the owner route.
- **`dev` promoted to `main` as v2.0.20, tag `prod-baseline-20261006`** (106 commits, S122 → S150).
  Found while doing it: `main` was v2.0.16's promotion (`prod-baseline-20260904`, #324) plus the
  misrouted #338, not v2.0.13 as BOOT and CONSTANTS had said since S122; both corrected. The merge
  conflicted in ten docs and `ops/campaign_analyze.py` (#338's hunks against `dev`'s later
  rewrites, #339 having already carried its content to `dev`), every conflict resolved in `dev`'s
  favor and the result's tree checked equal to `dev`'s.
- **`pressure_service.py` reads `bar_absolute` beside `bar_sea_level` and injects it as `pressure`**
  when the packet's is null; weewx's `prefer_hardware` keeps it, so the archive's station pressure is
  measured and `altimeter` derives from it instead of from the reversed sea-level value. Without the
  key nothing changes (one warning). Five new tests; the S82b injection test split in two. Baked, so
  it rides a v2.0.20 release — not built this session.
- **Both consumers answered on `eaglehunt-ops#357`** (dashboard 09-29, HLF S362, rung from here):
  neither reads `pressure_inHg` or `altimeter_inHg`; HLF needs the value in the archive. The owner
  chose (A). `DISC-0002` records the boundary (timestamp and shift filled at the deploy); INTERFACES
  §1 rewritten; the ROADMAP line closed; CWOP noted as the one uploader that moves (it posts
  `altimeter`).
- **The station's response carries the key (owner-run probe, the in-session `marvinctl exec` was
  classifier-denied as a production read):** the barometer sensor's record (type 242, data
  structure 19) reads `bar_absolute = 29.534` beside `bar_sea_level = 30.127`, `bar_offset = 0`,
  inHg — one record, the shape the code assumes. The probe printed key names and `bar_*` values
  only.
