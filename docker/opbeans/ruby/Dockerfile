ARG OPBEANS_RUBY_IMAGE=opbeans/opbeans-ruby
ARG OPBEANS_RUBY_VERSION=latest
FROM ${OPBEANS_RUBY_IMAGE}:${OPBEANS_RUBY_VERSION}
ENV ELASTIC_APM_LOG_LEVEL=DEBUG

COPY entrypoint.sh /app/entrypoint.sh

CMD ["bin/boot"]
ENTRYPOINT ["/app/entrypoint.sh"]
