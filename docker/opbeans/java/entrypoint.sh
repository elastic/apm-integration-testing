#!/usr/bin/env sh
set -ex
if [ -f /local-install/pom.xml ]; then
    echo "Using Java agent from from local folder"
    rm -f /app/elastic-apm-agent.jar
    # Install xmllint in the alpine
    apk --no-cache add libxml2-utils
    #Extract current version without using maven which is not available in this image
    JAVA_AGENT_LOCAL_VERSION=$(xmllint --xpath '/*[local-name()="project"]/*[local-name()="version"]/text()' /local-install/pom.xml)

    cp -v "/local-install/elastic-apm-agent/target/elastic-apm-agent-${JAVA_AGENT_LOCAL_VERSION}.jar" /app/elastic-apm-agent.jar
elif [ -n "${JAVA_AGENT_VERSION}" ]; then
    echo "Downloading Java agent $JAVA_AGENT_VERSION from maven central"
    rm -f /app/elastic-apm-agent.jar
    wget -O /app/elastic-apm-agent.jar "http://repo1.maven.org/maven2/co/elastic/apm/elastic-apm-agent/$JAVA_AGENT_VERSION/elastic-apm-agent-$JAVA_AGENT_VERSION.jar"
else
    echo "Using Java agent from the docker image"
fi

exec "$@"
