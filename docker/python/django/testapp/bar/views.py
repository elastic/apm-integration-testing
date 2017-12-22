from django.http import HttpResponse
import logging
import elasticapm
logger = logging.getLogger('mysite')


def show(request):
    return HttpResponse(bar())


@elasticapm.capture_span()
def bar():
    extra()
    return "bar"


@elasticapm.capture_span()
def extra():
    return "extra"
