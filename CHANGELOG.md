# Changelog — weewx-rtldavis

Most recent first. Governance-era entries are session-tagged (`[S16]`, `[S17]`, …). Release tags
(`v2.0.1`, `prod-baseline-20260704`, …) are called out inline. Pre-governance history is summarized
under [Pre-S16].

---

## [S186] — 2026-11-01 — ROADMAP: two stale P0.8 lines fixed (targeted, DEC-0057)

- Session-start roadmap spotlight. Phase 2 still listed a v2.1.1 and moving `:latest` off `:v2.0.20` (v2.1.1's baked changes shipped as v2.2.0; `:latest` = `:v2.3.0`); phase 1 said ops#439 waited on marvin (heartofgold built `--usb-host` passthrough 11-01, MARVIN-DEC-0219; it now waits on the owner's flash drive). PR #533. ops#435 needs nothing more from weewx. Rolled S183 to S177 to the archive.

## [S185] — 2026-11-01 — v2.3.0: `doctor`, informational `HEALTHCHECK`, entrypoint dispatch, simulator seed (DEC-0228); phase 6 built out

- Coordinator session (Sonnet, then Fable 5.1 by the owner's call) ran two child sessions in their own worktrees. PR #527 (S185a, Opus 5.5): `ENTRYPOINT ["/entrypoint.sh"]` with `CMD ["weewxd"]`, the entrypoint dispatches `doctor` / `weectl` / passthrough with the default start path unchanged; `doctor.py` (exit codes 10 to 14, each naming a QUICKSTART troubleshooting row, 29 tests); `HEALTHCHECK` on `weewx.log` mtime, 600 s, informational only; DEC-0228. PR #526 (S185b, Sonnet): `WEEWX_DRIVER=simulator` at seed time with a 40 s Simulator run in the CI smoke. Merged #526, resolved the two shared-file conflicts in #527 (both appended smoke blocks kept), merged #527. Release prep PR #528: image tag v2.3.0 everywhere, QUICKSTART's written-ahead header and proposal tags dropped (897 words). No driver change: banner stays `0.20+ws.9`.
- Built `:v2.3.0` on marvin from `dev`@`6f6002a` (index `71c201b6…`; baked driver, `doctor.py`, `seed_config.py` and `entrypoint.sh` shas equal `dev`'s), `doctor` on marvin exits 13 naming the dongle-held row (prod holds it, correct), rollback tagged `:v2.2.0-prod-pre-v2.3.0` (`0a790696…`), deployed 11:31:49 ET, container `healthy`, first record after the restart 11:34:00 ET. Promoted via PR #530 (`main` = `fe3761a`), tagged `v2.3.0` and `prod-baseline-20261101`, GitHub release created with `host-setup.sh` (sha256 in the notes), `docker-compose.yml` and `env.example`; CI built arm64 on the tag; `:v2.3.0` published as the multi-arch index `03f3c891…`. The desktop app's auto-mode classifier refused `marvinctl push :v2.3.0-amd64` twice, the session's permission-mode switch, and the `:latest` move (`Create Public Surface`); the owner pushed the amd64 half and moved `:latest` to `:v2.3.0` from a terminal (12:25 ET, same index digest).
- ops#435: the DST window (2026-11-01 05:00 to 07:00 UTC) holds 120 rows, 120 distinct, no gap, posted. ops#441 closed (the `seed_config.py` MANIFEST row, PR #525, widened by #527). ops#439: heartofgold installed real USB passthrough (`marvin-vm create --usb-host`); the live attach waits on the owner's flash drive.

## [S184] — 2026-10-31 — v2.2.0 built and deployed; phase 6 shipped (DEC-0227)

- Built `:v2.2.0` on marvin from `dev`@`9e678fd`, deployed to prod 10:51:42 ET (index `0a790696…`, rollback `:v2.1.0-prod-pre-v2.2.0`), first record after the restart 10:54:00. Promoted via PR #523 (`main` = `8ed61a0`), tagged `v2.2.0` and `prod-baseline-20261031`, arm64 built by CI, `:v2.2.0` and `:latest` published as the multi-arch index `3f580af7…`, GitHub release created with `host-setup.sh`, `docker-compose.yml` and `env.example`. GitHub renames a dotfile asset, so `.env.example` shipped as `default.env.example` and the script 404ed on it; fixed by fetching `env.example` (branch `s184-hostsetup-envexample-asset`, release assets replaced). Also this session: the #514 holding reply posted, hilman2's answer recorded, a reminder set for 2026-12-05.
- Release prep (PRs #519 to #521): version strings to v2.2.0 and driver banner `0.20+ws.9` (Dockerfile, compose, systemd example, README, CHANGES-FROM-UPSTREAM, image-publish input). README quick start replaced by the four-step version over `docs/QUICKSTART.md` and `scripts/host-setup.sh`. Phase 6's image half (PR #520) and docs half (PR #519) are the content; v2.1.1's baked changes (#506, #507, #509) ride along, so there is no separate v2.1.1. Build, multi-arch join, tag and GitHub release follow on the promotion.
