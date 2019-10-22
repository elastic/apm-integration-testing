#!/usr/bin/env sh
set -ex
if [ -f /local-install/Gemfile ]; then
    echo "Installing from local folder"
    # copy to folder inside container to ensure were not poluting the local folder
    cp -r /local-install ~
    cd ~/local-install && bundle
    cd -
elif [ -n "${RUBY_AGENT_VERSION}" ]; then
    gem install elastic-apm -v "${RUBY_AGENT_VERSION}"
elif [ -n "${RUBY_AGENT_BRANCH}" ]; then
    gem install specific_install
    if [ -z "${RUBY_AGENT_REPO}" ]; then
        RUBY_AGENT_REPO="elastic/apm-agent-ruby"
    fi
    # This is required with the alpine version
    apk --no-cache add git
    echo "Installing ${RUBY_AGENT_REPO}:${RUBY_AGENT_BRANCH} from Github"
    gem specific_install https://github.com/${RUBY_AGENT_REPO}.git -b "${RUBY_AGENT_BRANCH}"
else
    gem install elastic-apm
fi
exec "$@"
