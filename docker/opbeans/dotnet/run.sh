#!/usr/bin/env bash
set -x
git clone https://github.com/${OPBEANS_DOTNET_REPO}.git /src/opbeans-dotnet -b ${OPBEANS_DOTNET_BRANCH}
CSPROJ="opbeans-dotnet.csproj"

PACKAGE=Elastic.Apm.NetCoreAll
CSPROJ_VERSION="/src/dotnet-agent/src/Elastic.Apm.NetCoreAll/${PACKAGE}.csproj"
BUILD_PROPS="/src/dotnet-agent/src/Directory.Build.props"

if [ -z "${DOTNET_AGENT_VERSION}" ] ; then
  git clone https://github.com/"${DOTNET_AGENT_REPO}".git /src/dotnet-agent -b "${DOTNET_AGENT_BRANCH}"
  cd /src/dotnet-agent || exit
  ### Otherwise: /usr/share/dotnet/sdk/2.2.203/NuGet.targets(119,5): error : The local source '/src/local-packages' doesn't exist. [/src/dotnet-agent/ElasticApmAgent.sln]
  mkdir /src/local-packages

  ### Errorlevels might happen when fetching PRs with some errors like: error: cannot lock ref 'refs/remotes/origin/pr/82/head': 'refs/remotes/origin/pr/82' exists; cannot create
  ### Let's fail if something bad happens when building the agent from the source code
  set -e
  # Remove Full Framework projects
  ## See https://github.com/elastic/apm-agent-dotnet/blob/480be30a699ba276ebd2a7055083e92f9f1e2207/.ci/linux/test.sh#L9-L11
  dotnet sln remove sample/AspNetFullFrameworkSampleApp/AspNetFullFrameworkSampleApp.csproj
  dotnet sln remove src/Elastic.Apm.AspNetFullFramework/Elastic.Apm.AspNetFullFramework.csproj
  dotnet sln remove test/Elastic.Apm.AspNetFullFramework.Tests/Elastic.Apm.AspNetFullFramework.Tests.csproj
  dotnet restore
  dotnet pack -c Release -o /src/local-packages

  cd /src/opbeans-dotnet/opbeans-dotnet || exit
  mv /src/NuGet.Config .
  # shellcheck disable=SC2016
  sed -ibck 's#<PropertyGroup>#<PropertyGroup><RestoreSources>$(RestoreSources);/src/local-packages;https://api.nuget.org/v3/index.json</RestoreSources>#' ${CSPROJ}
  DOTNET_AGENT_VERSION=$(grep 'PackageVersion' ${BUILD_PROPS} | sed 's#<.*>\(.*\)<.*>#\1#' | tr -d " ")

  if [ -z "${DOTNET_AGENT_VERSION}" ] ; then
    echo 'INFO: search version in the csproj. (only for agent version < 1.3)'
    DOTNET_AGENT_VERSION=$(grep 'PackageVersion' ${CSPROJ_VERSION} | sed 's#<.*>\(.*\)<.*>#\1#' | tr -d " ")
    if [ -z "${DOTNET_AGENT_VERSION}" ] ; then
      echo 'ERROR: DOTNET_AGENT_VERSION could not be calculated.' && exit 1
    fi
  fi

  dotnet add package ${PACKAGE} -v "${DOTNET_AGENT_VERSION}"
else
  ### Otherwise: The default NuGet.Config will fail as it's required
  mkdir /src/local-packages
fi

cd /src/opbeans-dotnet/opbeans-dotnet || exit
# This is the way to manipulate the csproj with the version of the dotnet agent to be used
sed -ibck "s#\(<PackageReference Include=\"Elastic\.Apm\.NetCoreAll\" Version=\)\"\(.*\)\"#\1\"${DOTNET_AGENT_VERSION}\"#" ${CSPROJ}

# Validate if the version has been updated
set -e
grep "Elastic.Apm.NetCoreAll" ${CSPROJ} | grep -i "Version=\"${DOTNET_AGENT_VERSION}\"" || (echo 'ERROR: DOTNET_AGENT_VERSION mismatch' && exit 1)
dotnet restore
dotnet publish -c Release -o build
