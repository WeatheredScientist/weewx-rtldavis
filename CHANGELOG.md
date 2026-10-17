# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S156] — 2026-10-17 — image downloads pinned; amd64 and arm64 builds proved in CI (DEC-0214)

- `src.tgz` and `weewx-influx2` are fetched at one commit each and checked against a sha256 (same
  bytes as v2.0.20's build); `tests/test_dockerfile_pins.py` guards it. `.github/workflows/image.yml`
  builds natively on GitHub-hosted amd64 and arm64 runners and smoke-tests the image; it publishes
  nothing (arm64 images on Hub are a wanted follow-up).

## [S156] — 2026-10-17 — README for a new user, `docs/DEPLOY.md`, cleaned systemd examples (DEC-0213)

- **README** 634 → 211 lines: what differs from stock, a six-step unprivileged quickstart that
  seeds the baked config first (the old one bind-mounted an empty directory over it and could not
  start), complete credits. **`docs/DEPLOY.md`**: systemd recommended, Synology kept.
  **`examples/systemd/`**: the container and monitor units, cleaned from prod's.
  **`docker-compose.yml`**: hardened, per-file mounts dropped.
- Scrub: a home-directory path in `.claude/settings.json`, a county name in DEC-0021, the station's
  own `iss_channel` in `weewx.conf.example` (now 1). Internal records keep their machine names.

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

## [S154] — 2026-10-12 — `scripts/scan_history.sh` and the "never leaked" correction (ops#404, DEC-0212)

- **`scripts/scan_history.sh`** runs the whole `check_secrets.sh` over every `(blob, path)` pair in
  history (1,731 blobs, about 2.5 minutes) and prints only `SECRET-SCAN:` header lines.
  `scripts/history_scan_known.txt` is the positive control: a new finding exits 1, a known one no
  longer reported exits 3. Both exits proved by deleting and adding a list line. First run: 7 headers,
  six benign, one the dead monitor-mail app password (rotated 2026-10-11 by ops).
- **DEC-0212** supersedes the "never leaked" lines in DEC-0076 and DEC-0084 and adds the CONVENTIONS
  rules: run the scan after any detector change; a redacting printer fingerprints every value-like
  token, whatever its length.
