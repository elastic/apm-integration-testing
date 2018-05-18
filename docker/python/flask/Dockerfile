FROM python:3

RUN pip install -U Flask blinker gunicorn

RUN mkdir -p /app
COPY app.py /app

WORKDIR /app
