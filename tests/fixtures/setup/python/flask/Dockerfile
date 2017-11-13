FROM python:3

RUN mkdir -p /app
COPY tests/fixtures/setup/python/flask/requirements.txt /app
COPY tests/agent/python/flask/app.py /app

WORKDIR /app
