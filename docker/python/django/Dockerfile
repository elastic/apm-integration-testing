FROM python:3

RUN pip install -q -U Django==2.1.5

RUN mkdir -p /app
COPY testapp /app/testapp

WORKDIR /app
