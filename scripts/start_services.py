import subprocess
import os
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


def elasticsearch():
    if os.environ.get('ES_URL') is None:
        os.environ['ES_PORT'] = '9200'
        os.environ['ES_HOST'] = 'elasticsearch'
        os.environ['ES_NAME'] = 'elasticsearch'
        os.environ['ES_URL'] = "http://elasticsearch:{}".format(os.environ['ES_PORT'])
        set_version('ES_VERSION', "6.0.0", "release")
        start("docker/elasticsearch/start.sh")
    else:
        parsed_url = urlparse(os.environ['ES_URL'])
        os.environ['ES_PORT'] = str(parsed_url.port)
        os.environ['ES_HOST'] = parsed_url.hostname
    return os.environ['ES_URL']


def kibana():
    if os.environ.get('KIBANA_URL') is None:
        os.environ['KIBANA_PORT'] = "5601"
        os.environ['KIBANA_HOST'] = 'kibana'
        os.environ['KIBANA_URL'] = "http://kibana:{}".format(os.environ['KIBANA_PORT'])
        set_version('KIBANA_VERSION', "6.0.0", "release")
        start("docker/kibana/start.sh")
    return os.environ['KIBANA_URL']


def apm_server():
    if os.environ.get('APM_SERVER_URL') is None:
        name = os.environ['APM_SERVER_NAME'] = 'apmserver'
        port = os.environ['APM_SERVER_PORT'] = "8200"
        os.environ['APM_SERVER_URL'] = "http://{}:{}".format(name, port)
        set_version('APM_SERVER_VERSION')
        start("docker/apm_server/start.sh")
    return "{}/healthcheck".format(os.environ['APM_SERVER_URL'])


def flask():
    set_version('PYTHON_AGENT_VERSION')
    os.environ['FLASK_APP_NAME'] = "flaskapp"
    os.environ['FLASK_PORT'] = "8001"
    os.environ['FLASK_URL'] = "http://{}:{}".format(os.environ['FLASK_APP_NAME'],
                                                    os.environ['FLASK_PORT'])
    start("docker/python/flask/start.sh")
    return "{}/healthcheck".format(os.environ['FLASK_URL'])


def flask_gunicorn():
    os.environ['PY_SERVER'] = 'gunicorn'
    set_version('PYTHON_AGENT_VERSION')
    os.environ['GUNICORN_APP_NAME'] = "gunicornapp"
    os.environ['GUNICORN_PORT'] = "8002"
    os.environ['GUNICORN_URL'] = "http://{}:{}".format(os.environ['GUNICORN_APP_NAME'],
                                                       os.environ['GUNICORN_PORT'])
    start("docker/python/flask/start.sh")
    return "{}/healthcheck".format(os.environ['GUNICORN_URL'])


def django():
    set_version('PYTHON_AGENT_VERSION')
    os.environ['DJANGO_APP_NAME'] = "djangoapp"
    os.environ['DJANGO_PORT'] = "8003"
    os.environ['DJANGO_URL'] = "http://{}:{}".format(os.environ['DJANGO_APP_NAME'],
                                                     os.environ['DJANGO_PORT'])
    start("docker/python/django/start.sh")
    return "{}/healthcheck".format(os.environ['DJANGO_URL'])


def express():
    set_version('NODEJS_AGENT_VERSION')
    os.environ['EXPRESS_APP_NAME'] = "expressapp"
    os.environ['EXPRESS_PORT'] = "8010"
    os.environ['EXPRESS_URL'] = "http://{}:{}".format(os.environ['EXPRESS_APP_NAME'],
                                                      os.environ['EXPRESS_PORT'])
    start("docker/nodejs/express/start.sh")
    return "{}/healthcheck".format(os.environ['EXPRESS_URL'])


def python_agents():
    urls = []
    urls.append(flask())
    urls.append(flask_gunicorn())
    urls.append(django())
    return urls


def nodejs_agents():
    return [express()]


def prepare():
    if os.environ.get("NETWORK") is None:
        os.environ["NETWORK"] = "apm_testing"
    start("docker/prepare_docker.sh")


def start(script):
    subprocess.check_call([script])
    print("starting..")

def set_version(env_var, default='master', state="github"):
    v = os.environ.get(env_var)
    env_var_state = "{}_STATE".format(env_var)
    if v is None or v == "":
        os.environ[env_var_state] = state
        os.environ[env_var] = default
    else:
        parts = v.split(":")
        if len(parts) == 1:
            os.environ[env_var_state] = state
            os.environ[env_var] = parts[0]
        elif len(parts) == 2:
            os.environ[env_var_state] = parts[0]
            os.environ[env_var] = parts[1]
        else:
            raise Exception("Invalid Version {}".format(v))


if __name__ == '__main__':
    prepare()

    urls = []
    urls.append(elasticsearch())
    # urls.append(kibana())
    urls.append(apm_server())

    agents = os.environ.get("AGENTS")
    if agents is not None:
        for agent in agents.split(','):
            if agent == "python":
                urls += python_agents()
            elif agent == "nodejs":
                urls += nodejs_agents()
            else:
                raise Exception("Agent {} not supported".format(agent))

    os.environ['URLS'] = ",".join(urls)
    subprocess.call(["docker/run_tests.sh"])
