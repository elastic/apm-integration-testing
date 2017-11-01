FROM python:3

RUN mkdir -p /app
WORKDIR /app
ADD . /app

#TODO: move this to CMD/runtime
RUN pip install -Ur requirements.txt
CMD ["python", "app.py"]
