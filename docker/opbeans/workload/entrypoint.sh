#!/usr/bin/env bash

rm -rf Procfile
python3 generate_procfile.py "$OPBEANS_URLS" > Procfile

exec "$@"