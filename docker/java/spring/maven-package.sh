#!/usr/bin/env bash
set -xe
JAVA_AGENT_BUILT_VERSION=${1}

ARTIFACT_ID=elastic-apm-agent

## This is for the CI
if [ -d "/.m2" ] ; then
  export MAVEN_CONFIG='-Dmaven.repo.local=/.m2'
fi

if [ -z "${JAVA_AGENT_BUILT_VERSION}" ] ; then
  cd /agent/apm-agent-java
  git --no-pager log -1
  mvn -q --batch-mode clean install \
    -DskipTests=true \
    -Dhttps.protocols=TLSv1.2 \
    -Dmaven.javadoc.skip=true \
    -Dmaven.wagon.http.retryHandler.count=10 \
    -Dhttp.keepAlive=false \
    -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn
  # shellcheck disable=SC2016
  JAVA_AGENT_BUILT_VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec)
  export JAVA_AGENT_BUILT_VERSION="${JAVA_AGENT_BUILT_VERSION}"
else
  mvn -q --batch-mode org.apache.maven.plugins:maven-dependency-plugin:2.1:get \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
      -Dhttps.protocols=TLSv1.2 \
      -DrepoUrl=https://repo1.maven.apache.org/maven2 \
      -Dmaven.wagon.http.retryHandler.count=10 \
      -Dhttp.keepAlive=false \
      -Dartifact="co.elastic.apm:${ARTIFACT_ID}:${JAVA_AGENT_BUILT_VERSION}"
fi

cd /app
mvn -q --batch-mode -DAGENT_API_VERSION="${JAVA_AGENT_BUILT_VERSION}" \
  -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
  -DskipTests=true \
  -Dhttps.protocols=TLSv1.2 \
  -Dmaven.javadoc.skip=true \
  -Dmaven.wagon.http.retryHandler.count=10 \
  -Dhttp.keepAlive=false \
  package

cp "/root/.m2/repository/co/elastic/apm/${ARTIFACT_ID}/${JAVA_AGENT_BUILT_VERSION}/${ARTIFACT_ID}-${JAVA_AGENT_BUILT_VERSION}.jar" /agent/apm-agent.jar
