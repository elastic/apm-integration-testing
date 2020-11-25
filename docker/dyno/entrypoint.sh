#!/bin/bash
echo "Staring server.."
gunicorn -b 0.0.0.0 app:app --capture-output  -t 90 -w 8
