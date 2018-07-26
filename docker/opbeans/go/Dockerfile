FROM opbeans/opbeans-go:latest

ENV OPBEANS_CACHE=inmem
ENV OPBEANS_PORT=3000
EXPOSE $OPBEANS_PORT

HEALTHCHECK \
  --interval=10s --retries=10 --timeout=3s \
  CMD ["/opbeans-go", "-healthcheck", "localhost:3000"]

CMD ["/opbeans-go", "-listen=:3000", "-frontend=/opbeans-frontend", "-db=postgres:", "-cache=redis://redis:6379"]
