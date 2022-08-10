from re import I
import requests
from random import randint
from time import sleep
from shelved_cache import PersistentCache
from cachetools import TTLCache, cached

filename = ".cache/dockerhub.cache"
pc = PersistentCache(TTLCache, filename=filename, maxsize=10000, ttl=86400)


def get_filter_string(repo):
    """
    For each repo, we need to get a filter string to avoid having to pull all possible tags, which can be a large number of API
    requests which could result in rate-limiting
    """
    if repo == "maven":
        return "adoptopenjdk"
    if repo == "adoptopenjdk":
        return "jre-hotspot"


# @cached(pc)
def get_tags_elastic(repo, namespace="apm", snapshots=False):
    """
    Get tags from the Elastic Docker repo using the internal API
    """
    ret = []
    request_url = f"https://docker-api.elastic.co/v1/r/{namespace}/{repo}/"
    if not snapshots:
        request_url += "?show_snapshots=false"
    resp = requests.get(request_url)
    decoded_response = resp.json()
    for result in decoded_response["results"]:
        ret.append(result["name"])
    return ret


@cached(pc)
def get_tags(repo, namespace="library"):
    """
    Get the tags using the Docker registry API

    The tags are in order of the date they were pushed, so no additional sorting
    should be needed.

    The syntax is a bit tricky. If you have an image that specifies a repo, it will look like this: opbeans/opbeans-python:latest

    In the above example, 'opbeans' is the namespace and 'opbeans-python' is the repo.

    But if you don't have a namspace your image name might look like this: python:3.7

    In that example, 'python' is the repo and the namespace should be the default of 'library'.
    """
    page_counter = 1
    ret = []
    while True:
        request_url = f"https://registry.hub.docker.com/v2/repositories/{namespace}/{repo}/tags/?page={page_counter}"
        filter_str = get_filter_string(repo)
        if filter_str:
            request_url += f"&name={filter_str}"
        resp = requests.get(request_url)
        if resp.status_code == 404 or page_counter > 20:
            break
        else:
            page_counter += 1
            decoded_response = resp.json()
            for result in decoded_response["results"]:
                ret.append(result["name"])
            sleep(randint(1, 5))
    return ret
