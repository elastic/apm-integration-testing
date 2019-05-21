
# Stage 0: clone opbeans-dotnet and build the project
# DOTNET_AGENT_VERSION parameterise the DOTNET agent version to be used
#   if unset then it uses the build generated above. (TODO: to be done)
# DOTNET_AGENT_REPO and DOTNET_AGENT_BRANCH parameterise the DOTNET agent
# repo and branch (or commit) to use.
FROM mcr.microsoft.com/dotnet/core/sdk:2.2 AS opbeans-dotnet
ARG DOTNET_AGENT_REPO=elastic/apm-agent-dotnet
ARG DOTNET_AGENT_BRANCH=master
ARG DOTNET_AGENT_VERSION=
ENV OPBEANS_DOTNET_REPO=elastic/opbeans-dotnet
ENV OPBEANS_DOTNET_BRANCH=master
WORKDIR /src
COPY . /src
RUN ./run.sh

# Stage 2: Run the opbeans-dotnet app
## Alpine image produces a segmentation fault:
##        further details: https://github.com/aspnet/EntityFrameworkCore/issues/14504
## FROM mcr.microsoft.com/dotnet/core/aspnet:2.2-alpine AS runtime
FROM mcr.microsoft.com/dotnet/core/aspnet:2.2 AS runtime
WORKDIR /app
COPY --from=opbeans-dotnet /src/opbeans-dotnet/opbeans-dotnet/build ./
COPY --from=opbeans/opbeans-frontend:latest /app/build /opbeans-frontend
EXPOSE 80
ENTRYPOINT ["dotnet", "opbeans-dotnet.dll"]
