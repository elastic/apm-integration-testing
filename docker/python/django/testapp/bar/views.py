from django.http import HttpResponse
import logging
import elasticapm
logger = logging.getLogger('mysite')


def show(request):
    return HttpResponse(bar())


@elasticapm.trace()
def bar():
    extra()
    return "bar"


@elasticapm.trace()
def extra():
    return "extra"
