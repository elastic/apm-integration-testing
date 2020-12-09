# Stage 0: clone opbeans-dotnet and build the project
# DOTNET_AGENT_VERSION parameterise the DOTNET agent version to be used
#   if unset then it uses the build generated above. (TODO: to be done)
# DOTNET_AGENT_REPO and DOTNET_AGENT_BRANCH parameterise the DOTNET agent
# repo and branch (or commit) to use.
FROM mcr.microsoft.com/dotnet/sdk:5.0 AS build
ENV DOTNET_ROOT=/usr/share/dotnet
ARG DOTNET_AGENT_REPO=elastic/apm-agent-dotnet
ARG DOTNET_AGENT_BRANCH=master
ARG DOTNET_AGENT_VERSION=
# Workaround for https://github.com/dotnet/sdk/issues/14497
ARG DOTNET_HOST_PATH=dotnet
WORKDIR /src
COPY . /src
RUN ./run.sh

# Stage 2: Run the opbeans-dotnet app
FROM mcr.microsoft.com/dotnet/core/aspnet:2.2-alpine AS runtime
WORKDIR /app
COPY --from=build /src/aspnetcore/build ./
RUN apk update \
    && apk add --no-cache curl \
    && rm -rf /var/cache/apk/*
EXPOSE 8100
ENTRYPOINT ["dotnet", "TestAspNetCoreApp.dll", "--urls=http://0.0.0.0:8100"]
