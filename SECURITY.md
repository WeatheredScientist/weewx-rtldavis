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

## 2026-09-01 history rewrite

On 2026-09-01 this repository's entire git history was rewritten (`git-filter-repo`) and
force-pushed, to remove inadvertently committed private infrastructure identifiers and personal
email addresses from a small number of historical file versions and early commit metadata. **No
credentials, keys, or tokens were ever committed on any branch** — this was a privacy scrub, not a
credential leak. Every commit SHA changed; if you cloned before this date, please **re-clone**
rather than pull. Release tags keep their names and now point at the rewritten commits.

## 2026-09-05 second history rewrite

On 2026-09-05 two commits from 2026-08-15 were rewritten (`git-filter-repo`, same method as above)
to remove a private LAN subnet reference from a diagnostic note. **No credentials, keys, or tokens
were involved** — a non-routable local-network address is a lower-severity class than the 2026-09-01
scrub, but the same privacy-first policy applies. Every branch/tag SHA from that point forward
changed again; re-clone rather than pull if you have a copy from before this date. GitHub's own
pull-request refs retain some pre-rewrite objects independent of this repo's branches/tags — a known
platform limitation, not a gap in the rewrite itself.

The gap that let this happen twice is now closed at the tool level, not just the discipline level:
`scripts/check_secrets.sh` (this repo's CI-enforced secret gate) previously only recognized
credential-shaped values; it now also blocks any private-range (RFC1918) IP or subnet literal in a
commit, regardless of whether that specific value was ever seen before.

## Scope notes

- This repository is **public**. It must never contain credentials, tokens, or personal
  identifiers. A `secret-scan` CI job (a required status check) fails the build if any tracked
  file carries a secret pattern — treat a failure as blocking, and see
  [CONTRIBUTING.md](CONTRIBUTING.md) before committing.
- Live operational config (`weewx.conf`, `monitor.env`) belongs only on your own host — the repo
  ships **`.example`** templates. Never commit your filled-in copies.
- The container runs `--privileged` for USB access to the RTL-SDR dongle; run it on a host you
  trust, and keep credentials in your gitignored local config, not in the image.
