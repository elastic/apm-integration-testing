FROM golang:latest
ENV GO111MODULE=on
WORKDIR /src/apmpkg
COPY . /src/apmpkg
RUN CGO_ENABLED=0 go build -o /apmpkg

FROM alpine
RUN apk --no-cache add ca-certificates --update curl
COPY --from=0 /apmpkg /apmpkg


CMD ["/apmpkg"]
