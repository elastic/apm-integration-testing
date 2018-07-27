#!/bin/bash -e
if [[ -f /local-install/pom.xml ]]; then
    echo "Using Java agent from from local folder"
    rm -f /app/elastic-apm-agent.jar
    #Extract current version without using maven which is not available in this image
    JAVA_AGENT_LOCAL_VERSION=$(xmllint --xpath '/*[local-name()="project"]/*[local-name()="version"]/text()' /local-install/pom.xml)
    
    cp -v /local-install/elastic-apm-agent/target/elastic-apm-agent-${JAVA_AGENT_LOCAL_VERSION}.jar /app/elastic-apm-agent.jar
    # copy to folder inside container to ensure were not polluting the local folder
    cp -r /local-install ~
    cd ~/local-install && python setup.py install
    cd -
elif [[ $JAVA_AGENT_VERSION ]]; then
    echo "Downloading Java agent $JAVA_AGENT_VERSION from maven central"
    rm -f /app/elastic-apm-agent.jar
    curl -o /app/elastic-apm-agent.jar -L http://repo1.maven.org/maven2/co/elastic/apm/elastic-apm-agent/$JAVA_AGENT_VERSION/elastic-apm-agent-$JAVA_AGENT_VERSION.jar 
else
    echo "Using Java agent from the docker image"
fi

exec "$@"