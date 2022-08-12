__version__ = "0.1.0"
import os
import re
import click
import json
import sys
import logging
import junit_xml

from scripts.modules import opbeans, elastic_stack  # type: ignore

from . import dockerhub

logger = logging.getLogger(__name__)

PROJECTS = [
    "apm-server",
    "apm-server/haproxy",
    "apm-server/managed",
    "apm-server/recorder",
    "apm-server/teeproxy",
    "dotnet",
    "dyno",
    "elastic-agent",
    "intake-receiver",
    "java/spring",
    "nodejs/express",
    "opbeans/dotnet",
    "opbeans/frontend_nginx",
    "opbeans/go",
    "opbeans/java",
    "opbeans/node",
    "opbeans/python",
    "opbeans/ruby",
    "opbeans/rum",
    "php/apache",
    "python/django",
    "python/flask",
    "ruby/rails",
    "rum",
    "statsd",
]


def setup_logging(is_debug: bool) -> None:
    """
    Initialize logging

    is_debug: Will set the logger to DEBUG logging level. Otherwise, defaults to INFO.
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
    Get Dockefile for a project and return a list line-by-line

    project: The project to get the Dockerfile for. This corresponds to the name of the directory on the file system inside apm-integration-testing/docker
    """
    logger.debug("Search for Docker file for %s" % project)
    docker_file_target_location = os.path.join(
        _get_script_path(), "..", "..", "..", "docker", project, "Dockerfile"
    )
    logger.debug(
        "Found Docker file for project %s in %s"
        % (project, docker_file_target_location)
    )
    if not os.path.exists(docker_file_target_location):
        logger.debug("Not found")
    else:
        logger.debug("Found Docker file for %s" % project)
        with open(docker_file_target_location, "r") as fh_:
            docker_lines = fh_.readlines()
    return docker_lines


def docker_extract_image(docker_lines: list, filter_to="FROM") -> list:
    """
    Given a line in a Dockerfile, return the image if found

    docker_lines: A list of lines in the Dockerfile
    filter_to: The Docker directive to consider as the keyword for a line containing a reference to an image
    """
    ret = []
    for line in docker_lines:
        tokens = line.split(" ")
        leading_token = tokens[0]
        if filter_to and re.match(filter_to, leading_token):
            ret.append(tokens[1].strip())
    return ret


def collect_opbean_env(opbean: str) -> dict:
    """
    Given an Opbean, determine the environment variables which are set
    by default.

    opbean: The name of the opbean. These correspond to directory names in apm-integration-testing/docker/opbeans
    """
    cls = getattr(opbeans, "Opbeans" + opbean.capitalize())
    inst = cls()
    opbean_config = inst._content()
    env_ret = {}
    if "args" in opbean_config["build"]:
        for arg in opbean_config["build"]["args"]:
            env_key, env_val = arg.split("=")
            env_ret[env_key] = env_val
    for environment in opbean_config["environment"]:
        if "=" not in environment:
            continue
        environment_key, environment_value = environment.split("=", maxsplit=1)
        env_ret[environment_key] = environment_value
    return env_ret


def collect_stack_env(stack: str) -> dict:
    """
    Given a stack component, determine the environment variables which are set
    by default.
    """
    if stack == "intake-receiver":
        stack = "apm-server"
    # Create camel-case name, i.e. apm-server -> ApmServer
    stack_camel = "".join(map(lambda x: x.capitalize(), stack.split("-")))
    cls = getattr(elastic_stack, stack_camel)
    inst = cls()
    # Must force build flag to get Docker env
    inst.build = "main@HEAD"

    config = inst._content()
    env_ret = {}
    if "args" in config["build"]:
        return config["build"]["args"]


def merge_env_to_directive(cls_env: dict, image_str: str, docker_lines=None):
    """
    Take an env which is generated from the class definition and merge the values
    into the name of an image. If `docker_lines` are passed in, this function will
    merge variables discovered in the Dockerfile as well.

    cls_env: A dictionary which contains all the values which are in a class definition for a particular opbean or stack component

    image_str: The image and tag to substitute into. Ex: `my_great_image:${my_version}`

    docker_lines: The content of a Dockefile, split into lines
    """
    if ":" in image_str:
        image_name, version = image_str.split(":")
    else:
        image_name = image_str
        version = ""

    if image_name.startswith("$"):
        image_name = re.sub(r"[\$\{\}]", "", image_name)
        if image_name in cls_env:
            image_name = cls_env[image_name]
            if ":" in image_name:
                image_name, version = image_name.split(":")
                return f"{image_name}:{version}"
        else:
            for line in docker_lines:
                if line.startswith("ARG"):
                    _, directive_value = line.split(" ")
                    if "=" in directive_value:
                        arg_key, arg_val = directive_value.split("=")
                        if arg_key == image_name:
                            if ":" in arg_val:
                                image_name, version = arg_val.split(":")
                            else:
                                image_name = arg_val.strip()

    if version.startswith("$"):
        version = re.sub(r"[\$\{\}]", "", version)
        if version in cls_env:
            version = cls_env[version]
        else:
            for line in docker_lines:
                if line.startswith("ARG"):
                    _, directive_value = line.split(" ")
                    if "=" in directive_value:
                        arg_key, arg_val = directive_value.split("=")
                        if arg_key == version:
                            version = arg_val.strip()

    return f"{image_name}:{version}"


def dockerhub_tags_for_image(image: str) -> str:
    """
    Get the latest version for a image

    Go out to the container registry and fetch all the tags for a given image.

    image: The full URI of the image. Ex: 'docker.elastic.co/apm/apm-server'

    Supported repos:

    * docker.elastic.co
    * registry.hub.docker.com
    """
    image_parts = image.split("/")
    if len(image_parts) == 3:
        # We have a specific repo to search.
        repo_url = image_parts[0]
        if repo_url == "docker.elastic.co":
            if image_parts[2] == "golang-crossbuild":
                tags = dockerhub.get_tags_elastic(image_parts[2], namespace="beats-dev")
            elif image_parts[2] == "elastic-agent":
                tags = dockerhub.get_tags_elastic(
                    image_parts[2], namespace="beats", snapshots=True
                )
            else:
                tags = dockerhub.get_tags_elastic(image_parts[2])
        else:
            logger.warning(
                f"Found alternative repo [{repo_url}]. Non-standard repo support not yet implemented."
            )
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
    Take a list of Maven tags and filter out tags which could potentially be an upgrade target.
    Order of tags is preserved, so the tag at position 0 is the most recent.

    We're looking for the most recent version of adoptopenjdk-11
    A sample version is something like `3.6.3-adoptopenjdk-11`

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    for tag in tags:
        if re.match(r"\d+(\.\d+)+\-adoptopenjdk-11", tag):
            matching_tags.append(tag)
    return matching_tags


_filter_adoptopenjdk_tags = _filter_maven_tags


def _filter_node_tags(tags: list, version: str):
    """
    Take a list of Node tags and filter out tags which could potentially be an upgrade target.
    Order of tags is preserved, so the tag at position 0 is the most recent.

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    if re.match(r"\d+(-[A-Za-z]+)+$", version):
        _, distro_name = version.split("-", maxsplit=1)
        for tag in tags:
            if re.match(r"\d+(-[A-Za-z]+)+$", tag):
                _, tag_distro_name = tag.split("-", maxsplit=1)
                if tag_distro_name == distro_name:
                    matching_tags.append(tag)
        return matching_tags
    else:
        return _filter_version_number(tags)


def _filter_agent_tags(tags: list, version: str):
    """
    Take a list of Elastic Agent tags and filter out tags which could potentially be an upgrade target.
    Order of tags is preserved, so the tag at position 0 is the most recent.

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    if re.match(r"\d+(\.\d+)+(-\w+)+$", version):
        _, distro_name = version.split("-", maxsplit=1)
        for tag in tags:
            if re.match(r"\d+(\.\d+)+(-\w+)+$", tag):
                _, tag_distro_name = tag.split("-", maxsplit=1)
                if tag_distro_name == distro_name:
                    matching_tags.append(tag)
        return matching_tags
    else:
        return _filter_version_number(tags)


def _filter_golang_tags(tags: list, version: str):
    """
    Take a list of Golang tags and filter out tags which could potentially be an upgrade target.
    Order of tags is preserved, so the tag at position 0 is the most recent.

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    if re.match(r"^[A-Za-z]+$", version):
        for tag in tags:
            if re.match(r"^[a-zA-Z]+$", tag):
                matching_tags.append(tag)
        return matching_tags
    else:
        return _filter_version_number(tags)


def _filter_php_tags(tags: list):
    """
    Take a list of PHP tags and filter out tags which could potentially be an upgrade target.
    Order of tags is preserved, so the tag at position 0 is the most recent.

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    for tag in tags:
        if re.match(r"\d+(\.\d+)+\-apache$", tag):
            matching_tags.append(tag)
    return matching_tags


def _filter_statsd_tags(tags: list):
    """
    Take a list of Statsd tags and filter out tags which could potentially be an upgrade target.
    Order of tags is preserved, so the tag at position 0 is the most recent.

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    for tag in tags:
        if re.match(r"v\d+(\.\d+)+$", tag):
            matching_tags.append(tag)
    return matching_tags


def _filter_stack_tags(tags: list):
    """
    Take a list of tags found for components in the Elastic Stack and filter out tags which could potentially be an upgrade target.
    Order of tags is preserved, so the tag at position 0 is the most recent.

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    for tag in tags:
        if re.match(r"\d+(\.\d+)+\-SNAPSHOT$", tag):
            matching_tags.append(tag)
    return matching_tags


def _filter_version_number(tags: list):
    """
    Generic filter which simply filters out tags which correspond just to a version number

    tags: A list of tags which the registry has indicated are available for a given image
    """
    matching_tags = []
    for tag in tags:
        if re.match(r"\d+(\.\d+)+$", tag):
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

    if repo == "maven":
        return _filter_maven_tags(tags)
    if repo in ["adoptopenjdk", "opbeans-java"]:
        return _filter_adoptopenjdk_tags(tags)
    if repo == "golang":
        return _filter_golang_tags(tags, version)
    if repo == "php":
        return _filter_php_tags(tags)
    if repo == "statsd":
        return _filter_statsd_tags(tags)
    if repo == "apm-server":
        return _filter_stack_tags(tags)
    if repo == "elastic-agent":
        return _filter_agent_tags(tags, version)
    if repo in ["node", "opbeans-node"]:
        return _filter_node_tags(tags, version)
    if repo in [
        "golang",
        "alpine",
        "nginx",
        "opbeans-python",
        "opbeans-ruby",
        "python",
        "ruby",
        "haproxy",
    ]:
        return _filter_version_number(tags)
    if repo == "golang-crossbuild":
        return tags

    raise Exception(f"No tag filter defined for repo: {repo}")

def process_junit(results: dict) -> list:
    """
    Produces a junit-xml test suite for consumption by Jenkins
    """
    suites = []
    for project_name, project_data in results.items():
        suite = junit_xml.TestSuite(project_name)
        for image_name, image_data in project_data.items():
            image_case = junit_xml.TestCase(image_name)
            if image_data:
                if image_data["current"] != image_data["upstream"]:
                    image_case.add_failure_info(f"Current image is '{image_data['current']}' and the upstream image is '{image_data['upstream']}'")
            else:  # We have an image name but no contents, possibly because we couldn't support the repo type
                image_case.add_skipped_info("No upstream information was retreivable")
            suite.test_cases.append(image_case)
        suites.append(suite)
    return suites


@click.command()
@click.option("--junit", is_flag=True)
@click.option("--debug", is_flag=True)
def bump(debug, junit):
    """
    Program entrypoint
    """
    setup_logging(debug)
    outdated_images = {} # TODO remove
    results = {}
    for project in PROJECTS:
        results[project] = {}
        docker_lines = get_docker_file(project)
        images = docker_extract_image(docker_lines)
        if project.startswith("opbeans") and "frontend_nginx" not in project:
            _, opbean_name = project.split("/")
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
        elif project in ["apm-server", "intake-receiver"]:
            stack_env = collect_stack_env(project)
            # FIXME dry
            if stack_env and images:
                tmp_image_list = []
                for image in images:
                    merged_image = merge_env_to_directive(
                        stack_env, image, docker_lines=docker_lines
                    )
                    tmp_image_list.append(merged_image)
                images = tmp_image_list
        elif project in ["ruby/rails", "elastic-agent"]:
            tmp_image_list = []
            for image in images:
                merged_image = merge_env_to_directive(
                    {}, image, docker_lines=docker_lines
                )
                tmp_image_list.append(merged_image)
            images = tmp_image_list

        for image in images:
            logger.debug(f"Processing image {image}")
            results[project][image] = {}
            try:
                image_name, version = image.split(":")
                repo = image_name.split("/").pop()
                tags = dockerhub_tags_for_image(image_name)
                if tags:
                    filtered_tags = filter_tags(repo, tags, version)
                else:
                    logger.warning(
                        f"Unable to resolve tags for repo [{repo}] in project [{project}]. Skipping repo."
                    )
                    continue
                if (
                    version != "latest"
                    and filtered_tags
                    and version != filtered_tags[0]
                ):
                    logger.debug(
                        f"Found outdated image for image {image} in project {project}"
                    )
                    results[project][image] = {
                        "current": version,
                        "upstream": filtered_tags[0]
                    }
                    if project not in outdated_images:
                        outdated_images[project] = {}
                    outdated_images[project][image] = {
                        "current_version": version,
                        "new_version": filtered_tags[0],
                    }
                else:
                    results[project][image] = {
                        "current": version,
                        "upstream": version
                    }

            except ValueError:
                logger.critical("Probable bug on image [%s]" % image)
    if junit:
        junit_results = process_junit(results)
        if debug:
            logger.debug(junit_xml.to_xml_report_string(junit_results))
        junit_target_file = os.path.join(_get_script_path(), '..', '..', '..', 'tests', 'results', 'docker-bump.xml')
        if not os.path.exists(junit_target_file):
            os.makedirs(os.path.dirname(junit_target_file))
        with open(junit_target_file, 'w') as fh_:
            junit_xml.to_xml_report_file(fh_, junit_results)
    if outdated_images:
        print("\n\nFound outdated images:\n")
        print(json.dumps(outdated_images, indent=4))
        sys.exit(1)
    else:
        print("No outdated images detected. Have a nice day!")
