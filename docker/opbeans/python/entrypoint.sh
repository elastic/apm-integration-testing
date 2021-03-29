#!/bin/bash -e
if [[ -f /local-install/setup.py ]]; then
    echo "Installing from local folder"
    pip uninstall -y elastic-apm
    # copy to folder inside container to ensure were not polluting the local folder
    cp -r /local-install ~
    cd ~/local-install && python setup.py install
    cd -
elif [ -n "$PYTHON_AGENT_VERSION" ] && [ "$PYTHON_AGENT_VERSION" != "latest" ]; then
    pip install -q -U elastic-apm=="$PYTHON_AGENT_VERSION"
elif [[ "$PYTHON_AGENT_BRANCH" ]]; then
    if [[ -z "${PYTHON_AGENT_REPO}" ]]; then
        PYTHON_AGENT_REPO="elastic/apm-agent-python"
    fi
    pip install -q -U "https://github.com/${PYTHON_AGENT_REPO}/archive/${PYTHON_AGENT_BRANCH}.zip"
else
    pip install -q -U elastic-apm
fi
rm -f celerybeat.pid
python manage.py migrate
python manage.py sqlsequencereset opbeans | python manage.py dbshell

exec "$@"
