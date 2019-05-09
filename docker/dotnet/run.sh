#!/usr/bin/env bash
set -x

CSPROJ="TestAspNetCoreApp.csproj"
if [ -z "${DOTNET_AGENT_VERSION}" ] ; then
  git clone https://github.com/${DOTNET_AGENT_REPO}.git /src/dotnet-agent -b ${DOTNET_AGENT_BRANCH}
  cd /src/dotnet-agent
  ### Otherwise: /usr/share/dotnet/sdk/2.2.203/NuGet.targets(119,5): error : The local source '/src/local-packages' doesn't exist. [/src/dotnet-agent/ElasticApmAgent.sln]
  mkdir /src/local-packages
  dotnet restore
  dotnet pack -c Release -o /src/local-packages

  cd /src/aspnetcore
  mv ../NuGet.Config .
  sed -ibck 's#<PropertyGroup>#<PropertyGroup><RestoreSources>$(RestoreSources);/src/local-packages;https://api.nuget.org/v3/index.json</RestoreSources>#' ${CSPROJ}
  DOTNET_AGENT_VERSION=$(cat /src/dotnet-agent/src/Elastic.Apm.All/Elastic.Apm.All.csproj | grep 'PackageVersion' | sed 's#<.*>\(.*\)<.*>#\1#' | tr -d " ")
  dotnet add package Elastic.Apm.All -v ${DOTNET_AGENT_VERSION}
fi

cd /src/aspnetcore
# This is the way to manipulate the csproj with the version of the dotnet agent to be used
sed -ibck "s#\(<PackageReference Include=\"Elastic\.Apm\.All\" Version=\)\"\(.*\)\"#\1\"${DOTNET_AGENT_VERSION}\"#" ${CSPROJ}
dotnet restore
dotnet publish -c Release -o build
