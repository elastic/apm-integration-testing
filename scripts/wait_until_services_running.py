import argparse
import time

import requests
import timeout_decorator


@timeout_decorator.timeout(180)
def wait_until_setup(url):
    def call_service():
        try:
            return requests.get(url, timeout=5).status_code
        except timeout_decorator.TimeoutError:
            raise
        except:
            return

    while call_service() != 200:
        time.sleep(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('urls', nargs='+', help='health check url(s)')
    args = parser.parse_args()

    # each url arg can contain comma-separated values, for backwards compat
    for urls in args.urls:
        for url in urls.split(","):
            print("wait_until running: {}".format(url))
            wait_until_setup(url)
    # temporarily necessary until we can configure
    # to ignore the healthcheck endpoint for writing to ES in all agents
    time.sleep(2)


if __name__ == '__main__':
    main()
