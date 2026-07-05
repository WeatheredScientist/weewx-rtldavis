# Contributing

Thanks for your interest in weewx-rtldavis. This is a published, **public** WeeWX driver + Docker
build for passively intercepting a Davis ISS at 915 MHz with an RTL-SDR dongle. Issues and pull
requests are welcome.

## Ground rules

- **Never commit secrets.** This repo is public. Live config (`weewx.conf`, `monitor.env`) and any
  credentials/tokens/personal identifiers must never enter a commit — ship changes against the
  `.example` templates instead. A `secret-scan` CI job is a **required status check** and will fail
  the build on any secret pattern. See [SECURITY.md](SECURITY.md).
- **License:** contributions are accepted under the project's **GPL v3** license.

## Branch model

- `main` — the released version; mirrors what is actually running in production (tagged
  `vX.Y.Z` / `prod-baseline-YYYYMMDD`). Protected.
- `dev` — the working branch. **Open pull requests against `dev`**, not `main`.

## Development & testing

The test suite is **offline** — it stubs the `weewx` modules, so you don't need weewx (or the
hardware) installed to run it:

```bash
# run every test file
for f in tests/test_*.py; do python3 "$f"; done
# or, if you have pytest:  python3 -m pytest tests/
```

Please add a regression test for any bug fix or behavior change (see the existing
`tests/test_*.py` for the stubbing pattern). Lint/format is `ruff` (a `lint` CI job runs
`ruff check` + `ruff format --check`; `mypy` runs advisory-only).

## Hardware-facing changes

The driver parses a real RF protocol. If you change packet decoding, the rain/wind filters, or the
reception metrics, explain the reasoning in the PR and, where possible, include captured/edge-case
data — the Davis ISS multiplexes sensors across message types, and "an honest null beats fabricated
data" is a design principle here (a missing reading should surface as `None`, not a stale
substitution). After editing a `.py` the running container imports, remember to clear the venv pyc
cache so WeeWX doesn't run stale bytecode:

```bash
find /opt/weewx-venv -name "*.pyc" -path "*/user/*" -delete
```

## Reporting bugs

Open a [GitHub issue](https://github.com/WeatheredScientist/weewx-rtldavis/issues) with your host
(Linux/NAS/etc.), the image tag, relevant `weewx.log` lines (scrub any credentials first), and
steps to reproduce.
