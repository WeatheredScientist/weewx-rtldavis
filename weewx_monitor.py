#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""weewx monitor: USB watchdog + service downtime alerting + reception tracking"""

import time
import smtplib
import os
import sys
import re
import sqlite3
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

# --- Watchdog escalation (S62, ERR-0005) ---
# The 2026-08-02 outage fired nine USB resets across 75 minutes, none of which
# helped, and the tenth preceded a strictly worse failure mode (the dongle still
# enumerated for rtl_biast while rtldavis could no longer claim it). Every one of
# those nine sent an identical "RTL-SDR reset" email, so the ninth read exactly
# like the first and the one alarm that mattered was buried. Detection was never
# the problem -- RECEPTION ALERT fired at 00:13, eight minutes in. What was
# missing was any notion of whether the remedy WORKED.
RESET_VERIFY_S  = 180   # seconds after a reset before judging it effective
# S73 (2026-08-11): demoted 3 -> 1. Across every forensically-captured event
# (08-02 x11, 08-06 x3, 08-10/11 x3) no USB reset ever demonstrably fixed a
# stall, and every full-fidelity capture shows the same non-USB mechanism: the
# rtldavis child goes silent/dies while the device stays enumerated (devnum
# unchanged since Aug 2). The stall class is RF-dead episodes, which resets
# cannot touch, and ERR-0005 suspects reset #10 CAUSED the worse
# process-not-running mode. One reset is kept as a hedge for a genuine (never
# yet observed) dongle wedge; retries are evidence-free churn.
RESET_MAX_TRIES = 1     # ineffective resets before we stop and escalate (was 3, see above)

# --- What a "reset" actually IS (S67, DEC-0074) ---
# Named here ONCE, and used for both the subprocess call and every log line about
# it, so the message can never again drift from the action. Until S67 this was
# logged as "RESET: triggering syno_vbus_reset" -- an operation that has not run
# since the logic moved out of the retired usb_watchdog.sh, which really did write
# that node. The monitor runs usb_reset.sh, which is a driver UNBIND/REBIND and not
# a power cycle. Months of logs named the wrong operation, and a reader reasoning
# from them (including a Claude session at S67) reasons about the wrong mechanism.
# If the script ever changes what it does, change USB_RESET_ACTION with it.
USB_RESET_SCRIPT = os.environ.get(
    'USB_RESET_SCRIPT', '/volume1/docker/weewx-rtldavis/usb_reset.sh')
USB_RESET_ACTION = 'USB driver unbind/rebind'

# --- Reset forensics (S68, BOOT blocker 4) ---
# The resets fire and do not work; nobody knows why. usb_forensics.sh photographs
# the USB state and rtldavis's grip on the device around a reset, so the NEXT
# stall answers the question instead of merely repeating it.
#
# The pre/post captures are fired by usb_reset.sh, NOT from here, because they
# need root and this monitor runs unprivileged (which is why the reset itself goes
# through sudo). This module fires only the +RESET_VERIFY_S capture, which is
# host-side and therefore degraded by construction -- it still shows whether the
# rebind's devnum change persisted, which is the question at that moment.
USB_FORENSICS_SCRIPT = os.environ.get(
    'USB_FORENSICS_SCRIPT', '/volume1/docker/weewx-rtldavis/usb_forensics.sh')
CONTAINER  = os.environ.get('WEEWX_CONTAINER', 'weewx-rtldavis-v2')

# --- Episode ledger (S73) ---
# One pipe-delimited row per reception episode (RECEPTION ALERT -> RECOVERY),
# written at recovery so post-campaign analysis and the LNA verdict read ONE
# file instead of re-deriving episodes from three logs. Fields:
#   onset_iso|recovery_iso|duration_s|stalls|resets|respawns|droughts|worst_avg_pct|last_cmd
# 'stalls' counts driver 'rtldavis process stalled' raises; 'respawns' counts
# 'startup process' lines; 'droughts' counts the driver's ws.5 'DATA DROUGHT'
# self-classification lines (receiver alive, no decodes -> RF-quiet class).
EPISODES_LOG = os.environ.get('EPISODES_LOG', f'{BASE_DIR}/logs/episodes.log')
DOCKER_BIN = os.environ.get('DOCKER_BIN', '/usr/local/bin/docker')

# Env names whose VALUES must never reach an email or a log (DEC-0062). The
# recreate command below is built from `docker inspect`, and this repo is public
# -- another user's container may well carry an API key in its env.
ENV_SECRET_RE = re.compile(
    r'(KEY|TOKEN|SECRET|PASS|PW|CRED|AUTH|SALT|SIGN)', re.IGNORECASE)
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
# WU_RF_EXPECTED is the number of records the ISS *physically transmits* per 60s
# window -- the correct denominator for a reception %. It is NOT a fixed 24. The
# Davis ISS transmit period depends on the transmitter id (driver loop_times run
# 2.5625s..3.0s); this station's ISS (Transmitter 4) transmits every ~2.8125s, so
# 60 / 2.8125 = ~21.3 records/min. The old value 24 ("one per 2.5s") assumed the
# fastest channel and under-reported reception by ~13%: a full-reception window
# read 22/24 = 92% when it was really ~22/21 = ~100% (S29). Override per station
# with the WU_RF_EXPECTED env var when re-pointing to a different transmitter id.
WU_RF_EXPECTED     = int(os.environ.get('WU_RF_EXPECTED', 21))  # physical TX/min = 60 / 2.8125s
WU_RF_MIN_PCT      = 60    # alert threshold %: a window below this is a real >~40% packet loss
WU_RF_WINDOW       = 60    # seconds per reception window
WU_RF_SUSTAIN      = 5     # consecutive bad windows before alert
WU_RF_LOG_INTERVAL = 300   # log reception summary every 5 min

# Every WeeWX "Published record ..." line ends in "(<unix_epoch>)". The driver
# publishes freqError freq-hop channel packets as extra dataless loop packets, so
# each real reading is posted to WU several times under the SAME epoch (DEC-0024).
WU_RECORD_RE = re.compile(r'\((\d+)\)\s*$')

# --- Archive-DB reception source (Layer A, S31) ---
# The WU-publish scrape above measures publish LIVENESS, not RF reception. It runs
# ~21+/min (padded by the freqError freq-hop publishes, DEC-0024) and reads ~100%
# even when the driver's own decode metric shows ~75% packet reception (S31 audit:
# 14 straight minutes at "100%" while rxCheckPercent ran 59-95%). The honest metric
# is the driver's rxCheckPercent (pct_good_all in rtldavis.py) -- good CRC-decoded
# packets / theoretical max per archive period -- already stored per record in the
# archive DB. The periodic reception summary is sourced from there instead of the
# scrape; the real-time WINDOW logging + outage alerting are left unchanged (they
# still catch a total stall). Read-only; a DB hiccup falls back to the old summary.
ARCHIVE_DB = os.environ.get('WEEWX_ARCHIVE_DB', f'{BASE_DIR}/weewx-data/archive/weewx.sdb')
# True physical ISS transmit rate (packets/min) for the dropped-packet estimate:
# 60 / 2.8125s = 21.33. This is the UN-rounded WU_RF_EXPECTED; the driver itself
# floor-divides the period, so rxCheckPercent runs ~1-2 pts optimistic (documented,
# minor -- S31). Override per station (different transmitter id) via the env var.
RF_TX_PER_MIN = float(os.environ.get('RF_TX_PER_MIN', 60.0 / 2.8125))
# How often to email the reception summary. Default 6 h (00/06/12/18 local) so a
# reception problem surfaces within ~6 h and can be acted on the same day, rather than
# read the next morning in a once-a-day midnight report. Set 12 for twice-daily or 24
# for the original daily cadence. Windows align to local midnight. Clamped to [1, 24].
# Env-overridable (e.g. RF_REPORT_INTERVAL_HOURS in monitor.env).
RF_REPORT_INTERVAL_HOURS = max(1, min(24, int(os.environ.get('RF_REPORT_INTERVAL_HOURS', 6))))

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

# --- Rain-counter glitch alert (DEC-0021; tripwire role added by DEC-0056) ---
# rtldavis.py logs this exact phrase when it rejects an implausible rain-counter
# delta -- an RF-decode glitch that, before the fix, would have become phantom
# rain. Watching for it turns each catch into an email: confirmation the filter
# earned its keep, plus a running record of how often the glitch actually fires.
# Since DEC-0056 tightened the cap (60 -> 16 tips), this email is ALSO the
# tripwire for the rare other explanation: real rain suppressed across a long
# reception gap. The body prompts the WeatherLink cross-check either way, and
# any rejection on a genuinely wet day is the predefined trigger to revisit
# the cap with that event's data (DEC-0056).
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
            f"No rain was recorded for that reading (DEC-0021 filter, cap tightened "
            f"by DEC-0056).\n\n"
            f"Most likely: an RF-decode glitch, caught working as designed.\n"
            f"But check one thing: if heavy rain was actually falling around this "
            f"time, this could be REAL rain suppressed across a rare long reception "
            f"gap. Cross-check the WeatherLink console total for this window and "
            f"reconcile per the DEC-0056 playbook (docs/DECISIONS-FULL.md). A "
            f"rejection on a genuinely wet day is the agreed trigger to revisit "
            f"the cap with this event's data.\n")
    if phantom_in is not None:
        body += f"\nA naive (pre-fix) decode would have logged +{phantom_in}\" of rain here.\n"
    if test:
        body += "\nThis is a TEST of the rain-glitch email alert. If you got it, alerting works."
    else:
        body += f"\nLog line:\n{raw_line}"
    send_email(f"{STATION_NAME}: {tag}rain-counter glitch rejected", body)

def usb_forensics(phase):
    """Fire one read-only USB capture. Evidence only -- never load-bearing.

    Deliberately swallows everything: a capture is worth strictly less than the
    watchdog it observes, so no failure here may disturb the reset path. A
    missing script is the normal state on a box where S68's deploy has not
    landed, and is not worth an ERROR line every time.
    """
    import subprocess
    try:
        if not os.access(USB_FORENSICS_SCRIPT, os.X_OK):
            return None
        out = subprocess.run([USB_FORENSICS_SCRIPT, phase],
                             capture_output=True, text=True, timeout=30)
        path = out.stdout.strip()
        if path:
            log(f"FORENSICS: {phase} capture -> {path}")
        return path or None
    except Exception as e:
        log(f"FORENSICS: {phase} capture failed ({e}) -- reset path unaffected")
        return None


def do_reset(notify=True):
    try:
        log(f"RESET: running {USB_RESET_SCRIPT} via sudo ({USB_RESET_ACTION})")
        import subprocess
        result = subprocess.run(
            ['sudo', USB_RESET_SCRIPT],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            try:
                vendor = open('/sys/bus/usb/devices/1-3/idVendor').read().strip()
            except OSError:
                vendor = 'unknown'
            log(f"RESET: done, idVendor={vendor}")
            # A zero exit does not mean the script had nothing to say. It refuses
            # to run the forensics helper if that helper is not root-owned and
            # root-only-writable (it would escalate our own sudo grant), and it
            # reports that on stderr while still performing the reset. Discarding
            # output on success would turn that refusal into a silent no-op --
            # the capture would simply never happen and nothing would say so.
            for stream in (result.stdout, result.stderr):
                for line in (stream or '').splitlines():
                    if line.strip():
                        log(f"RESET script: {line.strip()}")
            # notify=False for repeat resets within one outage: nine identical
            # "RTL-SDR reset" emails is how the real alarm got buried (ERR-0005).
            if notify:
                send_email(f"{STATION_NAME}: RTL-SDR reset", f"Dongle reset at {datetime.now()}. Vendor: {vendor}")
        else:
            log(f"RESET error: {result.stderr}")
            send_email(f"{STATION_NAME}: RTL-SDR reset FAILED", f"{USB_RESET_SCRIPT} failed: {result.stderr}")
    except Exception as e:
        log(f"RESET error: {e}")

# Watchdog escalation state (S62). Kept in one dict rather than threaded through
# main()'s locals: the reset path spans both the line scanner and the poll loop,
# and widening close_reception_window()'s return tuple to carry it would disturb
# code this change has no business touching (DEC-0014).
WD = {
    'last_reset': 0.0,
    'tries': 0,          # consecutive INEFFECTIVE resets
    'check_at': 0.0,     # when to judge the pending reset (0 = none pending)
    'escalated': False,  # escalation already sent for this outage
}


def build_recreate_cmd(container=None):
    """Build the container-recreate command from the LIVE container's config.

    Deliberately derived from `docker inspect` and never from the NAS
    docker-compose.yml, which is stale and decorative (CONSTANTS.md). Returns
    None if anything is uncertain -- a half-right recreate line is worse than
    none, because `rm` is not reversible.

    Env VALUES matching ENV_SECRET_RE are redacted: this monitor ships in a
    public repo and another user's container may carry credentials (DEC-0062).
    """
    import json
    import subprocess
    container = container or CONTAINER
    try:
        out = subprocess.run([DOCKER_BIN, 'inspect', container],
                             capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return None
        c = json.loads(out.stdout)[0]
        hc, cf = c['HostConfig'], c['Config']
        parts = [f"{DOCKER_BIN} kill {container}",
                 f"{DOCKER_BIN} rm {container}",
                 "sleep 3"]
        run = [DOCKER_BIN, 'run', '-d', '--name', container]
        pol = (hc.get('RestartPolicy') or {}).get('Name')
        if pol and pol != 'no':
            run += ['--restart', pol]
        if hc.get('Privileged'):
            run += ['--privileged']
        for d in (hc.get('Devices') or []):
            run += ['--device',
                    f"{d['PathOnHost']}:{d['PathInContainer']}:{d['CgroupPermissions']}"]
        net = hc.get('NetworkMode')
        if net and net not in ('default', 'bridge'):
            run += ['--network', net]
        for e in (cf.get('Env') or []):
            name = e.split('=', 1)[0]
            if name == 'PATH':
                continue          # image default; passing it back is noise
            val = e.split('=', 1)[1] if '=' in e else ''
            run += ['-e', f"{name}=<REDACTED>" if ENV_SECRET_RE.search(name)
                    else f"{name}={val}"]
        for b in (hc.get('Binds') or []):
            run += ['-v', b]
        run += [cf['Image']]
        run += (cf.get('Cmd') or [])
        parts.append(' '.join(run))
        return '\n'.join(parts)
    except Exception as e:
        log(f"RECREATE-CMD build failed: {e}")
        return None


def send_unrecoverable_alert(reason, detail=''):
    """The escalation the 2026-08-02 outage never produced.

    Nine identical "RTL-SDR reset" emails told the owner nothing was different
    about the ninth. This fires ONCE per outage, says plainly that automatic
    recovery has failed, and carries the command that actually worked.
    """
    cmd = build_recreate_cmd()
    body = (f"Automatic recovery has FAILED. Manual intervention needed.\n\n"
            f"Reason: {reason}\n")
    if detail:
        body += f"{detail}\n"
    body += (f"\nTried: {WD['tries']} USB reset(s), none effective.\n"
             f"Time: {datetime.now()}\n\n")
    if cmd:
        body += ("The remedy that resolved the 2026-08-02 outage (ERR-0005) was a full\n"
                 "container recreate -- NOT a restart; a kill+start was tried during that\n"
                 "incident and did not help. Command below is built from the LIVE container\n"
                 "config via `docker inspect`. Review it before running.\n"
                 "Any <REDACTED> env value must be filled in by hand.\n\n"
                 f"{cmd}\n")
    else:
        body += ("Could not build the recreate command (`docker inspect` failed).\n"
                 "Derive it by hand from the live container -- do NOT use the NAS\n"
                 "docker-compose.yml, it is stale and decorative.\n")
    log(f"ESCALATION: {reason} (after {WD['tries']} ineffective resets)")
    send_email(f"{STATION_NAME}: RTL-SDR UNRECOVERABLE - manual intervention needed", body)


def reset_dongle(last_reset, notify=True):
    now = time.time()
    if now - last_reset < RESET_CD:
        log(f"SKIP reset: cooldown ({int(now-last_reset)}s)")
        return last_reset
    log(f"RESET: {USB_RESET_ACTION} via {USB_RESET_SCRIPT}")
    import threading
    t = threading.Thread(target=do_reset, kwargs={'notify': notify}, daemon=True)
    t.start()
    return time.time()


def watchdog_stall(wu_bad_windows):
    """Handle a 'rtldavis process stalled' line, with escalation.

    Unbounded retry is what ERR-0005 measured failing: 9 resets, 0 successes,
    and harm on the 10th. After RESET_MAX_TRIES ineffective resets we stop
    resetting entirely and hand it to a human.

    S73: RESET_MAX_TRIES is now 1. The forensics record (see the constant's
    comment) shows the stall class is RF-dead episodes -- the child goes
    silent while the device stays enumerated -- which a USB reset cannot fix.
    The single remaining reset is a hedge for a genuine dongle wedge, a mode
    never yet captured. The driver's own ws.5 'STALL DIAGNOSIS' / 'DATA
    DROUGHT' lines now classify each event at the source.
    """
    if WD['tries'] >= RESET_MAX_TRIES:
        if not WD['escalated']:
            WD['escalated'] = True
            send_unrecoverable_alert(
                f"{WD['tries']} consecutive USB resets did not restore reception",
                f"Consecutive bad reception windows: {wu_bad_windows}")
        else:
            log(f"STALL: escalated already; not resetting (tries={WD['tries']})")
        return
    prev = WD['last_reset']
    # Only the FIRST reset of an outage emails; the rest are log-only. Nine
    # identical notices is how the real alarm got buried (ERR-0005).
    WD['last_reset'] = reset_dongle(prev, notify=(WD['tries'] == 0))
    if WD['last_reset'] != prev:
        WD['check_at'] = WD['last_reset'] + RESET_VERIFY_S


def watchdog_not_running(wu_bad_windows):
    """Handle 'rtldavis process is not running' -- a DIFFERENT fault.

    'stalled' means the process runs and yields nothing. 'not running' means it
    dies on startup, which a USB unbind/rebind demonstrably does not fix and, on
    the ERR-0005 evidence, may well have caused. So: never reset here, escalate
    straight away.
    """
    if WD['escalated']:
        return
    WD['escalated'] = True
    send_unrecoverable_alert(
        "rtldavis exits immediately on startup (process is not running)",
        "A USB reset does NOT fix this mode and may have caused it (ERR-0005).\n"
        f"Consecutive bad reception windows: {wu_bad_windows}")


def watchdog_poll(wu_bad_windows, now):
    """Judge whether the pending reset worked. Called once per poll."""
    if not WD['check_at'] or now < WD['check_at']:
        return
    WD['check_at'] = 0.0
    if wu_bad_windows == 0:
        log("RESET verified effective; watchdog counters cleared")
        # Captured on success too, on purpose: a working reset is the control
        # this whole investigation lacks. Without it there is nothing to diff a
        # failed reset against, and every observation looks equally suspicious.
        usb_forensics('verify-effective')
        WD['tries'] = 0
        WD['escalated'] = False
    else:
        WD['tries'] += 1
        log(f"RESET ineffective ({WD['tries']}/{RESET_MAX_TRIES}); "
            f"bad windows still {wu_bad_windows}")
        usb_forensics('verify-ineffective')


def watchdog_recovered():
    """Reception came back on its own -- clear the escalation latch."""
    if WD['tries'] or WD['escalated']:
        log("Watchdog: reception recovered, counters cleared")
    WD['tries'] = 0
    WD['escalated'] = False
    WD['check_at'] = 0.0

# Episode state (S73). Opened by the RECEPTION ALERT transition, closed by
# RECOVERY; counters fed by the main dispatch loop. Module-global like WD.
EP = {
    'onset': 0.0,       # epoch of the ALERT transition; 0.0 = no open episode
    'stalls': 0,        # driver 'rtldavis process stalled' raises seen
    'resets': 0,        # USB resets actually fired during the episode
    'respawns': 0,      # driver 'startup process' lines seen
    'droughts': 0,      # driver 'DATA DROUGHT' self-classifications seen
    'worst_avg': 100.0, # lowest reported window average
    'last_cmd': '',     # cmd from the most recent 'startup process' line
}


def episode_open(avg, now):
    EP['onset'] = now
    EP['stalls'] = EP['resets'] = EP['respawns'] = EP['droughts'] = 0
    EP['worst_avg'] = avg
    EP['last_cmd'] = ''


def episode_note_avg(avg):
    if EP['onset'] and avg < EP['worst_avg']:
        EP['worst_avg'] = avg


def episode_close(now):
    """Write the ledger row and clear. No-op if no episode is open."""
    if not EP['onset']:
        return
    row = "%s|%s|%d|%d|%d|%d|%d|%.0f|%s\n" % (
        datetime.fromtimestamp(EP['onset']).strftime('%Y-%m-%d %H:%M:%S'),
        datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S'),
        int(now - EP['onset']), EP['stalls'], EP['resets'], EP['respawns'],
        EP['droughts'], EP['worst_avg'], EP['last_cmd'])
    try:
        with open(EPISODES_LOG, 'a') as f:
            f.write(row)
        log(f"EPISODE closed: {row.strip()}")
    except OSError as e:
        log(f"EPISODE ledger write failed: {e}")
    EP['onset'] = 0.0


def wu_pct(count):
    """Reception % = records received / records the ISS physically transmitted
    (WU_RF_EXPECTED), capped at 100. You cannot receive more than were sent; a raw
    value just over 100 only means a 60s window caught one extra phase-aligned
    transmission. Single source of truth for every reception % the monitor reports."""
    return min(100.0, 100.0 * count / WU_RF_EXPECTED)


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
            avg_pct = wu_pct(avg_count)
            day_counts.extend(buckets)
            status = "OK" if avg_pct >= WU_RF_MIN_PCT else "LOW"
            lines.append(f"{hour:02d}:00    {avg_count:>10.1f} {avg_pct:>9.0f}% {status:>8}")
        else:
            lines.append(f"{hour:02d}:00    {'--':>10} {'--':>9}  {'--':>8}")
    lines.append("-" * 42)
    if day_counts:
        day_avg = wu_pct(sum(day_counts) / len(day_counts))
        lines.append(f"{'Daily avg':<8} {'':>10} {day_avg:>9.0f}%")
    return "\n".join(lines)

def summarize_reception_rows(rows, tx_per_min):
    """Pure reception math over archive rows -> summary dict (no DB, unit-testable).

    ROWS: iterable of (dateTime_utc_epoch, interval_minutes, rxCheckPercent-or-None).
    rxCheckPercent is the driver's honest metric: good CRC-decoded packets over the
    theoretical max for that archive period. Per record the ISS transmits
    interval*tx_per_min packets; received ~= expected * pct/100, dropped = the rest.
    NULL-rxCheckPercent records (first record after a restart, or the pre-fix
    deadlock era) carry no reception info, so they are counted as 'gaps' and left
    out of the expected/received totals -- a conservative under-count of drops.
    Returns None when there is nothing for the day."""
    hours = {}
    for dt, interval_min, pct in rows:
        hour = time.localtime(dt).tm_hour
        h = hours.setdefault(hour, {'pcts': [], 'expected': 0.0, 'received': 0.0, 'gaps': 0})
        if pct is None:
            h['gaps'] += 1
            continue
        exp = (interval_min or 1) * tx_per_min
        h['pcts'].append(pct)
        h['expected'] += exp
        h['received'] += exp * pct / 100.0
    day = {'expected': 0.0, 'received': 0.0, 'gaps': 0, 'records': 0, 'hours': {}}
    for hour, h in hours.items():
        exp, rec, n = h['expected'], h['received'], len(h['pcts'])
        day['hours'][hour] = {
            'records': n, 'gaps': h['gaps'],
            'mean_pct': (100.0 * rec / exp) if exp else None,
            'min_pct': min(h['pcts']) if h['pcts'] else None,
            'expected': exp, 'received': rec, 'dropped': exp - rec,
        }
        day['expected'] += exp
        day['received'] += rec
        day['gaps'] += h['gaps']
        day['records'] += n
    if not day['records'] and not day['gaps']:
        return None
    day['mean_pct'] = (100.0 * day['received'] / day['expected']) if day['expected'] else None
    day['dropped'] = day['expected'] - day['received']
    return day


def period_floor(ts, interval_h):
    """Epoch of the start of the INTERVAL_H-hour reporting block (aligned to local
    midnight) that contains TS. E.g. interval_h=12 -> 00:00 or 12:00 local; =6 ->
    00/06/12/18; =24 -> local midnight (the original once-daily cadence)."""
    lt = time.localtime(ts)
    floored = (lt.tm_year, lt.tm_mon, lt.tm_mday,
               (lt.tm_hour // interval_h) * interval_h, 0, 0, 0, 0, -1)
    return int(time.mktime(floored))


def period_label(start_ts, end_ts):
    """Human label for a reporting window, e.g. '2026-07-08 00:00–12:00' (or with a
    date on the end when the window crosses midnight)."""
    s, e = time.localtime(start_ts), time.localtime(end_ts)
    same_day = (s.tm_year, s.tm_yday) == (e.tm_year, e.tm_yday)
    end_fmt = "%H:%M" if same_day else "%Y-%m-%d %H:%M"
    return time.strftime("%Y-%m-%d %H:%M", s) + "–" + time.strftime(end_fmt, e)


def db_reception_summary(start_ts, end_ts, db_path=None):
    """Read rxCheckPercent for the [START_TS, END_TS) epoch window from the archive
    DB (read-only) and return the reception summary dict, or None if the DB can't be
    read / the window is empty. Any DB error is logged and swallowed so the monitor
    never dies on a DB hiccup (the caller falls back to the legacy WU-scrape summary)."""
    db_path = db_path or ARCHIVE_DB
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        try:
            rows = con.execute(
                "SELECT dateTime, interval, rxCheckPercent FROM archive "
                "WHERE dateTime >= ? AND dateTime < ? ORDER BY dateTime",
                (start_ts, end_ts)).fetchall()
        finally:
            con.close()
    except Exception as e:
        log(f"DB RECEPTION SUMMARY ERROR: {e}")
        return None
    return summarize_reception_rows(rows, RF_TX_PER_MIN)


def format_reception_summary(summary, label):
    """Format the archive-sourced reception summary (S31) as a text table. Reports
    packets dropped -- not just windows above a threshold. LABEL names the reporting
    window (e.g. '2026-07-08 00:00–12:00'); rows are the hours present in the window."""
    lines = [
        f"{STATION_NAME} — RF Reception Summary — {label}",
        "Source: driver rxCheckPercent (good decoded packets / transmitted, per record)",
        f"Physical TX rate: {RF_TX_PER_MIN:.1f} packets/min",
        "",
        f"{'Hour':<6} {'Recept.':>8} {'Min':>6} {'Dropped':>9} {'Recs':>6}",
        "-" * 40,
    ]
    for hour in sorted(summary['hours']):
        h = summary['hours'][hour]
        if h['records']:
            lines.append(f"{hour:02d}:00 {h['mean_pct']:>6.0f}% {h['min_pct']:>5.0f}% "
                         f"{h['dropped']:>9.0f} {h['records']:>6}")
        else:
            lines.append(f"{hour:02d}:00 {'--':>6}  {'--':>5} {'--':>9} {('gap x%d' % h['gaps']):>6}")
    lines.append("-" * 40)
    mean = summary['mean_pct']
    lines.append(f"Mean reception:            {mean:.0f}%" if mean is not None else
                 "Mean reception:            --")
    lines.append(f"Packets transmitted (est): {summary['expected']:.0f}")
    lines.append(f"Packets received (est):    {summary['received']:.0f}")
    lines.append(f"Packets dropped (est):     {summary['dropped']:.0f}")
    if summary['gaps']:
        lines.append(f"Records with no reception data (gaps/restarts): {summary['gaps']}")
    lines.append("")
    lines.append("Note: estimate = per-record rxCheckPercent x physical TX rate; the driver "
                 "floor-divides per period so it runs ~1-2 pts optimistic (S31, DEC-0024).")
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
        pct = wu_pct(wu_window_count)
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
                avg = wu_pct(sum(wu_period_counts) / len(wu_period_counts))
                log(f"RECEPTION RECOVERY: {avg:.0f}% avg after {td//60}min")
                episode_close(now)
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
            episode_open(avg, now)
            send_email(
                f"{STATION_NAME}: RF reception LOW",
                f"WU-RF reception below {WU_RF_MIN_PCT}% for {wu_bad_windows} consecutive minutes.\n"
                f"Average over last {wu_bad_windows} windows: {avg:.0f}%\n"
                f"Alert time: {datetime.now()}"
            )
        elif wu_in_alert and (now - wu_repeat_sent_at) >= REPEAT:
            wu_repeat_sent_at = now
            avg = (sum(wu_period_counts[-WU_RF_SUSTAIN:]) / (WU_RF_SUSTAIN * WU_RF_EXPECTED)) * 100
            episode_note_avg(avg)
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
    wu_report_start   = period_floor(time.time(), RF_REPORT_INTERVAL_HOURS)

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
                    EP['stalls'] += 1
                    _reset_before = WD['last_reset']
                    watchdog_stall(wu_bad_windows)
                    if WD['last_reset'] != _reset_before:
                        EP['resets'] += 1
                elif 'rtldavis process is not running' in line:
                    # A DIFFERENT fault from a stall -- the binary dies on
                    # startup. Never reset here (S62, ERR-0005).
                    log("DRIVER NOT RUNNING detected")
                    watchdog_not_running(wu_bad_windows)
                elif 'startup process' in line:
                    # Driver (re)spawned its child -- episode respawn counter
                    # plus the cmd it ran, for the ledger row (S73).
                    EP['respawns'] += 1
                    m = re.search(r"startup process '([^']*)'", line)
                    if m:
                        EP['last_cmd'] = m.group(1)
                elif 'DATA DROUGHT' in line:
                    # Driver ws.5 self-classification: receiver emitting,
                    # nothing decoding -- the RF-quiet class (S73).
                    EP['droughts'] += 1
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
            # S62: judge the pending reset now that a fresh window has closed,
            # and drop the escalation latch if reception came back on its own.
            watchdog_poll(wu_bad_windows, now)
            if wu_bad_windows == 0 and (WD['tries'] or WD['escalated']):
                watchdog_recovered()

        # --- Reception: log 5-min summary ---
        if wu_first_seen and (now - wu_period_start) >= WU_RF_LOG_INTERVAL:
            if wu_period_counts:
                avg = (sum(wu_period_counts) / len(wu_period_counts) / WU_RF_EXPECTED) * 100
                maintained = "OK" if avg >= WU_RF_MIN_PCT else "LOW"
                log(f"RECEPTION: {avg:.0f}% avg over last {len(wu_period_counts)} windows "
                    f"[{maintained}] (bad windows: {wu_bad_windows})")
            wu_period_counts = []
            wu_period_start  = now

        # --- Reception summary email, every RF_REPORT_INTERVAL_HOURS ---
        # Fire when the wall clock crosses into a new reporting block; report the block
        # that just ended, [wu_report_start, block). Prefer the honest archive-sourced
        # summary (rxCheckPercent, S31); fall back to the legacy WU-scrape summary only
        # if the DB read yields nothing, so a report is never lost to a DB hiccup.
        block = period_floor(now, RF_REPORT_INTERVAL_HOURS)
        if block > wu_report_start:
            label = period_label(wu_report_start, block)
            db_summary = db_reception_summary(wu_report_start, block)
            if db_summary:
                body = format_reception_summary(db_summary, label)
                log(f"RECEPTION SUMMARY (rxCheckPercent): sending for {label}")
            elif wu_hourly_buckets:
                body = format_daily_summary(wu_hourly_buckets, label)
                log(f"RECEPTION SUMMARY (WU-scrape fallback): sending for {label}")
            else:
                body = None
            if body:
                send_email(f"{STATION_NAME}: RF Reception — {label}", body)
            wu_hourly_buckets = {}
            wu_report_start   = block

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
