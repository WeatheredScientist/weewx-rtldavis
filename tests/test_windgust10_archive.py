"""DEC-0232: the ISS's 10-minute gust (windGust10) gets a SQLite archive column.

A new install's archive is created from `user.rtldavis.schema` (wview_extended plus the
column); an existing one takes it with `weectl database add-column windGust10`. The real-WeeWX
test below proves the two routes give the same archive column and daily summary, that a US
record stores mph, and that the day table follows. `ops/backfill_windgust10.py` copies the
InfluxDB history into NULL cells only; `ops/windgust10_check.sql` reads the result.
"""
import ast
import json
import os
import re
import sqlite3
import subprocess
import sys

import pytest

import backfill_windgust10 as bf
import rtldavis
import weewx.schemas.wview_extended as wv  # the conftest stand-in

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKERFILE = os.path.join(ROOT, 'Dockerfile')
CONF_EXAMPLE = os.path.join(ROOT, 'weewx.conf.example')
CHECK_SQL = os.path.join(ROOT, 'ops', 'windgust10_check.sql')
DRIVER = os.path.join(ROOT, 'rtldavis.py')

# A Flux CSV answer as the proxy returns it: CRLF, a header, one result table.
FLUX_CSV = (
    ',result,table,_time,_value\r\n'
    ',_result,0,2026-10-28T16:30:00Z,2\r\n'
    ',_result,0,2026-10-28T16:31:00Z,13.000000000000002\r\n'
    ',_result,0,2026-10-28T16:33:00Z,4.5\r\n'
    '\r\n'
)
T0 = 1793205000  # 2026-10-28 16:30:00 UTC, the first record with windGust10


# --- the schema ---------------------------------------------------------------------------

def test_schema_is_wview_extended_plus_one_column():
    assert rtldavis.schema['table'] == wv.table + [('windGust10', 'REAL')]


def test_schema_adds_a_scalar_day_summary():
    assert rtldavis.schema['day_summaries'] == wv.day_summaries + [('windGust10', 'scalar')]


def test_schema_does_not_change_wview_extended_itself():
    assert ('windGust10', 'REAL') not in wv.table


def test_unit_group_is_speed():
    assert rtldavis.obs_group_dict['windGust10'] == 'group_speed'


def _dockerfile():
    with open(DOCKERFILE) as f:
        return f.read()


def test_dockerfile_points_the_starter_config_at_the_schema_and_asserts_it():
    text = _dockerfile()
    assert 'schema = user.rtldavis.schema|' in text
    assert re.search(r"grep -q '\^\[\[:space:\]\]\*schema = user\\\.rtldavis\\\.schema\$'", text)
    assert 'FATAL: the archive schema line did not change' in text


def test_schema_edit_comes_before_the_pristine_copy():
    """seed_config.py copies /opt/weewx-dist into an empty mount; it must carry the edit."""
    text = _dockerfile()
    assert text.index('schema = user.rtldavis.schema|') < text.index(
        'cp -a /opt/weewx-data /opt/weewx-dist')


def test_example_config_names_the_schema():
    with open(CONF_EXAMPLE) as f:
        text = f.read()
    assert re.search(r'^\s*schema = user\.rtldavis\.schema$', text, re.M)
    assert 'schema = weewx.schemas.wview_extended.schema' not in text


# --- the InfluxDB backfill -------------------------------------------------------------------

def test_parse_points_reads_proxy_csv():
    assert bf.parse_points(FLUX_CSV) == [
        (T0, 2.0), (T0 + 60, 13.000000000000002), (T0 + 180, 4.5)]


def test_parse_points_handles_annotations_and_repeated_tables():
    text = ('#datatype,string,long,dateTime:RFC3339,double\r\n'
            ',result,table,_time,_value\r\n,_result,0,2026-10-28T16:30:00Z,2\r\n\r\n'
            ',result,table,_time,_value\r\n,_result,1,2026-10-28T16:31:00Z,3\r\n')
    assert bf.parse_points(text) == [(T0, 2.0), (T0 + 60, 3.0)]


@pytest.mark.parametrize('value', ['nan', 'inf', '-1', '201'])
def test_parse_points_refuses_an_implausible_value(value):
    with pytest.raises(ValueError):
        bf.parse_points(',result,table,_time,_value\n,_result,0,2026-10-28T16:30:00Z,%s\n' % value)


def test_parse_points_refuses_a_csv_without_time_and_value():
    with pytest.raises(ValueError):
        bf.parse_points(',result,table,_start,_stop\n,_result,0,a,b\n')


def test_parse_points_refuses_two_values_at_one_time():
    with pytest.raises(ValueError):
        bf.parse_points(',result,table,_time,_value\n'
                        ',_result,0,2026-10-28T16:30:00Z,2\n,_result,0,2026-10-28T16:30:00Z,3\n')


def _archive(path, with_column=True, us_units=1):
    con = sqlite3.connect(path)
    col = ', windGust10 REAL' if with_column else ''
    con.execute('CREATE TABLE archive (dateTime INTEGER NOT NULL PRIMARY KEY, '
                'usUnits INTEGER NOT NULL, `interval` INTEGER NOT NULL, windGust REAL, '
                'windSpeed REAL%s)' % col)
    con.executemany('INSERT INTO archive (dateTime, usUnits, `interval`) VALUES (?, ?, 1)',
                    [(T0 + 60 * i, us_units) for i in range(5)])
    con.commit()
    return con


def _apply(con, sql):
    """Run the generated SQL as the sqlite3 shell would, minus its dot-commands."""
    con.executescript('\n'.join(line for line in sql.splitlines() if not line.startswith('.')))


def _gusts(con):
    return dict(con.execute('SELECT dateTime, windGust10 FROM archive'))


def test_backfill_fills_null_cells_only(tmp_path):
    con = _archive(str(tmp_path / 'a.sdb'))
    con.execute('UPDATE archive SET windGust10 = 9 WHERE dateTime = ?', (T0 + 60,))
    con.commit()
    _apply(con, bf.build_sql(bf.parse_points(FLUX_CSV), 'test'))
    assert _gusts(con) == {T0: 2.0, T0 + 60: 9.0, T0 + 120: None, T0 + 180: 4.5, T0 + 240: None}


def test_backfill_inserts_no_row(tmp_path):
    con = _archive(str(tmp_path / 'a.sdb'))
    sql = bf.build_sql([(T0 + 3600, 5.0)], 'test')
    _apply(con, sql)
    assert con.execute('SELECT COUNT(*) FROM archive').fetchone()[0] == 5
    assert all(v is None for v in _gusts(con).values())


def test_backfill_sets_nothing_in_a_metric_archive(tmp_path):
    con = _archive(str(tmp_path / 'a.sdb'), us_units=16)
    _apply(con, bf.build_sql(bf.parse_points(FLUX_CSV), 'test'))
    assert all(v is None for v in _gusts(con).values())


def test_backfill_fails_and_commits_nothing_without_the_column(tmp_path):
    path = str(tmp_path / 'a.sdb')
    con = _archive(path, with_column=False)
    with pytest.raises(sqlite3.OperationalError, match='windGust10'):
        _apply(con, bf.build_sql(bf.parse_points(FLUX_CSV), 'test'))
    con.close()
    assert sqlite3.connect(path).execute('SELECT COUNT(*) FROM archive').fetchone()[0] == 5


def test_backfill_sql_runs_in_one_transaction_and_bails_on_error():
    sql = bf.build_sql([(T0, 2.0)], 'test')
    lines = sql.splitlines()
    assert '.bail on' in lines and '.timeout 30000' in lines
    assert lines.index('BEGIN;') < lines.index('COMMIT;')
    assert all(line.startswith('UPDATE archive SET windGust10 = ') for line in lines
               if line.startswith('UPDATE'))


def test_flux_query_reads_the_one_field_in_the_archive_series():
    q = bf.flux_query('weewx', bf.DEFAULT_START, 'now()')
    assert 'r._field == "windGust10_mph"' in q
    assert 'r.binding == "archive"' in q and 'r._measurement == "record"' in q


def test_main_writes_sql_from_a_saved_csv(tmp_path):
    src, out = tmp_path / 'in.csv', tmp_path / 'out.sql'
    src.write_text(FLUX_CSV)
    assert bf.main(['--csv', str(src), '--out', str(out)]) == 0
    assert out.read_text().count('UPDATE archive') == 3


def test_main_refuses_an_empty_answer(tmp_path):
    src = tmp_path / 'in.csv'
    src.write_text(',result,table,_time,_value\r\n')
    assert bf.main(['--csv', str(src), '--out', str(tmp_path / 'o.sql')]) == 1
    assert not (tmp_path / 'o.sql').exists()


def test_check_sql_runs_read_only(tmp_path):
    con = _archive(str(tmp_path / 'a.sdb'))
    con.execute('CREATE TABLE archive_day_windGust10 (dateTime INTEGER PRIMARY KEY, max REAL, '
                'count INTEGER)')
    with open(CHECK_SQL) as f:
        body = [line for line in f.read().splitlines() if not line.startswith('.')]
    for stmt in body:
        if stmt.startswith('SELECT'):
            con.execute(stmt).fetchall()
        else:
            assert stmt.startswith('--') or not stmt.strip(), stmt


def _field_map(name):
    # Read by AST: backfill_container imports configobj, which a bare venv may lack.
    with open(os.path.join(ROOT, 'ops', name)) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'FIELD_MAP' for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError('%s defines no FIELD_MAP' % name)


@pytest.mark.parametrize('name', ['backfill_influx.py', 'backfill_container.py'])
def test_influx_backfill_carries_windgust10(name):
    assert _field_map(name)['windGust10'] == 'windGust10_mph'


# --- against real WeeWX ---------------------------------------------------------------------

_REAL = r'''
import importlib.util, json, os, sys, tempfile
import weewx.manager, weewx.units, weewx.schemas.wview_extended as wv
spec = importlib.util.spec_from_file_location("rtldavis", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
d = tempfile.mkdtemp()
def db(name):
    return {"database_name": os.path.join(d, name), "driver": "weedb.sqlite"}
def shape(dbd):
    m = weewx.manager.DaySummaryManager.open(dbd)
    cols = m.connection.columnsOf("archive")
    tables = sorted(m.connection.tables())
    m.close()
    return cols, tables
new = weewx.manager.DaySummaryManager.open_with_create(db("new.sdb"), schema=mod.schema)
new.close()
old = weewx.manager.DaySummaryManager.open_with_create(db("old.sdb"), schema=wv.schema)
old.add_column("windGust10")
old.close()
m = weewx.manager.DaySummaryManager.open(db("old.sdb"))
t0 = 1793205000
for i, g in enumerate([4.0, 13.0, None, 6.0]):
    m.addRecord({"dateTime": t0 + 60 * i, "usUnits": weewx.US, "interval": 1,
                 "windSpeed": 2.0, "windGust10": g})
stored = list(m.genSql("SELECT windGust10 FROM archive ORDER BY dateTime"))
day = list(m.genSql("SELECT max, count FROM archive_day_windGust10"))
m.close()
print(json.dumps({"new": shape(db("new.sdb")), "old": shape(db("old.sdb")),
                  "stored": [r[0] for r in stored], "day": [list(r) for r in day],
                  "unit": list(weewx.units.getStandardUnitType(weewx.US, "windGust10")),
                  "extractor": __import__("weewx.accum").accum.DEFAULTS_INI}))
'''


def _python_with_weewx():
    for exe in (sys.executable, os.environ.get('WEEWX_TEST_PYTHON')):
        if exe and subprocess.run([exe, '-I', '-c', 'import weewx.manager'],
                                  capture_output=True).returncode == 0:
            return exe
    return None


def test_both_routes_give_the_same_archive_against_real_weewx(tmp_path):
    exe = _python_with_weewx()
    if exe is None:
        if os.environ.get('REQUIRE_REAL_WEEWX') == '1':
            pytest.fail('REQUIRE_REAL_WEEWX=1 but no Python with weewx was found')
        pytest.skip('real weewx not installed (set WEEWX_TEST_PYTHON to run this locally)')
    r = subprocess.run([exe, '-I', '-c', _REAL, DRIVER], capture_output=True, text=True,
                       cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout.strip().splitlines()[-1])
    new_cols, new_tables = got['new']
    old_cols, old_tables = got['old']
    # The image's schema and the prod route (add-column on wview_extended) agree.
    assert 'windGust10' in new_cols and new_cols == old_cols
    assert 'archive_day_windGust10' in new_tables and new_tables == old_tables
    # A US record stores mph as given; a minute without message 9 stays NULL, never 0.
    assert got['stored'] == [4.0, 13.0, None, 6.0]
    assert got['day'] == [[13.0, 3]]
    assert got['unit'] == ['mile_per_hour', 'group_speed']
    # WeeWX's stock extractor is `last`, the value InfluxDB already holds (DEC-0224).
    assert re.search(r'\[\[windGust10\]\]\s*extractor = last', got['extractor'])
