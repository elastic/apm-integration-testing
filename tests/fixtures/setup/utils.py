import timeout_decorator
import time
import requests


@timeout_decorator.timeout(90)
def wait_until_service_responding(url):
    def call_service():
        try:
            return requests.get(url).status_code
        except:
            return None

    while call_service() != 200:
        time.sleep(1)
