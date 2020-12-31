FROM alpine:latest
RUN apk update && apk add --no-cache bash \
    && apk add curl \ 
    && apk add jq

COPY docker-entrypoint.sh /

CMD ["./docker-entrypoint.sh"]