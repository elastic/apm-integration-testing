FROM python:3.7

#Install elasticdump
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - \
    && apt-get -yqq update \
    && apt-get install -yqq nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install elasticdump -g

COPY requirements.txt requirements.txt
RUN pip install -q -r requirements.txt

RUN useradd -U -m -s /bin/bash -d /app tester

COPY . /app
WORKDIR /app
USER tester
