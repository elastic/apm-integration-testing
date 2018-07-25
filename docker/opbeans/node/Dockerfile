FROM opbeans/opbeans-node:latest

ENV NODE_ENV=production
RUN npm install pm2 -g

COPY entrypoint.sh /app/entrypoint.sh
COPY processes.config.js /app/processes.config.js

CMD ["pm2-runtime", "processes.config.js"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
