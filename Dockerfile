FROM node:12-buster
RUN npm install elasticdump -g

FROM python:3.7-buster
COPY requirements.txt requirements.txt
RUN pip install -q -r requirements.txt

RUN useradd -U -m -s /bin/bash -d /app tester

COPY . /app
WORKDIR /app
USER tester
