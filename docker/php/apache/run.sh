#!/usr/bin/env bash
set -x

## If no version to be installed, then use the source code
if [ -z "${PHP_AGENT_VERSION}" ] ; then
  git clone https://github.com/"${PHP_AGENT_REPO}".git /src/apm-agent-php
  cd /src/apm-agent-php || exit 1
  git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*'
  git checkout "${PHP_AGENT_BRANCH}"
  git rev-parse HEAD

  cd /src/apm-agent-php/src/ext || exit 1
  phpize
  ./configure --enable-elastic_apm
  make clean install
  cp /src/ext-elastic-apm.ini /usr/local/etc/php/conf.d/ext-elastic-apm.ini
else
  ## Install the given release
  wget -q "https://github.com/elastic/apm-agent-php/releases/download/v${PHP_AGENT_VERSION}/apm-agent-php_${PHP_AGENT_VERSION}_all.deb" \
       -O "/tmp/apm-agent-php.deb"
  dpkg -i "/tmp/apm-agent-php.deb"
fi

## Copy the app to the /var/www/html folder
cp -rf /src/app/* /var/www/html
