#--------------------------------------------
# weewx-rtldavis v2.0.6
# Ubuntu 26.04 LTS / Python 3.14 / weewx 5.x
# Multistage build for minimal runtime image
#
# Credits:
# weewx: Tom Keffer and Matthew Wall (weewx.com)
# weewx-rtldavis weewx extension: Luc Heijst (github.com/lheijst/weewx-rtldavis)
# weewx-rtldavis installer wrapper: Vince Skahan (github.com/weewx-contrib/weewx-rtldavis)
# rtldavis Go binary: Luc Heijst (github.com/lheijst/rtldavis)
# gortlsdr Go wrapper: Joseph Poirier (github.com/jpoirier/gortlsdr)
# librtlsdr: Steve Markgraf (original), Kacper Ludwinski (current maintainer)
#   (github.com/steve-m/librtlsdr)
#--------------------------------------------

FROM ubuntu:26.04 AS base

ENV DEBIAN_FRONTEND=noninteractive

#--------------------------------------------
# Install build dependencies
#--------------------------------------------
RUN apt-get update && apt-get install -y \
    cmake \
    curl \
    gcc \
    golang \
    libusb-1.0-0-dev \
    libusb-dev \
    make \
    python3-pip \
    python3-venv \
    rtl-sdr \
    && rm -rf /var/lib/apt/lists/*

#--------------------------------------------
# Blacklist DVB kernel module that conflicts with RTL-SDR
#--------------------------------------------
RUN mkdir -p /etc/modprobe.d && \
    echo "blacklist dvb_usb_rtl28xxu" > /etc/modprobe.d/blacklist_rtlsdr.conf

#--------------------------------------------
# Build librtlsdr and rtldavis Go binary from src.tgz
# librtlsdr is bundled in src.tgz — no git clone needed
#--------------------------------------------
RUN curl -L -o /tmp/src.tgz \
    https://github.com/weewx-contrib/weewx-rtldavis/raw/refs/heads/main/src.tgz && \
    cd /tmp && tar zxf src.tgz && \
    cd /tmp/src/librtlsdr && \
    mkdir build && cd build && \
    cmake ../ -DINSTALL_UDEV_RULES=OFF -DDETACH_KERNEL_DRIVER=ON -DENABLE_ZEROCOPY=OFF && \
    make -j2 && make install && ldconfig && \
    cd /tmp/src/rtldavis/src/lheijst/rtldavis && \
    echo "receiveWindow (upstream default, unpatched — rw350 is an unproven experiment; 24h sweep backlogged, see ROADMAP/ARCHITECTURE §6):" && grep -R "receiveWindow" . && \
    GOBIN=/usr/local/bin go install -buildvcs=false -v .

#--------------------------------------------
# Install weewx and configure for rtldavis
#--------------------------------------------
RUN python3 -m venv --copies /opt/weewx-venv && \
    /opt/weewx-venv/bin/pip install -q weewx requests && \
    /opt/weewx-venv/bin/weectl station create /opt/weewx-data --no-prompt && \
    /opt/weewx-venv/bin/weectl extension install /tmp/src/weewx-rtldavis \
        --yes --config=/opt/weewx-data/weewx.conf && \
    /opt/weewx-venv/bin/weectl extension install https://github.com/david-lutz/weewx-influx2/archive/master.zip --yes --config=/opt/weewx-data/weewx.conf && \
    /opt/weewx-venv/bin/weectl station reconfigure \
        --driver=user.rtldavis --no-prompt --config=/opt/weewx-data/weewx.conf && \
    sed -i 's/frequency = EU/frequency = US/' /opt/weewx-data/weewx.conf && \
    sed -i 's/rain_bucket_type = 1/rain_bucket_type = 0/' /opt/weewx-data/weewx.conf && \
    sed -i 's|cmd = /home/pi/work/bin/rtldavis|cmd = /usr/local/bin/rtldavis|' \
        /opt/weewx-data/weewx.conf && \
    sed -i 's/cmd = \/usr\/local\/bin\/rtldavis \[options\]/cmd = \/usr\/local\/bin\/rtldavis/' \
        /opt/weewx-data/weewx.conf && \
    sed -i 's/debug = 0/debug = 0/' /opt/weewx-data/weewx.conf && \
    rm -rf /tmp/*

#--------------------------------------------
# Add logging config (file + stdout)
#--------------------------------------------
COPY logging.additions /tmp/logging.additions
RUN cat /tmp/logging.additions >> /opt/weewx-data/weewx.conf && \
    rm /tmp/logging.additions

#--------------------------------------------
# Remove StdPrint from the baked default config (DEC-0041)
#--------------------------------------------
# weewx ships with StdPrint enabled by default. It print()s every LOOP packet
# straight to stdout, BYPASSING the logging handlers -- so the console handler
# level (set to WARNING in logging.additions) does NOT quiet it. That was the
# hole left open by v2.0.5.
#
# In a container, stdout is a pipe drained by the Docker daemon. On Synology the
# store behind it is a SQLite log.db that CANNOT be size-capped (the `db` driver
# accepts --log-opt max-size and silently ignores it -- measured). If that
# consumer stalls, the 64 KB pipe fills and weewx blocks FOREVER on its next
# print: no crash, no traceback, container still "Up". That is DEC-0036, a
# 7h18m outage. StdPrint was writing ~25 MB/day into that pipe.
#
# It buys nothing in a container: nothing reads stdout, and the full log already
# goes to the rotating FILE that we and weewx_monitor.py actually read.
RUN sed -i 's|^\([[:space:]]*\)report_services = weewx.engine.StdPrint, weewx.engine.StdReport|\1report_services = weewx.engine.StdReport|' /opt/weewx-data/weewx.conf && \
    grep -q '^[[:space:]]*report_services = weewx.engine.StdReport$' /opt/weewx-data/weewx.conf || \
    (echo "FATAL: StdPrint removal did not apply — the baked config would ship the freeze hazard" && exit 1)

#--------------------------------------------
# Copy custom service files
#--------------------------------------------
COPY dewpoint_service.py /opt/weewx-venv/lib/python3.14/site-packages/user/dewpoint_service.py
COPY pressure_service.py /opt/weewx-venv/lib/python3.14/site-packages/user/pressure_service.py
COPY owm.py /opt/weewx-venv/lib/python3.14/site-packages/user/owm.py
COPY windy.py /opt/weewx-venv/lib/python3.14/site-packages/user/windy.py
COPY wcloud.py /opt/weewx-venv/lib/python3.14/site-packages/user/wcloud.py
COPY influx.py /opt/weewx-venv/lib/python3.14/site-packages/user/influx.py

#--------------------------------------------
# Copy the patched rtldavis.py — the driver weewx actually imports (user.* resolves
# to venv site-packages/user). Carries: windDir fix (v2.0.2), rain spike filter,
# the S24 H1/H2/M3 fixes (H2 revives rxCheckPercent), and the SensorQC
# decode-layer plausibility filter (DEC-0029). v2.0.4.
#--------------------------------------------
COPY rtldavis.py /opt/weewx-venv/lib/python3.14/site-packages/user/rtldavis.py

# NOTE: do NOT copy /opt/weewx-data/bin/user/rtldavis.py over the venv copy here.
# That path holds the STOCK driver from `weectl extension install` (upstream
# src.tgz) and would clobber the patched rtldavis.py COPY'd above — which is the
# file weewx actually imports (user.* resolves to the venv site-packages/user).
# The old `cp` silently shipped the stock driver (no rain filter, no H1/H2/M3).
RUN touch /opt/weewx-venv/lib/python3.14/site-packages/user/__init__.py && \
    touch /opt/weewx-venv/lib/python3.14/site-packages/user/extensions.py

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

#--------------------------------------------
# Minimal runtime image
# Only copies what's needed to run weewx
#--------------------------------------------
FROM ubuntu:26.04 AS minimal

ENV DEBIAN_FRONTEND=noninteractive

COPY --from=base /opt/weewx-venv /opt/weewx-venv
COPY --from=base /opt/weewx-data /opt/weewx-data
COPY --from=base /usr/local /usr/local
COPY --from=base /entrypoint.sh /entrypoint.sh
COPY --from=base /etc/modprobe.d /etc/modprobe.d

RUN apt-get update && apt-get install -y \
    libusb-1.0-0 \
    python3 \
    python3-venv \
    rtl-sdr \
    && apt-get clean autoclean \
    && apt-get autoremove --yes \
    && rm -rf /var/lib/{apt,dpkg,cache,log} \
    && rm -rf /usr/share/{doc,man,info} \
    && ln -sf /usr/bin/python3 /opt/weewx-venv/bin/python3 \
    && chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
