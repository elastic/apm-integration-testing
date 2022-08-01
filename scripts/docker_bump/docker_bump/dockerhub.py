import requests

def get_tags(repo, namespace='library'):
    """
    Get the tags using the Docker registry API

    The tags are in order of the date they were pushed, so no additional sorting
    should be needed.

    The syntax is a bit tricky. If you have an image that specifies a repo, it will look like this: opbeans/opbeans-python:latest

    In the above example, 'opbeans' is the namespace and 'opbeans-python' is the repo.

    But if you don't have a namspace your image name might look like this: python:3.7

    In that example, 'python' is the repo and the namespace should be the default of 'library'.
    """
    resp = requests.get(f'https://registry.hub.docker.com/v2/repositories/{namespace}/{repo}/tags/')
    decoded_response = resp.json()
    ret = []
    for result in decoded_response['results']:
        ret.append(result['name'])
    return ret
