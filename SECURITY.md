# Security Policy

## Supported versions

This is a small, actively maintained project. Security fixes target the **latest release** only
(see [GitHub Releases](https://github.com/WeatheredScientist/weewx-rtldavis/releases) and the
`:latest` Docker Hub tag). Older tags are frozen and not patched.

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Instead use GitHub's
**[private vulnerability reporting](https://github.com/WeatheredScientist/weewx-rtldavis/security/advisories/new)**
(Security → Advisories → *Report a vulnerability*). Include reproduction steps and the affected
version/tag. You'll get an acknowledgement as soon as practical; this is a personal project, so
please allow a reasonable window before any public disclosure.

## Scope notes

- This repository is **public**. It must never contain credentials, tokens, or personal
  identifiers. A `secret-scan` CI job (a required status check) fails the build if any tracked
  file carries a secret pattern — treat a failure as blocking, and see
  [CONTRIBUTING.md](CONTRIBUTING.md) before committing.
- Live operational config (`weewx.conf`, `monitor.env`) belongs only on your own host — the repo
  ships **`.example`** templates. Never commit your filled-in copies.
- The container runs `--privileged` for USB access to the RTL-SDR dongle; run it on a host you
  trust, and keep credentials in your gitignored local config, not in the image.
