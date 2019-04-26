#!/usr/bin/env bash
set -x
git clone https://github.com/${OPBEANS_DOTNET_REPO}.git /src/opbeans-dotnet -b ${OPBEANS_DOTNET_BRANCH}

if [ -z "${DOTNET_AGENT_VERSION}" ] ; then
  git clone https://github.com/${DOTNET_AGENT_REPO}.git /src/dotnet-agent -b ${DOTNET_AGENT_BRANCH}
  cd /src/dotnet-agent
  dotnet restore
  dotnet publish -c Release -o build

  cd /src/opbeans-dotnet/opbeans-dotnet
  sed -ibck 's#<PropertyGroup>#<PropertyGroup><RestoreSources>$(RestoreSources);/src/dotnet-agent/src/Elastic.Apm.All/build;https://api.nuget.org/v3/index.json</RestoreSources>#' opbeans-dotnet.csproj
  DOTNET_AGENT_VERSION=$(cat /src/dotnet-agent/src/Elastic.Apm.All/Elastic.Apm.All.csproj | grep 'PackageVersion' | sed 's#<.*>\(.*\)<.*>#\1#' | tr -d " ")
  dotnet add package Elastic.Apm.All -v ${DOTNET_AGENT_VERSION}
fi

cd /src/opbeans-dotnet/opbeans-dotnet
# This is the way to manipulate the csproj with the version of the dotnet agent to be used
sed -ibck "s#\(<PackageReference Include=\"Elastic\.Apm\.All\" Version=\)\"\(.*\)\"#\1\"${DOTNET_AGENT_VERSION}\"#" opbeans-dotnet.csproj
dotnet restore
dotnet publish -c Release -o build
