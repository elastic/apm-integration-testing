FROM opbeans/opbeans-node:latest

ENV NODE_ENV=production

COPY entrypoint.sh /app/entrypoint.sh

CMD ["pm2-runtime", "ecosystem-workload.config.js"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
