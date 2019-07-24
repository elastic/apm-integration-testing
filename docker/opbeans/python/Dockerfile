ARG OPBEANS_PYTHON_IMAGE=latest
FROM opbeans/opbeans-python:${OPBEANS_PYTHON_IMAGE}

COPY entrypoint.sh /app/

CMD ["honcho", "start"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
