# Conventions — weewx-rtldavis

**Status:** Source of truth (how we operate)
**Last updated:** 2026-07-28 (S55)

The hard-won operational rules. PRINCIPLES = why; DECISIONS = what; this = how.

## Infra constants

| Thing | Value |
|-------|-------|
| NAS | `<NAS_HOST>` — Synology DS918+ · `<NAS_IP>` · SSH port **`<SSH_PORT>`** · user `<NAS_USER>` |
| SSH / SCP | `ssh -p <SSH_PORT> <NAS_USER>@<NAS_IP>` · `scp -P <SSH_PORT> -O` (capital `-P`, `-O` for the legacy protocol) |
| Real values | gitignored `docs/LOCAL_INFRA.md` (this repo is public — placeholders only in committed docs, DEC-0012) |
| Docker binary | `/usr/local/bin/docker` (no sudo needed; not on the default PATH) |
| Container | `weewx-rtldavis-v2` · **prod runs `:v2.0.11`** (rollback: `:v2.0.10`) |
| Published image | **`:v2.0.11` + `:latest`** — matches prod, no drift (S55c). |
| Driver location | **BAKED** in the image venv (`site-packages/user/rtldavis.py`) — *not* `weewx-data/bin/user/`. Never bind-mount it (DEC-0031); a driver change needs a rebuild. |
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
- Commit messages: imperative subject, session tag where useful; end with a
  `Co-Authored-By: Claude <model> <noreply@anthropic.com>` trailer naming whichever model is
  actually running the session. **Never hardcode a specific model name here** — found stale at S77
  (this line still said `Opus 4.8` while the session running was Sonnet 5), the same
  bump-in-anticipation-not-at-the-event trap as `soak_check.sh`'s `EXPECT_IMAGE` (ops#147 item 6).
- Remote note: origin is the lowercase URL; GitHub redirects to canonical `WeatheredScientist/`
  (backlogged to fix).
- **⚠️ `Closes #N` / `Fixes #N` DO NOT WORK on this repo's normal flow.** GitHub auto-closes only on
  a merge to the **default branch**, which here is `main` — and `main` advances only at a
  prod-baseline release, typically weeks behind. Work merged to `dev` with a `Closes #N` trailer
  leaves the issue **open indefinitely**, and the trailer reads to everyone (including the next
  session) as though it were handled. Found S68d, having done exactly that to #147 and then written
  "✅ #147 closed" into `BOOT.md`. **Close the issue explicitly** (`gh issue close N -c "landed in
  PR #M"`) once the PR merges, or say "addressed in #M" and leave it open on purpose. Keep the
  trailer only as a cross-reference, never as the mechanism.

## Transient prod state (DEC-0079)

- This repo opts into the ops-wide `.claude/transient-state` convention (ops#113): a tracked,
  one-line-per-entry file — `<revert-by-epoch> <tracking-ref> <description>` — for anything
  intentionally put into a non-default, reversible mode (a debug flag, a verbose log level) with
  a planned revert. SessionStart surfaces overdue entries; **deleting the line is the whole close
  mechanism**, nothing to fall out of sync with reality.
- `.claude/` is locally gitignored (`.git/info/exclude`); this file and `settings.json` are the
  two force-added (`git add -f`) exceptions that stay tracked despite that.

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

- Before considering `.py` work done, run these three **from the repo venv** (as applicable).
  Enforced by `.pre-commit-config.yaml` + CI:

  ```
  .venv/bin/python -m ruff check .
  .venv/bin/python -m pytest
  .venv/bin/python -m mypy --ignore-missing-imports --no-strict-optional $(git ls-files '*.py')
  ```

  **`.venv/bin/python` is the only interpreter on this box that has the tooling** (verified S59).
  Neither of the obvious alternatives works: bare `python` is a pyenv shim (3.12.12) and `python3`
  is Homebrew 3.14 — **both lack pytest, mypy and ruff entirely**, so following a bare
  `python -m pytest` gets you `No module named pytest`, not a green gate. pre-commit and CI supply
  their own environments and are unaffected.

  **mypy needs the flags and the file list spelled out**: this repo has no mypy config at all (no
  `pyproject.toml`, no `mypy.ini`, no `setup.cfg` — only `ruff.toml`), so a bare `python -m mypy`
  exits `Missing target module, package, files, or command`. The invocation above is what
  `.pre-commit-config.yaml` passes, and it reproduces CI locally.

  **`ruff format` is NOT a gate — do not run it (DEC-0027).** It was listed here as one until S59.
  It would reformat 30 of 33 files against the deliberate column alignment DEC-0027 exists to
  protect. The same contradiction reached `.pre-commit-config.yaml` and was removed there at S43;
  this line was the surviving copy.

  *(Secret gate, standalone: `bash scripts/check_secrets.sh`. **It prints nothing and exits 0 on a
  clean pass — and also exits 0 with `SECRET-SCAN: nothing to scan` when no files are staged.**
  Those look alike and are not alike: the second scanned nothing. `git add` first, then scan, and
  positive-control any clean result by staging a planted payload — DEC-0039/DEC-0045.)*
- **A local `pre-commit run mypy --all-files` "Passed" is not proof CI will pass.** mypy's
  incremental cache (`.mypy_cache/`, gitignored) persists between runs and can silently mask real
  errors on files nothing else touched (S49, issue #67 follow-up: a stale cache hid 2 real errors
  in `tests/test_reception_pct.py` that CI's cache-free run caught immediately). Before trusting a
  local "0 errors" result — especially right before opening/merging a PR — `rm -rf .mypy_cache`
  first.
- **`git ls-files` lists TRACKED files only, so the mypy gate silently skips anything new until
  you `git add` it.** Measured S76: the gate printed `Success: no issues found in 42 source files`
  while checking **neither** of the session's two new files; staging them first turned the same
  command into `44 source files` and **5 real errors**. The failure is silent in the worst way —
  the count is the only tell, and nobody reads the count. **`git add` first, then run the gate**
  (the same ordering the secret gate already requires, and for the same reason). A green gate that
  skipped the file you just wrote is the S67 failure class in one line: a signal resting on
  evidence about something other than what you were asking (DEC-0083, ops#147).
- Follow the WeeWX `RESTThread` pattern for uploaders (DEC-0007); honest nulls on rejection,
  never stale substitution (DEC-0006).

## RF testing (PRINCIPLES §3)

- Tune from **averaged sweeps over meaningful windows** (24 h+), not single short samples. Short
  windows mislead (see BACKLOG RF findings). Scripts live in `ops/`; result CSVs are gitignored.
