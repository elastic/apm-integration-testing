#!/usr/bin/env sh
set -ex
if [ -f /local-install/package.json ]; then
    echo "Installing elastic-apm-node from local folder (--opbeans-node-agent-local-repo)"
    # Copy to a folder inside container to ensure we're not polluting the
    # local folder. Skip possibly huge dirs to speed this up.
    rsync -a /local-install/ ~/local-install/ --exclude node_modules --exclude build --exclude .git
    # Install elastic-apm-node from this copied dir.
    npm install ~/local-install
    npm ls elastic-apm-node
elif [ -n "${NODE_AGENT_VERSION}" ]; then
    echo "Installing ${NODE_AGENT_VERSION} from npm"
    npm install elastic-apm-node@"${NODE_AGENT_VERSION}"
elif [ -n "${NODE_AGENT_BRANCH}" ]; then
    if [ -z "${NODE_AGENT_REPO}" ]; then
        NODE_AGENT_REPO="elastic/apm-agent-nodejs"
    fi
    echo "Installing ${NODE_AGENT_REPO}:${NODE_AGENT_BRANCH} from Github"
    npm install "https://github.com/${NODE_AGENT_REPO}/archive/${NODE_AGENT_BRANCH}.tar.gz"
fi
if [ -f /sourcemaps/README.md ]; then
    rm -f /sourcemaps/*.map
    cp -f ./client/build/static/js/*.map /sourcemaps/
    chmod 0666 /sourcemaps/*.map
fi
exec "$@"
