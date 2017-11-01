import docker
import timeout_decorator
import time
import requests
from io import BytesIO


def client():
    return docker.from_env()


@timeout_decorator.timeout(30)
def wait_until_container_running(container):
    print(container.status)
    while container.status != "running":
        time.sleep(1)
        container.reload()


@timeout_decorator.timeout(90)
def wait_until_service_responding(url):
    def call_service():
        try:
            return requests.get(url).status_code
        except:
            return None

    while call_service() != 200:
        time.sleep(1)


def clean_containers(name):
    containers = client().containers.list(all=True, filters={'name': name})
    for c in containers:
        c.stop()
        c.remove(force=True)


def build_image(name, imgFile):
    if isinstance(imgFile, BytesIO):
        return client().images.build(fileobj=imgFile,
                                     tag=name,
                                     rm=True,
                                     pull=True)
    else:
        return client().images.build(path=imgFile,
                                     tag=name,
                                     rm=True,
                                     pull=True)


def run_container(img, ports={}, env={}, name=None, url=None):
    if name is None:
        name = img
    clean_containers(name)
    container = client().containers.run(img,
                                        name=name,
                                        ports=ports,
                                        environment=env,
                                        detach=True)
    if url is None:
        wait_until_container_running(container)
    else:
        wait_until_service_responding(url)
    network().connect(container)
    return container


def network(name="apm_test"):
    networks = client().networks.list(name)
    if len(networks) > 0:
        return networks[0]
    else:
        return client().networks.create(name, check_duplicate=True)
