#!/usr/bin/env bash
set -x
JAVA_AGENT_BUILT_VERSION=${1}

if [ -z "${JAVA_AGENT_BUILT_VERSION}" ] ; then
  cd /agent/apm-agent-java
  mvn -q --batch-mode install -DskipTests \
      -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn

  export JAVA_AGENT_BUILT_VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec)
fi

cd /app
mvn -q --batch-mode -DAGENT_API_VERSION=${JAVA_AGENT_BUILT_VERSION} \
  -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
  package

cp /root/.m2/repository/co/elastic/apm/apm-agent-api/${JAVA_AGENT_BUILT_VERSION}/apm-agent-api-${JAVA_AGENT_BUILT_VERSION}.jar /agent/apm-agent.jar
