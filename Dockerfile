FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    git cmake libusb-1.0-0-dev libusb-dev python3-pip python3-venv \
    curl pkg-config busybox \
    && rm -rf /var/lib/apt/lists/*
RUN curl -L -o /tmp/go.tar.gz https://go.dev/dl/go1.24.4.linux-amd64.tar.gz && tar -C /usr/local -xzf /tmp/go.tar.gz && ln -s /usr/local/go/bin/go /usr/local/bin/go
RUN mkdir -p /etc/modprobe.d && echo "blacklist dvb_usb_rtl28xxu" > /etc/modprobe.d/blacklist_rtlsdr.conf
RUN cd /tmp && \
    git clone https://github.com/steve-m/librtlsdr.git && \
    cd librtlsdr && mkdir build && cd build && \
    cmake ../ -DINSTALL_UDEV_RULES=OFF -DDETACH_KERNEL_DRIVER=ON -DENABLE_ZEROCOPY=OFF && \
    make -j2 && make install && ldconfig
RUN curl -L -o /tmp/src.tgz https://github.com/weewx-contrib/weewx-rtldavis/raw/refs/heads/main/src.tgz && \
    cd /tmp && tar zxf src.tgz && \
    cd /tmp/src/rtldavis/src/lheijst/rtldavis && \
    GOBIN=/usr/local/bin go install -buildvcs=false -v .
RUN python3 -m venv /opt/weewx-venv && \
    /opt/weewx-venv/bin/pip install -q weewx requests
RUN /opt/weewx-venv/bin/weectl station create /opt/weewx-data --no-prompt
RUN /opt/weewx-venv/bin/weectl extension install /tmp/src/weewx-rtldavis --yes --config=/opt/weewx-data/weewx.conf && \
    /opt/weewx-venv/bin/weectl station reconfigure --driver=user.rtldavis --no-prompt --config=/opt/weewx-data/weewx.conf
RUN sed -i 's/frequency = EU/frequency = US/' /opt/weewx-data/weewx.conf && \
    sed -i 's/rain_bucket_type = 1/rain_bucket_type = 0/' /opt/weewx-data/weewx.conf && \
    sed -i 's|cmd = /home/pi/work/bin/rtldavis|cmd = /usr/local/bin/rtldavis|' /opt/weewx-data/weewx.conf && \
    sed -i 's/cmd = \/usr\/local\/bin\/rtldavis \[options\]/cmd = \/usr\/local\/bin\/rtldavis/' /opt/weewx-data/weewx.conf
RUN mkdir -p /opt/weewx-venv/lib/python3.10/site-packages/user && \
    touch /opt/weewx-venv/lib/python3.10/site-packages/user/__init__.py && \
    cp /opt/weewx-data/bin/user/rtldavis.py /opt/weewx-venv/lib/python3.10/site-packages/user/rtldavis.py
RUN sed -i "s/>APWEE5,TCPIP\*:/>APRS:/" /opt/weewx-venv/lib/python3.10/site-packages/weewx/restx.py
RUN /opt/weewx-venv/bin/python3 -c "import re; content = open('/opt/weewx-venv/lib/python3.10/site-packages/weewx/restx.py').read(); content = content.replace(\"                        self._send(_sock, login, dbg_msg='login')\\n                        # ... and then the packet\", \"                        self._send(_sock, login, dbg_msg='login')\\n                        import time; time.sleep(2)\\n                        # ... and then the packet\"); open('/opt/weewx-venv/lib/python3.10/site-packages/weewx/restx.py', 'w').write(content)" 
COPY entrypoint.sh /entrypoint.sh
COPY dewpoint_service.py /opt/weewx-venv/lib/python3.10/site-packages/user/dewpoint_service.py
COPY pressure_service.py /opt/weewx-venv/lib/python3.10/site-packages/user/pressure_service.py
COPY owm.py /opt/weewx-venv/lib/python3.10/site-packages/user/owm.py
COPY windy.py /opt/weewx-venv/lib/python3.10/site-packages/user/windy.py
COPY wcloud.py /opt/weewx-venv/lib/python3.10/site-packages/user/wcloud.py
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    git cmake libusb-1.0-0-dev libusb-dev python3-pip python3-venv \
    curl pkg-config busybox \
    && rm -rf /var/lib/apt/lists/*
RUN curl -L -o /tmp/go.tar.gz https://go.dev/dl/go1.24.4.linux-amd64.tar.gz && tar -C /usr/local -xzf /tmp/go.tar.gz && ln -s /usr/local/go/bin/go /usr/local/bin/go
RUN mkdir -p /etc/modprobe.d && echo "blacklist dvb_usb_rtl28xxu" > /etc/modprobe.d/blacklist_rtlsdr.conf
RUN cd /tmp && \
    git clone https://github.com/steve-m/librtlsdr.git && \
    cd librtlsdr && mkdir build && cd build && \
    cmake ../ -DINSTALL_UDEV_RULES=OFF -DDETACH_KERNEL_DRIVER=ON -DENABLE_ZEROCOPY=OFF && \
    make -j2 && make install && ldconfig
RUN curl -L -o /tmp/src.tgz https://github.com/weewx-contrib/weewx-rtldavis/raw/refs/heads/main/src.tgz && \
    cd /tmp && tar zxf src.tgz && \
    cd /tmp/src/rtldavis/src/lheijst/rtldavis && \
    GOBIN=/usr/local/bin go install -buildvcs=false -v .
RUN python3 -m venv /opt/weewx-venv && \
    /opt/weewx-venv/bin/pip install -q weewx requests
RUN /opt/weewx-venv/bin/weectl station create /opt/weewx-data --no-prompt
RUN /opt/weewx-venv/bin/weectl extension install /tmp/src/weewx-rtldavis --yes --config=/opt/weewx-data/weewx.conf && \
    /opt/weewx-venv/bin/weectl station reconfigure --driver=user.rtldavis --no-prompt --config=/opt/weewx-data/weewx.conf
RUN sed -i 's/frequency = EU/frequency = US/' /opt/weewx-data/weewx.conf && \
    sed -i 's/rain_bucket_type = 1/rain_bucket_type = 0/' /opt/weewx-data/weewx.conf && \
    sed -i 's|cmd = /home/pi/work/bin/rtldavis|cmd = /usr/local/bin/rtldavis|' /opt/weewx-data/weewx.conf && \
    sed -i 's/cmd = \/usr\/local\/bin\/rtldavis \[options\]/cmd = \/usr\/local\/bin\/rtldavis/' /opt/weewx-data/weewx.conf
RUN mkdir -p /opt/weewx-venv/lib/python3.10/site-packages/user && \
    touch /opt/weewx-venv/lib/python3.10/site-packages/user/__init__.py && \
    cp /opt/weewx-data/bin/user/rtldavis.py /opt/weewx-venv/lib/python3.10/site-packages/user/rtldavis.py
RUN sed -i "s/>APWEE5,TCPIP\*:/>APRS:/" /opt/weewx-venv/lib/python3.10/site-packages/weewx/restx.py
RUN /opt/weewx-venv/bin/python3 -c "import re; content = open('/opt/weewx-venv/lib/python3.10/site-packages/weewx/restx.py').read(); content = content.replace(\"                        self._send(_sock, login, dbg_msg='login')\\n                        # ... and then the packet\", \"                        self._send(_sock, login, dbg_msg='login')\\n                        import time; time.sleep(2)\\n                        # ... and then the packet\"); open('/opt/weewx-venv/lib/python3.10/site-packages/weewx/restx.py', 'w').write(content)"
COPY entrypoint.sh /entrypoint.sh
COPY dewpoint_service.py /opt/weewx-venv/lib/python3.10/site-packages/user/dewpoint_service.py
COPY pressure_service.py /opt/weewx-venv/lib/python3.10/site-packages/user/pressure_service.py
COPY owm.py /opt/weewx-venv/lib/python3.10/site-packages/user/owm.py
COPY windy.py /opt/weewx-venv/lib/python3.10/site-packages/user/windy.py
COPY wcloud.py /opt/weewx-venv/lib/python3.10/site-packages/user/wcloud.py
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
