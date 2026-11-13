# The data contract, machine-checkable

The contract itself is [docs/INTERFACES.md](../docs/INTERFACES.md): three surfaces, the loop-JSON
file (§1), the InfluxDB bucket (§2) and the SQLite archive (§3). This directory makes the loop file
checkable, for a producer proving its feed and for a consumer proving its reader (DEC-0234).

| File | What it is |
|---|---|
| `loop-json.v1.schema.json` | JSON Schema (draft 2020-12, draft-07-compatible keywords only) for every 1.x loop file. Types, not ranges |
| `check_contract.py` | The checker. One file, Python 3.8 or later, standard library only |
| `fixtures/loop/` | Valid and invalid loop files, with each one's expected verdict in `expected.json` |
| `fixtures/influx/` | InfluxDB field lists: this station, a metric station, a broken one |

Each release (`loopjson-vX.Y.Z`) also carries `check_contract.py` and the schema as assets, so
both have a stable URL pinned to that version.

## Check your feed

```
curl -LO https://github.com/WeatheredScientist/weewx-rtldavis/releases/download/loopjson-v1.2.0/check_contract.py
python3 check_contract.py loop --max-age 30 loop-data.txt
```

The source can be a path, `-` for stdin, or an `http(s)://` URL. Output is one line per finding,
then a summary:

```
OK: contract 1.2, 17 keys, writer loop_json_writer/1.2.0, age 2 s
```

Exit 0 means valid (warnings allowed), 1 invalid, 2 a usage or read error. Codes are stable:
`E-PARSE`, `E-PARSE-NAN`, `E-PARSE-OVERFLOW`, `E-DUPLICATE-KEY`, `E-BOM`, `E-NOT-OBJECT` (parse);
`E-REQUIRED`, `E-TYPE`, `E-NULL`, `E-KEY-NAME`, `E-PATTERN`, `E-RANGE` (schema); `E-MAJOR`,
`E-STALE`, `W-NO-CONTRACT` (contract). Without `--max-age` the age is only printed;
`current.json` is a snapshot, so check it without `--max-age`.

For InfluxDB, list the bucket's field names, one per line, or pass the annotated CSV that
`influx query 'import "influxdata/influxdb/schema" schema.fieldKeys(bucket: "weewx")' --raw`
prints:

```
python3 check_contract.py influx-fields fields.txt
```

It reports each contract field as present or absent, and fails on an observation stored under two
unit systems (`outTemp_F` and `outTemp_C`) or without its unit label (bare `outTemp`), since
consumers would find neither.

## Check your reader

Run every file in `fixtures/loop/` through your own parser. It should accept every file under
`valid/` and reject every file under `invalid/`. `expected.json` gives the reason for each (its
code and whether it fails at parse, schema or contract level). If your reader accepts `nan.json`,
`overflow-1e400.json` or `duplicate-key.json`, it is parsing laxly.

## A strict reader in ten lines

Python. Its `json` module accepts `NaN`, `Infinity` and duplicate keys unless told not to:

```python
import json, time

def no_constant(name):
    raise ValueError(name + ' is not a JSON number')

def no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate key')
    return dict(pairs)

feed = json.loads(text, parse_constant=no_constant, object_pairs_hook=no_duplicates)
if feed.get('contract', '1.1').split('.')[0] != '1':
    raise ValueError('loop contract %s not supported' % feed['contract'])
stale = time.time() - feed['dateTime'] > max(30, 3 * feed.get('loop_interval_s', 0))
temperature = feed.get('outTemp_F')          # by presence: None when absent
```

JavaScript. `JSON.parse` rejects `NaN` but turns `1e400` into `Infinity`, and keeps the last of
duplicate keys:

```javascript
const feed = JSON.parse(text);
for (const v of Object.values(feed)) {
  if (typeof v === 'number' && !Number.isFinite(v)) throw new Error('non-finite value');
}
const major = String(feed.contract ?? '1.1').split('.')[0];
if (major !== '1') throw new Error(`loop contract ${feed.contract} not supported`);
const ageS = Date.now() / 1000 - feed.dateTime;
const stale = ageS > Math.max(30, 3 * (feed.loop_interval_s ?? 0));
const temperature = feed.outTemp_F;          // by presence: undefined when absent
```

Use keys by presence, never by version: every key except `dateTime` is optional, and a newer minor
version only adds keys. Ignore keys you do not know.

## Using your own validator

The schema works with any draft 2020-12 or draft-07 validator (ajv: `ajv/dist/2020`; Python:
`jsonschema`). A schema validator only sees the already-parsed value, so it cannot catch `NaN`,
overflow, duplicate keys, a byte-order mark, trailing data or staleness: parse strictly first, as
above, or run the checker.

The schema has one file per contract major. A minor version adds optional keys, which the schema's
key pattern already accepts, so `v1` validates every 1.x file. A file whose `contract` names
another major fails it, on purpose.
