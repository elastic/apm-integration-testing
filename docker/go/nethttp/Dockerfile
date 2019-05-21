FROM golang:latest
ENV GO111MODULE=on
WORKDIR /src/testapp
COPY . /src/testapp
ARG GO_AGENT_REPO=elastic/apm-agent-go
ARG GO_AGENT_BRANCH=master
RUN git clone https://github.com/${GO_AGENT_REPO}.git /src/apm-agent-go
RUN (cd /src/apm-agent-go \
  && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
  && git checkout ${GO_AGENT_BRANCH})
RUN CGO_ENABLED=0 go build

FROM alpine:latest
RUN apk add --update curl && rm -rf /var/cache/apk/*
COPY --from=0 /src/testapp/testapp /
EXPOSE 8080
ENV ELASTIC_APM_IGNORE_URLS *healthcheck*
ENV ELASTIC_APM_API_REQUEST_TIME 50ms
CMD ["/testapp"]
