#!/usr/bin/env bash
# check_secrets.sh — block credentials and personal identifiers from entering
# this PUBLIC repo (DEC-0012, DEC-0039). Invoked by pre-commit on staged files,
# and by CI over the whole tracked tree.
#
# Exit non-zero (and print the offending line) if a scanned file contains:
#   - an assignment-style secret with a real-looking value
#   - a known personal identifier (PWS id, place name, the NAS IP, …)
#
# ---------------------------------------------------------------------------
# READ THIS BEFORE TOUCHING THE ALLOW-LIST. Three bug classes have already shipped
# here, each of which made the gate GREEN WHILE CATCHING NOTHING:
#
#   1. `grep -viE` (case-INSENSITIVE allow-list). Its [A-Z] terms then matched
#      lowercase code, so the ALL_CAPS-constant rule swallowed nearly every
#      unquoted secret. Fixed S36. (Dashboard DEC-0063 — the same bug, found
#      twice, independently, in two repos.)
#
#   2. FREE-FLOATING ALLOW TERMS. An allow term that may match ANYWHERE on the
#      line is not an allow-list, it is an escape hatch: THE SECRET SITS ON THE
#      LEFT AND THE EXCUSE ON THE RIGHT.
#          token = REALSECRET1234   # falls back to os.environ    <-- passed!
#      Fixed S38 by making every allow term either ANCHORED (comment-only lines)
#      or POSITIONED (it must appear as the assignment's VALUE, or in key
#      position). No free-floating terms remain. Keep it that way: a new term that
#      can match mid-line re-opens the hole.
#
#   3. THE `grep -n` PREFIX. The old version piped `grep -n` output into the
#      allow-list, so every line arrived prefixed with "N:" — and a rule keyed on
#      a colon then matched that prefix instead of the code. The anchors had to
#      compensate (`^[0-9]+:`), which is fragile, and is exactly why the dashboard
#      warns against porting our anchors verbatim. Fixed S38 by REMOVING THE
#      CAUSE: the line number is stripped with bash parameter expansion, and the
#      allow-list runs on the RAW line. Anchors are plain `^[[:space:]]*`.
#
# A GREEN EXIT CODE IS NOT EVIDENCE THAT THIS WORKS. That belief is precisely how
# the gate stayed broken for nine sessions. It ships with a planted-payload test:
#
#       scripts/test_check_secrets.sh        <-- RUN IT AFTER ANY CHANGE HERE
#
# ---------------------------------------------------------------------------
set -u
status=0
files=("$@")
[ ${#files[@]} -eq 0 ] && files=($(git diff --cached --name-only --diff-filter=ACM))
# Nothing to scan (run by hand on a clean tree, or an empty staged set): pass
# cleanly instead of tripping `set -u` on the empty-array expansion below.
[ ${#files[@]} -eq 0 ] && { echo "SECRET-SCAN: nothing to scan."; exit 0; }

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

# --- What looks like a secret: KEY <sep> VALUE, value 8+ credential-ish chars ---
# `_key` is shared by the detector AND by every POSITIONED allow term below, so
# an allow can only ever fire against the key the detector actually matched —
# never against some other word that happens to appear later on the line.
_key='(password|passcode|api_?key|api_?secret|token|secret|[^A-Za-z_]key)'
secret_re="${_key}"'[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_./+=-]{8,}'

# --- ALLOW (1): the whole line is a comment. ANCHORED to line start. ---
# Python/shell `#`, C/JS `//` and `/* … */`, and ` *` JSDoc continuations.
allow_comment='^[[:space:]]*(#|//|/\*|\*)'

# --- ALLOW (2): the VALUE is a placeholder or a reference, not a literal. ---
# POSITIONED: each term must sit immediately after the key's `=` / `:`, so a
# trailing comment or a stray mention elsewhere on the line CANNOT rescue a real
# secret. This is the fix for bug class (2) above.
#   YOUR_* / your_*                 placeholder
#   ${VAR}                          shell / compose interpolation
#   os.environ / getenv / argv / input()   runtime lookup
#   "" / '' / None / -1             empty
#   self.x / options. / .get( / *_dict    weewx config plumbing
#   FOO_BAR                         an ALL_CAPS *underscored* constant REFERENCE.
#     The underscore does the real work: `= INFLUX_TOKEN` is a reference, while
#     `= REALSECRETVALUE` is a bare literal and is NOT allowed.
_val='(YOUR_|your_|\$\{|os\.environ|getenv|sys\.argv|argv|input\(|""|'"''"'|None|-1\b|self\.|options\.|[A-Za-z_][A-Za-z_0-9]*\.get\(|(site|config|stn)_dict|[A-Z][A-Z0-9]*(_[A-Z0-9]+)+\b)'
allow_value="${_key}"'[[:space:]]*[:=][[:space:]]*["'"'"']?'"$_val"

# --- ALLOW (3): prose, as the value of THE SECRET KEY ITSELF. ---
# A docstring / table row describing a field ("token: InfluxDB 2.x Authorization
# Token") is not a credential. Requires a Capitalized word FOLLOWED BY another
# word — genuine multi-word prose, which a bare token never is. A single
# capitalized token (`api_key: Secret123x`) is still CAUGHT.
#
# POSITIONED with $_key, and that is load-bearing. An earlier cut of this rule
# began `[A-Za-z]:` — any letter, any colon, anywhere — which let a trailing
# comment do the excusing:
#     token = "abc123def456"   # Authorization: Bearer xyz      <-- passed!
# The planted-payload test caught that while this very gate was being written.
allow_prose="${_key}"'[[:space:]]*:[[:space:]]*[A-Z][A-Za-z]*[[:space:]]+[A-Za-z0-9]'

# --- ALLOW (4): `description` / `Authorization` as the line's OWN key. ---
# ANCHORED to line start. These two were free-floating in both repos' gates, and
# so were an escape hatch: `token = "abc123def456"  # Authorization: Bearer xyz`
# passed clean. They are only ever allowed when they are what the line IS, not
# something the line happens to mention.
allow_keys='^[[:space:]]*[-{,]?[[:space:]]*["'"'"']?(description|Authorization)["'"'"']?[[:space:]]*[:=]'

# --- ALLOW (5): `self.x = x` constructor plumbing. ANCHORED, and deliberately
# narrow. The VALUE is a bare unquoted lowercase identifier, i.e. a variable
# reference (`self.password = password`). Anchoring matters: a bare lowercase
# literal is exactly the shape a real leaked credential takes in weewx.conf
# (`api_key = mysecretkey123`), so this must NOT generalise beyond `self.` .
allow_selfassign='^[[:space:]]*self\.[A-Za-z_0-9]+[[:space:]]*=[[:space:]]*[a-z_][a-z_0-9]*[[:space:]]*$'

allow_re="${allow_comment}|${allow_value}|${allow_prose}|${allow_keys}|${allow_selfassign}"

for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  case "$f" in
    *.png|*.jpg|*.jpeg|*.gif|*.svg|*.zip|*.tar.gz|*.sdb|*.ico) continue ;;
    # The gate's OWN test is the one file whose job is to contain planted secrets.
    # Exempt by EXACT PATH — never by pattern (`*test*` would silently exempt real
    # code the moment someone adds tests/test_credentials.py).
    scripts/test_check_secrets.sh) continue ;;
  esac

  # (a) identifiers (only if the gitignored pattern file is present)
  if [ -n "$ident_re" ] && [ "$f" != ".gitignore" ]; then
    hits=$(grep -nEi "$ident_re" "$f" 2>/dev/null)
    if [ -n "$hits" ]; then
      echo "SECRET-SCAN: personal identifier in $f:"; echo "$hits"; status=1
    fi
  fi

  # (b) assignment-style secrets with a real value.
  #
  # The allow-list is evaluated against the RAW line. `grep -n` gives us the line
  # number for the human; the "N:" prefix is then stripped with bash parameter
  # expansion (NOT a regex) before the allow-list ever sees the content — which is
  # what kills bug class (3) at the root instead of compensating for it.
  #
  # Detection keeps -i (Token / TOKEN / token all match). THE ALLOW-LIST IS
  # CASE-SENSITIVE (`grep -qE`, never `-qEi`) — its [A-Z] terms carry the whole
  # distinction between a constant reference and a literal secret (bug class 1).
  while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    n="${hit%%:*}"        # line number
    line="${hit#*:}"      # RAW line content, prefix removed
    printf '%s\n' "$line" | grep -qE "$allow_re" && continue
    echo "SECRET-SCAN: possible embedded secret in $f:"
    echo "  ${n}: ${line}"
    status=1
  done < <(grep -nEi "$secret_re" "$f" 2>/dev/null)
done

if [ "$status" -ne 0 ]; then
  echo ""
  echo "Blocked by secret scan. Replace real values with YOUR_* / \${ENV} placeholders,"
  echo "move infra facts to the gitignored docs/LOCAL_INFRA.md, or — if this is a false"
  echo "positive — adjust the allow-lists in scripts/check_secrets.sh AND re-run"
  echo "scripts/test_check_secrets.sh to prove you did not open a hole."
fi
exit "$status"
