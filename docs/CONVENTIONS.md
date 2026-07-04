# Conventions — weewx-rtldavis

**Status:** Source of truth (how we operate)
**Last updated:** 2026-07-04 (S17)

The hard-won operational rules. PRINCIPLES = why; DECISIONS = what; this = how.

## Infra constants

| Thing | Value |
|-------|-------|
| NAS | `<NAS_HOST>` — Synology DS918+ · `<NAS_IP>` · SSH port **`<SSH_PORT>`** · user `<NAS_USER>` |
| SSH / SCP | `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` · `scp -P <SSH_PORT> -O` (capital `-P`, `-O` for the legacy protocol) |
| Real values | gitignored `docs/LOCAL_INFRA.md` (this repo is public — placeholders only in committed docs, DEC-0012) |
| Docker binary | `/usr/local/bin/docker` (no sudo needed; not on the default PATH) |
| Container | `weewx-rtldavis-v2` · image `weatheredscientist/weewx-rtldavis:rw250-test` |
| Project root (NAS) | `/volume1/docker/weewx-rtldavis/` |
| Live config | `.../weewx-data/weewx.conf` (bind-mounted; gain/ppm edits need only a restart) |
| Container venv user files | `/opt/weewx-venv/lib/python3.14/site-packages/user/` |
| Loop-JSON output | `/opt/weewx-data/loop-data.txt` (in container) |
| Missing NAS tools | no `bc`, `tmux`, `screen` — use bash integer arithmetic and `nohup` |

## Command hygiene

- **`docker kill` + `docker start`, never `docker stop`** (DEC-0008) — clean SDR handoff.
- **`docker logs` always with `--tail N`** — the log is large.
- **`[MAC]` / `[NAS]` labels go *above* command blocks, never inside; no inline `#` comments inside
  pasteable blocks** (zsh copy-paste safety).
- **After editing any mounted `.py` the venv imports, clear pyc:**
  `find /opt/weewx-venv -name "*.pyc" -path "*/user/*" -delete` (ARCHITECTURE §pyc-gotcha).
- Prefer **python3 heredocs over `sed`** for non-trivial file patches; put **assert guards** on
  replace-style patches so a missed match fails loudly rather than silently no-op'ing.
- **Verify before write** — read the target and confirm it's the file you think (the driver runs from
  `weewx-data/bin/user/rtldavis.py`, *not* the stale root-level copy — easy to grab the wrong one).
- **Read-only NAS access by default.** Capture via `docker exec … cat` / `cat` streamed to local;
  don't write on the NAS during audits. Do not spawn a second `rtldavis` process (USB dongle
  contention with the live receiver) — read the image build history instead.
- SSH can flake on rapid reconnects; batch remote work into a **single `bash -s` session** rather
  than many quick `ssh` calls. Filter the post-quantum SSH warning banner in captured output.

## Git workflow

- **`main` = production truth** (tagged `prod-baseline-YYYYMMDD`); **`dev` = work**; feature branches
  off `dev` for individual changes (DEC-0011). Promotion = merge + deploy + tag.
- **Start of session:** `git fetch && git status`. **End:** `git status` shows *up to date*.
- **Pause for approval before every commit and before any push.** Show `git status` + a diff summary
  first; show `git log --oneline --all` before any push.
- Commit messages: imperative subject, session tag where useful; end with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Remote note: origin is the lowercase URL; GitHub redirects to canonical `WeatheredScientist/`
  (backlogged to fix).

## Secrets (the public-repo rule — DEC-0012)

- **The repo is PUBLIC.** `weewx.conf`, `monitor.env`, `proxy.env`, anything with a credential →
  **never** committed. They are gitignored; committed source carries `YOUR_*` placeholders.
- **Show every secret found before scrubbing** (so the owner can rotate), then scrub on the NAS so
  plaintext values never enter a local file or an LLM prompt.
- **Token-pattern grep before every commit** — over the staged diff and the whole tracked tree.
  Also sweep for personal identifiers: the WU PWS id, place names, coordinates, the org name, the
  NAS IP/user (the exact patterns live in gitignored `scripts/.identifiers`).
- **Never paste a live secret into an LLM chat.** Treat anything that reaches a prompt as compromised;
  rotate it server-side. `gh`/SSH creds live in the OS keychain — an assistant runs `gh`/`git`/`scp`
  against that auth and never needs the raw value.

## Python / validation (DEC-0015)

- Before considering `.py` work done: `python -m ruff check .` · `python -m ruff format` ·
  `python -m mypy` · `python -m pytest` (as applicable). Enforced by `.pre-commit-config.yaml` + CI.
- Follow the WeeWX `RESTThread` pattern for uploaders (DEC-0007); honest nulls on rejection,
  never stale substitution (DEC-0006).

## RF testing (PRINCIPLES §3)

- Tune from **averaged sweeps over meaningful windows** (24 h+), not single short samples. Short
  windows mislead (see BACKLOG RF findings). Scripts live in `ops/`; result CSVs are gitignored.
