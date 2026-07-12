#!/usr/bin/env bash
# check_secrets.sh — block credentials and personal identifiers from entering
# this PUBLIC repo (DEC-0012). Invoked by pre-commit on staged files, and by CI.
#
# Exit non-zero (and print the offending line) if a staged file contains:
#   - an assignment-style secret with a real-looking value (not a YOUR_* / env placeholder)
#   - a known personal identifier (PWS id, place name, the org name, the NAS IP, an email)
#
# It deliberately allows: YOUR_* placeholders, ${ENV} refs, os.environ/getenv,
# self.<attr> = <attr> assignments, docstrings/comments describing a field.
set -u
status=0
files=("$@")
[ ${#files[@]} -eq 0 ] && files=($(git diff --cached --name-only --diff-filter=ACM))
# Nothing to scan (run by hand on a clean tree, or an empty staged set): pass cleanly
# instead of tripping `set -u` on the empty-array expansion in the loop below.
[ ${#files[@]} -eq 0 ] && exit 0

# --- Personal / infra identifiers that must never be committed ---
# The patterns themselves are private (naming them here would leak them in this
# PUBLIC script), so they live in the GITIGNORED scripts/.identifiers file (one
# extended-regex per line). If that file is absent (CI, a fork, another user),
# the identifier check is skipped — there is nothing owner-specific to catch.
# No broad email regex: upstream author attribution (Keffer, Heijst, Skahan,
# OgoXe) is legitimate in a public repo.
ident_file="$(dirname "$0")/.identifiers"
ident_re=""
if [ -f "$ident_file" ]; then
  ident_re="$(grep -vE '^[[:space:]]*(#|$)' "$ident_file" | paste -sd '|' -)"
fi

# --- Assignment-style secrets with a real value ---
secret_re='(password|passcode|api_key|apikey|api_secret|token|secret|[^A-Za-z_]key)[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_./+=-]{8,}'

for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  case "$f" in
    *.png|*.jpg|*.jpeg|*.gif|*.zip|*.tar.gz|*.sdb) continue ;;
  esac

  # (a) identifiers (only if the gitignored pattern file is present)
  if [ -n "$ident_re" ] && [ "$f" != ".gitignore" ]; then
    hits=$(grep -nEi "$ident_re" "$f" 2>/dev/null)
    if [ -n "$hits" ]; then
      echo "SECRET-SCAN: personal identifier in $f:"; echo "$hits"; status=1
    fi
  fi

  # (b) assignment-style secrets with a real value.
  # Allow-list (not a secret): YOUR_* / ${ENV} / env lookups / empty / self-assign /
  # config lookups / comment-only lines / an ALL_CAPS constant reference (= FOO_KEY) /
  # a docstring param description (: WeatherCloud key, i.e. prose, not a token).
  #
  # THE ALLOW-LIST MUST BE CASE-SENSITIVE (`grep -vE`, NOT `grep -viE`).
  # Its [A-Z] terms carry the whole distinction between a constant reference and a
  # literal secret, and `-i` erases it: with -i, the ALL_CAPS rule (= FOO_KEY) also
  # matches `token = abc12345678`, so essentially every unquoted real secret was
  # whitelisted. The gate looked green and caught nothing. (Same bug, same fix, as
  # the dashboard repo's DEC-0063.) The secret_re grep below KEEPS -i, so Token /
  # TOKEN / token are all still detected -- it is only the allow-list that is strict.
  #
  # Two further holes closed at the same time (both were live here and upstream):
  #   - `# ` matched a comment ANYWHERE on the line, so `api_key = REAL  # note`
  #     passed. Now anchored to comment-ONLY lines.
  #   - the docstring rule matched a capitalized single token, so `api_key: Secret123`
  #     passed. Now it requires a capitalized word FOLLOWED BY ANOTHER WORD, i.e.
  #     actual prose ("key: WeatherCloud key"), which a bare credential never is.
  #     `api_key: Secret123` and `api_key: SecretValue` are both caught; only a
  #     multi-word description is let through.
  #
  # NOTE: the allow-list runs against `grep -n` output, so every line carries a
  # leading "<lineno>:" prefix. The docstring-param rule must require an ALPHA char
  # immediately before the colon ([A-Za-z]:) — otherwise it matches that numeric
  # prefix's colon (e.g. "1:api_key = ...") and silently whitelists real secrets.
  hits=$(grep -nEi "$secret_re" "$f" 2>/dev/null \
    | grep -vE 'YOUR_|your_|\$\{|os\.environ|getenv|argv|input\(|= *""|= *None|= *-1\b|self\.(password|token|key|api[_a-z]*)|options\.|\.get\(|site_dict|config_dict|^[0-9]+:[[:space:]]*#|description|Authorization|InfluxDB 2\.x|=[[:space:]]*[A-Z][A-Z0-9_]{3,}\b|[A-Za-z]:[[:space:]]*[A-Z][A-Za-z]*[[:space:]]+[A-Za-z]')
  if [ -n "$hits" ]; then
    echo "SECRET-SCAN: possible embedded secret in $f:"; echo "$hits"; status=1
  fi
done

if [ "$status" -ne 0 ]; then
  echo ""
  echo "Blocked by secret scan. Replace real values with YOUR_* / \${ENV} placeholders,"
  echo "or if this is a false positive, adjust scripts/check_secrets.sh allow-lists."
fi
exit "$status"
