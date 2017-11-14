FROM python:3

RUN pip install -U django

RUN mkdir -p /app
COPY docker/python/django/testapp /app/testapp

WORKDIR /app
