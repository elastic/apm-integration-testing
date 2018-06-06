FROM opbeans/opbeans-python:latest

COPY requirements.molotov.txt /app/
RUN pip install -r requirements.molotov.txt

COPY entrypoint.sh molotov_scenarios.py  /app/
RUN echo "\nload: molotov --delay 0.6 molotov_scenarios.py" >> Procfile

CMD ["honcho", "start"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]