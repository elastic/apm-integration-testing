FROM maven:3.6.3-adoptopenjdk-11

ARG JAVA_AGENT_REPO=elastic/apm-agent-java
ARG JAVA_AGENT_BRANCH=main
ARG JAVA_AGENT_BUILT_VERSION=
ARG JAVA_M2_CACHE=false

RUN mkdir /agent \
    && mkdir /app

COPY testapp /app

WORKDIR /agent

RUN git clone https://github.com/${JAVA_AGENT_REPO}.git /agent/apm-agent-java
RUN cd /agent/apm-agent-java \
  && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
  && git checkout ${JAVA_AGENT_BRANCH}

COPY maven-package.sh /agent
COPY .m2 /root/.m2
RUN ./maven-package.sh "${JAVA_AGENT_BUILT_VERSION}"

FROM adoptopenjdk:11-jre-hotspot
COPY --from=0 /app /app
COPY --from=0 /agent/apm-agent.jar /app
RUN apt-get -qq update \
  && apt-get -qq install -y --no-install-recommends curl \
  && apt-get -qq clean \
  && rm -fr /var/lib/apt/lists/*
WORKDIR /app
EXPOSE 8090
ENV ELASTIC_APM_API_REQUEST_TIME 50ms
CMD ["java", "-javaagent:/app/apm-agent.jar", "-Delastic.apm.service_name=springapp", "-Delastic.apm.application_packages=hello", "-Delastic.apm.max_queue_size=2048", "-Delastic.apm.ignore_urls=/healthcheck", "-jar","/app/target/hello-spring-0.1.jar"]
