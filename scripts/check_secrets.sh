#!/usr/bin/env bash
# check_secrets.sh — block credentials and personal identifiers from entering
# this PUBLIC repo (DEC-0012, DEC-0039). Invoked by pre-commit on staged files,
# and by CI over the whole tracked tree.
#
# Exit non-zero (and print the offending line) if a scanned file contains:
#   - an assignment-style secret with a real-looking value
#   - a known personal identifier (PWS id, place name, the NAS IP, …)
#   - a private-range LAN IP/subnet written as bare prose, known or not (DEC-0144)
#
# ---------------------------------------------------------------------------
# READ THIS BEFORE TOUCHING THE ALLOW-LIST. Seven bug classes have already shipped
# here, each of which made the gate GREEN WHILE CATCHING NOTHING. Every one of them
# is now a planted payload in scripts/test_check_secrets.sh — the literals live
# THERE, where they execute, not here, where they would merely be prose (DEC-0040).
# Classes 1-4 are written up below. Classes 5-7 are documented where their detector
# is defined: 5 is the `pass` key plus the quoted app-password literal (S68), 6 the
# unquoted app password (S76, DEC-0084), 7 a private-range LAN address as prose (DEC-0144).
#
#   1. `grep -viE` (case-INSENSITIVE allow-list). Its [A-Z] terms then matched
#      lowercase code, so the ALL_CAPS-constant rule swallowed nearly every
#      unquoted secret. Fixed S36. (Dashboard DEC-0063 — the same bug, found
#      twice, independently, in two repos.)
#
#   2. FREE-FLOATING ALLOW TERMS. An allow term that may match ANYWHERE on the
#      line is not an allow-list, it is an escape hatch: THE SECRET SITS ON THE
#      LEFT AND THE EXCUSE ON THE RIGHT — a real value, then a trailing "falls
#      back to os.environ" that excused it. Fixed S38 by making every allow term
#      either ANCHORED to line start or POSITIONED (it must appear as the
#      assignment's VALUE, or in key position). No free-floating terms remain.
#      Keep it that way: a new term that can match mid-line re-opens the hole.
#      (test: BAD payloads "the excuse on the right")
#
#   3. THE `grep -n` PREFIX. The old version piped `grep -n` output into the
#      allow-list, so every line arrived prefixed with "N:" — and a rule keyed on
#      a colon then matched that prefix instead of the code. The anchors had to
#      compensate (`^[0-9]+:`), which is fragile, and is exactly why the dashboard
#      warns against porting our anchors verbatim. Fixed S38 by REMOVING THE
#      CAUSE: the line number is stripped with bash parameter expansion, and the
#      allow-list runs on the RAW line. Anchors are plain `^[[:space:]]*`.
#
#   4. THE COMMENT EXEMPTION (fixed S40, DEC-0045). The gate used to allow ANY
#      full-line comment outright — `#`, `//`, `/* */`, ` *`. So a commented-out
#      credential shipped clean. IN A PUBLIC REPO A COMMENTED-OUT CREDENTIAL IS
#      STILL A LEAKED CREDENTIAL: `git push` does not strip comments, and neither
#      does anyone reading the file. The rule was not merely a blind spot — the
#      test ASSERTED it, listing commented secrets under "must PASS". The proof
#      certified the hole.
#      COMMENTS ARE NOW SCANNED EXACTLY LIKE CODE. A comment earns no exemption;
#      only its VALUE can (a placeholder, an ${ENV} ref, prose — rules 2 and 3
#      below). Do not re-add a marker-based exemption.
#      (test: BAD payloads "commented-out credential", every marker form)
#
# A GREEN EXIT CODE IS NOT EVIDENCE THAT THIS WORKS. That belief is precisely how
# the gate stayed broken for nine sessions. It ships with a planted-payload test:
#
#       scripts/test_check_secrets.sh        <-- RUN IT AFTER ANY CHANGE HERE
#
# "EVERY CLASS HAS A PLANTED PAYLOAD" WAS ITSELF UNVERIFIED (S145, #409). A mutation
# pass — delete one alternate from a scratch copy of this file, re-run the test,
# expect it to go red — found that `passcode`, the bare `key` alternate, the quoted
# app-password shape, most private-range sub-ranges, most allow-list alternates and the
# whole identifier check could each be deleted with every control still green. Each now
# has a planted control. Two kinds of deletion still stay green, and no control can kill
# them: `api_?secret` is redundant with the unanchored `secret`, and six allow alternates
# are inert (see INERT ALTERNATES below). When you add or change an alternate, delete it
# in a scratch copy and confirm the test goes red.
#
# S151 (#421) closed the four holes that pass found, one planted control each, every new
# alternate mutation-tested: quoted key names (`_sep`), `secret_key`/`access_key`/
# `private_key`, `os.getenv(` as a false positive, and the allow-list applied per LINE
# (it is now per MATCH, in the scan loop). One new deletion stays green and no control
# can kill it: the scan loop's fail-closed branch for a flagged line that yields no match
# (the detector and the splitter run the same regex, so it cannot happen). It stays as a
# guard against a future edit to either.
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
# extended-regex per line). If that file is absent (CI, a fork, another user, and
# every git WORKTREE, which never checks out a gitignored file), the identifier check
# is skipped, and since S145 (#409) it says so on stderr instead of staying silent.
# Two switches, both read from the environment (the pre-commit hook inherits it):
#   CHECK_SECRETS_REQUIRE_IDENTIFIERS=1  exit 2 unless the list is present and holds a
#       pattern. The owner opts in on a machine that has the file; CI must not, it
#       has none. Unset, empty and 0 all mean "skip if absent", as before. Any other
#       value counts as on: a typo makes the gate stricter, never quieter.
#   CHECK_SECRETS_IDENT_FILE=<path>      read the list from here instead. The test
#       plants a synthetic list this way, so the check has a control that does not
#       depend on the private file.
# A list that is not a valid regex is fatal in either mode: grep would exit 2 with no
# output, and the per-file scan below would read that as "no hits".
# Exit codes: 1 = a finding, 2 = the gate could not run as configured.
# No broad email regex: upstream author attribution (Keffer, Heijst, Skahan,
# OgoXe) is legitimate in a public repo.
ident_file="${CHECK_SECRETS_IDENT_FILE:-$(dirname "$0")/.identifiers}"
ident_re=""
if [ -f "$ident_file" ]; then
  ident_re="$(grep -vE '^[[:space:]]*(#|$)' "$ident_file" | paste -sd '|' -)"
fi
require_ident=0
case "${CHECK_SECRETS_REQUIRE_IDENTIFIERS:-}" in ''|0) ;; *) require_ident=1 ;; esac
if [ -z "$ident_re" ]; then
  if [ "$require_ident" -eq 1 ]; then
    echo "SECRET-SCAN: CHECK_SECRETS_REQUIRE_IDENTIFIERS is set but the identifier list is missing or empty: $ident_file" >&2
    echo "  A git worktree does not carry the gitignored list; copy scripts/.identifiers in from the main checkout." >&2
    exit 2
  fi
  echo "SECRET-SCAN: note: identifier check SKIPPED (no patterns in $ident_file)." >&2
else
  printf '' | grep -E "$ident_re" >/dev/null 2>&1
  if [ $? -eq 2 ]; then
    echo "SECRET-SCAN: $ident_file is not a valid extended-regex list; the identifier check cannot run." >&2
    exit 2
  fi
fi

# --- What looks like a secret: KEY <sep> VALUE, value 8+ credential-ish chars ---
# `_key` is shared by the detector AND by every POSITIONED allow term below, so
# an allow term must sit right after a credential key — not float anywhere on the line.
# The allow-list is tested per MATCH, not per line (S151, #421 item 1): see the scan loop.
#
# S151 (#421 items 2 and 3):
#   - `_sep` lets a closing quote sit between the key and its separator, so a JSON or
#     dict-style `"api_key": "<value>"` is scanned. It is shared by the detector and the
#     positioned allow terms, like `_key`, so a quoted key is excused the same way.
#   - `PASSWORD` is listed for the same reason `PASS` is (S68): detection ignores case, the
#     allow-list does not, and windy.py's `'PASSWORD': self.password` (an upload parameter)
#     became visible with the quoted-key change and could not be excused.
#   - `(secret|access|private)_?key` was missing: `secret` needs the separator right
#     after it and the bare `key` alternate wants a non-letter, non-underscore character
#     before it, so `SECRET_KEY = <value>` slipped between both. The allow-list is
#     case-sensitive, so the uppercase and camelCase spellings are listed on their own.
_key='(password|PASSWORD|passcode|pass|PASS|api_?key|api_?secret|token|secret|[^A-Za-z_]key|(secret|access|private)_?[Kk]ey|(SECRET|ACCESS|PRIVATE)_?KEY)'
_sep='["'"'"']?[[:space:]]*[:=]'
_assign="${_key}${_sep}"'[[:space:]]*["'"'"']?[A-Za-z0-9_./+=-]{8,}'

# --- S68: bare `pass`, and the app-password literal (hole class 5) ---
# `pass` was added to _key above because the key list held `password` and
# `passcode` but nothing for the `_PASS` abbreviation — so `GMAIL_PASS = "..."`
# was missed in every spelling, and GMAIL_PASS is the exact variable this
# project's monitor uses. Verified missed before the fix, caught after.
#
# `PASS` is listed separately from `pass` on purpose. Detection is case-insensitive,
# but THE ALLOW-LIST IS NOT (see bug class 1 above) — so without the uppercase
# spelling here, the allow rules could never excuse `GMAIL_PASS = os.environ.get(...)`
# or README's `GMAIL_PASS="your_gmail_app_password"`, and widening the key list
# would have turned the gate into a false-positive machine on this repo's own
# source. The harness caught exactly that, which is what it is for.
#
# `pass` is deliberately bare rather than `passwd`: README documents the sudoers
# line `NOPASSWD: /volume1/...`, and a `passwd` alternative matches that and
# reports the path as a credential. Bare `pass` cannot, because the detector
# requires `[:=]` right after the key and `NOPASSWD` has `WD` there. Same reason
# Python's `pass` statement and `passed = True` do not trip it.
#
# The second detector below exists because _assign needs 8+ CONSECUTIVE value
# characters, and Google displays an app password as four 4-character groups.
# the four-group form people actually paste breaks that run at 4 and slips through
# even with `pass` in the key list. Matching the literal shape is narrow enough to
# stay quiet: four lowercase 4-letter groups inside one pair of quotes. (Spelled
# out here in prose rather than as an example, because writing the example would
# make this comment a finding — comments earn no exemption, DEC-0045.)
_apppw='["'"'"'][a-z]{4}([[:space:]][a-z]{4}){3}["'"'"']'

# --- S76: the UNQUOTED app password (hole class 6, DEC-0084) ---
# `_apppw` above requires quotes, and `_assign` requires 8+ CONSECUTIVE value
# characters — which the four-group form breaks at 4. So an app password written
# WITHOUT quotes was missed in every spelling, and unquoted is the native form of
# the two files this repo must never commit: `weewx.conf` is ConfigObj (bare
# values are the norm) and `monitor.env` is an env file. The gate would have
# missed this project's own credential in the format its own config writes it.
#
# Found by the routine pre-commit positive control, same as hole class 5. S68's
# harness asserted the QUOTED form and stopped there; the neighbouring spelling
# was never asked about, so the fix certified its own blind spot (DEC-0045 again).
#
# Anchored on `_key` + `[:=]` rather than just dropping the quote requirement.
# That anchor is load-bearing, not decoration: four consecutive lowercase
# four-letter words occur in ordinary English, so a bare shape match would flag
# prose and comments across the repo and train people to skip the gate (ops#147
# item 6). Requiring the credential key immediately before it cannot fire on
# prose. Quotes stay OPTIONAL here so this one rule covers both spellings.
_apppw_assign="${_key}${_sep}"'[[:space:]]*["'"'"']?[a-z]{4}([[:space:]][a-z]{4}){3}'

secret_re="${_assign}|${_apppw}|${_apppw_assign}"

# --- hole class 7 (DEC-0144): a private-range LAN IP/subnet as bare PROSE ---
# Everything above is KEY=VALUE shaped: a credential always sits after an `=`/`:`.
# A LAN IP/subnet does not — it shows up mid-sentence in a diagnostic note (an
# "X is on this subnet, Y is on that one" routing observation) or a routing
# comment, so no assignment-shaped rule was ever going to catch it, and none of
# the ALLOW rules below apply to it (they are all keyed off `$_key`, which a bare
# IP never has). This is a SEPARATE, pattern-based detector for that reason,
# matching the same "general shape, not a finite list" approach `_assign` takes
# for credentials — `.identifiers` (below) is the opposite approach, a finite list
# of exact known values, and that is precisely why it never caught this: a subnet
# written a new way, or with a wildcard octet, is not a value that list can
# enumerate in advance.
#
# Proven blind before this fix, not assumed: a throwaway file containing a real
# private IP in prose passed the gate clean (exit 0) pre-fix. Two real instances
# already shipped through it — DEC-0127 (a personal LAN identifier in tracked
# docs, full history rewrite) and DEC-0144 (this one: the same subnet class, plus
# a raw marvin IP posted straight to a GitHub comment, which no git-triggered gate
# could ever reach — see the DEC for why that half needs a different fix, not this
# script).
#
# RFC1918 ranges only (10/8, 172.16/12, 192.168/16) — a public IP is not a LAN
# secret. The `x` alternation matches this repo's own placeholder-adjacent habit
# of writing a subnet with a wildcard trailing octet, which is prose ABOUT the
# exposure, not an escape from it (see the planted BAD payloads in
# scripts/test_check_secrets.sh for the exact shape, per DEC-0040 — this comment
# deliberately does not spell it out, for the same reason the `_apppw` comment
# above doesn't). Boundary groups (`^|[^0-9.]` / `[^0-9]|$`) stop a match from
# starting or ending mid-octet, which is what keeps this from firing on a
# three-dotted-number version string like weewx's own (see the GOOD payloads) —
# the pattern requires all four octets, so a three-number version string never
# engages it; verified against that exact repo line, not assumed.
_private_ip='(^|[^0-9.])(10\.[0-9x]{1,3}\.[0-9x]{1,3}\.[0-9x]{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.[0-9x]{1,3}\.[0-9x]{1,3}|192\.168\.[0-9x]{1,3}\.[0-9x]{1,3})([^0-9]|$)'

# NOTE: there is deliberately NO "the line is a comment" allow rule. It was
# removed in S40 (bug class 4 / DEC-0045). A comment marker is not evidence about
# the VALUE, and a commented-out credential in a public repo is still leaked.
# Comments are scanned exactly like code; only the rules below can excuse a line,
# and every one of them tests the VALUE.

# --- ALLOW (1): the VALUE is a placeholder or a reference, not a literal. ---
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
# INERT ALTERNATES (S145, #409). The detector only fires on 8+ value characters, and
# an allow term only matters on a line the detector fired on. `${`, the two empty-quote
# forms and `input(` can never start such a value, so on their own assignment they never
# fire; their one remaining effect is to excuse a literal elsewhere on the same line.
# `None` and `-1` fire only when the value merely BEGINS with the token, so no natural
# line exercises them. A bare `getenv(` is the same, and its control is a helper name
# starting with it. All stay as documented intent; a green GOOD line for one of them is
# not coverage. `os.getenv(...)` is flagged, not excused: the value must begin with the
# token. The test marks such lines (inert).
# `os.getenv(` is the exception (S151, #421 item 4): the value does begin with `os.`, so
# it is excused on its own alternate, like `os.environ`.
_val='(YOUR_|your_|\$\{|os\.environ|os\.getenv|getenv|sys\.argv|argv|input\(|""|'"''"'|None|-1\b|self\.|options\.|[A-Za-z_][A-Za-z_0-9]*\.get\(|(site|config|stn)_dict|[A-Z][A-Z0-9]*(_[A-Z0-9]+)+\b)'
allow_value="${_key}${_sep}"'[[:space:]]*["'"'"']?'"$_val"

# --- ALLOW (2): prose, as the value of THE SECRET KEY ITSELF. ---
# A docstring / table row describing a field (influx.py's "InfluxDB 2.x
# Authorization Token" line) is not a credential. Requires a Capitalized word
# FOLLOWED BY another word — genuine multi-word prose, which a bare credential
# never is. A single capitalized value is still CAUGHT.
# (test: BAD payload "single Capitalized token")
#
# POSITIONED with $_key, and that is load-bearing. An earlier cut of this rule
# began `[A-Za-z]:` — any letter, any colon, anywhere — so a trailing
# "Authorization: Bearer …" comment excused a real value sitting on the left.
# The planted-payload test caught that while this very gate was being written.
allow_prose="${_key}"'["'"'"']?[[:space:]]*:[[:space:]]*[A-Z][A-Za-z]*[[:space:]]+[A-Za-z0-9]'

# --- ALLOW (3): `description` / `Authorization` as the line's OWN key. ---
# ANCHORED to line start. These two were free-floating in both repos' gates, and
# so were an escape hatch — a real value on the left, a trailing "Authorization:
# Bearer …" on the right, and the line passed clean. They are only ever allowed
# when they are what the line IS, not something the line happens to mention.
allow_keys='^[[:space:]]*[-{,]?[[:space:]]*["'"'"']?(description|Authorization)["'"'"']?[[:space:]]*[:=]'

# --- ALLOW (4): `self.x = x` constructor plumbing. ANCHORED, and deliberately
# narrow. The VALUE is a bare unquoted lowercase identifier, i.e. a variable
# reference (`self.<field> = <field>`). Anchoring matters: a bare lowercase
# literal is exactly the shape a real leaked credential takes in weewx.conf, so
# this must NOT generalise beyond `self.` — and, since S40, it does not
# generalise past a comment marker either: a commented-out constructor line is
# scanned like any other. Delete the dead comment rather than re-widening this.
allow_selfassign='^[[:space:]]*self\.[A-Za-z_0-9]+[[:space:]]*=[[:space:]]*[a-z_][a-z_0-9]*[[:space:]]*$'

# S151 (#421 item 1): the two kinds of excuse apply at different scales.
#   allow_line  describes the LINE (its own key is `description`, or it is `self.x = x`),
#               so it excuses the whole line, anchored at the start as before.
#   allow_match describes ONE assignment's VALUE, so each secret-shaped match on the line
#               must carry its own. One excused assignment no longer excuses a literal
#               beside it; before, `a = os.environ[..], b = <literal>` passed.
allow_line="${allow_keys}|${allow_selfassign}"
allow_match="${allow_value}|${allow_prose}"

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

  # (b) a private-range LAN IP/subnet as bare prose (hole class 7, DEC-0144).
  # Own check, not folded into (c): it is not KEY=VALUE shaped, so none of (c)'s
  # allow-list applies to it, and it needs none — a placeholder like <NAS_IP> or
  # <MARVIN_IP> contains no digits, so it cannot accidentally match this pattern.
  hits=$(grep -nE "$_private_ip" "$f" 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "SECRET-SCAN: private LAN IP/subnet literal in $f (use a <..._IP>/<..._SUBNET> placeholder):"
    echo "$hits"; status=1
  fi

  # (c) assignment-style secrets with a real value.
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
    printf '%s\n' "$line" | grep -qE "$allow_line" && continue
    # Split the line into one segment per match (from a match's start to the next one's)
    # and demand an allow term in EVERY segment. Literal string surgery, no offsets, so
    # it does not depend on the locale. A line the detector fired on but that yields no
    # match here stays flagged: failing closed, never open.
    cur=""; scan="$line"; excused=1
    while IFS= read -r m; do
      [ -n "$m" ] || continue
      pre="${scan%%"$m"*}"
      start="${scan#"$pre"}"
      if [ -n "$cur" ]; then
        printf '%s\n' "${cur%"$start"}" | grep -qE "$allow_match" || excused=0
      fi
      cur="$start"
      scan="${start#"$m"}"
    done < <(printf '%s\n' "$line" | grep -oEi "$secret_re")
    if [ -z "$cur" ]; then excused=0
    else printf '%s\n' "$cur" | grep -qE "$allow_match" || excused=0; fi
    [ "$excused" -eq 1 ] && continue
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
