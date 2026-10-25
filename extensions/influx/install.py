# SPDX-License-Identifier: GPL-3.0-or-later
"""WeeWX extension installer for influx.py (DEC-0219, weewx-rtldavis#474).

Same extension name, service class and [StdRESTful][[Influx]] stanza as david-lutz/weewx-influx2,
so it replaces that extension in place and an existing weewx.conf keeps working.

Install:  weectl extension install <URL of the weewx-influx-VERSION.zip release asset>
"""
from weecfg.extension import ExtensionInstaller

# Keep equal to influx.VERSION; scripts/build_influx_zip.sh fails the build if they differ,
# or if the release tag disagrees.
VERSION = "0.20+ws.2"


def loader():
    return InfluxInstaller()


class InfluxInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            version=VERSION,
            name='influx',
            description='Upload weather data to InfluxDB 2.x (patched: Python 3.12+, '
                        'TLS verified by default).',
            author='Matthew Wall; David Lutz; WeatheredScientist',
            author_email='',
            restful_services='user.influx.Influx',
            config={
                'StdRESTful': {
                    'Influx': {
                        'server_url': 'http://localhost:8086',
                        'org': 'YOUR_INFLUX_ORG',
                        'bucket': 'YOUR_INFLUX_BUCKET',
                        'token': 'YOUR_INFLUX_TOKEN'}}},
            files=[('bin/user', ['bin/user/influx.py'])],
        )
