ARG OPBEANS_RUBY_IMAGE=opbeans/opbeans-ruby
ARG OPBEANS_RUBY_VERSION=latest
FROM ${OPBEANS_RUBY_IMAGE}:${OPBEANS_RUBY_VERSION}

RUN apk update && \
    apk --no-cache add curl bash && \
    rm -rf /var/cache/apk/*

COPY entrypoint.sh /app/entrypoint.sh

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
CMD ["bin/boot"]
