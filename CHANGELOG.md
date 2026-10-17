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

## [S153] — 2026-10-10 — `weewx#440` designed: the loop writer ships as a WeeWX extension from this repo (DEC-0211)

- **Design only, no code.** `loop_json_writer.py` stays the only copy; `extensions/loopjson/` will hold
  `install.py` and an adopter README; CI packs `weewx-loopjson-X.Y.Z.zip` and releases it on a
  `loopjson-vX.Y.Z` tag with `--latest=false`. The writer gains a `writer` version key, relative paths
  against `WEEWX_ROOT`, a created output directory, and a barometer TTL that falls back to
  `ttl_default` without `[DavisPressure]`; CI proves the install on WeeWX 5.5.2 with the Simulator.
  Checked first against WeeWX 5.5.2's installer source (service append order, archive layout,
  Content-Disposition) and the dashboard's `/loopdata` passthrough. Owner: "go with all your
  recommendations". Prod untouched; the build is one Sonnet session.
- `#440`'s `dayRain_in` and `loopSpeed_mph` are dashboard-side keys, not writer keys; said on the
  issue. S150 rolled to the archive verbatim.
- **`docs/ARCHITECTURE.md` §4 reads `BIAS_TEE` from `weewx.service`, not `inspect`'s `Config.Env`**,
  which prints every value as `<REDACTED>` since MARVIN-DEC-0198 (#443, rung from heartofgold). The
  unit-file `grep` was run and shows `BIAS_TEE=0`. Docs only.

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
