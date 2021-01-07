#!/bin/bash
echo "Staring server.."
gunicorn -b 0.0.0.0 dyno.app:app --capture-output  -t 90 -w 8
