#Multi-Stage build

#Build application stage
#We need maven.
FROM maven:3.5.3-jdk-10
LABEL lastupdate="2018-05-25"
ARG JAVA_AGENT_BRANCH=master
ARG JAVA_AGENT_REPO=elastic/apm-agent-java

WORKDIR /usr/src/java-app

#build the application
WORKDIR /usr/src/java-code
RUN curl -L https://github.com/elastic/opbeans-java/archive/master.tar.gz | tar --strip-components=1 -xzv

WORKDIR /usr/src/java-code/opbeans
RUN mvn package -DskipTests
RUN cp -v /usr/src/java-code/opbeans/target/*.jar /usr/src/java-app/app.jar

#build te agent
WORKDIR /usr/src/java-agent-code
RUN curl -L https://github.com/$JAVA_AGENT_REPO/archive/$JAVA_AGENT_BRANCH.tar.gz | tar --strip-components=1 --exclude=demo/db.sql.bz2 -xzv
RUN mvn package -DskipTests
RUN export JAVA_AGENT_BUILT_VERSION=$(mvn -q -Dexec.executable="echo" -Dexec.args='${project.version}' --non-recursive org.codehaus.mojo:exec-maven-plugin:1.3.1:exec) \
    && cp -v /usr/src/java-agent-code/elastic-apm-agent/target/elastic-apm-agent-${JAVA_AGENT_BUILT_VERSION}.jar /usr/src/java-app/elastic-apm-agent.jar

WORKDIR /usr/src/java-app
RUN ls -la

#Run application Stage
#We only need java

FROM openjdk:10
LABEL lastupdate="2018-05-21"

RUN export
WORKDIR /app
COPY --from=0 /usr/src/java-app/*.jar ./

COPY entrypoint.sh /app/entrypoint.sh
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]