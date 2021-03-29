ARG OPBEANS_PYTHON_IMAGE=opbeans/opbeans-python
ARG OPBEANS_PYTHON_VERSION=latest
FROM ${OPBEANS_PYTHON_IMAGE}:${OPBEANS_PYTHON_VERSION}
ENV ELASTIC_APM_ENABLE_LOG_CORRELATION=true

# postgresql-client is used for the dbshell command in the entrypoint
RUN apt-get -qq update \
 && apt-get -qq install -y \
    postgresql-client \
	--no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /app/

CMD ["honcho", "start", "--no-prefix"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
