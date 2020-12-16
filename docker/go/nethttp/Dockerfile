FROM golang:1.14
WORKDIR /go/src/testapp
COPY main.go /go/src/testapp
ARG GO_AGENT_REPO=elastic/apm-agent-go
ARG GO_AGENT_BRANCH=master
RUN git clone https://github.com/${GO_AGENT_REPO}.git /go/src/go.elastic.co/apm
RUN (cd /go/src/go.elastic.co/apm \
  && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
  && git checkout ${GO_AGENT_BRANCH})
RUN CGO_ENABLED=0 go get -v

FROM alpine:latest
RUN apk add --update curl && rm -rf /var/cache/apk/*
COPY --from=0 /go/bin/testapp /
EXPOSE 8080
ENV ELASTIC_APM_IGNORE_URLS *healthcheck*
ENV ELASTIC_APM_API_REQUEST_TIME 50ms
CMD ["/testapp"]
