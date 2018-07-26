FROM python:3.7

WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY molotov_scenarios.py entrypoint.py /app/

CMD ["honcho", "start"]
ENTRYPOINT ["/usr/bin/python3", "/app/entrypoint.py"]
