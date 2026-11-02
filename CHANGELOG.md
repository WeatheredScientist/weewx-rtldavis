# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S187] — 2026-11-02 — ops#439 passed, ops#442 already done, ERR-0012, #536 filed

- ops#439: HoG ran `weewx-439.sh` in a guest with a real USB stick (`154b:1006`) passed through; all three `docs/DEPLOY.md` checks pass (the unit starts unprivileged, the container sees and opens the bus node, `usb_reset.sh` refuses non-RTL ids and resets by id). Verdict posted; the owner closed it. S186's `NRestarts` prediction for check 1b was wrong (a manual restart resets the counter), not the unit.
- PR #534: DEPLOY.md pointed at Quick start steps that no longer exist. It now starts from `host-setup.sh`, adds a by-hand `seed_config.py` run with the location (the unit's `test -e` means the image never seeds under systemd; the command ops#439 proved), widens the udev rule to `0bda:2832`, and points the Synology section at the unit's `docker run` line.
- ops#442: `windGust10_mph` has been in every InfluxDB archive point since 2026-10-28 12:30 ET (the driver has no hardware archive, so the record comes from the accumulator, `last` extractor, and `influx.py` uploads every field); only SQLite lacks it. 926 of 1,440 minutes carry it (no message 9 = no field, never 0). No build; documented in `docs/INTERFACES.md` §2 (PR #537); the dashboard confirmed its Flux query; closed.
- ERR-0012 (PR #535): the 2026-10-31 10:04 EDT 30 mph gust at 150° in a 2 mph north breeze, one CRC-valid garbage frame (12.5 m/s jump, under the 20 m/s wind delta; reception 100%). Recorded, data left as is by the owner's call. The ISS gust read 4 mph.
- #536 filed (tier:frontier): ~400,000 CRC failures a day, so a few chance passes a day; on 10-30 13:10 EDT a rejected 187 mph frame was followed by a 2 min 49 s reception loss. Proposes measuring arrival offset against the expected slot before any timing check.

## [S186] — 2026-11-01 — ROADMAP: two stale P0.8 lines fixed (targeted, DEC-0057)

- Session-start roadmap spotlight. Phase 2 still listed a v2.1.1 and moving `:latest` off `:v2.0.20` (v2.1.1's baked changes shipped as v2.2.0; `:latest` = `:v2.3.0`); phase 1 said ops#439 waited on marvin (heartofgold built `--usb-host` passthrough 11-01, MARVIN-DEC-0219; it now waits on the owner's flash drive). PR #533. ops#435 needs nothing more from weewx. Rolled S183 to S177 to the archive.

## [S185] — 2026-11-01 — v2.3.0: `doctor`, informational `HEALTHCHECK`, entrypoint dispatch, simulator seed (DEC-0228); phase 6 built out

- Coordinator session (Sonnet, then Fable 5.1 by the owner's call) ran two child sessions in their own worktrees. PR #527 (S185a, Opus 5.5): `ENTRYPOINT ["/entrypoint.sh"]` with `CMD ["weewxd"]`, the entrypoint dispatches `doctor` / `weectl` / passthrough with the default start path unchanged; `doctor.py` (exit codes 10 to 14, each naming a QUICKSTART troubleshooting row, 29 tests); `HEALTHCHECK` on `weewx.log` mtime, 600 s, informational only; DEC-0228. PR #526 (S185b, Sonnet): `WEEWX_DRIVER=simulator` at seed time with a 40 s Simulator run in the CI smoke. Merged #526, resolved the two shared-file conflicts in #527 (both appended smoke blocks kept), merged #527. Release prep PR #528: image tag v2.3.0 everywhere, QUICKSTART's written-ahead header and proposal tags dropped (897 words). No driver change: banner stays `0.20+ws.9`.
- Built `:v2.3.0` on marvin from `dev`@`6f6002a` (index `71c201b6…`; baked driver, `doctor.py`, `seed_config.py` and `entrypoint.sh` shas equal `dev`'s), `doctor` on marvin exits 13 naming the dongle-held row (prod holds it, correct), rollback tagged `:v2.2.0-prod-pre-v2.3.0` (`0a790696…`), deployed 11:31:49 ET, container `healthy`, first record after the restart 11:34:00 ET. Promoted via PR #530 (`main` = `fe3761a`), tagged `v2.3.0` and `prod-baseline-20261101`, GitHub release created with `host-setup.sh` (sha256 in the notes), `docker-compose.yml` and `env.example`; CI built arm64 on the tag; `:v2.3.0` published as the multi-arch index `03f3c891…`. The desktop app's auto-mode classifier refused `marvinctl push :v2.3.0-amd64` twice, the session's permission-mode switch, and the `:latest` move (`Create Public Surface`); the owner pushed the amd64 half and moved `:latest` to `:v2.3.0` from a terminal (12:25 ET, same index digest).
- ops#435: the DST window (2026-11-01 05:00 to 07:00 UTC) holds 120 rows, 120 distinct, no gap, posted. ops#441 closed (the `seed_config.py` MANIFEST row, PR #525, widened by #527). ops#439: heartofgold installed real USB passthrough (`marvin-vm create --usb-host`); the live attach waits on the owner's flash drive.
