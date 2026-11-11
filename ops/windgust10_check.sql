-- Read-only check of the archive's windGust10 column (DEC-0232). Feed it to the sqlite3 shell
-- with -readonly; docs/WINDGUST10-MIGRATION.md has the exact command. Changes nothing.
.timeout 30000
.headers on
.mode list
SELECT 'column' AS check_name, COUNT(*) AS present FROM pragma_table_info('archive') WHERE name = 'windGust10';
SELECT 'day table' AS check_name, COUNT(*) AS present FROM sqlite_master WHERE type = 'table' AND name = 'archive_day_windGust10';
SELECT datetime(dateTime, 'unixepoch', 'localtime') AS record, windGust10, windGust, windSpeed FROM archive ORDER BY dateTime DESC LIMIT 10;
SELECT COUNT(*) AS rows_last_24h, COUNT(windGust10) AS with_windGust10 FROM archive WHERE dateTime > (SELECT MAX(dateTime) FROM archive) - 86400;
SELECT COUNT(*) AS rows_since_2026_10_28_1630Z, COUNT(windGust10) AS with_windGust10 FROM archive WHERE dateTime >= 1793205000;
SELECT date(dateTime, 'unixepoch', 'localtime') AS day, max AS max_windGust10, count FROM archive_day_windGust10 ORDER BY dateTime DESC LIMIT 16;
