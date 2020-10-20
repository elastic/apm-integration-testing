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
<<<<<<< HEAD
  if [ "${PHP_AGENT_VERSION}" == "latest" ]  ; then
    wget -O jq https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
    chmod 755 jq
    TAG_NAME=$(curl -s https://api.github.com/repos/elastic/apm-agent-php/releases/latest | ./jq -r .tag_name)
    VERSION="${TAG_NAME/v/}"
  else
    TAG_NAME="v${PHP_AGENT_VERSION}"
    VERSION=${PHP_AGENT_VERSION}
  fi
  wget -q "https://github.com/elastic/apm-agent-php/releases/download/${TAG_NAME}/apm-agent-php_${VERSION}_all.deb" \
=======
  ## Install the given release
  wget -q "https://github.com/elastic/apm-agent-php/releases/download/v${PHP_AGENT_VERSION}/apm-agent-php_${PHP_AGENT_VERSION}_all.deb" \
>>>>>>> 4c63a2a (support PHP ITs (#946))
       -O "/tmp/apm-agent-php.deb"
  dpkg -i "/tmp/apm-agent-php.deb"
fi

## Copy the app to the /var/www/html folder
cp -rf /src/app/* /var/www/html
