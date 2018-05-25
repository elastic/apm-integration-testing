FROM python:3.6

LABEL lastupdate="2018-02-09"

WORKDIR /app

RUN curl -L https://github.com/elastic/opbeans-python/archive/master.tar.gz | tar --strip-components=1 --exclude=demo/db.sql.bz2 -xzv

RUN pip install -r requirements.txt

RUN python manage.py collectstatic

COPY entrypoint.sh /app/entrypoint.sh

CMD ["honcho", "start"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
