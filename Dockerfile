FROM node:12-buster as BUILD_IMAGE
WORKDIR /app
RUN npm install elasticdump

FROM python:3.7-buster
COPY requirements.txt requirements.txt
RUN pip install -q -r requirements.txt

RUN useradd -U -m -s /bin/bash -d /app tester
COPY . /app
WORKDIR /app
COPY --from=BUILD_IMAGE /app .
RUN ln -s /app/node_modules/elasticdump/bin/elasticdump /usr/local/bin/elasticdump
RUN ln -s /app/node_modules/elasticdump/bin/multielasticdump /usr/local/bin/multielasticdump
COPY --from=BUILD_IMAGE /usr/local/bin/node /usr/local/bin/node
USER tester
