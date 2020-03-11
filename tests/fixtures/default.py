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
DOTNET_SERVICE_NAME = "dotnetapp"
DOTNET_URL = "http://localhost:8100"
EXPRESS_SERVICE_NAME = "expressapp"
EXPRESS_URL = "http://localhost:8010"
FLASK_SERVICE_NAME = "flaskapp"
FLASK_URL = "http://localhost:8001"
GO_NETHTTP_SERVICE_NAME = "gonethttpapp"
GO_NETHTTP_URL = "http://localhost:8080"
RAILS_SERVICE_NAME = "railsapp"
RAILS_URL = "http://localhost:8020"
JAVA_SPRING_SERVICE_NAME = "springapp"
JAVA_SPRING_URL = "http://localhost:8090"
RUM_SERVICE_NAME = "rumapp"
RUM_URL = "http://localhost:8000"
ES_USER = "elastic"
ES_PASS = "changeme"
ELASTIC_APM_SECRET_TOKEN = "SuPeRsEcReT"


def from_env(var):
    return os.getenv(var, getattr(sys.modules[__name__], var))
