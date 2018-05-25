"""
Group fixture defaults and provide convenient access to them.
"""
import os
import sys


APM_SERVER_URL = "http://localhost:8200"
ES_URL = "http://localhost:9200"
KIBANA_URL = "http://localhost:5601"

DJANGO_SERVICE_NAME = "djangoapp"
DJANGO_URL = "http://localhost:8003"
EXPRESS_SERVICE_NAME = "expressapp"
EXPRESS_URL = "http://localhost:8010"
FLASK_SERVICE_NAME = "flaskapp"
FLASK_URL = "http://localhost:8001"
GO_NETHTTP_SERVICE_NAME = "gonethttpapp"
GO_NETHTTP_URL = "http://localhost:8080"
RAILS_SERVICE_NAME = "railsapp"
RAILS_URL = "http://localhost:8020"


def from_env(var):
    return os.getenv(var, getattr(sys.modules[__name__], var))
