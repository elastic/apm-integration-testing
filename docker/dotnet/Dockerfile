# Stage 0: clone opbeans-dotnet and build the project
# DOTNET_AGENT_VERSION parameterise the DOTNET agent version to be used
#   if unset then it uses the build generated above. (TODO: to be done)
# DOTNET_AGENT_REPO and DOTNET_AGENT_BRANCH parameterise the DOTNET agent
# repo and branch (or commit) to use.
FROM mcr.microsoft.com/dotnet/sdk:6.0 AS build
ENV DOTNET_ROOT=/usr/share/dotnet
ARG DOTNET_AGENT_REPO=elastic/apm-agent-dotnet
ARG DOTNET_AGENT_BRANCH=main
ARG DOTNET_AGENT_VERSION=
# Workaround for https://github.com/dotnet/sdk/issues/14497
ARG DOTNET_HOST_PATH=/usr/share/dotnet/dotnet
WORKDIR /src
COPY . /src
# install SDK version in global.json of elastic/apm-agent-dotnet
# Needed when building branches that specify 3.1.100 SDK in global.json
RUN curl -sSL https://dot.net/v1/dotnet-install.sh | bash /dev/stdin --install-dir ${DOTNET_ROOT} -version 3.1.100

# SDK 5.x is also needed
RUN curl -sSL https://dot.net/v1/dotnet-install.sh | bash /dev/stdin --install-dir ${DOTNET_ROOT} -version 5.0.100
RUN ./run.sh

# Stage 2: Run the TestAspNetCoreApp app
FROM mcr.microsoft.com/dotnet/aspnet:3.1-alpine AS runtime
WORKDIR /app
COPY --from=build /src/aspnetcore/build ./
RUN apk update \
    && apk add --no-cache curl \
    && rm -rf /var/cache/apk/*
EXPOSE 8100
ENTRYPOINT ["dotnet", "TestAspNetCoreApp.dll", "--urls=http://0.0.0.0:8100"]
