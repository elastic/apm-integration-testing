ARG OPBEANS_NODE_IMAGE=opbeans/opbeans-node
ARG OPBEANS_NODE_VERSION=latest
FROM ${OPBEANS_NODE_IMAGE}:${OPBEANS_NODE_VERSION}

RUN apk --no-cache add rsync git
COPY entrypoint.sh /app/entrypoint.sh

CMD ["pm2-runtime", "ecosystem-workload.config.js"]
ENTRYPOINT ["/app/entrypoint.sh"]
