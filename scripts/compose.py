#!/usr/bin/env python
"""CLI for starting a testing environment using docker-compose."""
from __future__ import print_function

import logging
import subprocess
import sys

from modules.cli import LocalSetup


def main():
    # Enable logging
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    setup = LocalSetup(sys.argv[1:])
    setup()


def verify_if_docker_is_installed():
    try:
        subprocess.check_call('docker ps')
    except OSError as err:
        print("Please start Docker before running the apm-integration-testing.")
        sys.exit(1)


if __name__ == '__main__':
    verify_if_docker_is_installed()
    main()
