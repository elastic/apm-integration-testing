FROM opbeans/opbeans-ruby:latest

RUN apk update && \
    apk --no-cache add curl bash && \
    rm -rf /var/cache/apk/*

COPY entrypoint.sh /app/entrypoint.sh

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
CMD ["bin/boot"]
