from django.http import HttpResponse
from django.conf.urls import include, url


urlpatterns = [
    url(r'^foo', include('foo.urls')),
    url(r'^bar', include('bar.urls'))
]
