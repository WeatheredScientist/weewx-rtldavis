# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

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
