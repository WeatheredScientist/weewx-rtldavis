#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""weewx monitor: USB watchdog + service downtime alerting + reception tracking"""

import time
import smtplib
import ssl
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

# --- Which automatic remedy the watchdog is allowed to try (S107, ops#233) ---
# The host moved to marvin (DEC-0118), where the Foundation-era USB path does not
# just fail -- it is DANGEROUS. `usb_reset.sh` unbinds a driver at a hardcoded
# Synology bus path (`/sys/bus/usb/devices/1-3`); marvin's USB topology is
# different (MARVIN-DEC-0051 reassigned two controller roles), so the same call
# there either no-ops or resets SOMEONE ELSE'S device on a box now hosting two
# live tenants and a passed-through ASM3142 controller.
#
# So the mechanism is now selected, not assumed:
#
#   usb_reset     the Foundation/Synology body: sudo usb_reset.sh (driver
#                 unbind/rebind). DEFAULT, because this is a published extension
#                 and changing an existing install's behavior silently would be
#                 its own defect. But read RESET_MAX_TRIES' comment before
#                 trusting it: across ~17 forensically-captured events on our
#                 hardware it never once demonstrably fixed a stall, and
#                 ERR-0005 suspects reset #10 caused a strictly worse mode.
#   restart_unit  marvin: `systemctl restart <REMEDY_UNIT>`. weewx.service is
#                 `docker run --rm` with `ExecStartPre=docker rm -f`, so a
#                 restart IS the full container recreate -- the remedy that
#                 actually resolved ERR-0005, which the Foundation monitor could
#                 only reconstruct via `docker inspect` and mail to a human.
#   none          detect and escalate only; never act. The honest setting for
#                 any host where no remedy has been shown to work.
#
# Every mode keeps the SAME escalation discipline (RESET_MAX_TRIES, the verify
# window, one email per outage). Only the action in the middle changes.
REMEDY_MODE = os.environ.get('REMEDY_MODE', 'usb_reset')
REMEDY_UNIT = os.environ.get('REMEDY_UNIT', 'weewx.service')
# How to invoke systemctl. marvin's tenant runs unprivileged, so this is the
# seam where a deployment supplies whatever it is actually allowed to use
# (a path-scoped sudo grant, or marvinctl's tier-2 own-unit verb).
REMEDY_SYSTEMCTL = os.environ.get('REMEDY_SYSTEMCTL', 'sudo systemctl')

# --- Campaign inhibit (S107) ---
# An RX campaign restarts weewx deliberately, once per arm. Every one of those
# restarts looks exactly like the fault this watchdog exists to remedy: a gap in
# decodes, then a respawn. Left unguarded the monitor would fight the campaign
# it is supposed to be observing -- and worse, a remedy restart landing mid-arm
# corrupts the block, which is the measurement the whole campaign is for.
#
# While this file exists: alerting and logging continue unchanged (we still want
# the record), but NO automatic remedy fires. Detection is never inhibited --
# only action. Same spirit as void_pending_verdict(): when the situation cannot
# be judged honestly, say so loudly rather than act on it.
CAMPAIGN_INHIBIT = os.environ.get(
    'CAMPAIGN_INHIBIT', f'{BASE_DIR}/logs/campaign.inhibit')

# --- Episode ledger (S73) ---
# One pipe-delimited row per reception episode (RECEPTION ALERT -> RECOVERY),
# written at recovery so post-campaign analysis and the LNA verdict read ONE
# file instead of re-deriving episodes from three logs. Fields:
#   onset_iso|recovery_iso|duration_s|stalls|resets|respawns|droughts|worst_avg_pct|last_cmd
# 'stalls' counts driver 'rtldavis process stalled' raises; 'respawns' counts
# 'startup process' lines; 'droughts' counts the driver's ws.5 'DATA DROUGHT'
# self-classification lines (receiver alive, no decodes -> RF-quiet class).
EPISODES_LOG = os.environ.get('EPISODES_LOG', f'{BASE_DIR}/logs/episodes.log')
# S82b (#180): the open episode, mirrored to disk. EP is module memory, and a
# monitor restart mid-episode (every deploy is one) used to silently lose the
# open episode: no ledger row ever written -- the pre-registered LNA datum --
# no RECOVERY line for rx_experiment.sh's fast resume path, and the ALERT
# email never got its RECOVERY pair. The mirror is rewritten on every episode
# mutation and removed at close; startup restores it (episode_load).
EPISODE_STATE = os.environ.get('EPISODE_STATE', f'{BASE_DIR}/logs/monitor_episode.state')
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
# Davis ISS transmit period depends on the transmitter id: (41 + id) / 16 s for
# packet id 0..7, i.e. DIP-switch ID 1..8 = 2.5625s..3.0s. Davis's own spec sheets
# (Vue: "varies with transmitter ID code"; VP2: every sensor interval is N x 2.5-3 s)
# and DeKay's protocol notes agree -- verified S119, #313. This station's ISS (packet
# id 4 = DIP ID 5) transmits every 2.8125s, measured 2.8124s +/- 1 ms (S115 capture),
# so 60 / 2.8125 = ~21.3 records/min. The old value 24 ("one per 2.5s") assumed the
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
# floor-divides the period (60 s -> 21, 59 s -> 20), so a fully received minute
# reads 101-105% -- ~3 pts, measured once DEC-0135 unmasked it (#313; S31 had
# called it ~1-2 pts under the old ~73% ceiling). summarize_reception_rows() clamps
# each record at 100 before multiplying it out. Override per station (different
# transmitter id) via the env var.
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
        # S91: explicit verifying context -- smtplib's default (no context=)
        # falls back to ssl._create_stdlib_context(), an alias for
        # _create_unverified_context() (no cert chain check, no hostname
        # check). Without this, an on-path attacker can intercept the
        # handshake with any certificate and capture GMAIL_PASS. See
        # influx.py's post_request() for the same pattern already in use
        # elsewhere in this repo.
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl.create_default_context()) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.send_message(msg)
        log(f"EMAIL sent: {subject}")
    except Exception as e:
        log(f"EMAIL error: {e}")

WEEWX_LOG_PATH = os.environ.get('WEEWX_LOG', f'{BASE_DIR}/logs/weewx.log')

# --- Input staleness: THIS MONITOR'S OWN FAILURE MODE (S107, ops#233) ---
# On 2026-08-29 this monitor sent ~14 hours of "STILL DOWN" alerts about six
# uploaders that were all healthy. Nothing in it was broken. weewx had moved to
# marvin (DEC-0118) and the log file it reads froze at 22:33:46 the night
# before; every alert after that reported the age of a DEAD FILE, not the state
# of the station. Live rxCheckPercent ran 74-77% the whole time it was calling
# reception "below 60%".
#
# The defect is structural, not a wrong path: EVERY threshold in this file is of
# the form "nothing has been seen for N seconds", and a stalled input satisfies
# all of them at once, forever, while looking exactly like a total outage. The
# monitor could not tell "the station is down" from "I am blind".
#
# So blindness is now its own state, checked BEFORE any threshold is evaluated,
# and reported as its own alert class. Two independent signals, because they
# fail differently:
#
#   mtime      cheap, catches the file not growing. Fooled by a touch, and by a
#              writer that reopens the path without writing.
#   last line  the timestamp parsed from the newest line we actually consumed.
#              Catches content going stale even when something keeps the file's
#              mtime fresh -- the "right path, wrong host" shape, which is
#              precisely what the marvin cutover produced.
#
# Staleness is the WORSE of the two. weewx publishes every ~3 s and archives
# every 60 s, so five minutes of silence is already far outside normal.
INPUT_STALE_S   = int(os.environ.get('INPUT_STALE_S', 300))
# Timestamp prefix weewx writes on every line: '2026-08-30 07:20:50,192 ...'.
LOG_TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')

# Blind state, module-global like WD/EP. 'since' is when we first went blind;
# 'alerted_at' drives the REPEAT cadence, reusing the same clock as everything
# else here so a blind episode reads like any other outage in the mail.
BLIND = {
    'active': False,
    'since': 0.0,
    'alerted_at': 0.0,
    'last_line_ts': 0.0,   # epoch of the newest weewx.log line we have parsed
}


def parse_log_ts(line):
    """Epoch of LINE's leading weewx timestamp, or None if it has none.

    Deliberately anchored (`^`) and second-resolution: the millisecond suffix
    and everything after it is noise for a staleness question, and a regex that
    could match a timestamp appearing LATER in a line would happily read a
    quoted one out of an error message and call the input fresh."""
    m = LOG_TS_RE.match(line)
    if not m:
        return None
    try:
        return time.mktime(time.strptime(m.group(1), '%Y-%m-%d %H:%M:%S'))
    except ValueError:
        return None


def log_mtime():
    """mtime of the weewx log, or 0.0 if it cannot be stated (missing/denied).

    0.0 is deliberately the WORST possible answer rather than an exception: a
    log we cannot stat is a log we cannot trust, and input_staleness() turns
    that into maximum staleness, which is the honest reading."""
    try:
        return os.path.getmtime(WEEWX_LOG_PATH)
    except OSError:
        return 0.0


def input_staleness(now):
    """Seconds since the input last showed evidence of life -- the WORSE of the
    file's mtime age and the newest parsed line's age.

    Returns a float. A never-seen line (last_line_ts 0.0) does not by itself
    mean stale: at startup we have not read anything yet, so that signal is
    skipped until it has a value and mtime carries the check alone."""
    ages = [now - log_mtime()]
    if BLIND['last_line_ts']:
        ages.append(now - BLIND['last_line_ts'])
    return max(ages)


def send_blind_alert(stale_s, now, recovered=False):
    """Alert on the monitor's own blindness -- a DIFFERENT class from '<svc> DOWN'.

    Kept deliberately distinct in subject and body. Collapsing the two is the
    original defect: 14 hours of mail said six uploaders were down when the
    truth was that the monitor could not see. A reader must be able to tell
    'your station stopped' from 'your monitoring stopped' at a glance, because
    the actions are completely different."""
    mtime = log_mtime()
    seen = (datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            if mtime else 'never (cannot stat the file)')
    if recovered:
        log(f"INPUT RECOVERED: {WEEWX_LOG_PATH} is being written again")
        send_email(
            f"{STATION_NAME}: monitoring input RECOVERED",
            f"{WEEWX_LOG_PATH} is growing again as of {datetime.now()}.\n"
            f"Uploader and reception checks have resumed.\n\n"
            f"Alerts sent while blind said nothing about station health.")
        return
    log(f"INPUT STALE: {WEEWX_LOG_PATH} unchanged for {int(stale_s)}s -- "
        f"checks suspended, NOT reporting station health")
    send_email(
        f"{STATION_NAME}: MONITORING BLIND - input stale, station state UNKNOWN",
        f"This is NOT a station alert. The monitor cannot see.\n\n"
        f"Input:      {WEEWX_LOG_PATH}\n"
        f"Last write: {seen}\n"
        f"Stale for:  {int(stale_s // 60)} min (threshold {INPUT_STALE_S // 60} min)\n"
        f"As of:      {datetime.now()}\n\n"
        f"Uploader and reception checks are SUSPENDED while this holds, so no\n"
        f"'DOWN' mail will follow. The station may be perfectly healthy; this\n"
        f"says only that the file this monitor reads has stopped changing.\n\n"
        f"Most likely causes, in the order they have actually happened here:\n"
        f"  - weewx moved host and this monitor still points at the old path\n"
        f"    (2026-08-29, ops#233: 14 h of false alerts about healthy uploaders)\n"
        f"  - the container is down, or stopped writing its log\n"
        f"  - the path is a stale mount, or an export that no longer covers it\n\n"
        f"Check the log path first, not the station.")


def check_input_freshness(now):
    """Update the blind latch. Returns True when the input is TRUSTWORTHY.

    Called once per poll, before any threshold is evaluated. When this returns
    False the caller must skip uploader and reception judgement entirely --
    every threshold in this file would otherwise fire on the same stale input
    and mail a confident, wrong answer."""
    stale = input_staleness(now)
    if stale > INPUT_STALE_S:
        if not BLIND['active']:
            BLIND['active'] = True
            BLIND['since'] = now
            BLIND['alerted_at'] = now
            send_blind_alert(stale, now)
        elif now - BLIND['alerted_at'] >= REPEAT:
            BLIND['alerted_at'] = now
            log(f"INPUT STALE: still blind after {int((now - BLIND['since'])//60)}min")
            send_blind_alert(stale, now)
        return False
    if BLIND['active']:
        BLIND['active'] = False
        send_blind_alert(0.0, now, recovered=True)
    return True


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
        # S82b (#180): this path used to log only, unlike the nonzero-exit
        # branch above which emails -- it fired live 2026-08-14 01:56:30 as a
        # 15 s sudo timeout and told nobody. A reset that never ran is at
        # least as alarming as one that ran and failed.
        log(f"RESET error: {e}")
        send_email(f"{STATION_NAME}: RTL-SDR reset FAILED",
                   f"{USB_RESET_SCRIPT} raised: {e}")

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


def campaign_inhibited():
    """True while an RX campaign has asked for no automatic action (S107).

    Cheap existence check, re-read every time rather than cached: a campaign
    starts and ends without restarting this monitor, so a value read once at
    startup would be wrong for the entire run that mattered."""
    return os.path.exists(CAMPAIGN_INHIBIT)


def remedy_action():
    """Human name of the action REMEDY_MODE will actually take.

    Exists for the same reason USB_RESET_ACTION does (S67, DEC-0074): months of
    logs named an operation that had stopped happening, and a reader reasoning
    from them reasons about the wrong mechanism. Now that the action is
    mode-selected, a single hardcoded string would be that defect by
    construction."""
    if REMEDY_MODE == 'restart_unit':
        return f'{REMEDY_SYSTEMCTL} restart {REMEDY_UNIT}'
    if REMEDY_MODE == 'usb_reset':
        return f'{USB_RESET_ACTION} via {USB_RESET_SCRIPT}'
    return 'no automatic remedy (REMEDY_MODE=none)'


def do_restart_unit(notify=True):
    """marvin's remedy: restart the systemd unit that owns the container.

    This is not the timid option. `weewx.service` is `docker run --rm` with
    `ExecStartPre=/usr/bin/docker rm -f`, so a restart is a FULL CONTAINER
    RECREATE -- the exact remedy that resolved ERR-0005 and the one the
    Foundation monitor could only rebuild via `docker inspect` and mail to a
    human to run by hand. It costs ~2-3 minutes of data, which is why
    RESET_MAX_TRIES bounds it to one attempt per outage, same as every other
    remedy here."""
    import subprocess
    cmd = REMEDY_SYSTEMCTL.split() + ['restart', REMEDY_UNIT]
    try:
        log(f"REMEDY: running {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            log(f"REMEDY: {REMEDY_UNIT} restart returned 0")
            if notify:
                send_email(f"{STATION_NAME}: weewx restarted",
                           f"Restarted {REMEDY_UNIT} at {datetime.now()} after a "
                           f"stall.\n\nThis is a full container recreate "
                           f"(docker run --rm + ExecStartPre rm -f).\n"
                           f"Expect a 2-3 minute gap in data around this time.")
        else:
            log(f"REMEDY error: rc={result.returncode} {result.stderr}")
            send_email(f"{STATION_NAME}: weewx restart FAILED",
                       f"{' '.join(cmd)} exited {result.returncode}:\n"
                       f"{result.stderr}")
    except Exception as e:
        # Same lesson as do_reset()'s exception path (S82b, #180): a remedy that
        # never ran is at least as alarming as one that ran and failed, and the
        # 15 s sudo timeout that told nobody is why that branch emails.
        log(f"REMEDY error: {e}")
        send_email(f"{STATION_NAME}: weewx restart FAILED",
                   f"{' '.join(cmd)} raised: {e}")


def reset_dongle(last_reset, notify=True):
    """Fire ONE automatic remedy, subject to cooldown and the campaign inhibit.

    Name retained deliberately: `watchdog_stall()` and the S62 escalation tests
    reach this by name, and renaming the single choke point through which every
    automatic action passes is not worth the churn (DEC-0014). What it DOES is
    now selected by REMEDY_MODE -- see that constant. Every log line here takes
    its wording from remedy_action() so the record can never again describe an
    operation that is not the one being performed (DEC-0074)."""
    now = time.time()
    if campaign_inhibited():
        # Detection is never inhibited; only action. Loud on purpose -- a silent
        # skip here would read, months later, exactly like a remedy that fired
        # and worked.
        log(f"SKIP remedy: campaign inhibit present ({CAMPAIGN_INHIBIT}); "
            f"would have run {remedy_action()}")
        return last_reset
    if REMEDY_MODE == 'none':
        log("SKIP remedy: REMEDY_MODE=none; detection and escalation only")
        return last_reset
    if now - last_reset < RESET_CD:
        log(f"SKIP remedy: cooldown ({int(now-last_reset)}s)")
        return last_reset
    log(f"REMEDY: {remedy_action()}")
    import threading
    target = do_restart_unit if REMEDY_MODE == 'restart_unit' else do_reset
    t = threading.Thread(target=target, kwargs={'notify': notify}, daemon=True)
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


def void_pending_verdict(reason):
    """Void a pending reset verdict that cannot be honestly judged (S82b, #180).

    The rotation-reset branch zeroes wu_bad_windows as OFFSET bookkeeping, not
    because reception verified good -- letting watchdog_poll() judge a pending
    reset by that zeroed counter logged 'verified effective' at midnight,
    mislabeled the verify-effective forensics capture (the control evidence
    DEC-0075/0081-class analysis depends on), and silently refreshed the
    RESET_MAX_TRIES hedge budget mid-episode. Voided loudly instead;
    tries/escalated stay exactly as they were."""
    if WD['check_at']:
        WD['check_at'] = 0.0
        log(f"RESET verdict void: {reason}")


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


def episode_persist():
    """Mirror the open episode to EPISODE_STATE (S82b, #180).

    No open episode -> the mirror is removed. Telemetry must never take the
    watchdog down (same rule as the ledger itself), so every failure here is
    logged and swallowed."""
    import json
    try:
        if not EP['onset']:
            if os.path.exists(EPISODE_STATE):
                os.remove(EPISODE_STATE)
            return
        tmp = EPISODE_STATE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(EP, f)
        os.replace(tmp, EPISODE_STATE)
    except OSError as e:
        log(f"EPISODE state persist failed: {e}")


def episode_load():
    """Restore an open episode left by a previous monitor process (startup).
    Returns True when one was restored. Any defect in the file is logged and
    ignored -- a corrupt mirror must not stop the monitor."""
    import json
    try:
        if not os.path.exists(EPISODE_STATE):
            return False
        with open(EPISODE_STATE) as f:
            saved = json.load(f)
        if not saved.get('onset'):
            return False
        EP.update({k: saved[k] for k in EP if k in saved})
        log("EPISODE restored from state file: open since %s "
            "(monitor restarted mid-episode)" % datetime.fromtimestamp(
                EP['onset']).strftime('%Y-%m-%d %H:%M:%S'))
        return True
    except Exception as e:
        log(f"EPISODE state load failed (ignored): {e}")
        return False


def episode_open(avg, now):
    EP['onset'] = now
    EP['stalls'] = EP['resets'] = EP['respawns'] = EP['droughts'] = 0
    EP['worst_avg'] = avg
    EP['last_cmd'] = ''
    episode_persist()


def episode_note_avg(avg):
    if EP['onset'] and avg < EP['worst_avg']:
        EP['worst_avg'] = avg
        episode_persist()


def episode_close(now):
    """Write the ledger row and clear. No-op if no episode is open.

    Order is row-first, then clear-and-remove-the-mirror: a crash between the
    two can at worst duplicate an adjacent ledger row on the next recovery,
    never lose one -- the mirror exists precisely because losing rows was the
    failure mode (S82b, #180)."""
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
    episode_persist()


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
    rxCheckPercent is the driver's metric: good CRC-decoded packets over
    floor(period / loop period) for that archive period. Per record the ISS
    transmits interval*tx_per_min packets; received ~= expected * pct/100, dropped =
    the rest.

    Each record's pct is CLAMPED at 100 before it is multiplied out (#313). The
    driver floors its denominator (60 s // 2.8125 s = 21 against 21.33 real
    transmissions, and a 59 s period floors to 20), so a fully received minute reads
    101-105% -- ~103% mean, measured once DEC-0135 unmasked it. Unclamped,
    'received' exceeds 'expected' and 'dropped' goes negative every good hour, and a
    daily total silently nets real loss against the over-read. Clamped, 'dropped' is
    a lower bound on real loss: it can under-count, never invent a negative. The
    number of clamped records is returned as 'over100' so the over-read stays
    visible rather than hidden.
    NULL-rxCheckPercent records (first record after a restart, or the pre-fix
    deadlock era) carry no reception info, so they are counted as 'gaps' and left
    out of the expected/received totals -- a conservative under-count of drops.
    Returns None when there is nothing for the day."""
    hours = {}
    for dt, interval_min, pct in rows:
        hour = time.localtime(dt).tm_hour
        h = hours.setdefault(hour, {'pcts': [], 'expected': 0.0, 'received': 0.0,
                                    'gaps': 0, 'over100': 0})
        if pct is None:
            h['gaps'] += 1
            continue
        exp = (interval_min or 1) * tx_per_min
        if pct > 100.0:
            h['over100'] += 1
            pct = 100.0
        h['pcts'].append(pct)
        h['expected'] += exp
        # exp * 100.0 / 100.0 is not always exp in floating point; a fully received
        # record must contribute exactly its expected packets so 'dropped' is 0, not 1e-13.
        h['received'] += exp if pct == 100.0 else exp * pct / 100.0
    day = {'expected': 0.0, 'received': 0.0, 'gaps': 0, 'records': 0, 'over100': 0,
           'hours': {}}
    for hour, h in hours.items():
        exp, rec, n = h['expected'], h['received'], len(h['pcts'])
        day['hours'][hour] = {
            'records': n, 'gaps': h['gaps'], 'over100': h['over100'],
            'mean_pct': (100.0 * rec / exp) if exp else None,
            'min_pct': min(h['pcts']) if h['pcts'] else None,
            'expected': exp, 'received': rec, 'dropped': exp - rec,
        }
        day['expected'] += exp
        day['received'] += rec
        day['gaps'] += h['gaps']
        day['records'] += n
        day['over100'] += h['over100']
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
    window (e.g. '2026-07-08 00:00–12:00'); rows are the hours present in the window.
    Per-record rxCheckPercent is clamped at 100% upstream (#313), so 'dropped' is a
    lower bound on real loss; the count of clamped records is printed so the driver's
    over-read stays visible."""
    lines = [
        f"{STATION_NAME} — RF Reception Summary — {label}",
        "Source: driver rxCheckPercent per archive record, clamped at 100%",
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
    lines.append(f"{'Mean reception:':<36}{mean:.0f}%" if mean is not None else
                 f"{'Mean reception:':<36}--")
    lines.append(f"{'Packets transmitted (est):':<36}{summary['expected']:.0f}")
    lines.append(f"{'Packets received (est):':<36}{summary['received']:.0f}")
    lines.append(f"{'Packets dropped (est, lower bound):':<36}{summary['dropped']:.0f}")
    if summary['gaps']:
        lines.append(f"Records with no reception data (gaps/restarts): {summary['gaps']}")
    if summary.get('over100'):
        lines.append(f"Records reading over 100% (clamped): {summary['over100']} of "
                     f"{summary['records']}")
    lines.append("")
    lines.append("Note: received = per-record rxCheckPercent x physical TX rate, each record "
                 "clamped at 100%. The driver floor-divides the archive period by the loop "
                 f"period (60 s -> {int(RF_TX_PER_MIN)}, a 59 s period -> {int(RF_TX_PER_MIN) - 1}) "
                 f"against {RF_TX_PER_MIN:.2f} real transmissions/min, so a fully received minute "
                 "reads 101-105% (~103% mean, measured since DEC-0135; #313). The clamp keeps "
                 "'dropped' a lower bound on real loss instead of netting good hours negative.")
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

    # S82b (#180): pick up an episode a previous monitor process left open.
    # wu_in_alert is re-derived from the restored onset (the two are the same
    # fact: an alert IS an open episode); the repeat clock restarts now so a
    # pre-restart REPEAT cannot double-send.
    if episode_load():
        wu_in_alert       = True
        wu_alert_sent_at  = EP['onset']
        wu_repeat_sent_at = time.time()

    log("Monitor started")
    log(f"Remedy armed: {remedy_action()}")
    send_email(f"{STATION_NAME}: monitor started", f"Started at {datetime.now()}")

    last_offset = get_log_size()
    log(f"Starting at log byte-offset {last_offset}")

    while True:
        time.sleep(POLL)
        now = time.time()

        cur = get_log_size()
        if cur < last_offset:
            log(f"Log reset detected (was {last_offset} bytes, now {cur}) - container restarted")
            void_pending_verdict("log rotated before the verification window closed")
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
                # Freshness signal first, and from EVERY line rather than the
                # ones we happen to match below: the point is to know the input
                # is alive, which is independent of whether it is interesting.
                _ts = parse_log_ts(line)
                if _ts:
                    BLIND['last_line_ts'] = _ts
                if 'rtldavis process stalled' in line:
                    log("STALL detected")
                    EP['stalls'] += 1
                    _reset_before = WD['last_reset']
                    watchdog_stall(wu_bad_windows)
                    if WD['last_reset'] != _reset_before:
                        EP['resets'] += 1
                    episode_persist()
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
                    episode_persist()
                elif 'DATA DROUGHT' in line:
                    # Driver ws.5 self-classification: receiver emitting,
                    # nothing decoding -- the RF-quiet class (S73).
                    EP['droughts'] += 1
                    episode_persist()
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

        # --- Is the input worth judging at all? (S107, ops#233) ---
        # Everything below this line is a "nothing seen for N seconds" test, and
        # a frozen input satisfies every one of them simultaneously and forever.
        # That is not a hypothetical: it is what shipped 14 hours of confident,
        # false "STILL DOWN" mail about six healthy uploaders. Judge the input
        # before judging the station.
        _was_blind = BLIND['active']
        if not check_input_freshness(now):
            continue
        if _was_blind:
            # Recovered. The window/period clocks have been parked for however
            # long the blindness lasted; carrying them forward would close a
            # single "window" spanning hours and read it as catastrophic
            # reception. Restart the accounting instead of reporting a number
            # built out of the gap.
            log("INPUT RECOVERED: restarting reception window accounting")
            wu_window_start   = now
            wu_window_epochs  = set()
            wu_period_counts  = []
            wu_period_start   = now
            wu_bad_windows    = 0
            wu_first_seen     = False
            void_pending_verdict("input was stale across the verification window")

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
                # Logged, not just emailed (ops#257 limb 3): the email-only path meant
                # this summary was unreachable by any ad-hoc tenant read.
                log(body)
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
