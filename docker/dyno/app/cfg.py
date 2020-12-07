# -*- coding: utf-8 -*-
import yaml


class Config(object):
    # Configuration information may reside here

    def __init__(self):
        self.slider_range = self._load_range('range.yml')

    def _load_range(self, range_file):
        with open(range_file, 'r') as fh_:
            slider_range = yaml.load(fh_, Loader=yaml.FullLoader)
        return slider_range
