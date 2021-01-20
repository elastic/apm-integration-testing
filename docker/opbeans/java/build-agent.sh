#!/usr/bin/env bash
set -xe
JAVA_AGENT_REPO=${1}
JAVA_AGENT_BRANCH=${2}

ARTIFACT_ID=elastic-apm-agent

function mavenRun() {
  ## If settings.xml file exists and there is `ci` profile
  SETTINGS=.ci/settings.xml
  if [ -e ${SETTINGS} ] ; then
    if grep -q '<id>ci</id>' ${SETTINGS} ; then
      export MAVEN_CONFIG="-s ${SETTINGS} -Pci ${MAVEN_CONFIG}"
    fi
  fi
  mvn -q --batch-mode \
    -DskipTests=true \
    -Dmaven.javadoc.skip=true \
    -Dhttps.protocols=TLSv1.2 \
    -Dmaven.wagon.http.retryHandler.count=10 \
    -Dmaven.wagon.httpconnectionManager.ttlSeconds=25 \
    -Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn \
    -Dmaven.repo.local="${M2_REPOSITORY_FOLDER}" \
    "$@"
}

if [ -n "${JAVA_AGENT_BRANCH}" ] ; then
  # build agent from source, install to ~/.m2 repo
  git clone "https://github.com/${JAVA_AGENT_REPO}.git" /apm-agent-java
  cd /apm-agent-java
  git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*'
  git checkout "${JAVA_AGENT_BRANCH}"

  mvn dependency:go-offline --fail-never -q -B
  if ! mavenRun clean install ; then
    echo 'Sleep and try again'
    sleep 5
    mavenRun install
  fi
  # shellcheck disable=SC2016
  VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec)
  export VERSION="${VERSION}"
  cp "/root/.m2/repository/co/elastic/apm/${ARTIFACT_ID}/${VERSION}/${ARTIFACT_ID}-${VERSION}.jar" /agent/elastic-apm-agent.jar
fi
