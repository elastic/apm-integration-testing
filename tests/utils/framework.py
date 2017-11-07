from utils import docker_helper


class Framework:
    def __init__(self, name):
        self.name = name

    def start(self, ports, path):
        docker_helper.build_image(self.name, path)
        return docker_helper.run_container(self.name, ports=ports)
