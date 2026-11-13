#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""check_contract.py: check a feed against the weewx-rtldavis data contract.

One file, Python 3.8 or later, standard library only. Download it and run it:

    python3 check_contract.py loop loop-data.txt          # a file
    python3 check_contract.py loop -                      # stdin
    python3 check_contract.py loop http://host/loop-data.txt
    python3 check_contract.py loop --max-age 30 loop-data.txt   # also check liveness
    python3 check_contract.py influx-fields fields.txt    # InfluxDB field names

The contract is docs/INTERFACES.md in
https://github.com/WeatheredScientist/weewx-rtldavis (DEC-0233, DEC-0234).

`loop` parses strictly first (NaN, Infinity, numbers that overflow to infinity, duplicate
keys, a byte-order mark and trailing data are all errors, though Python's own json module
accepts most of them), then validates against the v1 JSON Schema, then checks what a schema
cannot express: the contract's major version and, with --max-age, staleness.

`influx-fields` reads one InfluxDB field name per line (or the annotated CSV that
`schema.fieldKeys()` returns) and reports the contract fields found, an observation stored
under two unit systems, and an observation stored without its unit label.

Each finding is one line: a stable code, a path, a message. Codes starting E- are errors,
W- warnings, I- information. Exit status: 0 valid (warnings allowed), 1 invalid, 2 usage or
read error.
"""
import argparse
import collections
import json
import math
import re
import sys
import time

CHECKER_VERSION = '1.0.0'
# The newest contract this checker knows. Any 1.x file is read; see INTERFACES §1.
CONTRACT = '1.2'
SUPPORTED_MAJOR = 1

Finding = collections.namedtuple('Finding', 'code level path message')


class SchemaError(Exception):
    """The schema uses something this validator does not implement."""


# --- the v1 schema --------------------------------------------------------------------
# A copy of contract/loop-json.v1.schema.json, kept here so this file runs on its own.
# tests/test_contract_checker.py fails if the two differ.
SCHEMA_V1 = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': 'https://github.com/WeatheredScientist/weewx-rtldavis/contract/'
           'loop-json.v1.schema.json',
    '$comment': 'Loop-JSON contract 1.2, docs/INTERFACES.md section 1. One schema per '
                'major version: it validates every 1.x file.',
    'title': 'weewx-rtldavis loop-JSON file, contract 1.x',
    'description': 'Types only, not ranges. JSON Schema cannot see NaN or Infinity tokens, '
                   'numbers that overflow to infinity, duplicate keys, a byte-order mark, '
                   'trailing data or staleness: parse strictly, or run '
                   'contract/check_contract.py. Four names are reserved for consumers\' '
                   'proxies and never appear in a feed: skyState, ongoingEvents, '
                   'loop_cadence_s, stale_after_s.',
    'type': 'object',
    'required': ['dateTime'],
    'additionalProperties': False,
    'properties': {
        'dateTime': {'type': 'integer', 'minimum': 0},
        'contract': {'type': 'string', 'pattern': '^1\\.(0|[1-9][0-9]*)$'},
        'writer': {'type': 'string', 'pattern': '^\\S+/\\S+$'},
        'loop_interval_s': {'type': 'number', 'minimum': 1, 'maximum': 3600},
        'barometer_fetch_epoch': {'type': 'integer', 'minimum': 0},
        'windSpeed_mph': {'type': 'number'},
        'windGust_mph': {'type': 'number'},
        'windDir': {'type': 'number'},
        'outTemp_F': {'type': 'number'},
        'dewpoint_F': {'type': 'number'},
        'outHumidity': {'type': 'number'},
        'heatindex_F': {'type': 'number'},
        'windchill_F': {'type': 'number'},
        'barometer_inHg': {'type': 'number'},
        'rainRate_inch_per_hour': {'type': 'number'},
        'radiation_Wpm2': {'type': 'number'},
        'UV': {'type': 'number'},
        'cloudbase_foot': {'type': 'number'},
    },
    'patternProperties': {
        '^(?!(skyState|ongoingEvents|loop_cadence_s|stale_after_s)$)'
        '[A-Za-z][A-Za-z0-9_]{0,63}$': {'type': ['number', 'string']},
    },
}


# --- a small JSON Schema validator ----------------------------------------------------
# It implements exactly the keywords below. Any other keyword raises SchemaError instead
# of being ignored, so a schema change this code does not understand cannot pass silently.
_ANNOTATIONS = frozenset(['$schema', '$id', '$comment', 'title', 'description'])
_KEYWORDS = frozenset(['type', 'required', 'properties', 'patternProperties',
                       'additionalProperties', 'pattern', 'minimum', 'maximum',
                       'minLength', 'maxLength'])


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _type_ok(name, v):
    if name == 'number':
        return _is_number(v)
    if name == 'integer':
        return _is_number(v) and (isinstance(v, int) or float(v).is_integer())
    if name == 'string':
        return isinstance(v, str)
    if name == 'object':
        return isinstance(v, dict)
    if name == 'array':
        return isinstance(v, list)
    if name == 'boolean':
        return isinstance(v, bool)
    if name == 'null':
        return v is None
    raise SchemaError('unknown type %r' % name)


def _ptr(path, key):
    return '%s/%s' % (path, str(key).replace('~', '~0').replace('/', '~1'))


def validate(schema, instance, path=''):
    """Validate instance against schema; return a list of schema-level Findings."""
    unknown = set(schema) - _ANNOTATIONS - _KEYWORDS
    if unknown:
        raise SchemaError('unsupported keyword(s): %s' % ', '.join(sorted(unknown)))
    out = []
    shown = path or '/'
    if 'type' in schema:
        types = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        if not any(_type_ok(t, instance) for t in types):
            code = 'E-NULL' if instance is None else 'E-TYPE'
            out.append(Finding(code, 'schema', shown, '%s is not %s' % (
                json.dumps(instance), ' or '.join(types))))
            return out
    if isinstance(instance, dict):
        for key in schema.get('required', []):
            if key not in instance:
                out.append(Finding('E-REQUIRED', 'schema', _ptr(path, key),
                                   '%s is required' % key))
        props = schema.get('properties', {})
        patterns = schema.get('patternProperties', {})
        extra = schema.get('additionalProperties', True)
        for key, value in instance.items():
            matched = False
            if key in props:
                matched = True
                out.extend(validate(props[key], value, _ptr(path, key)))
            for pattern, sub in patterns.items():
                if re.search(pattern, key):
                    matched = True
                    out.extend(validate(sub, value, _ptr(path, key)))
            if not matched:
                if extra is False:
                    out.append(Finding('E-KEY-NAME', 'schema', _ptr(path, key),
                                       'key %s is not allowed' % json.dumps(key)))
                elif isinstance(extra, dict):
                    out.extend(validate(extra, value, _ptr(path, key)))
    if isinstance(instance, str):
        if 'pattern' in schema and not re.search(schema['pattern'], instance):
            out.append(Finding('E-PATTERN', 'schema', shown, '%s does not match %s' % (
                json.dumps(instance), schema['pattern'])))
        if 'minLength' in schema and len(instance) < schema['minLength']:
            out.append(Finding('E-RANGE', 'schema', shown, 'shorter than %d'
                               % schema['minLength']))
        if 'maxLength' in schema and len(instance) > schema['maxLength']:
            out.append(Finding('E-RANGE', 'schema', shown, 'longer than %d'
                               % schema['maxLength']))
    if _is_number(instance):
        if 'minimum' in schema and instance < schema['minimum']:
            out.append(Finding('E-RANGE', 'schema', shown, '%s is below %s' % (
                instance, schema['minimum'])))
        if 'maximum' in schema and instance > schema['maximum']:
            out.append(Finding('E-RANGE', 'schema', shown, '%s is above %s' % (
                instance, schema['maximum'])))
    return out


# --- strict parse -----------------------------------------------------------------------

class _ParseError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code


def _reject_constant(name):
    raise _ParseError('E-PARSE-NAN', '%s is not a JSON number' % name)


def _parse_float(text):
    value = float(text)
    if math.isinf(value):
        raise _ParseError('E-PARSE-OVERFLOW', '%s overflows to infinity' % text[:40])
    return value


def _parse_int(text):
    try:
        value = int(text)
    except ValueError:  # Python 3.11+ refuses very long digit strings
        raise _ParseError('E-PARSE-OVERFLOW', 'integer of %d digits' % len(text))
    if abs(value) > sys.float_info.max:
        raise _ParseError('E-PARSE-OVERFLOW', '%s... overflows to infinity' % text[:20])
    return value


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise _ParseError('E-DUPLICATE-KEY', 'key %s appears twice' % json.dumps(key))
        out[key] = value
    return out


def parse_strict(raw):
    """Parse bytes (or str) as strict JSON. Return (object or None, [Finding])."""
    if isinstance(raw, str):
        raw = raw.encode('utf-8')
    if raw.startswith(b'\xef\xbb\xbf'):
        return None, [Finding('E-BOM', 'parse', '', 'starts with a byte-order mark')]
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        return None, [Finding('E-PARSE', 'parse', '', 'not UTF-8: %s' % e)]
    if not text.strip():
        return None, [Finding('E-PARSE', 'parse', '', 'empty')]
    try:
        obj = json.loads(text, parse_constant=_reject_constant, parse_float=_parse_float,
                         parse_int=_parse_int, object_pairs_hook=_pairs)
    except _ParseError as e:
        return None, [Finding(e.code, 'parse', '', str(e))]
    except ValueError as e:  # json.JSONDecodeError, trailing data included
        return None, [Finding('E-PARSE', 'parse', '', str(e))]
    if not isinstance(obj, dict):
        return None, [Finding('E-NOT-OBJECT', 'parse', '',
                              'top level is %s, not an object' % type(obj).__name__)]
    return obj, []


# --- loop ---------------------------------------------------------------------------------

_VERSION = re.compile(r'^([0-9]+)\.([0-9]+)$')

Result = collections.namedtuple('Result', 'findings summary status')


def _errors(findings):
    return [f for f in findings if f.code.startswith('E-')]


def check_loop(raw, now=None, max_age=None, schema=None):
    """Check one loop-JSON document. Return Result(findings, summary line, exit status)."""
    schema = SCHEMA_V1 if schema is None else schema
    obj, findings = parse_strict(raw)
    if obj is None:
        return Result(findings, 'INVALID: does not parse', 1)
    contract = obj.get('contract')
    m = _VERSION.match(contract) if isinstance(contract, str) else None
    if m and int(m.group(1)) != SUPPORTED_MAJOR:
        findings.append(Finding('E-MAJOR', 'contract', '/contract',
                                'loop contract %s not supported; this checker reads %d.x'
                                % (contract, SUPPORTED_MAJOR)))
        return Result(findings, 'INVALID: contract %s' % contract, 1)
    seen = set()
    for f in validate(schema, obj):
        # a key matched by both properties and patternProperties can fail both the same way
        if (f.code, f.path) not in seen:
            seen.add((f.code, f.path))
            findings.append(f)
    if 'contract' not in obj:
        findings.append(Finding('W-NO-CONTRACT', 'contract', '/contract',
                                'no contract key: a pre-1.2 producer, read as 1.1'))
    age = None
    stamp = obj.get('dateTime')
    if _is_number(stamp):
        age = (time.time() if now is None else now) - stamp
        if max_age is not None and age > max_age:
            findings.append(Finding('E-STALE', 'contract', '/dateTime',
                                    'dateTime is %.0f s old, over --max-age %s'
                                    % (age, max_age)))
    errors = _errors(findings)
    if errors:
        return Result(findings, 'INVALID: %d error%s' % (
            len(errors), '' if len(errors) == 1 else 's'), 1)
    parts = ['contract %s' % contract if 'contract' in obj
             else 'contract absent (read as 1.1)',
             '%d key%s' % (len(obj), '' if len(obj) == 1 else 's')]
    if 'writer' in obj:
        parts.append('writer %s' % obj['writer'])
    if age is not None:
        parts.append('age %.0f s' % age)
    return Result(findings, 'OK: ' + ', '.join(parts), 0)


# --- influx-fields ------------------------------------------------------------------------
# INTERFACES §2's contract fields: observation -> (class, label by unit system). A label of
# None means the field is the bare observation name. Labels follow influx.py's rule; a test
# checks them against real WeeWX's unit registry.
_SYSTEMS = ('US', 'METRIC', 'METRICWX')
_T = ('F', 'C', 'C')
_SPEED = ('mph', 'kph', 'mps')
_RAIN = ('in', 'cm', 'mm')
_PRESS = ('inHg', 'mbar', 'mbar')
_BARE = (None, None, None)
INFLUX_CONTRACT = {
    'outTemp': ('thermo-hygro', _T),
    'dewpoint': ('thermo-hygro', _T),
    'heatindex': ('thermo-hygro', _T),
    'windchill': ('thermo-hygro', _T),
    'outHumidity': ('thermo-hygro', _BARE),
    'windSpeed': ('wind', _SPEED),
    'windGust': ('wind', _SPEED),
    'windDir': ('wind', _BARE),
    'windGust10': ('wind', _SPEED),
    'barometer': ('barometer', _PRESS),
    'rain': ('rain', _RAIN),
    'rainRate': ('rain', ('inch_per_hour', 'cm_per_hour', 'mm_per_hour')),
    'dayRain': ('rain', _RAIN),
    'ET': ('ET', _RAIN),
    'radiation': ('solar', ('Wpm2', 'Wpm2', 'Wpm2')),
    'UV': ('UV', _BARE),
    'cloudbase': ('derived', ('foot', 'meter', 'meter')),
}
# §2's "written, optional" tier: information only.
INFLUX_OPTIONAL = {
    'altimeter': _PRESS, 'appTemp': _T, 'hourRain': _RAIN, 'humidex': _T,
    'maxSolarRad': ('Wpm2', 'Wpm2', 'Wpm2'), 'pressure': _PRESS, 'rain24': _RAIN,
    'rxCheckPercent': _BARE, 'txBatteryStatus': _BARE, 'windGustDir': _BARE,
    'windrun': ('mile', 'km', 'km'), 'barometer_fetch_epoch': _BARE,
}
# §2's "outside the contract" tier: this driver's diagnostics under borrowed names.
INFLUX_DIAGNOSTICS = frozenset([
    'consBatteryVoltage_hertz', 'hail_hertz', 'hailRate_hertz', 'heatingTemp_hertz',
    'heatingVoltage_hertz', 'supplyVoltage_volt', 'referenceVoltage_volt'])


def _spelling(obs, label):
    return obs if label is None else '%s_%s' % (obs, label)


def _spellings(obs, labels):
    """{field name: set of unit systems that spell obs that way}."""
    out = collections.defaultdict(set)
    for system, label in zip(_SYSTEMS, labels):
        out[_spelling(obs, label)].add(system)
    return out


def read_field_names(text):
    """Field names from one-per-line text, or from annotated CSV with a _value column."""
    names = []
    col = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ',' in line:
            cells = [c.strip() for c in line.split(',')]
            if col is None:
                if '_value' in cells:
                    col = cells.index('_value')
                continue
            if col < len(cells) and cells[col]:
                names.append(cells[col])
            continue
        names.append(line)
    return names


def check_influx_fields(text):
    """Check a list of InfluxDB field names. Return Result."""
    names = read_field_names(text)
    if not names:
        return Result([Finding('E-EMPTY', 'contract', '', 'no field names')],
                      'INVALID: no field names', 1)
    present = set(names)
    findings = []
    systems = None
    found = 0
    for obs, (cls, labels) in INFLUX_CONTRACT.items():
        spell = _spellings(obs, labels)
        hits = sorted(n for n in spell if n in present)
        if len(hits) > 1:
            findings.append(Finding('E-MIXED-UNITS', 'contract', obs,
                                    '%s is stored as %s; one bucket holds one unit system'
                                    % (obs, ' and '.join(hits))))
        if obs in present and obs not in spell:
            findings.append(Finding('E-NO-UNIT-LABEL', 'contract', obs,
                                    'bare %s: consumers look for %s (is append_units_label '
                                    'off?)' % (obs, ' or '.join(sorted(spell)))))
        if hits:
            found += 1
            findings.append(Finding('I-PRESENT', 'contract', obs,
                                    '%s (%s)' % (', '.join(hits), cls)))
            these = set()
            for h in hits:
                these |= spell[h]
            systems = these if systems is None else systems & these
        elif obs not in present:
            findings.append(Finding('I-ABSENT', 'contract', obs,
                                    'no field (%s sensor class)' % cls))
    known = set()
    for obs, (_cls, labels) in INFLUX_CONTRACT.items():
        known |= set(_spellings(obs, labels)) | {obs}
    for obs, labels in INFLUX_OPTIONAL.items():
        for name in _spellings(obs, labels):
            known.add(name)
            if name in present:
                findings.append(Finding('I-OPTIONAL', 'contract', name,
                                        'written, optional (INTERFACES §2)'))
    for name in sorted(present & INFLUX_DIAGNOSTICS):
        findings.append(Finding('I-DIAGNOSTIC', 'contract', name,
                                'outside the contract: a driver diagnostic'))
    known |= INFLUX_DIAGNOSTICS
    for name in sorted(present - known):
        findings.append(Finding('I-UNKNOWN', 'contract', name, 'not in the contract'))
    if systems is not None and not systems:
        findings.append(Finding('W-SYSTEMS', 'contract', '',
                                'contract fields come from more than one unit system'))
    errors = _errors(findings)
    if errors:
        return Result(findings, 'INVALID: %d error%s' % (
            len(errors), '' if len(errors) == 1 else 's'), 1)
    unit = ' or '.join(s for s in _SYSTEMS if s in systems) if systems else 'unknown'
    return Result(findings, 'OK: %d of %d contract fields, unit system %s'
                  % (found, len(INFLUX_CONTRACT), unit), 0)


# --- command line -------------------------------------------------------------------------

def _read(source):
    if source == '-':
        return sys.stdin.buffer.read()
    if source.startswith(('http://', 'https://')):
        import urllib.request
        with urllib.request.urlopen(source, timeout=10) as resp:  # noqa: S310
            return resp.read()
    with open(source, 'rb') as f:
        return f.read()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='check_contract.py',
        description='Check a feed against the weewx-rtldavis data contract %s '
                    '(checker %s).' % (CONTRACT, CHECKER_VERSION))
    sub = parser.add_subparsers(dest='command')
    loop = sub.add_parser('loop', help='check a loop-JSON file (path, - or URL)')
    loop.add_argument('source')
    loop.add_argument('--max-age', type=float, default=None,
                      help='fail when dateTime is older than this many seconds')
    loop.add_argument('--now', type=float, default=None, help=argparse.SUPPRESS)
    fields = sub.add_parser('influx-fields', help='check InfluxDB field names (path or -)')
    fields.add_argument('source')
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        raw = _read(args.source)
    except Exception as e:  # any read failure is a usage-level error, not a verdict
        print('E-READ %s: %s' % (args.source, e), file=sys.stderr)
        return 2
    if args.command == 'loop':
        result = check_loop(raw, now=args.now, max_age=args.max_age)
    else:
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as e:
            print('E-READ %s: not UTF-8: %s' % (args.source, e), file=sys.stderr)
            return 2
        result = check_influx_fields(text)
    for f in result.findings:
        print('%s %s: %s' % (f.code, f.path or '/', f.message))
    print(result.summary)
    return result.status


if __name__ == '__main__':
    sys.exit(main())
