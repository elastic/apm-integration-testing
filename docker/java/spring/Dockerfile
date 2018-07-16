FROM maven:3.5.3-jdk-10

RUN mkdir /agent \
    && mkdir /app

COPY testapp /app

WORKDIR /agent

RUN curl -L https://github.com/elastic/apm-agent-java/archive/master.tar.gz | tar --strip-components=1 --exclude=demo/db.sql.bz2 -xzv \
    && mvn package -DskipTests \
    && export JAVA_AGENT_BUILT_VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec) \
    && mv elastic-apm-agent/target/elastic-apm-agent-${JAVA_AGENT_BUILT_VERSION}.jar apm-agent.jar \
    && mvn install:install-file -Dfile=apm-agent-api/target/apm-agent-api-${JAVA_AGENT_BUILT_VERSION}.jar -DgroupId=co.elastic.apm -DartifactId=apm-agent-api -Dversion=${JAVA_AGENT_BUILT_VERSION} -Dpackaging=jar \
    && cd /app \
    && mvn -DAGENT_API_VERSION=${JAVA_AGENT_BUILT_VERSION} package

WORKDIR /app

EXPOSE 8090

CMD ["java", "-javaagent:../agent/apm-agent.jar", "-Delastic.apm.service_name=my-service", "-Delastic.apm.application_packages=hello", "-jar","target/hello-spring-0.1.jar"]


