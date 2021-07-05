FROM python:3.7

#Install elasticdump
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - \
    && apt-get -yqq update \
    && apt-get install -yqq nodejs \
    && npm install elasticdump -g

#Install docker to validate test-helps make goal
RUN apt-get -yqq install \
      apt-transport-https \
      ca-certificates \
      curl \
      gnupg \
      lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo \
       "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
       $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get -yqq update \
    && apt-get -yqq install docker-ce docker-ce-cli containerd.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install -q -r requirements.txt

RUN useradd -U -m -s /bin/bash -d /app tester

COPY . /app
WORKDIR /app
USER tester
