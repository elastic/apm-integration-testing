FROM node:boron

WORKDIR /app
ENV BUILDDATE="2018-04-10"
ENV ELASTIC_APM_JS_BASE_SERVICE_VERSION="v${BUILDDATE}"
RUN curl -L https://github.com/elastic/opbeans/archive/master.tar.gz | tar --strip-components=1 -xzv
ENV NODE_ENV=production
ENV ELASTIC_APM_JS_BASE_SERVER_URL=http://apm-server:8200
ENV ELASTIC_APM_JS_BASE_SERVICE_NAME=opbeans-react
RUN npm install && npm run client-install && npm install pm2 -g

RUN npm run client-build
COPY entrypoint.sh /app/entrypoint.sh
COPY processes.config.js /app/processes.config.js

CMD ["pm2-docker", "processes.config.js"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
