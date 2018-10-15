FROM golang:1.10
WORKDIR /go/src/testapp
COPY main.go /go/src/testapp
ARG go_agent_package=master
RUN go get github.com/elastic/apm-agent-go &&\
  cd $GOPATH/src/github.com/elastic/apm-agent-go &&\
  git checkout -b ${go_agent_package} &&\
  cd -
RUN CGO_ENABLED=0 go build

FROM alpine:latest
RUN apk add --update curl && rm -rf /var/cache/apk/*
COPY --from=0 /go/src/testapp/testapp /
EXPOSE 8080
ENV ELASTIC_APM_IGNORE_URLS /healthcheck
CMD ["/testapp"]
