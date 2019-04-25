FROM maven:3.5.3-jdk-10

ARG JAVA_AGENT_REPO=elastic/apm-agent-java
ARG JAVA_AGENT_BRANCH=master
ARG JAVA_AGENT_BUILT_VERSION=

RUN mkdir /agent \
    && mkdir /app

COPY testapp /app

WORKDIR /agent

RUN git clone https://github.com/${JAVA_AGENT_REPO}.git /agent/apm-agent-java
RUN cd /agent/apm-agent-java \
  && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
  && git checkout ${JAVA_AGENT_BRANCH}

## If the JAVA_AGENT_BUILT_VERSION is set then download the release artifact from maven.org
RUN [ -n "${JAVA_AGENT_BUILT_VERSION}" ] && (curl -s https://search.maven.org/remotecontent?filepath=co/elastic/apm/elastic-apm-agent/${JAVA_AGENT_BUILT_VERSION}/elastic-apm-agent-${JAVA_AGENT_BUILT_VERSION}.jar -o /agent/apm-agent.jar \
    && mvn -q --batch-mode install:install-file \
      -Dfile=/agent/apm-agent.jar \
      -DgroupId=co.elastic.apm -DartifactId=apm-agent-api -Dversion=${JAVA_AGENT_BUILT_VERSION} \
      -Dpackaging=jar \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn) || echo true

## If the JAVA_AGENT_BUILT_VERSION is not set then build from the source code
RUN [ -z "${JAVA_AGENT_BUILT_VERSION}" ] && (cd /agent/apm-agent-java \
    && mvn -q --batch-mode package -DskipTests \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
    && export JAVA_AGENT_BUILT_VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec) \
    && mv elastic-apm-agent/target/elastic-apm-agent-${JAVA_AGENT_BUILT_VERSION}.jar /agent/apm-agent.jar \
    && mvn -q --batch-mode install:install-file \
      -Dfile=apm-agent-api/target/apm-agent-api-${JAVA_AGENT_BUILT_VERSION}.jar \
      -DgroupId=co.elastic.apm -DartifactId=apm-agent-api -Dversion=${JAVA_AGENT_BUILT_VERSION} \
      -Dpackaging=jar \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn) || echo true

RUN cd /app \
    && mvn -q --batch-mode -DAGENT_API_VERSION=${JAVA_AGENT_BUILT_VERSION} \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
      package

FROM openjdk:10-jre-slim
COPY --from=0 /app /app
COPY --from=0 /agent/apm-agent.jar  /app
RUN apt-get -qq update \
  && apt-get -qq install -y curl \
  && apt-get -qq clean \
  && rm -fr /var/lib/apt/lists/* 
WORKDIR /app
EXPOSE 8090
ENV ELASTIC_APM_API_REQUEST_TIME 50ms
CMD ["java", "-javaagent:/app/apm-agent.jar", "-Delastic.apm.service_name=springapp", "-Delastic.apm.application_packages=hello", "-Delastic.apm.max_queue_size=2048", "-Delastic.apm.ignore_urls=/healthcheck", "-jar","/app/target/hello-spring-0.1.jar"]


