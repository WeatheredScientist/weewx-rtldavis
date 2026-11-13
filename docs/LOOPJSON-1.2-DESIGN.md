# loopjson 1.2.0: contract version, finite-only output, schema and checker

**Status:** Approved by the owner 2026-11-12 with Q1–Q4 as recommended (§9), and built on
`s201b-loopjson-1.2`. Not released or deployed; §6 is still the plan for both. Two additions made
while building, both stricter: the schema also refuses the proxy's four names, and the writer
refuses an extra whose key fails the schema's key pattern.
**Decision:** DEC-0234 (proposed) · **Implements:** DEC-0233 parts 5 to 7 · **Session:** S201b
(Opus 5.5), 2026-11-12 · **Contract:** 1.1 → 1.2 · **Extension:** `loopjson` 1.1.0 → 1.2.0

This is the design for the next loop-JSON writer release. It does four things:

1. It adds a key that states the contract version.
2. It guarantees the feed never carries NaN, infinity or `null`.
3. It ships a JSON Schema, a set of example files and a checker, all tied to the writer by tests.
4. It sets out how to release, deploy and roll back.

Every choice below says why. The open questions for the owner are in §9.

---

## 1. What exists today (measured, not assumed)

- **The writer** is `loop_json_writer.py` 1.1.0. It writes `json.dump(data, f)` with Python's
  defaults, and those defaults are not strict JSON:
  - `allow_nan=True` turns `float('nan')` into a bare `NaN` token.
  - `True` becomes `true`, a type the contract does not allow.
  - A packet without `dateTime` writes `"dateTime": null`.
  - A value of a type `json` cannot serialize (for example numpy's `int64`, which some SDR drivers
    produce) raises `TypeError`. The write then fails and the feed freezes, so the station looks
    offline after 30 s.
  - The writer serializes the payload twice, once for each file.
- **The rtldavis driver produces no NaN.** A grep of `rtldavis.py`, `pressure_service.py` and
  `dewpoint_service.py` found none. So the hazard comes from other drivers and from extras. That
  is the audience this contract is meant to serve.
- **Python's own parser is lax.** `json.loads('{"a":NaN,"b":1e400,"b":2}')` returns
  `{'a': nan, 'b': 2}`. It accepts NaN, silently replaces a duplicate key with the last value, and
  would turn `1e400` into infinity. A JSON Schema validator in Python gets the already-parsed
  value, and `nan` passes `"type": "number"`. **So a schema alone cannot enforce "finite": the
  parse has to be strict.** JavaScript's `JSON.parse` rejects `NaN`, but it also turns `1e400`
  into `Infinity`.
- **The only consumer of the feed is the dashboard.** HLF reads only SQLite. eaglehunt-ops only
  describes the feed. The dashboard reads it like this (S201b survey, read-only):
  - The proxy (`server.js:2045`) runs `JSON.parse`, and any parse failure returns a 503, which
    the browser shows as "station offline". **A bare `NaN` takes the whole feed down.**
  - The proxy passes every key through to the browser as `{...parsed, skyState, ongoingEvents,
    loop_cadence_s, stale_after_s}` (`:2070`). An unknown key is therefore harmless. A feed key
    with one of those four names, though, would be silently overwritten.
  - The browser picks keys by name and treats `null` and an absent key the same way.
  - Nobody reads `writer`. No schema library is used anywhere (the dashboard has no
    `package.json`; HLF has pydantic, not `jsonschema`).
- **Prod** mounts `<tenant root>/loop_json_writer.py`, which is a `dev` checkout at `694938f`. Its
  sha equals `dev`'s tip, and so does `influx.py`'s. `weewx_monitor.py` differs: `dev` carries
  S193's edit to comments and messages only (#567). The image does not bundle the writer
  (Dockerfile: only `influx.py` is installed as an extension), so this release needs no image.

## 2. Contract-version key (part 5)

**The key is `contract`, a JSON string `"MAJOR.MINOR"`.** For this release it is
`"contract": "1.2"`. The 1.2.0 writer puts it in every write of both files, next to `writer`.

**Why each choice:**

| Choice | Picked | Rejected, and why |
|---|---|---|
| Name | `contract` | `contract_version` is longer and no clearer. `schema_version` is wrong because the schema is one artifact of the contract, not the contract itself. `$schema` (a URL) would make consumers parse a URL to compare versions and tie the feed to GitHub hosting. `writer` already exists and names the implementation, and a non-WeeWX producer needs a version that does not pretend to be our writer (audit finding 12) |
| Type | string | A number fails at 1.10, which equals 1.1 as a number. A string compares by splitting on the dot |
| Parts | two, `MAJOR.MINOR` | The contract text has no patch level: INTERFACES' header says "1.1". A fix that brings behavior back to the text is a patch of a *producer*, which `writer` reports |
| Placement | top level, flat | §1 forbids nesting. Both files carry it, because `current.json` is the same content |

**What it means.** A producer that writes `"contract": "1.N"` claims to meet every rule of
contract 1.N as INTERFACES.md states it. The key is optional *for consumers*, because 1.0 and 1.1
writers never wrote it. It is **mandatory for any producer that claims 1.2 or later**: a producer
that omits it is read as 1.1. For the key table, Required is "optional (written by every 1.2+
producer)".

**How a consumer should treat versions.** This becomes a new rule in INTERFACES §1:

| `contract` in the file | Consumer does |
|---|---|
| absent | Treat the file as contract 1.1. It is what 1.0 and 1.1 writers produce, and 1.0's output is valid 1.1 |
| same major, any minor (older or newer than the consumer knows) | Read it. Use keys by *presence*, never by version: every key except `dateTime` is optional anyway, so "is `windGust10_mph` here?" is the right test, and "is contract ≥ 1.2?" is not. Ignore unknown keys |
| different major | Do not interpret the values. Fail closed with a message naming the version ("loop contract 2.0 not supported"). A major means a key changed meaning or units, so guessing would show wrong numbers, which is worse than showing none |
| present but malformed (not a string, or not `digits.digits`) | The file is invalid. Treat it like a parse failure |

**The forward-compatibility rule, stated for every surface.** A new §0 row: *"Unknown keys,
fields and columns are ignored. A consumer reads what it knows; that is what lets a minor version
add one without a consumer change."* INTERFACES' change discipline already assumes this. Nothing
states it yet, and the dashboard already behaves this way.

**Reserved names.** §1 gains a short list of names a producer must not use as feed keys:
`contract`, `writer`, `dateTime`, `loop_interval_s` and `barometer_fetch_epoch` (all stamped by
the writer), plus the four the reference proxy adds (`skyState`, `ongoingEvents`,
`loop_cadence_s`, `stale_after_s`). The writer refuses an `extra_fields` entry that maps to any of
them; it already does this for the first four. Reserving the proxy's names costs nothing, and it
closes the silent-overwrite case the survey found.

**`writer` and `contract`, side by side.** `writer` stays `loop_json_writer/<semver>`: it names
the implementation and its version. Our writer's version follows these rules:
- **Major:** the contract's major changes.
- **Minor:** the contract's minor changes, or the writer gains a config feature without a contract
  change.
- **Patch:** a fix.

So `loop_json_writer/1.2.0` writes contract `1.2`, but a later `1.3.0` might still write `1.2`.
The module holds two constants, `__version__ = '1.2.0'` and `CONTRACT = '1.2'`, and tests tie
`CONTRACT` to INTERFACES' header and to the schema (§5).

**InfluxDB and SQLite stay versioned by the document** (DEC-0233 part 5). There is no in-band key
to add there. A field or column cannot carry a version without becoming data.

## 3. Finite-only, strict output (part 6)

**Rule: a value the contract cannot carry is treated as absent, exactly like `None`.** That
covers NaN, ±infinity, and any value of a type other than a real number or (for extras) a string.
It does not enter the cache, so the last good value, if any, keeps being served until its TTL runs
out. Then it is omitted with the existing expiry WARNING.

**Omit, not `null`.** This is already decided in the spec: §0's absence rule ("omitted ... never
written as 0 or as a placeholder") and §1's "no `null`" both say so. Re-justified here:
- Omitting gives one way to say "absent". With `null` there would be two, and a consumer would
  have to handle both.
- The bounded cache already defines "absent this packet" as omit-after-TTL. A non-finite reading
  is a reading the sensor could not make, which is the same thing.
- The schema stays simple, with no `["number","null"]` type unions.
- The dashboard treats `null` and absent alike, so it would not notice the difference. Some other
  consumer might.

**Why not evict the cached value on NaN?** You could read a NaN as a firmer "invalid now" than
`None`. But WeeWX itself has no such distinction: `None` is its only missing marker. And a
driver's NaN means "no reading", not "the last reading was wrong". Treating both alike keeps one
rule, and the TTL already bounds how long a value can go stale. (Rejected; one line in the DEC.)

**How each value is cleaned, at cache-insert time** (one function, `_clean(value, out_key)`):

| Value from the packet (after `to_US`) | Written as |
|---|---|
| `int` (not `bool`), `float` that is finite | itself |
| `float` NaN / ±inf | absent |
| `bool` | `int` (0 or 1), the same value the archive and InfluxDB store. **Open question Q2** |
| any other object with `__index__` (numpy integers) | `int(value)` |
| any other object with `__float__` (numpy floats, `Decimal`) | `float(value)` if finite, else absent |
| `str` | itself for an extra. Absent for one of the 13 standard keys, which the contract types as numbers |
| anything else (`None` included, plus lists, dicts, bytes) | absent |

Every *non-`None`* value that comes out absent, whether non-finite, the wrong type or impossible
to convert, gets **one WARNING per key per run**:
`LoopJsonWriter: outTemp_F value nan is not finite, treated as missing`. It repeats at the next
recovery, like the expiry WARNING. If it logged on every packet, a driver that sends NaN every
2.5 s would flood the log.

**Where else non-finite values can enter, path by path:**

| Path | Can it produce a non-finite value? | Covered by |
|---|---|---|
| Driver packet values (13 standard keys and extras) | yes, from a third-party driver | `_clean` |
| `weewx.units.to_US` | only by carrying one through (inf × k = inf). It never makes one from finite input | `_clean` runs after `to_US` |
| `StdWXCalculate` derived values (`dewpoint`, `heatindex`, `windchill`, `cloudbase`) | WeeWX guards them with `None`. Any that slips through | `_clean` |
| Extras (`windGust10` and any opt-in) | yes, same as the driver | `_clean` |
| `loop_interval_s` | no: the median of finite monotonic gaps, range-checked | unchanged |
| `barometer_fetch_epoch` | not from `pressure_service`; maybe from another service | `_clean` (it bypasses the cache, not the cleaning) |
| `dateTime` | possibly `None`, a float, or a non-number from a broken driver | the `dateTime` rule below |
| `writer`, `contract` | constants | — |

**The `dateTime` rule.** Today's code can write `"dateTime": null`. In 1.2.0, if the packet's
`dateTime` is not a finite number, the writer **skips both writes for that packet** and logs an
ERROR, once until it recovers. Why skip and not fall back to the wall clock: a wall-clock
`dateTime` would claim the station is live when the packet is broken, and the liveness gate exists
to tell the truth. A finite non-integer is truncated with `int()`, because §0 says whole seconds.
The writer's internal clock (`now`, used for TTLs) keeps its existing fallback.

**`allow_nan=False` as the hard guard.** The payload is serialized **once** with
`json.dumps(data, allow_nan=False)`, and the same string is written to both files. Content
identical "when written" is now true by construction, and the work per packet halves. After
`_clean`, the guard should never fire. If it does (a future code path that skips `_clean`), it
raises `ValueError`. The writer then logs an ERROR naming the keys whose values are non-finite and
skips this packet's writes. Writing nothing for a packet makes the consumer see an older
`dateTime`, which is honest. Writing `NaN` makes the consumer answer 503 at once, which is
outright broken. A test bypasses `_clean` to prove the guard fires.

**Output bytes stay the same otherwise.** Key order and separators are unchanged. For this
station the only visible difference is the new `contract` key; the golden-output test proves that
(§5).

## 4. JSON Schema, examples, checker (part 7)

### 4.1 The schema

- **Where:** a new top-level directory, `contract/`. It is not under `docs/`, because these are
  executable artifacts a consumer downloads; it is not under `extensions/loopjson/`, because the
  contract covers producers that are not our writer. The file is
  `contract/loop-json.v1.schema.json`. MANIFEST gets one row for the directory.
- **Draft: 2020-12.** It is the current published dialect. Python `jsonschema` picks it from
  `$schema`, and ajv supports it via `ajv/dist/2020`. The schema uses only keywords that mean the
  same in draft-07 (`type`, `required`, `properties`, `patternProperties`,
  `additionalProperties`, `pattern`, `minimum`, `maximum`, `minLength`, `maxLength`), so a
  draft-07-only validator still works. No custom keywords, because ajv's strict mode rejects
  unknown ones; the version goes in `$comment` and `title`.
- **One schema per major.** Minors only add optional keys, and the generic extras rule accepts any
  well-formed key. So a v1 schema validates every 1.x file, older or newer, and each minor
  updates the same file. A 2.0 contract gets `loop-json.v2.schema.json`. The `$id` is
  `https://github.com/WeatheredScientist/weewx-rtldavis/contract/loop-json.v1.schema.json`, an
  identifier that need not resolve. The documented download URL is tag-pinned (§6).
- **Strictness:**

  | Part | Rule |
  |---|---|
  | top level | `type: object`, `required: ["dateTime"]`, `additionalProperties: false` |
  | `dateTime` | `integer`, `minimum: 0` |
  | `contract` | `string`, `pattern: ^1\.(0|[1-9][0-9]*)$`. A `2.x` file fails the v1 schema, which is correct |
  | `writer` | `string`, `pattern: ^\S+/\S+$` (`<name>/<version>`; a non-WeeWX producer names itself) |
  | `loop_interval_s` | `number`, 1 to 3600 (the writer omits it outside that range, DEC-0221) |
  | the 13 standard keys, `barometer_fetch_epoch` | `number` (the epoch: `integer`) |
  | extras: `patternProperties` `^[A-Za-z][A-Za-z0-9_]{0,63}$` | `number` or `string` |

- **Types, not ranges.** The schema says nothing about humidity ≤ 100 or wind direction ≤ 360.
  Ranges are value QC: they belong in drivers (#475, parked), and if the schema imposed them it
  could fail an honest calibrated station. The only bounds are the two the writer itself enforces.
- **What JSON Schema cannot see**, and so the checker must: NaN/Infinity tokens, numbers that
  overflow to infinity (`1e400`), duplicate keys, a byte-order mark, trailing data, staleness.
  The schema's `description` says so in one sentence, so a consumer using ajv knows the gap.

### 4.2 The checker: `contract/check_contract.py`

**One file, Python standard library only, Python ≥ 3.8.** You download it and run it. Nothing to
install, and it runs inside the WeeWX container, on a Pi, or in a consumer's CI (PRINCIPLES §6).

```
python3 check_contract.py loop feed/loop-data.txt     # a file
python3 check_contract.py loop -                      # stdin (marvinctl cat … | …)
python3 check_contract.py loop http://host/loop-data.txt
python3 check_contract.py loop --max-age 30 feed/loop-data.txt   # also check liveness
python3 check_contract.py influx-fields fields.txt    # one InfluxDB field name per line
```

- **The schema lives in one place.** The checker embeds the schema as a dict literal, and a test
  asserts that the dict equals `loop-json.v1.schema.json`. Its validator is about 60 lines and
  covers exactly the keywords listed in §4.1. **An unknown keyword raises an error instead of
  being ignored.** Without that, someone could add `oneOf` to the schema and the checker would
  silently ignore it (GOTCHAS §1: an interface that accepts an instruction and drops it).
- **Strict parse first:**
  - `parse_constant` rejects `NaN`, `Infinity` and `-Infinity`.
  - A `parse_float` hook rejects numbers that overflow to infinity.
  - `object_pairs_hook` rejects duplicate keys.
  - The top level must be an object, and a BOM or trailing data is an error.
- **Checks the schema cannot express:**
  - `contract`'s major must be 1. A different major is error `E-MAJOR`; an absent key is warning
    `W-NO-CONTRACT`, meaning a pre-1.2 producer.
  - With `--max-age`, `now - dateTime` must be within the limit (`E-STALE`). Without the option
    it only prints the age.
- **Output:** one line per finding, with a stable code (`E-PARSE-NAN`, `E-DUPLICATE-KEY`,
  `E-NULL`, `E-TYPE`, `E-REQUIRED`, `E-KEY-NAME`, `E-MAJOR`, `E-STALE`, `W-NO-CONTRACT`, …),
  then a summary such as `OK: contract 1.2, 16 keys, writer loop_json_writer/1.2.0, age 2 s`.
  Exit codes: 0 valid (warnings allowed), 1 invalid, 2 usage or read error.
- **`influx-fields`** carries out DEC-0233 part 7's "list of bucket field names". Input: the
  output of the documented Flux one-liner
  `import "influxdata/influxdb/schema" schema.fieldKeys(bucket: "weewx")`, or any one-per-line
  list. A small catalog embedded in the checker holds §2's contract fields, each with its US,
  METRIC and METRICWX suffix. The check reports:
  - each contract field as present or absent, by sensor class (absence is only information);
  - **errors** for one observation under two unit systems (`outTemp_F` and `outTemp_C`), and for
    a contract observation under a non-contract spelling (bare `outTemp`, the sign of
    `append_units_label` off), since consumers would not find either;
  - the seven diagnostics as "outside the contract", and unknown fields as information.

### 4.3 Example files, which double as a conformance suite

`contract/fixtures/loop/valid/*.json`, `contract/fixtures/loop/invalid/*`, and
`contract/fixtures/loop/expected.json`, which maps each file to its expected verdict, code and
level (`parse`, `schema` or `contract`). Consumers can run the whole set through *their own*
parser and check they accept and reject the same files. That is the quickest way for an adopter
to prove their reader is strict.

- **Valid:**
  - `minimal` (only `dateTime`);
  - `reference-1.1` (the INTERFACES example as it is, no `contract`: valid, with a warning);
  - `reference-1.2`;
  - `extras` (`windGust10_mph`, `luminosity_lux`, a bare string extra);
  - `calm` (`windSpeed_mph: 0`, cached `windDir`);
  - `future-minor` (`contract: "1.9"` plus an unknown key: valid, because consumers ignore
    unknown keys);
  - `integer-float-datetime` (`1794409271.0`: valid under JSON Schema's integer rule).
- **Invalid:**
  - `nan`, `infinity`, `neg-infinity`, `overflow-1e400`;
  - `null-value`, `missing-datetime`, `datetime-string`, `datetime-fraction`;
  - `nested-object`, `array-value`, `boolean-value`;
  - `contract-number`, `contract-major-2`, `contract-malformed`;
  - `standard-key-string` (`outTemp_F: "59"`), `bad-key-name`, `loop-interval-out-of-range`;
  - `duplicate-key`, `not-an-object`, `empty`, `truncated`, `bom`.
- `contract/fixtures/influx/` holds three field lists: this station's 36 fields, a metric station
  and a mixed (broken) one.

### 4.4 Tests that tie the parts together (pytest only, #502)

| Test | Fails when |
|---|---|
| **writer ↔ schema, adversarial:** drive the real `new_loop` with packets carrying NaN, ±inf, `bool`, numpy-like objects (stub classes with `__index__`/`__float__`), strings in standard keys, `None`, a float `dateTime`, no `dateTime`, a list; validate **every written file** with the checker and, where installed, `jsonschema` | the writer can emit anything the schema rejects |
| writer ↔ schema, names: every `_FIELDS` output key and reserved key the writer stamps is a schema property with the right type | a key is added to the writer without the schema |
| schema ↔ INTERFACES §1: the backticked keys in §1's Keys table and the relayed-barometer table equal the schema's `properties` | the doc and schema drift |
| `CONTRACT` ↔ INTERFACES header "Contract version: X.Y" ↔ the schema's `$comment` | the three disagree |
| checker's embedded schema == the JSON file | the copies drift |
| **checker ↔ `jsonschema`:** every fixture at schema level, plus the writer outputs above, get the same verdict from both. `jsonschema` is a CI-only test dependency (the `tests` job's pip line); locally the test skips without it unless `REQUIRE_JSONSCHEMA=1`, which CI sets (the `REQUIRE_REAL_WEEWX` pattern) | the hand-written validator disagrees with the reference implementation |
| fixtures ↔ `expected.json`: every fixture listed, every verdict and code matches | a fixture goes unchecked, or a code changes |
| validator rejects an unknown keyword; a planted NaN fixture is rejected (positive controls) | the checker goes quietly permissive |
| golden: the existing 1.0.0 golden sequence produces the same output with only `contract` added | 1.2.0 changes anything else |
| `_clean` table: each row of §3's table | |
| guard: monkeypatch `_clean` to pass NaN through, then assert ERROR logged, no file written, no `NaN` on disk | the hard guard is gone |
| `dateTime` rule: `None`, NaN and a string skip the write with one ERROR; `1000.7` writes `1000` | |
| reserved names: `extra_fields` mapping to any of the nine is refused | |
| influx catalog ↔ INTERFACES §2's contract table; the catalog's suffixes ↔ real WeeWX's unit labels (subprocess with real WeeWX, as `test_loop_json_extra_names.py` does) | the catalog drifts from the doc or from WeeWX |

**End-to-end:** `scripts/prove_loopjson.sh` already runs the Simulator on a real WeeWX 5.5.2 with
the zip installed. It gains one line: `python3 contract/check_contract.py loop` on both output
files must exit 0 and print `contract 1.2`. **`loopjson.yml` also runs the checker over the
fixtures under Python 3.9** (`actions/setup-python`), so the "Python ≥ 3.8" claim is measured on
an old interpreter, not asserted.

## 5. Ease of use: from zero to a validated feed in minutes

- **`contract/README.md`**, the adopter's page, short:
  1. What the three surfaces are, with one link to INTERFACES.md.
  2. "Check your feed", two commands: `curl -LO` the checker from the release, then run it on
     your file.
  3. "Check your reader": run `fixtures/` through your parser.
  4. A Python and a JavaScript reader of about ten lines each: parse strictly, check `contract`'s
     major, use keys by presence, apply the liveness rule `max(30, 3 × loop_interval_s)`.
  5. Using your own validator (ajv, `jsonschema`), plus the one-paragraph caveat that Python's
     `json` accepts NaN unless you pass `parse_constant`.
- **INTERFACES §1** gains a three-line "Validate" paragraph that points at `contract/`, and the
  `contract` key row, the version table and the reserved names.
- **The extension README** gains a "Check your feed" section with the tag-pinned checker URL.
- **The release** carries `check_contract.py` and `loop-json.v1.schema.json` as assets beside the
  zip, so each has a stable versioned URL.

## 6. Rollout

**Version bumps.**
- Contract: 1.1 → 1.2, a minor (a new optional key).
- `loopjson`: 1.1.0 → 1.2.0, a minor (the contract minor plus behavior fixes).
- No image change: the image does not bundle the writer. DEC-0222's image SemVer is untouched, and
  the next image (already a minor, for DEC-0232) is unrelated.

**Build, one PR to `dev`** (feature branch `s201b-loopjson-1.2`, opened with `land`):
- `loop_json_writer.py` (1.2.0, `CONTRACT`, `_clean`, the `dateTime` rule, a single
  serialization, the reserved names; the startup INFO line gains `1.2.0 (contract 1.2)` so a log
  grep proves which code runs);
- `extensions/loopjson/install.py` and `README.md`;
- `contract/` (schema, checker, fixtures, README);
- tests;
- `ci.yml` (`jsonschema` in the tests job, `REQUIRE_JSONSCHEMA=1`);
- `loopjson.yml` (the Python 3.9 checker run, release assets);
- `scripts/prove_loopjson.sh`;
- INTERFACES.md (header 1.2, Versioning, §0 forward-compatibility row, §1 changes; Appendix A
  untouched);
- the DEC, CHANGELOG, MANIFEST.

**Release** (owner's go): tag `loopjson-v1.2.0` on the merge commit on `dev`, push the tag, and
`loopjson.yml` publishes the zip and both assets with `--latest=false`. Then test an install from
the asset URL on a clean station, as was done for 1.0.0.

**Prod deploy** (the writer is a mount; S171's proven path):
1. **Before:** read the tenant checkout's HEAD (`marvinctl cat .git/refs/heads/dev`) and diff the
   mounted files against `dev`'s tip. Measured today: the only other mounted file that would
   change is `weewx_monitor.py`, comments and messages only. **Its daemon reads it only at start,
   so the pull changes its bytes but not what runs** until the next monitor restart (Q4).
2. `marvinctl --tenant weewx pull`.
3. `marvinctl --tenant weewx restart weewx.service`.

**Verify, all read-only, in this order:**
1. The mounted writer's sha (`marvinctl sha /srv/docker/weewx/loop_json_writer.py`) equals
   `dev`'s.
2. The unit started after the file's mtime.
3. The log after the restart has `LoopJsonWriter 1.2.0 (contract 1.2)` and no traceback.
4. `marvinctl cat /srv/docker/weewx/weewx-data/feed/loop-data.txt | python3
   contract/check_contract.py loop --max-age 30 -` exits 0 and prints `contract 1.2`. The same
   for `current.json` without `--max-age`. **Not the dashboard proxy's `/loopdata`:** the proxy
   adds its own keys, including the nested `ongoingEvents`, so its output is not the feed.
5. The next archive record lands (`grep Added`), and the dashboard shows live data with no 503.
6. The key set equals the pre-deploy set plus `contract`.

**Rollback.** The writer is one mounted file, so rollback puts 1.1.0's bytes back and restarts.
The fast path is owner-run, because the tenant key cannot write files:
`git -C /srv/docker/weewx checkout 694938f -- loop_json_writer.py`, then
`marvinctl restart weewx.service`. The tracked path is a revert PR on `dev`, then `pull` and
`restart`. Neither needs an image. Consumers need nothing either way, because `contract` is
optional and 1.1.0 never wrote it.

## 7. Risks

| Risk | Mitigation |
|---|---|
| A writer bug freezes the feed (the station looks offline) | `_clean` cannot raise: every branch is wrapped, and a failure makes that one key absent. The test suite drives adversarial packets. Rollback is one file and needs no image |
| The hand-written validator disagrees with real JSON Schema | Tested against `jsonschema` on every fixture and writer output in CI; unknown keywords raise |
| A dependency creeps into the image | The checker is stdlib-only and the image is untouched. `jsonschema` is a CI test dependency only |
| The proxy's reserved names collide with a future feed key | Reserved in §1 and refused by the writer |
| `pull` carries other `dev` changes to prod | The step-1 diff: today only a monitor change to comments and messages, inert until its restart |

## 8. Not in this release

- Range or plausibility checks (#475).
- A station tag (DEC-0053).
- Renaming the diagnostics.
- CumulusMX code.
- An SQLite mode for the checker (Q3).
- Wiring the checker into the image's `doctor`: a baked change, for a later image.

## 9. Open questions for the owner

- **Q1. Key name.** `contract` (recommended) or `contract_version`?
- **Q2. Booleans.** Convert to 0/1, the archive's own encoding (recommended), or treat them as
  absent? No driver we know of puts a `bool` in a loop packet, so this decides only the
  third-party case.
- **Q3. SQLite mode for the checker.** It would check `usUnits` and `interval` consistency,
  `journal_mode`, and the §3 columns. It is useful for a non-Davis producer, but it is not in
  DEC-0233 part 7. The recommendation is a later minor of the checker, outside this release.
- **Q4. The monitor's bytes ride the pull.** Leave the running monitor as it is (recommended: the
  change is comments and messages only), or restart it deliberately and verify it (sha, start
  after mtime, the `Remedy armed:` line) in the same window?

## 10. Implementation plan (after approval)

1. `contract/loop-json.v1.schema.json`, then `check_contract.py` (validator, strict parse,
   `loop`, `influx-fields`), then the fixtures and `expected.json`. Checker tests first: the
   positive controls must go red before green.
2. Writer: `CONTRACT`, `_clean`, the `dateTime` rule, a single serialization with
   `allow_nan=False`, the reserved names, the startup line, 1.2.0. Tests: the adversarial
   sequence, the guard, the golden test, the `_clean` table.
3. Tie tests: schema ↔ INTERFACES, `CONTRACT` ↔ header, embedded ↔ file, checker ↔ `jsonschema`,
   the influx catalog ↔ §2 and real WeeWX.
4. CI: `ci.yml`, `loopjson.yml` (Python 3.9, assets), `prove_loopjson.sh`.
5. Docs: INTERFACES.md to 1.2, `contract/README.md`, the extension README, MANIFEST row (checked
   with ops' `manifest-coverage-sweep.sh`).
6. Gates (ruff, pytest, mypy with new files staged, secret gate with the identifier file copied
   in and a positive control). Then pause for the owner's approval of the commit, then `land`.
   The merge, the tag push and the prod deploy are the owner's go, each.

---

## Appendix: the S197 cross-repo drift issue (draft, not posted)

Kept out of this public file on purpose. The draft text is in the session's shared notes, and it
goes to `eaglehunt-ops` only on the owner's go (BOOT job 0a).
