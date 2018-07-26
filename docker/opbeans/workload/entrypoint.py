#!/bin/env python3

import os
import sys
from urllib.parse import urlparse

services = os.environ['OPBEANS_URLS'].split(',')
with open('Procfile', mode='w') as procfile:
    for service_url in services:
        parsed_url = urlparse(service_url)
        service_name = parsed_url.netloc.split(':')[0]
        process_name = service_name.split('-', maxsplit=1)[1].replace('-', '') # we use second part of name and strip all remaining dashes
        procfile.write(
            '{0}: OPBEANS_BASE_URL={1} OPBEANS_NAME={2} molotov --duration {3} --delay 0.6 --uvloop molotov_scenarios.py\n'.format(
                process_name,
                service_url,
                service_name,
                365*24*60*60,
            )
        )

os.execvp(sys.argv[1], sys.argv[1:])