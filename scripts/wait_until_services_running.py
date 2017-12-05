import timeout_decorator
import requests
import time
import sys


@timeout_decorator.timeout(90)
def wait_until_setup(url):
    time.sleep(5)

    def call_service():
        try:
            return requests.get(url).status_code
        except timeout_decorator.TimeoutError:
            raise
        except:
            return None

    while call_service() != 200:
        time.sleep(5)


if __name__ == '__main__':
    args = sys.argv
    if len(args) == 1:
        exit
    elif len(args) == 2:
        for url in args[1].split(","):
            print("wait_until running: {}".format(url))
            wait_until_setup(url)
    else:
        raise Exception("Urls should be passed in as comma seperated string.")
