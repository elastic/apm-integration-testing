ARG OPBEANS_NODE_IMAGE=latest
FROM opbeans/opbeans-node:${OPBEANS_NODE_IMAGE}

COPY entrypoint.sh /app/entrypoint.sh

CMD ["pm2-runtime", "ecosystem-workload.config.js"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
