FROM node:12.18.1

RUN mkdir -p /app
RUN npm install express

COPY app.js /app

WORKDIR /app
RUN npm install

ARG NODE_AGENT_PACKAGE=
RUN npm install $NODE_AGENT_PACKAGE
