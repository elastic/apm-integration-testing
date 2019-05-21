# Stage 0: clone opbeans-go and apm-agent-go, and build.
#
# GO_AGENT_REPO and GO_AGENT_BRANCH parameterise the Go agent
# repo and branch (or commit) to use.
FROM golang:latest
ENV GO111MODULE=on
WORKDIR /src/opbeans-go
RUN git clone https://github.com/elastic/opbeans-go.git .
RUN rm -fr vendor/go.elastic.co/apm
ARG GO_AGENT_REPO=elastic/apm-agent-go
ARG GO_AGENT_BRANCH=master
# adding this file will invalidate the layer cache when the branch head changes
ADD https://api.github.com/repos/${GO_AGENT_REPO}/git/refs/heads/${GO_AGENT_BRANCH} version.json
RUN git clone https://github.com/${GO_AGENT_REPO}.git /src/go.elastic.co/apm
RUN (cd /src/go.elastic.co/apm && git checkout ${GO_AGENT_BRANCH})
# Add "replace" stanzas to go.mod to use the local agent repo
RUN go list -m all | grep apm | cut -d' ' -f1 | xargs -i go mod edit -replace {}=/src/{}
RUN go build

# Stage 1: copy static assets from opbeans/opbeans-frontend and
# opbeans-go from stage 0 into a minimal image.
FROM gcr.io/distroless/base
COPY --from=opbeans/opbeans-frontend:latest /app/build /opbeans-frontend
COPY --from=0 /src/opbeans-go/opbeans-go /
COPY --from=0 /src/opbeans-go/db /
EXPOSE 3000

HEALTHCHECK \
  --interval=10s --retries=10 --timeout=3s \
  CMD ["/opbeans-go", "-healthcheck", "localhost:3000"]

CMD ["/opbeans-go", "-log-json", "-log-level=debug", "-listen=:3000", "-frontend=/opbeans-frontend", "-db=postgres:", "-cache=redis://redis:6379"]
