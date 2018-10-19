from django.http import HttpResponse
import logging
import elasticapm
logger = logging.getLogger('mysite')


def show(request):
    return HttpResponse(oof())


def oof():
    raise Exception('oof')
