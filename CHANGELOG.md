# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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

## [S149] — 2026-10-02 — v2.0.19 in prod (DEC-0208): weewx 5.5.2, the rapidfire endpoint confirmed live

- **weewx 5.5.0 → 5.5.2 is live as `:v2.0.19` since 2026-10-02 00:18:38 ET.** PR #429 moved the
  Dockerfile stamp and `soak_check.sh`'s fallback (`ws.6` canary unchanged: no driver change); built
  on marvin from `dev`@`fee78e3`. `exec-ro` against v2.0.18: the Go binary and the five baked
  modules are sha-identical, only the engine differs. `soak_check.sh`: 19 passed. Tagged `v2.0.19`
  with a GitHub release.
- **`:v2.0.19` is on Docker Hub: the first real `marvinctl --tenant weewx push`** (00:31 ET, exit 0).
  The manifest's `publish` line had been ratified since 2026-09-04, so `eaglehunt-ops#265`'s trigger
  fired; commented there. Hub's digest equals prod's index digest. `:latest` stays at v2.0.13 (owner
  route); v2.0.17 and v2.0.18 were never pushed.
- **The one prod-visible change is confirmed.** The rapidfire thread now posts to
  `rtupdate.wunderground.com`. Its failures never reach `weewx.log`, so the check was external: the
  station's public wunderground.com page read CONNECTED, 2 seconds old, after the restart.

## [S148] — 2026-09-30/10-01 — #423's swap path proved end to end as `t-weewx`; `weewx.service` under #360's flags, accepted

- **No campaign was queued** (the schedule has been empty since DEC-0128), so the owner chose a
  test-only one: new arm `T` (prod's cmd plus an explicit `-ex 0`, the flag's default), then
  `BASELINE`, driven by two hand-started passes of `weewx-rx-experiment.service`. No timer and no
  `install`: the tenant-root snapshot was verified byte-identical to the live conf, and the state
  file was seeded over sftp. PR #427; its dates moved once when it sat unmerged past the first
  terminator.
- **Both passes worked.** 2026-10-01 21:04:30 ET, `NONE -> T`: config write verified, restart through
  `sudo -n marvin-own weewx restart`, healthy in 106 s via `systemctl is-active`. 22:31:22,
  `T -> BASELINE`: live conf restored byte-exact (mode 0600 kept), harvest wrote 17 rx and 85 dup
  rows under `T`, no mail failure. Schedule stood down again on the closeout PR.
- **`eaglehunt-ops#360`: the 21:04:30 restart was also `weewx.service`'s flag restart.**
  `NoNewPrivs: 1`, every capability set 0, uid 996. One record lost (21:05), 21:06 partial with
  `rxCheckPercent` NULL, 21:07 at 100%. Posted; heartofgold confirmed on the box.
- `GOTCHAS.md` §3: `marvinctl grep` also refuses `/` in a pattern. S144 rolled to the archive.
