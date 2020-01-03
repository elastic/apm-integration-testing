#
# helpers
#

import codecs
import functools
import json
import multiprocessing
import os
import re
import subprocess
import sys
import uuid

try:
    from urllib.request import urlopen, urlretrieve, Request
except ImportError:
    from urllib import urlretrieve
    from urllib2 import urlopen, Request


def _camel_hyphen(string):
    return re.sub(r'([a-z])([A-Z])', r'\1-\2', string)


def _load_image(cache_dir, url):
    filename = os.path.basename(url)
    filepath = os.path.join(cache_dir, filename)
    etag_cache_file = filepath + '.etag'
    if os.path.exists(etag_cache_file):
        with open(etag_cache_file, mode='r') as f:
            etag = f.read().strip()
    else:
        etag = None
    request = Request(url)
    request.get_method = lambda: 'HEAD'
    try:
        response = urlopen(request)
    except Exception as e:
        print('Error while fetching %s: %s' % (url, str(e)))
        return False
    new_etag = response.info().get('ETag')
    if etag == new_etag:
        print("Skipping download of %s, local file is current" % filename)
        return True
    print("downloading", url)
    try:
        os.makedirs(cache_dir)
    except Exception:  # noqa: E722
        pass  # ignore
    try:
        urlretrieve(url, filepath)
    except Exception as e:
        print('Error while fetching %s: %s' % (url, str(e)))
        return False
    subprocess.check_call(["docker", "load", "-i", filepath])
    with open(etag_cache_file, mode='w') as f:
        f.write(new_etag)
    return True

def generated_version():
    """Generates a service version randomly."""
    return uuid.uuid4()


def load_images(urls, cache_dir):
    load_image_fn = functools.partial(_load_image, cache_dir)
    pool = multiprocessing.Pool(4)
    # b/c python2
    try:
        results = pool.map_async(load_image_fn, urls).get(timeout=10000000)
    except KeyboardInterrupt:
        pool.terminate()
        raise
    if not all(results):
        print("Errors while downloading. Exiting.")
        sys.exit(1)


DEFAULT_HEALTHCHECK_INTERVAL = "10s"
DEFAULT_HEALTHCHECK_RETRIES = 12


def curl_healthcheck(port, host="localhost", path="/healthcheck",
                     interval=DEFAULT_HEALTHCHECK_INTERVAL, retries=DEFAULT_HEALTHCHECK_RETRIES):
    return {
        "interval": interval,
        "retries": retries,
        "test": ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent",
                 "--output", "/dev/null",
                 "http://{}:{}{}".format(host, port, path)]
    }


def wget_healthcheck(port, host="localhost", path="/healthcheck",
                     interval=DEFAULT_HEALTHCHECK_INTERVAL, retries=DEFAULT_HEALTHCHECK_RETRIES):
    return {
        "interval": interval,
        "retries": retries,
        "test": ["CMD", "wget", "-q", "--server-response", "-O", "/dev/null",
                 "http://{}:{}{}".format(host, port, path)]
    }


build_manifests = {}  # version -> manifest cache


def latest_build_manifest(version):
    minor_version = ".".join(version.split(".", 2)[:2])
    rsp = urlopen("https://staging.elastic.co/latest/{}.json".format(minor_version))
    if rsp.code != 200:
        raise Exception("failed to query build candidates at {}: {}".format(rsp.geturl(), rsp.info()))
    encoding = "utf-8"  # python2 rsp.headers.get_content_charset("utf-8")
    info = json.load(codecs.getreader(encoding)(rsp))
    if "summary_url" in info:
        print("found latest build candidate for {} - {} at {}".format(minor_version, info["summary_url"], rsp.geturl()))
    return info["manifest_url"]


def resolve_bc(version, build_id):
    """construct or discover build candidate manifest url"""
    if build_id is None:
        return

    if version is None:
        return

    # check cache
    if version in build_manifests:
        return build_manifests[version]

    if build_id == "latest":
        manifest_url = latest_build_manifest(version)
    else:
        manifest_url = "https://staging.elastic.co/{patch_version}-{sha}/manifest-{patch_version}.json".format(
            patch_version=version,
            sha=build_id,
        )
    rsp = urlopen(manifest_url)
    if rsp.code != 200:
        raise Exception("failed to fetch build manifest at {}: {}".format(rsp.geturl(), rsp.info()))
    encoding = "utf-8"  # python2 rsp.headers.get_content_charset("utf-8")
    manifest = json.load(codecs.getreader(encoding)(rsp))
    build_manifests[version] = manifest  # fill cache
    return manifest


def parse_version(version):
    res = []
    for x in version.split('.'):
        try:
            y = int(x)
        except ValueError:
            y = int(x.split("-", 1)[0])
        res.append(y)
    return res


def add_agent_environment(mappings):
    def fn(func):
        def add_content(self):
            content = func(self)
            for option, envvar in sorted(mappings):
                val = self.options.get(option)
                if val is not None:
                    if isinstance(content["environment"], dict):
                        content["environment"][envvar] = val
                    else:
                        content["environment"].append(envvar + "=" + val)
            return content
        return add_content
    return fn
