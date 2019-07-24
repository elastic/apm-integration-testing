ARG OPBEANS_PYTHON_IMAGE=opbeans/opbeans-python
ARG OPBEANS_PYTHON_VERSION=latest
FROM ${OPBEANS_PYTHON_IMAGE}:${OPBEANS_PYTHON_VERSION}

COPY entrypoint.sh /app/

CMD ["honcho", "start"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
