FROM golang:1.10
WORKDIR /go/src/testapp
COPY docker/go/nethttp/main.go /go/src/testapp
RUN go get github.com/elastic/apm-agent-go
RUN CGO_ENABLED=0 go build

FROM alpine:latest
COPY --from=0 /go/src/testapp/testapp /
EXPOSE 8080
CMD ["/testapp"]
