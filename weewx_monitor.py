#!/usr/bin/env python3
"""weewx monitor: USB watchdog + service downtime alerting"""

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
    except: return 0

def get_new_lines(from_line):
    try:
        with open(WEEWX_LOG_PATH) as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[from_line-1:]]
    except: return []

def do_reset():
    try:
        log("RESET: running usb_reset.sh via sudo")
        import subprocess
        result = subprocess.run(
            ['sudo', '/volume1/docker/weewx-rtldavis/usb_reset.sh'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            try: vendor = open('/sys/bus/usb/devices/1-3/idVendor').read().strip()
            except: vendor = 'unknown'
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

# --- Main ---
def main():
    now = time.time()
    last_seen   = {s: now for s in THRESHOLDS}
    alert_sent  = {s: 0.0 for s in THRESHOLDS}
    last_repeat = {s: 0.0 for s in THRESHOLDS}
    in_outage   = {s: False for s in THRESHOLDS}
    last_reset  = 0.0

    log("Monitor started")
    send_email("Eagle Hunt PWS: monitor started", f"Started at {datetime.now()}")

    last_line = get_linecount()
    log(f"Starting at log line {last_line}")

    while True:
        time.sleep(POLL)

        cur = get_linecount()
        if cur < last_line:
            log(f"Log reset detected (was {last_line}, now {cur}) - container restarted")
            last_line = 0
            # Reset last_seen to now to avoid false alerts after log rotation
            now = time.time()
            for svc in last_seen:
                last_seen[svc] = now
            for svc in in_outage:
                in_outage[svc] = False
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
            last_line = cur

        now = time.time()
        for svc, thr in THRESHOLDS.items():
            age = now - last_seen[svc]
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
