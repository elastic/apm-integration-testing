FROM node:8

RUN mkdir -p /app
WORKDIR /app
ADD . /app

#TODO: move this to CMD/runtime
RUN npm install elastic/apm-agent-nodejs#master && \
    npm install express
ENTRYPOINT cd /app && node app.js
