ARG go_version=1.17.7
FROM golang:${go_version} AS build
ENV CGO_ENABLED=0
# TODO(marclop) After https://github.com/elastic/apm-server/pull/7416 is merged, replace git clone
# with 'go install https://github.com/elastic/apm-server/cmd/intake-receiver@latest'.
RUN git clone --single-branch --branch f-add-intake-receiver https://github.com/marclop/apm-server /apm-server
RUN cd /apm-server/cmd/intake-receiver && go build .

FROM alpine
COPY --from=build /apm-server/cmd/intake-receiver/intake-receiver /intake-receiver
RUN apk update && apk add curl jq
ENTRYPOINT [ "/intake-receiver" ]

CMD [ "-host=0.0.0.0:8200" ]
