# Stage 0: clone opbeans-dotnet and apm-agent-dotnet, and build.
#
# DOTNET_AGENT_REPO and DOTNET_AGENT_BRANCH parameterise the DOTNET agent
# repo and branch (or commit) to use.
FROM mcr.microsoft.com/dotnet/core/sdk:2.2 AS build

ARG DOTNET_AGENT_REPO=elastic/apm-agent-dotnet
ARG DOTNET_AGENT_BRANCH=master

RUN git clone https://github.com/${DOTNET_AGENT_REPO}.git /src/dotnet-agent -b ${DOTNET_AGENT_BRANCH}
WORKDIR /src/dotnet-agent
RUN dotnet restore
RUN dotnet publish -c Release -o build

# Stage 1: clone opbeans-dotnet and build the project
# JAVA_AGENT_VERSION parameterise the DOTNET agent version to be used
#   if unset then it uses the build generated above. (TODO: to be done)
FROM mcr.microsoft.com/dotnet/core/sdk:2.2 AS opbeans-dotnet
ARG JAVA_AGENT_VERSION=0.0.1-alpha
ENV OPBEANS_DOTNET_REPO=elastic/opbeans-dotnet
ENV OPBEANS_DOTNET_BRANCH=master
RUN git clone https://github.com/${OPBEANS_DOTNET_REPO}.git /src -b ${OPBEANS_DOTNET_BRANCH}
WORKDIR /src/opbeans-dotnet
# This is the way to manipulate the csproj with the version of the dotnet agent to be used
RUN sed -ibck "s#\(<PackageReference Include=\"Elastic\.Apm\.All\" Version=\)\"\(.*\)\"#\1\"${JAVA_AGENT_VERSION}\"#" opbeans-dotnet.csproj
RUN dotnet restore
RUN dotnet publish -c Release -o build

# Stage 2: Run the opbeans-dotnet app
## Alpine image produces a segmentation fault:
##        further details: https://github.com/aspnet/EntityFrameworkCore/issues/14504
## FROM mcr.microsoft.com/dotnet/core/aspnet:2.2-alpine AS runtime
FROM mcr.microsoft.com/dotnet/core/aspnet:2.2 AS runtime
WORKDIR /app
COPY --from=opbeans-dotnet /src/opbeans-dotnet/build ./
COPY --from=opbeans/opbeans-frontend:latest /app/build /opbeans-frontend
EXPOSE 80
ENTRYPOINT ["dotnet", "opbeans-dotnet.dll"]
