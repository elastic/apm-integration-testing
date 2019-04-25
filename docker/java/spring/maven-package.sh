#!/usr/bin/env bash
set -x
JAVA_AGENT_BUILT_VERSION=${1}

ARTIFACT_ID=elastic-apm-agent

if [ -z "${JAVA_AGENT_BUILT_VERSION}" ] ; then
  cd /agent/apm-agent-java
  mvn -q --batch-mode install -DskipTests \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn

  export JAVA_AGENT_BUILT_VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec)
else
  mvn -q --batch-mode org.apache.maven.plugins:maven-dependency-plugin:2.1:get \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
      -DrepoUrl=http://repo1.maven.apache.org/maven2 \
      -Dartifact=co.elastic.apm:${ARTIFACT_ID}:${JAVA_AGENT_BUILT_VERSION}
fi

cd /app
mvn -q --batch-mode -DAGENT_API_VERSION=${JAVA_AGENT_BUILT_VERSION} \
  -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
  package

cp /root/.m2/repository/co/elastic/apm/${ARTIFACT_ID}/${JAVA_AGENT_BUILT_VERSION}/${ARTIFACT_ID}-${JAVA_AGENT_BUILT_VERSION}.jar /agent/apm-agent.jar
