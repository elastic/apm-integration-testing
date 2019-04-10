FROM golang:1.11
ENV CGO_ENABLED=0
# use fork to quickly pin https://github.com/chrislusf/teeproxy
RUN go get -v github.com/graphaelli/teeproxy
RUN go install github.com/graphaelli/teeproxy
CMD ["teeproxy"]
