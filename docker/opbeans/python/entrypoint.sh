#!/bin/bash -e
if [[ -f /local-install/setup.py ]]; then
    echo "Installing from local folder"
    pip uninstall -y elastic-apm
    # copy to folder inside container to ensure were not poluting the local folder
    cp -r /local-install ~
    cd ~/local-install && python setup.py install
    cd -
elif [[ $PYTHON_AGENT_VERSION ]]; then
    pip install -U elastic-apm==$PYTHON_AGENT_VERSION
elif [[ $PYTHON_AGENT_BRANCH ]]; then
    if [[ -z ${PYTHON_AGENT_REPO} ]]; then
        PYTHON_AGENT_REPO="elastic/apm-agent-python"
    fi
    pip install -U https://github.com/${PYTHON_AGENT_REPO}/archive/${PYTHON_AGENT_BRANCH}.zip
else
    pip install -U elastic-apm
fi
rm -f celerybeat.pid
exec "$@"
