ARG OPBEANS_PYTHON_IMAGE=opbeans/opbeans-python
ARG OPBEANS_PYTHON_VERSION=latest
FROM ${OPBEANS_PYTHON_IMAGE}:${OPBEANS_PYTHON_VERSION}
ENV ELASTIC_APM_ENABLE_LOG_CORRELATION=true

COPY entrypoint.sh /app/

CMD ["honcho", "start", "--no-prefix"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
