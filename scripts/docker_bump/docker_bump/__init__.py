__version__ = '0.1.0'
import os
import re
import click
import pprint
import json

import logging

# Hack in a path to modules
import sys
sys.path.append("..")
from modules import opbeans, elastic_stack # type: ignore

from . import dockerhub

logger = logging.getLogger(__name__)

# TODO cover special cases where the version is note defined like `FROM alpine` in docker/intake-receiver

PROJECTS = [
    'apm-server',
    'dotnet',
    'intake-receiver',
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
    # FIXME look recursively for files as well
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

def collect_stack_env(stack: str) -> dict:
    """
    Given a stack component, determine the environment variables which are set
    by default.
    """
    if stack == 'intake-receiver':
        stack = 'apm-server'
    # Create camel-case name, i.e. apm-server -> ApmServer
    stack_camel = ''.join(map(lambda x: x.capitalize(), stack.split('-') ))
    cls = getattr(elastic_stack, stack_camel)
    inst = cls()
    # Must force build flag to get Docker env
    inst.build = 'main@HEAD'

    config = inst._content()
    env_ret = {}
    if 'args' in config['build']:
        return config['build']['args']


def merge_env_to_directive(cls_env: dict, image_str: str, docker_lines=None):
    """
    Take an env and a image and try to substitute
    """
    if ':' in image_str:
        image_name, version = image_str.split(':')
    else:
        image_name = image_str
        version = ''
    
    if image_name.startswith('$'):
        image_name = re.sub(r'[\$\{\}]', '', image_name)
        if image_name in cls_env:
            image_name = cls_env[image_name]
            if ':' in image_name:
                image_name, version = image_name.split(':')
                return f"{image_name}:{version}"
        else:
            for line in docker_lines:
                if line.startswith('ARG'):
                    _, directive_value = line.split(' ')
                    if '=' in directive_value:
                        arg_key, arg_val = directive_value.split('=')
                        if arg_key == image_name:
                            if ':' in arg_val:
                                image_name, version = arg_val.split(':')
                            else:
                                image_name = arg_val.strip()

    if version.startswith('$'):
            version = re.sub(r'[\$\{\}]', '', version)
            if version in cls_env:
                version = cls_env[version]
            else:
                for line in docker_lines:
                    if line.startswith('ARG'):
                        _, directive_value = line.split(' ')
                        if '=' in directive_value:
                            arg_key, arg_val = directive_value.split('=')
                            if arg_key == version:
                                version = arg_val.strip()


    return f"{image_name}:{version}"

def dockerhub_tags_for_image(image: str) -> str:
    """
    Get the latest version for a image
    """
    image_parts = image.split('/')
    if len(image_parts) == 3:
        # We have a specific repo to search. 
        repo_url = image_parts[0]
        if repo_url == 'docker.elastic.co':
            tags = dockerhub.get_tags_elastic(image_parts[2])
        else:
            logger.warning(f"Found alternative repo [{repo_url}]. Non-standard repo support not yet implemented.")
            tags = []
    elif len(image_parts) == 2:
        # We have a repo and a namespace
        tags = dockerhub.get_tags(image_parts[1], image_parts[0])
    elif len(image_parts) == 1:
        tags = dockerhub.get_tags(image_parts[0])
    else:
        logger.critical("Unknown number of parts found in image: %s" % image)
        tags = []
    return tags

def _filter_maven_tags(tags: list):
    """
    We're looking for the most recent version of adoptopenjdk-11
    A sample version is something like `3.6.3-adoptopenjdk-11`
    """
    matching_tags = []
    for tag in tags:
        if re.match(r'\d+(\.\d+)+\-adoptopenjdk-11', tag):
            matching_tags.append(tag)
    return matching_tags

def _filter_adoptopenjdk_tags(tags: list):
    matching_tags = []
    for tag in tags:
        if re.match(r'\d+(\.\d+)+\-adoptopenjdk-11', tag):
            matching_tags.append(tag)
    return matching_tags

def _filter_node_tags(tags: list, version: str):
    matching_tags = []
    if re.match(r'\d+-[A-Za-z]+$', version):
        _, distro_name = version.split('-')
        for tag in tags:
            if re.match(r'\d+-[A-Za-z]+$', tag):
                _, tag_distro_name = tag.split('-')
                if tag_distro_name == distro_name:
                    matching_tags.append(tag)
        return matching_tags
    else:
        return _filter_version_number(tags)
    

def _filter_golang_tags(tags: list, version: str):
    matching_tags = []
    if re.match(r'^[A-Za-z]+$', version):
        for tag in tags:
            if re.match(r'^[a-zA-Z]+$', tag):
                matching_tags.append(tag)
        return matching_tags
    else:
        return _filter_version_number(tags)

def _filter_php_tags(tags: list):
    matching_tags = []
    for tag in tags:
        if re.match(r'\d+(\.\d+)+\-apache$', tag):
            matching_tags.append(tag)
    return matching_tags

def _filter_statsd_tags(tags: list):
    matching_tags = []
    for tag in tags:
        if re.match(r'v\d+(\.\d+)+$', tag):
            matching_tags.append(tag)
    return matching_tags

def _filter_stack_tags(tags: list):
    matching_tags = []
    for tag in tags:
        if re.match(r'\d+(\.\d+)+\-SNAPSHOT$', tag):
            matching_tags.append(tag)
    return matching_tags

def _filter_version_number(tags: list):
    matching_tags = []
    for tag in tags:
        if re.match(r'\d+(\.\d+)+$', tag):
            matching_tags.append(tag)
    return matching_tags




def filter_tags(repo: str, tags: list, version: str):
    """
    Dispatcher for tag filtering based on image type

    For each repo, we have a certain strategy to filter tags for what we're looking for.
    Without this type of filtering, we'll just grab whatever the most recent upload is, which
    is not what we want.
    """
    # Deconstruct repo name

    if repo == 'maven':
        return _filter_maven_tags(tags)
    if repo in ['adoptopenjdk', 'opbeans-java']:
        return _filter_adoptopenjdk_tags(tags)
    if repo == 'golang':
        return _filter_golang_tags(tags, version)
    if repo == 'php':
        return _filter_php_tags(tags)
    if repo == 'statsd':
        return _filter_statsd_tags(tags)
    if repo == 'apm-server':
        return _filter_stack_tags(tags)
    if repo in ['node', 'opbeans-node']:
        return _filter_node_tags(tags, version)
    if repo in ['golang', 'alpine', 'nginx', 'opbeans-python', 'opbeans-ruby', 'python', 'ruby']:
        return _filter_version_number(tags)


    raise Exception(f"No tag filter defined for repo: {repo}")




@click.command()
@click.option('--debug', is_flag=True)
@click.option('--dev', is_flag=True)
def bump(debug, dev):
    """
    Program entrypoint
    """
    setup_logging(debug)
    outdated_images = {}
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
        elif project in ['apm-server', 'intake-receiver']:
            stack_env = collect_stack_env(project)
            # FIXME dry
            if stack_env and images:
                tmp_image_list = []
                for image in images:
                    merged_image = merge_env_to_directive(stack_env, image, docker_lines=docker_lines)
                    tmp_image_list.append(merged_image)
                images = tmp_image_list

        for image in images:
            logger.debug(f"Processing image {image}")
            try:
                image_name, version = image.split(':')
                repo = image_name.split('/').pop()
                tags = dockerhub_tags_for_image(image_name)
                if tags:
                    filtered_tags = filter_tags(repo, tags, version)
                else:
                    logger.warning(f"Unable to resolve tags for repo [{repo}] in project [{project}]. Skipping repo.")
                    continue
                if version != 'latest' and filtered_tags and version != filtered_tags[0]:
                    logger.debug(f'Found outdated image for image {image} in project {project}')
                    if project not in outdated_images:
                        outdated_images[project] = {}
                    outdated_images[project][image] = {'current_version': version, 'new_version': filtered_tags[0]}

            except ValueError:
                logger.critical("Probable bug on image [%s]" % image)
    if outdated_images:
        print('\n\nFound outdated images:\n')
        print(json.dumps(outdated_images, indent=4))
        sys.exit(1)
    

        