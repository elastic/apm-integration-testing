FROM python:3

RUN mkdir -p /app
WORKDIR /app
ADD . /app

#TODO: move this to CMD/runtime
RUN pip install -Ur requirements.txt
CMD ["/bin/bash", "-c", "python testapp/manage.py runserver 0.0.0.0:8002"]
