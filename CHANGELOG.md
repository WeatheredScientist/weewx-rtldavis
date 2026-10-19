# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S157] — 2026-10-18 — CRC failures counted in the Go decoder, measurement only (#458, DEC-0216)

- `patch/rtldavis-crcstats.patch` (applied after `rtldavis-dupgate.patch`) counts every CRC failure
  per receiver hop slot and how many fall within 100 ms of an accepted frame, either order, and
  prints `crc_stats: crc_fail=N near=M slots=…` once a minute. The driver sums it per archive period
  and logs `crc failures this period` at INFO beside the duplicate and repeat counts. **Log only:**
  no accept, drop or hop decision reads it. Not deployed; rides the next release.
- Proofs: `tests/test_crcstats_patch.py` (the patch removes one line and adds only counters; the
  real `Parse` returns byte-identical messages patched and unpatched, with a positive control) and
  `tests/go/crcstat_test.go` (the tracker against a brute-force oracle; four mutations caught).
- Found on the way: `main.go` builds against the **vendored** `protocol` package, so the top-level
  `protocol/` directory is dead code for this build.

## [S156] — 2026-10-17 — image downloads pinned; amd64 and arm64 builds proved in CI (DEC-0214)

- `src.tgz` and `weewx-influx2` are fetched at one commit each and checked against a sha256 (same
  bytes as v2.0.20's build); `tests/test_dockerfile_pins.py` guards it. `.github/workflows/image.yml`
  builds natively on GitHub-hosted amd64 and arm64 runners and smoke-tests the image; it publishes
  nothing (arm64 images on Hub are a wanted follow-up).
- **arm64 on Docker Hub (DEC-0215):** `.github/workflows/image-publish.yml` builds, smoke-tests and
  pushes `ghcr.io/…:vX.Y.Z-arm64` on a release (or `backfill-vX.Y.Z`) tag with the job's own token;
  `scripts/join_multiarch.sh` joins it with marvin's `:vX.Y.Z-amd64` into Hub's multi-arch
  `:vX.Y.Z`; `scripts/smoke_image.sh` is now shared by both workflows; `tests/test_image_publish.py`
  guards the workflows' security shape (positive-controlled: 6 red). v2.0.20's backfill ran
  2026-10-17 18:41 ET on the owner's go: `:v2.0.20` and `:latest` are multi-arch (amd64 + arm64),
  `:v2.0.20-amd64` keeps prod's digest.

## [S156] — 2026-10-17 — README for a new user, `docs/DEPLOY.md`, cleaned systemd examples (DEC-0213)

- **README** 634 → 211 lines: what differs from stock, a six-step unprivileged quickstart that
  seeds the baked config first (the old one bind-mounted an empty directory over it and could not
  start), complete credits. **`docs/DEPLOY.md`**: systemd recommended, Synology kept.
  **`examples/systemd/`**: the container and monitor units, cleaned from prod's.
  **`docker-compose.yml`**: hardened, per-file mounts dropped.
- Scrub: a home-directory path in `.claude/settings.json`, a county name in DEC-0021, the station's
  own `iss_channel` in `weewx.conf.example` (now 1). Internal records keep their machine names.
- **ROADMAP P0.8 (public readiness, five phases) and P1.9 (decoder fixes in Go)** with issues
  #451–#456 and #458–#459 (#457). Filed `eaglehunt-weather-dashboard#936`: one Opus research
  session on non-Davis platforms, with a weewx section (the live feed's fixed 13-field list, the
  InfluxDB uploader as an extension, driver-agnostic filters, an rtl_433 sibling image);
  `eaglehunt-ops#422` for visibility. README's Requirements line now says multi-arch.

## [S155] — 2026-10-14 — `loop_json_writer.py` 1.0.0 and the `loopjson` WeeWX extension (#440, DEC-0211)

- **Writer** (no-op under prod's config except the new key): `__version__ = '1.0.0'` and a
  `writer: loop_json_writer/1.0.0` key in both files; relative `path`/`current_path` resolve against
  `WEEWX_ROOT` (defaults `loop-data.txt`, `current.json`); the output directories are created at
  startup; the long barometer TTL applies only when `[DavisPressure]` exists. 7 new tests, 1 updated.
- **Extension:** `extensions/loopjson/` (`install.py`, README), `scripts/build_loopjson_zip.sh`
  (fails if module, `install.py` and tag versions disagree), `scripts/prove_loopjson.sh` (installs the
  zip into a fresh WeeWX 5.5.2 and runs the Simulator), `.github/workflows/loopjson.yml` (every PR
  proves it; a `loopjson-v*` tag publishes the zip with `--latest=false`). Proved locally on 5.5.2,
  shipped the same night (PR #447; prod `git pull` + `weewx.service` restart 21:22 ET, `writer` key live; tag `loopjson-v1.0.0`, release not-latest, asset URL install tested on a clean station), plus two failing controls (tag mismatch, missing `writer` key). INTERFACES §1: the `writer` row and
  the stale `data_service` / every-packet opening fixed.
