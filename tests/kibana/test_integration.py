import os
import urllib.parse

from selenium.webdriver import Chrome, ChromeOptions
from webium import BasePage
from webium.driver import close_driver

import webium.settings


class HeadlessChrome(Chrome):
    def __init__(self):
        chrome_options = ChromeOptions()
        chrome_options.set_headless(True)
        super().__init__(chrome_options=chrome_options)


webium.settings.driver_class = HeadlessChrome


class KibanaPage(BasePage):
    def __init__(self, path):
        url = urllib.parse.urljoin(os.environ['KIBANA_URL'], path)
        super().__init__(url=url)


def test_sidebar():
    home_page = KibanaPage('/')
    home_page.open()
    close_driver()
