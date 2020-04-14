FROM alpine:3.7
RUN apk add --no-cache curl jq
COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
