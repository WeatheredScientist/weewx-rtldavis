#!/bin/bash
GAIN=$1
python3 -c "
import re
with open('/volume1/docker/weewx-rtldavis/weewx-data/weewx.conf', 'r') as f:
    c = f.read()
c = re.sub(r'-gain [0-9]+', '-gain ' + '$GAIN', c)
with open('/volume1/docker/weewx-rtldavis/weewx-data/weewx.conf', 'w') as f:
    f.write(c)
print('Gain set to ' + '$GAIN')
"
docker kill weewx-rtldavis-v2
docker start weewx-rtldavis-v2
