from django.http import HttpResponse
import logging
logger = logging.getLogger('mysite')


def show(request):
    return HttpResponse("foo")
