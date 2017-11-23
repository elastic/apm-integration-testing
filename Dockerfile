FROM python:3

RUN pip install -U pytest pytest-random-order requests timeout-decorator elasticsearch tornado pyyaml

COPY . /app
WORKDIR /app
