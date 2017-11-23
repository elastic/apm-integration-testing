FROM python:3

RUN pip install -U Flask blinker gunicorn

RUN mkdir -p /app
COPY docker/python/flask/app.py /app

WORKDIR /app
