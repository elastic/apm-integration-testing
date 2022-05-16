FROM node:16.15.0

RUN mkdir -p /app
COPY package.json .npmrc app.js /app/

WORKDIR /app
RUN npm install

