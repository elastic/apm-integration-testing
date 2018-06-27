FROM golang:1.10
ARG GO_AGENT_BRANCH=master
ARG GO_AGENT_REPO=elastic/apm-agent-go

WORKDIR /go/src/github.com/elastic/apm-agent-go
RUN curl -L https://github.com/$GO_AGENT_REPO/archive/$GO_AGENT_BRANCH.tar.gz | tar --strip-components=1 -xzv

WORKDIR /go/src/github.com/elastic/opbeans-go
RUN curl -L https://github.com/elastic/opbeans-go/archive/master.tar.gz | tar --strip-components=1 -xzv
RUN CGO_ENABLED=0 go get -v

FROM alpine:latest
COPY --from=opbeans/opbeans-frontend:latest /app/build /opbeans-frontend
COPY --from=0 /go/bin/opbeans-go /
ENV OPBEANS_CACHE=inmem
ENV OPBEANS_PORT=3003
EXPOSE $OPBEANS_PORT

HEALTHCHECK \
  --interval=10s --retries=10 --timeout=3s \
  CMD /opbeans-go -healthcheck localhost:${OPBEANS_PORT}

CMD /opbeans-go -listen=:$OPBEANS_PORT -frontend=/opbeans-frontend -db=postgres: -cache=$OPBEANS_CACHE
