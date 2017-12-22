from django.http import HttpResponse
import logging
import elasticapm
logger = logging.getLogger('mysite')


def show(request):
    return HttpResponse(foo())


@elasticapm.capture_span()
def foo():
    return "foo"
