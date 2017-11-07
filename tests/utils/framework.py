from utils import docker_helper


def start_framework(name, path, ports):
    docker_helper.build_image(name, path)
    container = docker_helper.run_container(name, ports=ports)
