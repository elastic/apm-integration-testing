ARG OPBEANS_IMAGE=latest
FROM opbeans/opbeans-ruby:${OPBEANS_IMAGE}

COPY entrypoint.sh /app/entrypoint.sh

CMD ["bin/boot"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
