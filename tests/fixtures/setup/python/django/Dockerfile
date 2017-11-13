FROM python:3

RUN mkdir -p /app
COPY tests/fixtures/setup/python/django/requirements.txt /app
COPY tests/agent/python/django/testapp /app/testapp

WORKDIR /app
