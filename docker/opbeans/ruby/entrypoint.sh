#!/bin/bash -e
if [[ -f /local-install/Gemfile ]]; then
    echo "Installing from local folder"
    # copy to folder inside container to ensure were not poluting the local folder
    cp -r /local-install ~
    cd ~/local-install && bundle
    cd -
elif [[ $RUBY_AGENT_VERSION ]]; then
    gem install elastic-apm -v $RUBY_AGENT_VERSION
elif [[ $RUBY_AGENT_BRANCH ]]; then
    gem install specific_install
    if [[ -z ${RUBY_AGENT_REPO} ]]; then
        RUBY_AGENT_REPO="elastic/apm-agent-ruby"
    fi
    echo "Installing ${RUBY_AGENT_REPO}:${RUBY_AGENT_BRANCH} from Github"
    gem specific_install https://github.com/${RUBY_AGENT_REPO}.git -b $RUBY_AGENT_BRANCH
else
    gem install elastic-apm
fi
exec "$@"
