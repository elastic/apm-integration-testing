FROM opbeans/opbeans-node:latest

RUN apk update && \
    apk --no-cache add curl bash && \
    rm -rf /var/cache/apk/*

COPY entrypoint.sh /app/entrypoint.sh

CMD ["pm2-runtime", "ecosystem-workload.config.js"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
