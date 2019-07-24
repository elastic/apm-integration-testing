ARG OPBEANS_IMAGE=latest
FROM opbeans/opbeans-python:${OPBEANS_IMAGE}

COPY entrypoint.sh /app/

CMD ["honcho", "start"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
