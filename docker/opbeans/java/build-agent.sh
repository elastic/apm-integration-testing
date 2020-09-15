#!/usr/bin/env bash
set -xe
JAVA_AGENT_REPO=${1}
JAVA_AGENT_BRANCH=${2}

ARTIFACT_ID=elastic-apm-agent

if [ -n "${JAVA_AGENT_BRANCH}" ] ; then
  # build agent from source, install to ~/.m2 repo
  git clone "https://github.com/${JAVA_AGENT_REPO}.git" /apm-agent-java
  cd /apm-agent-java
  git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*'
  git checkout "${JAVA_AGENT_BRANCH}"

  mvn -q --batch-mode clean install \
    -DskipTests=true \
    -Dhttps.protocols=TLSv1.2 \
    -Dmaven.javadoc.skip=true \
    -Dmaven.wagon.http.retryHandler.count=3 \
    -Dhttp.keepAlive=false \
    -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn
  # shellcheck disable=SC2016
  VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec)
  export VERSION="${VERSION}"
  cp "/root/.m2/repository/co/elastic/apm/${ARTIFACT_ID}/${VERSION}/${ARTIFACT_ID}-${VERSION}.jar" /agent/elastic-apm-agent.jar
fi
