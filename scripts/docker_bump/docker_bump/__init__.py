__version__ = '0.1.0'
from lib2to3.pgen2 import token
import os
import re
from tkinter import W
import click

import logging

# Hack in a path to modules
import sys
sys.path.append("..")
from modules import opbeans # type: ignore

from docker_bump import dockerhub

logger = logging.getLogger(__name__)

PROJECTS = [
    'apm-server',
    'dotnet',
    'intake-receiver', ## Possible special case
    'java/spring',
    'nodejs/express',
    'opbeans/dotnet',
    'opbeans/frontend_nginx',
    'opbeans/go',
    'opbeans/java',
    'opbeans/node',
    'opbeans/python',
    'opbeans/ruby',
    'opbeans/rum',
    'php/apache',
    'python/django',
    'python/flask',
    'ruby/rails',
    'rum',
    'statsd',
    ]

def setup_logging(is_debug: bool) -> None:
    """
    Initialize logging
    """
    if is_debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

def _get_script_path():
    """
    Helper func to get the location of the script
    """
    return os.path.dirname(os.path.abspath(__file__))

def get_docker_file(project: str) -> list:
    """
    Get Dockefile for a project and return a list
    line-by-line
    """
    logger.debug("Search for Docker file for %s" % project)
    docker_file_target_location = os.path.join(
        _get_script_path(),
        "..",
        "..",
        "..",
        "docker",
        project,
        "Dockerfile"
        ) 
    logger.debug(docker_file_target_location)
    if not os.path.exists(docker_file_target_location):
        logger.debug("Not found")
    else:
        logger.debug("Found Docker file for %s" % project)
        with open(docker_file_target_location, "r") as fh_:
            docker_lines = fh_.readlines()
    return docker_lines

def docker_extract_image(docker_lines: list, filter_to='FROM') -> list:
    """
    Given a line in a Dockerfile, return the image if found
    """
    ret = []
    for line in docker_lines:
        tokens = line.split(' ')
        leading_token = tokens[0]
        if filter_to and re.match(filter_to, leading_token):
            ret.append(tokens[1].strip())
    return ret

def collect_opbean_env(opbean: str) -> dict:
    """
    Given an Opbean, determine the environment variables which are set
    by default.
    """
    cls = getattr(opbeans, 'Opbeans' + opbean.capitalize())
    inst = cls()
    opbean_config = inst._content()
    env_ret = {}
    if 'args' in opbean_config['build']:
        for arg in opbean_config['build']['args']:
            env_key, env_val = arg.split('=')
            env_ret[env_key] = env_val
    for environment in opbean_config['environment']:
        if '=' not in environment:
            continue
        environment_key, environment_value = environment.split('=', maxsplit=1)
        env_ret[environment_key] = environment_value
    return env_ret

def merge_env_to_directive(opbean_env: dict, image_str: str):
    """
    Take an env and a image and try to substitute
    """
    # Extract actual var
    if ':' in image_str:
        image_name, version = image_str.split(':')
    else:
        image_name = image_str
        version = ''
    if image_name.startswith('$'):
       image_name = re.sub('[\$\{\}]', '', image_name)
       image_name = opbean_env[image_name]
    if version.startswith('$'):
        version = re.sub('[\$\{\}]', '', version)
        version = opbean_env[version]
    return f"{image_name}:{version}"

def dockerhub_latest(image: str) -> str:
    """
    Get the latest version for a image
    """


@click.command()
@click.option('--debug', is_flag=True)
@click.option('--dev', is_flag=True)
def bump(debug, dev):
    """
    Program entrypoint
    """
    setup_logging(debug)
    for project in PROJECTS:
        docker_lines = get_docker_file(project)
        images = docker_extract_image(docker_lines)
        if project.startswith('opbeans'):
            _, opbean_name = project.split('/')
            opbean_env = None
            try:
                opbean_env = collect_opbean_env(opbean_name)
            except AttributeError:
                logger.critical("Could not find environment for %s" % opbean_name)
            if opbean_env and images:
                tmp_image_list = []
                for image in images:
                    merged_image = merge_env_to_directive(opbean_env, image)
                    tmp_image_list.append(merged_image)
                images = tmp_image_list
        #print(project, images)
        for image in images:
            try:
                image_name, version = image.split(':')
                print(image_name)
            except ValueError:
                logger.critical("Probable bug on image [%s]" % image)
                

        