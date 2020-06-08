ARG OPBEANS_NODE_IMAGE=opbeans/opbeans-node
ARG OPBEANS_NODE_VERSION=latest
FROM ${OPBEANS_NODE_IMAGE}:${OPBEANS_NODE_VERSION}

RUN apk update && \
    apk --no-cache add curl bash && \
    rm -rf /var/cache/apk/*

COPY entrypoint.sh /app/entrypoint.sh

CMD ["pm2-runtime", "ecosystem-workload.config.js"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
