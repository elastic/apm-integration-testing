FROM python:3.7
# install latest Google Chrome & Chromedriver
RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get -yqq update \
    && apt-get -yqq --allow-unauthenticated install google-chrome-unstable

RUN curl -SLO https://chromedriver.storage.googleapis.com/$(curl -o- https://chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip \
    && apt-get -yqq update \
    && apt install -yqq --no-install-recommends unzip \
    && unzip -d /usr/local/bin/ chromedriver_linux64.zip chromedriver

#Install elasticdump
RUN curl -sL https://deb.nodesource.com/setup_11.x | bash - \
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
