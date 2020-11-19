#!/usr/bin/env python
"""CLI for starting a testing environment using docker-compose."""
from __future__ import print_function

import logging
import sys

from modules.cli import LocalSetup


def main():
    # Enable logging
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    setup = LocalSetup(sys.argv[1:])
    setup()


if __name__ == '__main__':
    main()
