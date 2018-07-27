FROM python:3.7

WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY molotov_scenarios.py entrypoint.sh generate_procfile.py /app/

ENV PYTHONUNBUFFERED=1

CMD ["honcho", "start"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
