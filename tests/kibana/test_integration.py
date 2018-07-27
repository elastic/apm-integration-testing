import urllib.parse

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from webium import BasePage, Find
from webium.driver import close_driver, get_driver

import pytest
import webium.settings


class HeadlessChrome(Chrome):
    def __init__(self):
        chrome_options = ChromeOptions()
        chrome_options.set_headless(True)
        super().__init__(chrome_options=chrome_options)


webium.settings.driver_class = HeadlessChrome


class KibanaPage(BasePage):
    def __init__(self, base, path):
        url = urllib.parse.urljoin(base, path)
        super().__init__(url=url)

    apm_sidebar_button = Find(by=By.CSS_SELECTOR, value='a[aria-label="APM"]')

    def current_url(self):
        return get_driver().current_url[len(self.url):]


@pytest.mark.skip(reason="disabled while kibana snapshot is troubled")
def test_sidebar(kibana):
    home_page = KibanaPage(kibana.url, '/')
    home_page.open()

    assert not home_page.current_url().startswith("app/apm")
    home_page.apm_sidebar_button.click()
    assert home_page.current_url().startswith("app/apm"), "current url: " + home_page.current_url()

    close_driver()
