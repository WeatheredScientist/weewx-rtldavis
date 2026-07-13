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
# This file is the ONE file check_secrets.sh exempts (by exact path) — its job is
# to contain secret-shaped strings. None of the values below is real.
set -u
cd "$(dirname "$0")/.." || exit 2
GATE="scripts/check_secrets.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

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
  'token = deadbeef123456  # falls back to os.environ'           # (hole 8)
  'password = hunter2hunter2  # comes from config_dict'          # (hole 9)
  'api_key = liveKey1234567  # replace with YOUR_API_KEY'        # (hole 10)
  "token = tok_abc123456  # see cfg.get('token')"                # (hole 11)
  'secret = s3cr3tvalue123  # ${NOT_ACTUALLY_INTERPOLATED}'      # (hole 12)
)

# --- must PASS (exit zero) ------------------------------------------------------
good=(
  'api_key = YOUR_API_KEY_HERE'                                  # placeholder
  'token = "${INFLUX_TOKEN}"'                                    # interpolation
  "password = os.environ.get('WEEWX_PW')"                        # runtime lookup
  'api_key = ""'                                                 # empty
  'token = None'                                                 # empty
  'self.api_key = api_key'                                       # self-assign
  'token = INFLUX_TOKEN'                                         # ALL_CAPS underscored REFERENCE
  "api_key = config_dict.get('api_key')"                         # config plumbing
  "password = stn_dict.get('password')"                          # config plumbing
  '# api_key = abc123def456xyz'                                  # comment-only line
  '// const token = "tok_abc12345";'                             # comment-only line (JS)
  ' * api_key: the upload credential'                            # JSDoc continuation
  'key: WeatherCloud upload key'                                 # multi-word prose
  '"description": "set api_key = abc123def456 here"'             # description in KEY position
)

echo "── planted BAD payloads (each MUST be caught) ──────────────────────────"
i=0
for payload in "${bad[@]}"; do
  i=$((i+1))
  case "$payload" in *const*|*//*|*/\**) ext=js ;; *) ext=py ;; esac
  f="$TMP/bad_$i.$ext"
  printf '%s\n' "$payload" > "$f"
  if "$GATE" "$f" >/dev/null 2>&1; then
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
  if "$GATE" "$f" >/dev/null 2>&1; then
    printf '  ok      %s\n' "$payload"; pass=$((pass+1))
  else
    printf '  \033[31mFALSE POSITIVE\033[0m  %s\n' "$payload"; fail=$((fail+1))
  fi
done

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
