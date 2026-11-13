#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run contract/check_contract.py over every fixture with the given interpreter and
# compare each verdict with contract/fixtures/*/expected.json (DEC-0234). loopjson.yml
# runs it in python:3.8-slim, so "Python 3.8+, standard library only" is measured.
# The expected.json files are read by the CURRENT python3, never by the one under test.
# Usage: scripts/check_contract_fixtures.sh [python]
set -euo pipefail
py=${1:-python3}
here=$(cd "$(dirname "$0")/.." && pwd)
"$py" -I -c 'import sys; assert sys.version_info >= (3, 8), sys.version'
"$py" --version
python3 - "$py" "$here" <<'PY'
import json, os, subprocess, sys
py, root = sys.argv[1], sys.argv[2]
checker = os.path.join(root, 'contract', 'check_contract.py')
fails = 0
for kind, cmd in (('loop', ['loop', '--now', '1794409280']), ('influx', ['influx-fields'])):
    base = os.path.join(root, 'contract', 'fixtures', kind)
    expected = json.load(open(os.path.join(base, 'expected.json')))
    for name, want in sorted(expected.items()):
        r = subprocess.run([py, '-I', checker] + cmd + [os.path.join(base, name)],
                           capture_output=True, text=True)
        status = 0 if want['valid'] else 1
        codes = [line.split()[0] for line in r.stdout.splitlines() if line.startswith('E-')]
        ok = r.returncode == status and (want['valid'] or
                                         codes == ([want['code']] if 'code' in want
                                                   else want['codes']))
        if not ok:
            fails += 1
            print('FAIL %s/%s: exit %d, codes %s' % (kind, name, r.returncode, codes))
            print(r.stdout + r.stderr)
print('%d fixtures checked, %d failed' % (sum(
    len(json.load(open(os.path.join(root, 'contract', 'fixtures', k, 'expected.json'))))
    for k in ('loop', 'influx')), fails))
sys.exit(1 if fails else 0)
PY
