#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""weewx monitor: USB watchdog + service downtime alerting + reception tracking"""

import time, smtplib, os, sys, re
from email.mime.text import MIMEText
from datetime import datetime

# --- Config ---
# Paths default to the NAS layout but are env-overridable for parity with the
# credentials, which already come from env (S24 L-D).
BASE_DIR = os.environ.get('WEEWX_RTLDAVIS_DIR', '/volume1/docker/weewx-rtldavis')
LOG      = os.environ.get('MONITOR_LOG', f'{BASE_DIR}/logs/weewx_monitor.log')
PIDFILE  = os.environ.get('MONITOR_PIDFILE', f'{BASE_DIR}/logs/weewx_monitor.pid')
POLL     = 30
RESET_CD = 300
REPEAT   = 7200
STATION_NAME = os.environ.get('STATION_NAME', 'My PWS')  # Set in monitor.env or edit here

GMAIL_USER = os.environ.get('ALERT_FROM', '')
GMAIL_PASS = os.environ.get('GMAIL_PASS', '')
ALERT_TO   = os.environ.get('ALERT_TO', '')

THRESHOLDS = {
    'Wunderground-RF': 600,
    'PWSWeather':      3600,
    'CWOP':            3600,
    'WOW':             3600,
    'AWEKAS':          3600,
    'windy':           3600,
    'WeatherCloud':    1800,
    'owm':             3600,
}

# --- Reception tracking config ---
WU_RF_EXPECTED     = 24    # expected WU-RF posts per 60s window (one per ~2.5s)
WU_RF_MIN_PCT      = 60    # alert threshold % (normal baseline is 65-75% at 150ft through walls)
WU_RF_WINDOW       = 60    # seconds per reception window
WU_RF_SUSTAIN      = 5     # consecutive bad windows before alert
WU_RF_LOG_INTERVAL = 300   # log reception summary every 5 min

# Every WeeWX "Published record ..." line ends in "(<unix_epoch>)". The driver
# publishes freqError freq-hop channel packets as extra dataless loop packets, so
# each real reading is posted to WU several times under the SAME epoch (DEC-0024).
WU_RECORD_RE = re.compile(r'\((\d+)\)\s*$')

# --- PID guard ---
# '--test-alert' bypasses the guard entirely: it sends one test email and exits,
# and must NOT touch the running monitor's pidfile.
_TEST_ALERT = '--test-alert' in sys.argv
if not _TEST_ALERT:
    if os.path.exists(PIDFILE):
        old = open(PIDFILE).read().strip()
        if old and os.path.exists(f'/proc/{old}'):
            print(f'Already running (PID {old}), exiting')
            sys.exit(0)
    with open(PIDFILE, 'w') as f:
        f.write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.remove(PIDFILE) if os.path.exists(PIDFILE) else None)

# --- Helpers ---
def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    with open(LOG, 'a') as f:
        f.write(line + '\n')
        f.flush()

def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = ALERT_TO
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.send_message(msg)
        log(f"EMAIL sent: {subject}")
    except Exception as e:
        log(f"EMAIL error: {e}")

WEEWX_LOG_PATH = os.environ.get('WEEWX_LOG', f'{BASE_DIR}/logs/weewx.log')

def get_log_size():
    """Current size of the weewx log in bytes (0 if missing). The caller compares
    this to the last byte-offset to detect rotation/truncation (file shrank)."""
    try:
        return os.path.getsize(WEEWX_LOG_PATH)
    except OSError:
        return 0

def get_new_lines(offset):
    """Read complete lines appended since byte OFFSET in a SINGLE open -- no
    whole-file re-scan (M-A) and no separate size/read double-open race (L-B);
    both used to re-read the growing 10 MB/day log twice per poll (DEC-0024).

    Returns (lines, new_offset). A trailing partial line (still being written, no
    final newline) is held back and new_offset stops before it, so it is parsed
    once, whole, on a later poll -- never split or double-counted. Rotation is the
    caller's job (get_log_size() < offset -> reset offset to 0)."""
    try:
        with open(WEEWX_LOG_PATH, 'rb') as f:
            f.seek(offset)
            data = f.read()
    except OSError:
        return [], offset
    consumed = data.rfind(b'\n') + 1          # bytes up to and including last '\n'
    if consumed == 0:                          # no complete line yet
        return [], offset
    lines = data[:consumed].decode('utf-8', 'replace').splitlines()
    return lines, offset + consumed

# --- Rain-counter glitch alert (DEC-0021) ---
# rtldavis.py logs this exact phrase when it rejects an implausible rain-counter
# delta -- an RF-decode glitch that, before the fix, would have become phantom
# rain. Watching for it turns each catch into an email: confirmation the filter
# earned its keep, plus a running record of how often the glitch actually fires.
RAIN_GLITCH_MARKER = 'rejecting implausible counter delta'
RAIN_GLITCH_CD     = 300   # seconds between glitch emails (dedupe a repeated line)

def parse_rain_glitch(line):
    """If LINE is a rain-glitch rejection, return (timestamp, detail, phantom_in);
    else None. phantom_in = the false rainfall (inches) the OLD buggy code would
    have recorded, for context in the alert."""
    if RAIN_GLITCH_MARKER not in line:
        return None
    m = re.search(r'last=(\S+)\s+new=(\S+)', line)
    detail = m.group(0) if m else '(counter values unparsed)'
    phantom_in = None
    if m:
        try:
            old = int(m.group(2)) - int(m.group(1))   # what the buggy code saw
            if old < 0:
                old += 128                             # its unconditional wraparound add
            phantom_in = round(old * 0.01, 2)          # bucket_type 0 = 0.01 in/tip
        except ValueError:
            pass
    ts = line[:19] if (len(line) >= 19 and line[4:5] == '-') else \
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return ts, detail, phantom_in

def send_rain_glitch_alert(ts, detail, phantom_in, raw_line, test=False):
    tag = '[TEST] ' if test else ''
    body = (f"{tag}At {ts}, the rtldavis driver rejected an implausible "
            f"rain-counter delta ({detail}).\n\n"
            f"No phantom rain was recorded -- the DEC-0021 filter caught it.\n")
    if phantom_in is not None:
        body += f"Before the fix this would have logged a false +{phantom_in}\" of rain.\n"
    if test:
        body += "\nThis is a TEST of the rain-glitch email alert. If you got it, alerting works."
    else:
        body += f"\nLog line:\n{raw_line}"
    send_email(f"{STATION_NAME}: {tag}rain-counter glitch rejected", body)

def do_reset():
    try:
        log("RESET: running usb_reset.sh via sudo")
        import subprocess
        result = subprocess.run(
            ['sudo', '/volume1/docker/weewx-rtldavis/usb_reset.sh'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            try:
                vendor = open('/sys/bus/usb/devices/1-3/idVendor').read().strip()
            except OSError:
                vendor = 'unknown'
            log(f"RESET: done, idVendor={vendor}")
            send_email(f"{STATION_NAME}: RTL-SDR reset", f"Dongle reset at {datetime.now()}. Vendor: {vendor}")
        else:
            log(f"RESET error: {result.stderr}")
            send_email(f"{STATION_NAME}: RTL-SDR reset FAILED", f"usb_reset.sh failed: {result.stderr}")
    except Exception as e:
        log(f"RESET error: {e}")

def reset_dongle(last_reset):
    now = time.time()
    if now - last_reset < RESET_CD:
        log(f"SKIP reset: cooldown ({int(now-last_reset)}s)")
        return last_reset
    log("RESET: triggering syno_vbus_reset")
    import threading
    t = threading.Thread(target=do_reset, daemon=True)
    t.start()
    return time.time()

def format_daily_summary(hourly_buckets, date_str):
    """Format 24-hour reception summary as a text table."""
    lines = [
        f"{STATION_NAME} — RF Reception Summary for {date_str}",
        f"Expected: {WU_RF_EXPECTED} posts/min  |  Alert threshold: {WU_RF_MIN_PCT}%",
        "",
        f"{'Hour':<8} {'Posts/min':>10} {'Reception':>10} {'Status':>8}",
        "-" * 42,
    ]
    day_counts = []
    for hour in range(24):
        buckets = hourly_buckets.get(hour, [])
        if buckets:
            avg_count = sum(buckets) / len(buckets)
            avg_pct = (avg_count / WU_RF_EXPECTED) * 100
            day_counts.extend(buckets)
            status = "OK" if avg_pct >= WU_RF_MIN_PCT else "LOW"
            lines.append(f"{hour:02d}:00    {avg_count:>10.1f} {avg_pct:>9.0f}% {status:>8}")
        else:
            lines.append(f"{hour:02d}:00    {'--':>10} {'--':>9}  {'--':>8}")
    lines.append("-" * 42)
    if day_counts:
        day_avg = (sum(day_counts) / len(day_counts) / WU_RF_EXPECTED) * 100
        lines.append(f"{'Daily avg':<8} {'':>10} {day_avg:>9.0f}%")
    return "\n".join(lines)

def wu_record_key(line):
    """Dedup key for a 'Wunderground-RF ... Published' line — the record epoch.

    The driver publishes freqError freq-hop channel packets as extra dataless
    loop packets, so each real reading is posted to WU several times under the
    SAME record epoch (DEC-0024, S21). Counting raw publish lines over-reads
    reception (~1.66x, up to 2x), which is why the RF summary showed ~150%.
    Collapsing on this key — the trailing "(<unix_epoch>)" WeeWX stamps on every
    'Published record' line — counts unique records for a true reception %. Falls
    back to the whole line if the epoch can't be parsed (rare); that still dedups
    identical lines. Two real records in the same integer second collapse to one
    (a conservative under-count, accepted per DEC-0024).
    """
    m = WU_RECORD_RE.search(line)
    return m.group(1) if m else line

def close_reception_window(wu_window_count, wu_period_counts, wu_bad_windows,
                            wu_in_alert, wu_alert_sent_at, wu_repeat_sent_at,
                            wu_hourly_buckets, now):
    """Close a 60s reception window. Returns updated state tuple."""
    try:
        pct = (wu_window_count / WU_RF_EXPECTED) * 100
        wu_period_counts.append(wu_window_count)
        log(f"WINDOW: {wu_window_count}/{WU_RF_EXPECTED} ({pct:.0f}%)")

        # Store in hourly bucket
        hour = datetime.now().hour
        wu_hourly_buckets.setdefault(hour, []).append(wu_window_count)

        if pct < WU_RF_MIN_PCT:
            wu_bad_windows += 1
        else:
            if wu_in_alert:
                wu_in_alert = False
                td = int(now - wu_alert_sent_at)
                avg = (sum(wu_period_counts) / len(wu_period_counts) / WU_RF_EXPECTED) * 100
                log(f"RECEPTION RECOVERY: {avg:.0f}% avg after {td//60}min")
                send_email(
                    f"{STATION_NAME}: RF reception RECOVERED",
                    f"WU-RF reception recovered after {td//60}min.\n"
                    f"Current window: {wu_window_count}/{WU_RF_EXPECTED} ({pct:.0f}%)\n"
                    f"Recovered at: {datetime.now()}"
                )
            wu_bad_windows = 0

        if wu_bad_windows >= WU_RF_SUSTAIN and not wu_in_alert:
            wu_in_alert = True
            wu_alert_sent_at = now
            wu_repeat_sent_at = now
            avg = (sum(wu_period_counts[-WU_RF_SUSTAIN:]) / (WU_RF_SUSTAIN * WU_RF_EXPECTED)) * 100
            log(f"RECEPTION ALERT: {wu_bad_windows} consecutive windows below {WU_RF_MIN_PCT}%, avg {avg:.0f}%")
            send_email(
                f"{STATION_NAME}: RF reception LOW",
                f"WU-RF reception below {WU_RF_MIN_PCT}% for {wu_bad_windows} consecutive minutes.\n"
                f"Average over last {wu_bad_windows} windows: {avg:.0f}%\n"
                f"Alert time: {datetime.now()}"
            )
        elif wu_in_alert and (now - wu_repeat_sent_at) >= REPEAT:
            wu_repeat_sent_at = now
            avg = (sum(wu_period_counts[-WU_RF_SUSTAIN:]) / (WU_RF_SUSTAIN * WU_RF_EXPECTED)) * 100
            td = int(now - wu_alert_sent_at)
            log(f"RECEPTION REPEAT: still low {avg:.0f}% after {td//60}min")
            send_email(
                f"{STATION_NAME}: RF reception STILL LOW",
                f"WU-RF reception still below {WU_RF_MIN_PCT}% — ongoing for {td//60}min.\n"
                f"Average over last {wu_bad_windows} windows: {avg:.0f}%\n"
                f"As of: {datetime.now()}"
            )
    except Exception as e:
        log(f"RECEPTION WINDOW ERROR: {e}")

    return wu_period_counts, wu_bad_windows, wu_in_alert, wu_alert_sent_at, wu_repeat_sent_at, wu_hourly_buckets

# --- Main ---
def main():
    last_seen   = {s: 0.0 for s in THRESHOLDS}
    alert_sent  = {s: 0.0 for s in THRESHOLDS}
    last_repeat = {s: 0.0 for s in THRESHOLDS}
    in_outage   = {s: False for s in THRESHOLDS}
    last_reset  = 0.0
    last_glitch_alert = 0.0

    # Reception tracking state
    wu_window_start   = time.time()
    wu_window_epochs  = set()   # unique record epochs seen this window (DEC-0024)
    wu_period_counts  = []
    wu_period_start   = time.time()
    wu_bad_windows    = 0
    wu_in_alert       = False
    wu_alert_sent_at  = 0.0
    wu_repeat_sent_at = 0.0
    wu_first_seen     = False
    wu_hourly_buckets = {}
    wu_current_date   = datetime.now().date()

    log("Monitor started")
    send_email(f"{STATION_NAME}: monitor started", f"Started at {datetime.now()}")

    last_offset = get_log_size()
    log(f"Starting at log byte-offset {last_offset}")

    while True:
        time.sleep(POLL)
        now = time.time()

        cur = get_log_size()
        if cur < last_offset:
            log(f"Log reset detected (was {last_offset} bytes, now {cur}) - container restarted")
            last_offset = 0
            for svc in last_seen:
                last_seen[svc] = 0.0
            for svc in in_outage:
                in_outage[svc] = False
            wu_window_start  = now
            wu_window_epochs = set()
            wu_period_counts = []
            wu_period_start  = now
            wu_bad_windows   = 0
            wu_first_seen    = False

        if cur > last_offset:
            lines, last_offset = get_new_lines(last_offset)
            if lines:
                log(f"Poll: {len(lines)} new lines")
            for line in lines:
                if 'rtldavis process stalled' in line:
                    log("STALL detected")
                    last_reset = reset_dongle(last_reset)
                g = parse_rain_glitch(line)
                if g and now - last_glitch_alert > RAIN_GLITCH_CD:
                    ts, detail, phantom_in = g
                    last_glitch_alert = now
                    log(f"RAIN GLITCH rejected: {detail}")
                    send_rain_glitch_alert(ts, detail, phantom_in, line)
                for svc in THRESHOLDS:
                    if svc in line and ('Published' in line or 'published' in line):
                        if in_outage[svc]:
                            td = int(time.time() - alert_sent[svc])
                            in_outage[svc] = False
                            log(f"RECOVERY: {svc} after {td//60}min")
                            send_email(f"{STATION_NAME}: {svc} RECOVERED",
                                       f"{svc} recovered after {td//60}min at {datetime.now()}")
                        last_seen[svc] = time.time()
                if 'Wunderground-RF' in line and 'Published' in line:
                    wu_window_epochs.add(wu_record_key(line))
                    wu_first_seen = True
            # last_offset already advanced by get_new_lines() above.


        # --- Reception: close window every 60s ---
        if wu_first_seen and (now - wu_window_start) >= WU_RF_WINDOW:
            (wu_period_counts, wu_bad_windows, wu_in_alert,
             wu_alert_sent_at, wu_repeat_sent_at,
             wu_hourly_buckets) = close_reception_window(
                len(wu_window_epochs), wu_period_counts, wu_bad_windows,
                wu_in_alert, wu_alert_sent_at, wu_repeat_sent_at,
                wu_hourly_buckets, now)
            wu_window_start = wu_window_start + WU_RF_WINDOW
            wu_window_epochs = set()

        # --- Reception: log 5-min summary ---
        if wu_first_seen and (now - wu_period_start) >= WU_RF_LOG_INTERVAL:
            if wu_period_counts:
                avg = (sum(wu_period_counts) / len(wu_period_counts) / WU_RF_EXPECTED) * 100
                maintained = "OK" if avg >= WU_RF_MIN_PCT else "LOW"
                log(f"RECEPTION: {avg:.0f}% avg over last {len(wu_period_counts)} windows "
                    f"[{maintained}] (bad windows: {wu_bad_windows})")
            wu_period_counts = []
            wu_period_start  = now

        # --- Daily summary at midnight ---
        today = datetime.now().date()
        if today != wu_current_date:
            if wu_hourly_buckets:
                summary = format_daily_summary(wu_hourly_buckets, str(wu_current_date))
                log(f"DAILY SUMMARY: sending for {wu_current_date}")
                send_email(f"{STATION_NAME}: Daily RF Reception — {wu_current_date}", summary)
            wu_hourly_buckets = {}
            wu_current_date   = today

        # --- Service downtime checks ---
        for svc, thr in THRESHOLDS.items():
            age = now - last_seen[svc]
            if last_seen[svc] == 0.0:
                continue
            if age > thr:
                if not in_outage[svc]:
                    in_outage[svc] = True
                    alert_sent[svc] = last_repeat[svc] = now
                    log(f"ALERT: {svc} down {int(age//60)}min")
                    send_email(f"{STATION_NAME}: {svc} DOWN",
                               f"{svc} not posted for {int(age//60)}min (threshold {thr//60}min)\n"
                               f"Last seen: {datetime.fromtimestamp(last_seen[svc])}")
                elif now - last_repeat[svc] > REPEAT:
                    last_repeat[svc] = now
                    td = int(now - alert_sent[svc])
                    log(f"REPEAT: {svc} still down {td//60}min")
                    send_email(f"{STATION_NAME}: {svc} STILL DOWN",
                               f"{svc} down {td//60}min\nLast seen: {datetime.fromtimestamp(last_seen[svc])}")
            elif in_outage[svc]:
                td = int(now - alert_sent[svc])
                in_outage[svc] = False
                log(f"RECOVERY: {svc} after {td//60}min")
                send_email(f"{STATION_NAME}: {svc} RECOVERED",
                           f"{svc} recovered after {td//60}min at {datetime.now()}")

if __name__ == '__main__':
    if _TEST_ALERT:
        sample = ("2026-07-04 03:03:45 user.rtldavis ERROR rain: rejecting implausible "
                  "counter delta last=70 new=6 (RF glitch, not rain -- DEC-0021)")
        ts, detail, phantom_in = parse_rain_glitch(sample)
        send_rain_glitch_alert(ts, detail, phantom_in, sample, test=True)
        print("test alert sent (check email + weewx_monitor.log)")
        sys.exit(0)
    main()
