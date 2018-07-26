FROM opbeans/opbeans-python:latest

COPY entrypoint.sh /app/

CMD ["honcho", "start"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]