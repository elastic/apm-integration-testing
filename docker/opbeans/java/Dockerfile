FROM maven:3.5.3-jdk-10
# setting --build-arg JAVA_AGENT_BRANCH=<branch> causes the agent to be built from source
# instead of using the agent which comes pre-built with opbeans-java:latest
ARG JAVA_AGENT_REPO=elastic/apm-agent-java
ARG JAVA_AGENT_BRANCH=

RUN mkdir /agent \
  # making sure there is at least one file to COPY (otherwise docker complains)
  && touch /agent/ignore
COPY build-agent.sh .
# noop if JAVA_AGENT_BRANCH is not set
RUN ./build-agent.sh "${JAVA_AGENT_REPO}" "${JAVA_AGENT_BRANCH}"

FROM opbeans/opbeans-java:latest
# replaces the /agent/elastc-apm-agent.jar if it has been built by build-agent.sh
COPY --from=0 /agent/* /app/
COPY entrypoint.sh /app/entrypoint.sh
CMD java -javaagent:/app/elastic-apm-agent.jar -Dspring.profiles.active=customdb\
                                        -Dserver.port=${OPBEANS_SERVER_PORT:-3002}\
                                        -Dspring.datasource.url=${DATABASE_URL:-jdbc:postgresql://postgres/opbeans?user=postgres&password=verysecure}\
                                        -Dspring.datasource.driverClassName=${DATABASE_DRIVER:-org.postgresql.Driver}\
                                        -Dspring.jpa.database=${DATABASE_DIALECT:-POSTGRESQL}\
                                        -jar /app/app.jar
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
