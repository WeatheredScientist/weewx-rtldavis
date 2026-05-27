#!/usr/bin/env python3
"""weewx monitor: USB watchdog + service downtime alerting + reception tracking"""

import time, smtplib, os, sys
from email.mime.text import MIMEText
from datetime import datetime

# --- Config ---
LOG      = '/volume1/docker/weewx-rtldavis/logs/weewx_monitor.log'
PIDFILE  = '/volume1/docker/weewx-rtldavis/logs/weewx_monitor.pid'
POLL     = 30
RESET_CD = 300
REPEAT   = 7200

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

# --- PID guard ---
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

WEEWX_LOG_PATH = '/volume1/docker/weewx-rtldavis/logs/weewx.log'

def get_linecount():
    try:
        with open(WEEWX_LOG_PATH) as f:
            return sum(1 for _ in f)
    except:
        return 0

def get_new_lines(from_line):
    try:
        with open(WEEWX_LOG_PATH) as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[from_line-1:]]
    except:
        return []

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
            except:
                vendor = 'unknown'
            log(f"RESET: done, idVendor={vendor}")
            send_email("Eagle Hunt PWS: RTL-SDR reset", f"Dongle reset at {datetime.now()}. Vendor: {vendor}")
        else:
            log(f"RESET error: {result.stderr}")
            send_email("Eagle Hunt PWS: RTL-SDR reset FAILED", f"usb_reset.sh failed: {result.stderr}")
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
        f"Eagle Hunt PWS — RF Reception Summary for {date_str}",
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
                    "Eagle Hunt PWS: RF reception RECOVERED",
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
                "Eagle Hunt PWS: RF reception LOW",
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
                "Eagle Hunt PWS: RF reception STILL LOW",
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

    # Reception tracking state
    wu_window_start   = time.time()
    wu_window_count   = 0
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
    send_email("Eagle Hunt PWS: monitor started", f"Started at {datetime.now()}")

    last_line = get_linecount()
    log(f"Starting at log line {last_line}")

    while True:
        time.sleep(POLL)
        now = time.time()

        cur = get_linecount()
        if cur < last_line:
            log(f"Log reset detected (was {last_line}, now {cur}) - container restarted")
            last_line = 0
            for svc in last_seen:
                last_seen[svc] = 0.0
            for svc in in_outage:
                in_outage[svc] = False
            wu_window_start  = now
            wu_window_count  = 0
            wu_period_counts = []
            wu_period_start  = now
            wu_bad_windows   = 0
            wu_first_seen    = False

        if cur > last_line:
            lines = get_new_lines(last_line + 1)
            log(f"Poll: {len(lines)} new lines")
            for line in lines:
                if 'rtldavis process stalled' in line:
                    log("STALL detected")
                    last_reset = reset_dongle(last_reset)
                for svc in THRESHOLDS:
                    if svc in line and ('Published' in line or 'published' in line):
                        if in_outage[svc]:
                            td = int(time.time() - alert_sent[svc])
                            in_outage[svc] = False
                            log(f"RECOVERY: {svc} after {td//60}min")
                            send_email(f"Eagle Hunt PWS: {svc} RECOVERED",
                                       f"{svc} recovered after {td//60}min at {datetime.now()}")
                        last_seen[svc] = time.time()
                if 'Wunderground-RF' in line and 'Published' in line:
                    wu_window_count += 1
                    wu_first_seen = True
            last_line = cur


        # --- Reception: close window every 60s ---
        if wu_first_seen and (now - wu_window_start) >= WU_RF_WINDOW:
            (wu_period_counts, wu_bad_windows, wu_in_alert,
             wu_alert_sent_at, wu_repeat_sent_at,
             wu_hourly_buckets) = close_reception_window(
                wu_window_count, wu_period_counts, wu_bad_windows,
                wu_in_alert, wu_alert_sent_at, wu_repeat_sent_at,
                wu_hourly_buckets, now)
            wu_window_start = wu_window_start + WU_RF_WINDOW
            wu_window_count = 0

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
                send_email(f"Eagle Hunt PWS: Daily RF Reception — {wu_current_date}", summary)
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
                    send_email(f"Eagle Hunt PWS: {svc} DOWN",
                               f"{svc} not posted for {int(age//60)}min (threshold {thr//60}min)\n"
                               f"Last seen: {datetime.fromtimestamp(last_seen[svc])}")
                elif now - last_repeat[svc] > REPEAT:
                    last_repeat[svc] = now
                    td = int(now - alert_sent[svc])
                    log(f"REPEAT: {svc} still down {td//60}min")
                    send_email(f"Eagle Hunt PWS: {svc} STILL DOWN",
                               f"{svc} down {td//60}min\nLast seen: {datetime.fromtimestamp(last_seen[svc])}")
            elif in_outage[svc]:
                td = int(now - alert_sent[svc])
                in_outage[svc] = False
                log(f"RECOVERY: {svc} after {td//60}min")
                send_email(f"Eagle Hunt PWS: {svc} RECOVERED",
                           f"{svc} recovered after {td//60}min at {datetime.now()}")

if __name__ == '__main__':
    main()
