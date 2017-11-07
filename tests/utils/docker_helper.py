import docker
import timeout_decorator
import time
import requests
from io import BytesIO


def clean_containers(name):
    containers = __client().containers.list(all=True, filters={'name': name})
    for c in containers:
        c.stop()
        c.remove(force=True)


def build_image(name, imgFile):
    if isinstance(imgFile, BytesIO):
        return __client().images.build(fileobj=imgFile,
                                       tag=name,
                                       rm=True,
                                       pull=True)
    else:
        return __client().images.build(path=imgFile,
                                       tag=name,
                                       rm=True,
                                       pull=True)


def run_container(img, ports={}, env={}, name=None, url=None):
    if name is None:
        name = img
    clean_containers(name)
    container = __client().containers.run(img,
                                          name=name,
                                          ports=ports,
                                          environment=env,
                                          detach=True)
    if url is None:
        __wait_until_container_running(container)
    else:
        __wait_until_service_responding(url)
    __network().connect(container)
    return container


def __network(name="apm_test"):
    networks = __client().networks.list(name)
    if len(networks) > 0:
        return networks[0]
    else:
        return __client().networks.create(name, check_duplicate=True)


def __client():
    return docker.from_env()


@timeout_decorator.timeout(30)
def __wait_until_container_running(container):
    while container.status != "running":
        time.sleep(1)
        container.reload()


@timeout_decorator.timeout(90)
def __wait_until_service_responding(url):
    def call_service():
        try:
            return requests.get(url).status_code
        except:
            return None

    while call_service() != 200:
        time.sleep(1)
