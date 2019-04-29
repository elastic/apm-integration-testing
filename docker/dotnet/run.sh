#!/usr/bin/env bash
set -x

CSPROJ="testapp.csproj"
if [ -z "${DOTNET_AGENT_VERSION}" ] ; then
  git clone https://github.com/${DOTNET_AGENT_REPO}.git /src/dotnet-agent -b ${DOTNET_AGENT_BRANCH}
  cd /src/dotnet-agent
  dotnet restore
  dotnet publish -c Release -o build

  cd /src/app/testapp
  sed -ibck 's#<PropertyGroup>#<PropertyGroup><RestoreSources>$(RestoreSources);/src/dotnet-agent/src/Elastic.Apm.All/build;https://api.nuget.org/v3/index.json</RestoreSources>#' ${CSPROJ}
  DOTNET_AGENT_VERSION=$(cat /src/dotnet-agent/src/Elastic.Apm.All/Elastic.Apm.All.csproj | grep 'PackageVersion' | sed 's#<.*>\(.*\)<.*>#\1#' | tr -d " ")
  dotnet add package Elastic.Apm.All -v ${DOTNET_AGENT_VERSION}
fi

cd /src/app/testapp
# This is the way to manipulate the csproj with the version of the dotnet agent to be used
sed -ibck "s#\(<PackageReference Include=\"Elastic\.Apm\.All\" Version=\)\"\(.*\)\"#\1\"${DOTNET_AGENT_VERSION}\"#" ${CSPROJ}
dotnet restore
dotnet publish -c Release -o build
