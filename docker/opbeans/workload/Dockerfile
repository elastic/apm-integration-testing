FROM node:carbon

WORKDIR /app

ADD . /app

RUN npm install && npm install foreman

CMD ["./node_modules/.bin/nf", "start"]
