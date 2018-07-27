FROM opbeans/opbeans-java:latest

COPY entrypoint.sh /app/entrypoint.sh
CMD java -javaagent:/app/elastic-apm-agent.jar -Dspring.profiles.active=customdb\
                                        -Dserver.port=${OPBEANS_SERVER_PORT:-3002}\
                                        -Dspring.datasource.url=${DATABASE_URL:-jdbc:postgresql://postgres/opbeans?user=postgres&password=verysecure}\
                                        -Dspring.datasource.driverClassName=${DATABASE_DRIVER:-org.postgresql.Driver}\
                                        -Dspring.jpa.database=${DATABASE_DIALECT:-POSTGRESQL}\
                                        -jar /app/app.jar
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]