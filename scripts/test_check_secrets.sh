#!/usr/bin/env bash
# test_check_secrets.sh — prove the secret gate actually catches secrets.
#
# WHY THIS EXISTS (DEC-0039). `scripts/check_secrets.sh` passed every commit for
# nine sessions while catching NOTHING. It was green because it was blind. The
# same bug shipped independently in the dashboard repo (their DEC-0063 / DEC-0100).
# A green exit code is not evidence. THIS is the evidence:
#
#   - every BAD payload below MUST be caught   (a miss = a credential leaks)
#   - every GOOD line below MUST pass          (a hit = the gate cries wolf)
#   - the real tracked tree MUST be clean      (no false positives in practice)
#
# Run it after ANY change to check_secrets.sh:   scripts/test_check_secrets.sh
#
# S40 (DEC-0045) sharpened the lesson. A test is not automatically evidence either:
# this file used to assert, under "must PASS", that `# api_key = <real value>` was
# fine. The gate did not merely have a blind spot — ITS PROOF CERTIFIED THE BLIND
# SPOT. Two of the payloads below (holes 15 and 16) are those exact lines, moved
# from `good` to `bad`. When you add a case here, ask which array it belongs in and
# why, because that judgement IS the gate.
#
# S145 (#409) found "63 controls green" to be weaker evidence than it looked. Deleting
# one alternate at a time from a scratch copy of the gate and re-running this file left
# it green for `passcode`, the bare `key` alternate, the quoted app-password shape, two
# of three 172.16/12 sub-ranges, the wildcard octets, the boundary groups, the 8-char
# threshold, most allow-list alternates, and the whole identifier check. Each now has a
# control. Nine such deletions still stay green and no control can kill them: `api_?secret`
# is redundant with the unanchored `secret`, and six allow-list alternates are inert
# (see INERT ALTERNATES in the gate). Eight GOOD lines below were also written to exercise
# an allow-list rule that the detector never lets them reach, so they pass whatever the
# allow-list says. They are marked (inert) and kept as guards against widening the
# detector; the live allow-list controls are the ones added under S145.
# S151 (#421) added a control for each of the four holes that pass found (holes 46-61 and
# the S151 GOOD block) and mutation-tested every new alternate: fourteen deletions go red.
# The fifteenth, the scan loop's fail-closed branch for a line that yields no match, stays
# green and cannot be killed (the detector and the splitter run one regex).
# THE RULE FOR EDITING THE GATE: delete the alternate you touched in a scratch copy and
# confirm this file goes red. A control that stays green under deletion is not one.
#
# Private-range addresses in the generated section are BUILT AT RUN TIME from octets, so
# this file carries no address literal there. A planted literal can coincide with a real
# address (ops#358), and the gate exempts this file by path, so nothing would notice.
#
# This file is the ONE file check_secrets.sh exempts (by exact path) — its job is
# to contain secret-shaped strings. None of the values below is real.
set -u
cd "$(dirname "$0")/.." || exit 2
ROOT="$(pwd)"
GATE="scripts/check_secrets.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

# The planted controls must not depend on the caller's environment. The owner's private
# scripts/.identifiers is absent in CI, forks and worktrees, so results would differ by
# machine; and a shell exporting CHECK_SECRETS_REQUIRE_IDENTIFIERS with no list to hand
# would make every gate call exit 2, so every BAD line would be "caught" for the wrong
# reason. `gate` pins both. Only the tracked-tree check at the end sees the real
# environment, which is exactly what the pre-commit hook sees.
EMPTY_IDENT="$TMP/empty.identifiers"; : > "$EMPTY_IDENT"
gate() { env CHECK_SECRETS_IDENT_FILE="$EMPTY_IDENT" CHECK_SECRETS_REQUIRE_IDENTIFIERS= "$ROOT/$GATE" "$@"; }

# --- must be CAUGHT (exit non-zero) --------------------------------------------
# Each entry is one line planted into a throwaway .py/.js file. The trailing
# comment on most of them is the point: it is the "excuse on the right" that the
# old allow-list accepted while the secret sat on the left.
bad=(
  'api_key = "abc123def456xyz"'                                  # plain literal
  'token = REALSECRET1234  # note'                                # trailing # comment  (hole 1)
  'api_key: Secret123x'                                          # single Capitalized token (hole 2)
  'const apiKey = "sk_live_abc123456";  // prod key'             # trailing // comment  (hole 3)
  'const token = "tok_abc12345";  /* prod */'                    # /* */ comment       (hole 4)
  'api_key = "abc123def456"  # description of the field'         # free-floating description (hole 5)
  'token = "abc123def456"  # Authorization: Bearer xyz'          # free-floating Authorization (hole 6)
  'token = REALSECRETVALUE'                                      # bare ALL_CAPS, NO underscore (hole 7)
  # --- S38: the free-floating "excuse" class the dashboard gate still allows ---
  # "the excuse on the right" — bug class 2 in check_secrets.sh
  'token = deadbeef123456  # falls back to os.environ'           # (hole 8)
  'password = hunter2hunter2  # comes from config_dict'          # (hole 9)
  'api_key = liveKey1234567  # replace with YOUR_API_KEY'        # (hole 10)
  "token = tok_abc123456  # see cfg.get('token')"                # (hole 11)
  'secret = s3cr3tvalue123  # ${NOT_ACTUALLY_INTERPOLATED}'      # (hole 12)
  'token = REALSECRET1234   # falls back to os.environ'          # (hole 13) the S38 header's own example
  'token = "abc123def456"   # Authorization: Bearer xyz'         # (hole 14) ditto
  # --- S40 (DEC-0045): the COMMENTED-OUT credential ---
  # These five were NOT merely unguarded — the two marked (was GOOD) sat in the
  # `good` array below, so the gate's own proof CERTIFIED that a commented
  # credential must ship. `git push` does not strip comments. Neither does a reader.
  '# api_key = abc123def456xyz'                                  # (hole 15) was GOOD
  '// const token = "tok_abc12345";'                             # (hole 16) was GOOD (JS)
  '/* password = hunter2hunter2 */'                              # (hole 17) block comment
  ' * api_key = liveKey1234567'                                  # (hole 18) JSDoc continuation
  '    # secret = s3cr3tvalue123'                                # (hole 19) indented comment
  '#token=deadbeef123456'                                        # (hole 20) no spaces
  '# self.password = hunter2hunter2'                             # (hole 21) NOT constructor plumbing
  # --- S68: the `_PASS` abbreviation, and the app-password literal ---
  # The key list held `password` and `passcode` but nothing for `_PASS`, which is
  # the spelling weewx_monitor.py itself uses for its Gmail credential. All three
  # forms below were verified MISSED before the fix. Nothing had ever been leaked
  # through it — the tracked tree and the full history were both checked — so this
  # closed a future hole, not a live one.
  'GMAIL_PASS = "abcdefghijklmnop"'                              # (hole 22) _PASS, spaced =
  'GMAIL_PASS="abcdefghijklmnop"'                                # (hole 23) _PASS, no spaces
  'SMTP_PASS: abcdefghijklmnop'                                  # (hole 24) _PASS, colon
  # The 4x4 form is what Google actually displays and what people paste. It slips
  # past the assignment detector even WITH `pass` in the key list, because that
  # detector needs 8+ consecutive value characters and this breaks every 4.
  'GMAIL_PASS = "abcd efgh ijkl mnop"'                           # (hole 25) app-password literal
  '# GMAIL_PASS = "abcd efgh ijkl mnop"'                         # (hole 26) ditto, commented
  # --- S76: the same literal UNQUOTED (hole class 6, DEC-0084) ---
  # Holes 25/26 pinned the QUOTED spelling and the harness stopped there, so the
  # S68 fix certified its own blind spot. Unquoted is not an exotic variant: it is
  # the NATIVE form of both files this repo must never commit -- weewx.conf is
  # ConfigObj (bare values are the norm) and monitor.env is an env file. All three
  # below were verified MISSED before the S76 fix, by the routine pre-commit
  # positive control. Nothing was ever leaked through it; this closes a future
  # hole, as hole 22-26 did.
  'GMAIL_PASS = abcd efgh ijkl mnop'                             # (hole 27) unquoted, spaced =
  '    gmail_pass = abcd efgh ijkl mnop'                         # (hole 28) unquoted, conf-style indent
  'GMAIL_PASS=abcd efgh ijkl mnop'                               # (hole 29) unquoted, env-style
  # --- hole class 7 (DEC-0144): a private-range LAN IP/subnet as bare prose ---
  # None of these are KEY=VALUE shaped, which is exactly why they slipped through
  # every rule above -- proven blind before the fix (`printf 'NAS on 192.168.211.37\n'
  # | check_secrets.sh -` exited 0). Real instances: DEC-0127 (BOOT.md, full
  # history rewrite) and DEC-0144 (this fix's own trigger).
  'NAS on 192.168.211.37, laptop on 192.168.211.52'                 # (hole 30) full IPs, mid-sentence
  'Mac on `192.168.211.x`, NAS on `10.77.140.x`'                 # (hole 31) the exact DEC-0127/0144 shape
  'server_url = http://10.77.140.23:8086'                           # (hole 32) 10/8, in a config value
  'bridge sits at 172.19.240.9 on the host'                        # (hole 33) 172.16/12
  # --- S145 (#409): a planted positive for every detector alternate that had none ---
  # Deleting each of these alternates left every control above green in a scratch copy of
  # the gate. Values are fake on purpose.
  'passcode = not-a-real-secret-0000'                              # (hole 34) key `passcode`
  'api_secret = not-a-real-secret-0000'                            # (hole 35) key `api_secret` (caught via `secret`: `api_?secret` is redundant)
  'apisecret: not-a-real-secret-0000'                              # (hole 36) same key, no underscore
  'apikey = not-a-real-secret-0000'                                # (hole 37) `api_?key`, no underscore
  '  key = not-a-real-secret-0000'                                 # (hole 38) bare `key`; it needs one character before it
  'send_mail(user, "abcd efgh ijkl mnop")'                         # (hole 39) quoted 4x4 literal with NO key: the `_apppw` shape alone
  'token = abcd1234'                                               # (hole 40) exactly 8 characters: the threshold itself
  'token = -./+=not-a-real-secret-0000'                            # (hole 41) every punctuation member of the value class, in its first 8
  'self.api_key = "not-a-real-secret-0000"'                        # (hole 42) constructor plumbing must not excuse a literal
  'self.api_key = api_key_value  # token = not-a-real-secret-0000' # (hole 43) `self.x = x` must END the line: excuse on the left
  'smtp_pass: abcd efgh ijkl mnop'                                 # (hole 44) unquoted 4x4 with a colon (holes 27-29 use `=`)
  "send_mail(user, 'abcd efgh ijkl mnop')"                         # (hole 45) the keyless 4x4 shape in single quotes
  # --- S151 (#421): the four detector holes the S145 mutation pass found ---
  # Hole class 8, quoted key names: the detector wanted the separator right after the key,
  # so a JSON or dict-style key (a closing quote in between) was never scanned.
  '"api_key": "not-a-real-secret-0000"'                            # (hole 46) JSON key, double quotes
  "'token': 'not-a-real-secret-0000'"                              # (hole 47) dict key, single quotes
  '{"password":"not-a-real-secret-0000"}'                          # (hole 48) no spaces around the colon
  '"key": "not-a-real-secret-0000"'                                # (hole 49) bare `key`; the opening quote is its one preceding character
  # Hole class 9, key names the list lacked.
  'SECRET_KEY = "not-a-real-secret-0000"'                          # (hole 50) `secret_key`, uppercase
  'secret_key = "not-a-real-secret-0000"'                          # (hole 51) lowercase
  'private_key = "not-a-real-secret-0000"'                         # (hole 52) `private_key`
  'access_key: not-a-real-secret-0000'                             # (hole 53) `access_key`, colon
  'accessKey = "not-a-real-secret-0000"'                           # (hole 54) camelCase
  'privatekey = not-a-real-secret-0000'                            # (hole 55) no underscore
  'PRIVATE_KEY=not-a-real-secret-0000'                             # (hole 56) env-file spelling
  # Hole class 10, the allow-list judged per LINE: one excused assignment excused the whole line.
  'api_key = os.environ["A"], token = "not-a-real-secret-0000"'    # (hole 57) the excused assignment first
  'token = "not-a-real-secret-0000", api_key = os.environ["A"]'    # (hole 58) the literal first
  'token = YOUR_TOKEN_HERE; password = not-a-real-secret-0000'     # (hole 59) a placeholder, then a literal
  'token = INFLUX_TOKEN  # api_key = not-a-real-secret-0000'       # (hole 60) a reference, then a commented literal
  '"gmail_pass": abcd efgh ijkl mnop'                              # (hole 61) unquoted 4x4 behind a quoted key (the `_apppw_assign` separator)
)

# --- must PASS (exit zero) ------------------------------------------------------
good=(
  'api_key = YOUR_API_KEY_HERE'                                  # placeholder
  'token = "${INFLUX_TOKEN}"'                                    # interpolation (inert: a value starting with $ is never detected)
  "password = os.environ.get('WEEWX_PW')"                        # runtime lookup
  'api_key = ""'                                                 # empty (inert: a quote is not a value character)
  'token = None'                                                 # empty (inert: 4 characters, under the threshold)
  'self.api_key = api_key'                                       # self-assign (inert: 7-character value, under the threshold)
  'token = INFLUX_TOKEN'                                         # ALL_CAPS underscored REFERENCE
  "api_key = config_dict.get('api_key')"                         # config plumbing
  "password = stn_dict.get('password')"                          # config plumbing
  ' * api_key: the upload credential'                            # JSDoc continuation
  'key: WeatherCloud upload key'                                 # multi-word prose (inert: column 0, so nothing precedes `key`)
  '"description": "set api_key = abc123def456 here"'             # description in KEY position
  # --- S40 (DEC-0045): a comment earns NO exemption, but its VALUE still can. ---
  # Commenting out a line must not change the verdict in EITHER direction: these
  # are the same placeholder/prose/empty values as above, wearing a comment marker.
  # This is what keeps the fix from becoming a false-positive machine — it is the
  # half of the change that the docs and the README depend on.
  '# api_key = YOUR_API_KEY_HERE'                                # placeholder, commented
  '# token = "${INFLUX_TOKEN}"'                                  # interpolation, commented (inert)
  '#         token: InfluxDB 2.x Authorization Token'            # prose, commented (influx.py docstring)
  '# api_key = ""'                                               # empty, commented (inert)
  '# token = INFLUX_TOKEN'                                       # ALL_CAPS reference, commented
  "# password = os.environ.get('WEEWX_PW')"                      # runtime lookup, commented
  # --- S68: widening the key list must not start crying wolf. ---
  # Each of these is a real line shape from this repo or its docs. The first is
  # weewx_monitor.py's own credential lookup; the second is the sudoers line in
  # README Setup step 4, which a `passwd` key alternative WOULD have reported as a
  # credential (with the binary path as the "value") — the reason the fix uses
  # bare `pass` instead. The last two are ordinary words that merely start with it.
  "GMAIL_PASS = os.environ.get('GMAIL_PASS', '')"                # runtime lookup, _PASS key
  'weewx-monitor ALL=(root) NOPASSWD: /volume1/docker/x.sh'      # sudoers line, not a secret
  'GMAIL_PASS = "${GMAIL_PASS}"'                                 # interpolation, _PASS key (inert)
  'passed = True'                                                # a word starting with pass
  'if verify_passcode(x): pass'                                  # the Python statement
  # --- hole class 7 (DEC-0144): the private-IP rule must not cry wolf ---
  'numeric -- "10.0.0" < "3" is True in Python, which would reject a'  # rtldavis.py:220 verbatim
  'server_url = http://<MARVIN_IP>:8086'                         # the placeholder itself
  'weewxd published to <NAS_IP>:8086 at 22:43:16'                # placeholder, prose
  'health check reached 8.8.8.8 to confirm internet routing'     # a public IP, out of scope
  'bound to 127.0.0.1 for local-only testing'                    # loopback, not RFC1918
  # --- S145 (#409): a planted negative for every allow-list alternate that can fire ---
  # Each line is DETECTED first (a key, then 8+ value characters) and excused by the ONE
  # alternate named. Alternates must not overlap on a line: with two excuses, deleting
  # either leaves the line green, which is how the old lines here survived deletion.
  'smtp_pass = os.environ["SMTP_PASS"]'                          # lowercase `pass` key (the allow-list is case-sensitive)
  'api_key = YOUR_key_here'                                      # `YOUR_`, with no ALL_CAPS rule behind it
  'api_key = your_api_key_here'                                  # `your_`
  'token = sys.argv[1]'                                          # `sys.argv`
  'password = argv.pop(0)'                                       # bare `argv`
  "password = getenv_default('WEEWX_PW')"                        # `getenv`, as the start of a helper name (see the INERT note in the gate)
  'token = self.token_value'                                     # `self.` as the VALUE
  'api_key = options.api_key_value'                              # `options.`
  "api_key = settings.get('api_key')"                            # `<name>.get(`, on a name that is not *_dict
  "token = site_dict['token']"                                   # `site_dict`, indexed so `.get(` cannot also excuse it
  "token = config_dict['token']"                                 # `config_dict`
  "token = stn_dict['token']"                                    # `stn_dict`
  'self.api_key = api_key_value'                                 # `allow_selfassign`, with a value over the 8-char threshold
  'Authorization: Bearer token=not-a-real-secret-0000'           # `allow_keys`: Authorization as the line's OWN key
  '- description: set token = not-a-real-secret-0000 here'       # `allow_keys` after a YAML list marker
  '{description: set token = not-a-real-secret-0000 here'        # `allow_keys` after an opening brace
  ', description: set token = not-a-real-secret-0000 here'       # `allow_keys` after a comma
  "'description': 'set token = not-a-real-secret-0000 here'"     # `allow_keys` with a single-quoted key
  'token = abc1234'                                              # 7 characters: the documented 8+ threshold, pinned from below
  # --- S151 (#421): each new allow alternate fires on a line it alone excuses ---
  '"api_key": "YOUR_API_KEY_HERE"'                               # a quoted key name still takes the value allow-list
  "'token': os.environ['T']"                                     # ditto, single quotes and a bare lookup
  'SECRET_KEY = sys.argv[1]'                                     # uppercase `SECRET_KEY`
  'ACCESS_KEY = sys.argv[1]'                                     # uppercase `ACCESS_KEY`
  'PRIVATE_KEY = sys.argv[1]'                                    # uppercase `PRIVATE_KEY`
  "secret_key = settings.get('secret_key')"                      # lowercase `secret_key`
  "private_key = settings.get('private_key')"                    # lowercase `private_key`
  "access_key = settings.get('access_key')"                      # lowercase `access_key`
  "accessKey = settings.get('accessKey')"                        # camelCase `Key`
  "password = os.getenv('WEEWX_PW')"                             # `os.getenv(`: a runtime lookup, not a literal (#421 item 4)
  'token = os.getenv("INFLUX_TOKEN")'                            # ditto, double quotes
  'api_key = settings.get("api_key"), token = os.environ["T"]'   # two excused assignments on one line stay excused
  '"token": InfluxDB 2.x Authorization Token'                    # multi-word prose behind a quoted key (`allow_prose`'s closing quote)
  "params = {'id': sid, 'PASSWORD': self.password}"               # uppercase `PASSWORD` as a quoted key (windy.py's upload parameter)
)

echo "── planted BAD payloads (each MUST be caught) ──────────────────────────"
i=0
for payload in "${bad[@]}"; do
  i=$((i+1))
  case "$payload" in *const*|*//*|*/\**) ext=js ;; *) ext=py ;; esac
  f="$TMP/bad_$i.$ext"
  printf '%s\n' "$payload" > "$f"
  if gate "$f" >/dev/null 2>&1; then
    printf '  \033[31mLEAKED\033[0m  %s\n' "$payload"; fail=$((fail+1))
  else
    printf '  caught  %s\n' "$payload"; pass=$((pass+1))
  fi
done

echo ""
echo "── known-GOOD lines (each MUST pass) ──────────────────────────────────"
i=0
for payload in "${good[@]}"; do
  i=$((i+1))
  case "$payload" in *const*|*//*|\ \**) ext=js ;; *) ext=py ;; esac
  f="$TMP/good_$i.$ext"
  printf '%s\n' "$payload" > "$f"
  if gate "$f" >/dev/null 2>&1; then
    printf '  ok      %s\n' "$payload"; pass=$((pass+1))
  else
    printf '  \033[31mFALSE POSITIVE\033[0m  %s\n' "$payload"; fail=$((fail+1))
  fi
done

# --- the generated sections below share these helpers --------------------------------
# One control per call, printed in the same shape as the loops above (caught / LEAKED,
# ok / FALSE POSITIVE) so the tally and the reader's eye stay the same. RUNNER is a
# command word: `gate`, or a function wrapping the gate in a different environment.
plant() { printf '%s\n' "$2" > "$TMP/$1"; }                       # plant FILE LINE
want_caught() {                                                    # want_caught RUNNER LABEL FILE
  if "$1" "$3" >/dev/null 2>&1; then
    printf '  \033[31mLEAKED\033[0m  %s\n' "$2"; fail=$((fail+1))
  else
    printf '  caught  %s\n' "$2"; pass=$((pass+1))
  fi
}
want_pass() {                                                      # want_pass RUNNER LABEL FILE
  if "$1" "$3" >/dev/null 2>&1; then
    printf '  ok      %s\n' "$2"; pass=$((pass+1))
  else
    printf '  \033[31mFALSE POSITIVE\033[0m  %s\n' "$2"; fail=$((fail+1))
  fi
}

echo ""
echo "── private-range sweep (addresses are built at run time) ───────────────"
# The detector's structure, not just its three families: line start, middle and end; a
# wildcard in every variable octet; all sixteen 172.16/12 second octets; non-private
# neighbors of each range; and look-alikes the boundary groups must reject. Each address
# is assembled from octets, so this file carries no address literal for them.
mkip() { printf '%s.%s.%s.%s' "$1" "$2" "$3" "$4"; }              # mkip O1 O2 O3 O4
ip_caught() { plant ip.txt "$2"; want_caught gate "$1" "$TMP/ip.txt"; }
ip_pass()   { plant ip.txt "$2"; want_pass   gate "$1" "$TMP/ip.txt"; }
for fam in "10/8:10 253 252 251" "172.16/12:172 20 252 251" "192.168/16:192 168 252 251"; do
  name="${fam%%:*}"; read -r o1 o2 o3 o4 <<< "${fam#*:}"
  a="$(mkip "$o1" "$o2" "$o3" "$o4")"
  ip_caught "$name: full address at line start" "$a is the host"
  ip_caught "$name: full address in the middle" "the host $a answers"
  ip_caught "$name: full address at line end"   "the host is $a"
done
ip_caught "10/8: wildcard in octet 2"       "subnet $(mkip 10 x 252 251) is the LAN"
ip_caught "10/8: wildcard in octet 3"       "subnet $(mkip 10 253 x 251) is the LAN"
ip_caught "10/8: wildcard in octet 4"       "subnet $(mkip 10 253 252 x) is the LAN"
ip_caught "172.16/12: wildcard in octet 3"  "subnet $(mkip 172 20 x 251) is the LAN"
ip_caught "172.16/12: wildcard in octet 4"  "subnet $(mkip 172 20 252 x) is the LAN"
ip_caught "192.168/16: wildcard in octet 3" "subnet $(mkip 192 168 x 251) is the LAN"
ip_caught "192.168/16: wildcard in octet 4" "subnet $(mkip 192 168 252 x) is the LAN"
for o in $(seq 16 31); do
  ip_caught "172.16/12: second octet $o" "bridge at $(mkip 172 "$o" 252 251) today"
done
for near in "9 253 252 251" "11 253 252 251" "172 15 252 251" "172 32 252 251" \
            "192 167 252 251" "192 169 252 251" "193 168 252 251"; do
  read -r o1 o2 o3 o4 <<< "$near"
  ip_pass "outside RFC1918: prefix $o1.$o2" "reached $(mkip "$o1" "$o2" "$o3" "$o4") fine"
done
ip_pass "boundary: a dot before the first octet (a five-part number)" "release 1.$(mkip 10 253 252 251) shipped"
ip_pass "boundary: a digit before the first octet"                    "id 2$(mkip 10 253 252 251)"
ip_pass "boundary: a fourth octet of four digits"                     "build $(mkip 10 253 252 2511)"

echo ""
echo "── skipped file types (must pass even holding a secret-shaped line) ────"
# Binary and image types are deliberately not scanned. Pinning the list makes changing
# it a decision instead of an accident.
for ext in png jpg jpeg gif svg zip tar.gz sdb ico; do
  plant "skip.$ext" 'api_key = "not-a-real-secret-0000"'
  want_pass gate "*.$ext is not scanned" "$TMP/skip.$ext"
done

echo ""
echo "── exemption by exact path, never by pattern ────────────────────────────"
want_pass gate "the gate's own test is exempt: it exists to hold planted secrets" "scripts/test_check_secrets.sh"
mkdir -p "$TMP/tests"
plant tests/test_credentials.py 'api_key = "not-a-real-secret-0000"'
want_caught gate "a file named test_* elsewhere is scanned (there is no *test* pattern)" "$TMP/tests/test_credentials.py"

echo ""
echo "── identifier list (a synthetic one: no dependence on the private file) ──"
# The real scripts/.identifiers is gitignored, so nothing here can name a real
# identifier. The list below is fake and CHECK_SECRETS_IDENT_FILE points the gate at it.
IDENT="$TMP/identifiers.txt"
printf '%s\n' '# a comment line is not a pattern' 'zz-fake-ident-alpha-0000' '' 'zz-fake-ident-beta-0000' > "$IDENT"
COMMENTS_ONLY="$TMP/comments-only.txt"; printf '%s\n' '# nothing but a comment' '' > "$COMMENTS_ONLY"
BAD_REGEX="$TMP/bad-regex.txt";         printf '%s\n' 'zz-fake-(unbalanced' > "$BAD_REGEX"
ident_gate() { env CHECK_SECRETS_IDENT_FILE="$IDENT" CHECK_SECRETS_REQUIRE_IDENTIFIERS= "$ROOT/$GATE" "$@"; }
plant i.txt 'notes mention zz-fake-ident-alpha-0000 in passing'; want_caught ident_gate "the first pattern is caught" "$TMP/i.txt"
plant i.txt 'notes mention zz-fake-ident-beta-0000 in passing';  want_caught ident_gate "a later pattern is caught (every line is joined)" "$TMP/i.txt"
plant i.txt 'notes mention ZZ-Fake-Ident-Alpha-0000 in passing'; want_caught ident_gate "matching is case-insensitive" "$TMP/i.txt"
plant i.txt 'an unrelated line of prose';                        want_pass   ident_gate "a blank line in the list is not a pattern" "$TMP/i.txt"
plant i.txt 'a comment line is not a pattern';                   want_pass   ident_gate "a comment line in the list is not a pattern" "$TMP/i.txt"
mkdir -p "$TMP/gi"
printf '%s\n' 'notes mention zz-fake-ident-alpha-0000 in passing' > "$TMP/gi/.gitignore"
printf '%s\n' 'notes mention zz-fake-ident-alpha-0000 in passing' > "$TMP/gi/notes.txt"
if ( cd "$TMP/gi" && ident_gate .gitignore >/dev/null 2>&1 ) && ! ( cd "$TMP/gi" && ident_gate notes.txt >/dev/null 2>&1 ); then
  printf '  ok      %s\n' ".gitignore is exempt from the identifier check, the same line elsewhere is not"; pass=$((pass+1))
else
  printf '  \033[31mWRONG\033[0m  %s\n' ".gitignore exemption from the identifier check"; fail=$((fail+1))
fi

echo ""
echo "── identifier switches (exit code AND message, not just non-zero) ───────"
# A bare non-zero exit would also be what a crash looks like, so each case pins the exit
# code and a word from the message. Strict means CHECK_SECRETS_REQUIRE_IDENTIFIERS is set
# to anything but empty or 0: a typo makes the gate stricter, never quieter.
plant clean.txt 'an unrelated line of prose'
expect_run() {                                     # expect_run LABEL WANT_EXIT WANT_TEXT ENV_ASSIGNMENT...
  local label="$1" want_rc="$2" want_text="$3" out rc
  shift 3
  out="$(env "$@" "$ROOT/$GATE" "$TMP/clean.txt" 2>&1)"; rc=$?
  if [ "$rc" -eq "$want_rc" ] && { [ -z "$want_text" ] || printf '%s' "$out" | grep -qi -e "$want_text"; }; then
    printf '  ok      %s\n' "$label"; pass=$((pass+1))
  else
    printf '  \033[31mWRONG\033[0m  %s (exit %s, wanted %s)\n' "$label" "$rc" "$want_rc"; fail=$((fail+1))
  fi
}
expect_run "strict, no list: exit 2 and names the identifier list"     2 identifier CHECK_SECRETS_IDENT_FILE="$TMP/no-such-list" CHECK_SECRETS_REQUIRE_IDENTIFIERS=1
expect_run "strict, a list holding only comments: exit 2"              2 identifier CHECK_SECRETS_IDENT_FILE="$COMMENTS_ONLY"     CHECK_SECRETS_REQUIRE_IDENTIFIERS=1
expect_run "strict, any value but 0 or empty counts (yes)"             2 identifier CHECK_SECRETS_IDENT_FILE="$TMP/no-such-list" CHECK_SECRETS_REQUIRE_IDENTIFIERS=yes
expect_run "strict with a usable list: runs, passes a clean line"      0 ""         CHECK_SECRETS_IDENT_FILE="$IDENT"             CHECK_SECRETS_REQUIRE_IDENTIFIERS=1
expect_run "not strict, no list: skips, and says so on stderr"         0 skipped    CHECK_SECRETS_IDENT_FILE="$TMP/no-such-list" CHECK_SECRETS_REQUIRE_IDENTIFIERS=
expect_run "strict switch set to 0 means off"                          0 skipped    CHECK_SECRETS_IDENT_FILE="$TMP/no-such-list" CHECK_SECRETS_REQUIRE_IDENTIFIERS=0
expect_run "a list that is not a valid regex: exit 2, even not strict" 2 "not a valid" CHECK_SECRETS_IDENT_FILE="$BAD_REGEX"       CHECK_SECRETS_REQUIRE_IDENTIFIERS=

echo ""
echo "── the real tracked tree (MUST be clean) ──────────────────────────────"
if git ls-files | xargs "$GATE" >/dev/null 2>&1; then
  echo "  ok      $(git ls-files | wc -l | tr -d ' ') tracked files, no findings"
  pass=$((pass+1))
else
  echo "  FAILED  the gate flags the tracked tree:"
  git ls-files | xargs "$GATE" 2>&1 | sed 's/^/    /'
  fail=$((fail+1))
fi

echo ""
if [ "$fail" -eq 0 ]; then
  echo "SECRET-GATE TEST: ${pass} passed, 0 failed."
  exit 0
fi
echo "SECRET-GATE TEST: ${pass} passed, ${fail} FAILED."
echo "A 'LEAKED' line means the gate would let that credential into a public commit."
exit 1
