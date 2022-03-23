ARG STACK_VERSION=8.2.0-SNAPSHOT
FROM docker.elastic.co/beats-dev/golang-crossbuild:1.17.8-main-debian10 as build
ARG ELASTIC_AGENT_BRANCH_OR_COMMIT="main"
ARG ELASTIC_AGENT_REPO=https://github.com/elastic/apm-server.git
ARG STACK_VERSION=8.2.0-SNAPSHOT

ENV SRC=/go/src/github.com/elastic/apm-server
ENV GOOS=linux

RUN git clone ${ELASTIC_AGENT_REPO} ${SRC} \
  && cd ${SRC} \
  && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
  && git checkout ${ELASTIC_AGENT_BRANCH_OR_COMMIT} \
  && git rev-parse HEAD \
  && echo ${ELASTIC_AGENT_BRANCH_OR_COMMIT}

RUN cd ${SRC} \
  && go install github.com/magefile/mage@v1.12.1 \
  && version=$(mage version) \
  && apmdir=apm-server-${version}-linux-x86_64 \
  && builddir=build/distributions/${apmdir} \
  && mkdir -p ${builddir} \
  && cp -f LICENSE.txt NOTICE.txt README.md apm-server.yml ${builddir} \
  && go build -o ${builddir}/apm-server ./x-pack/apm-server \
  && cd build/distributions \
  && tar -czf /apm-server.tgz ${apmdir}

ARG STACK_VERSION=8.2.0-SNAPSHOT
FROM docker.elastic.co/beats/elastic-agent:${STACK_VERSION}

USER root
COPY --from=build /apm-server.tgz /tmp
RUN cat /usr/share/elastic-agent/.build_hash.txt|cut -b 1-6 > /sha.txt
#RUN rm /usr/share/elastic-agent/data/elastic-agent-$(cat /sha.txt)/downloads/apm-server*
RUN dst=/usr/share/elastic-agent/data/elastic-agent-$(cat /sha.txt)/install \
  && mkdir -p ${dst} \
  && tar -xzf /tmp/apm-server.tgz -C ${dst} \
  && rm /tmp/apm-server.tgz \
  && chown -R elastic-agent:elastic-agent ${dst}
USER elastic-agent
# Add healthcheck for docker/healthcheck metricset to check during testing
HEALTHCHECK CMD exit 0
