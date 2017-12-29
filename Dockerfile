FROM python:3

# install latest Google Chrome & Chromedriver
RUN curl -SLO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
	dpkg -i google-chrome-stable_current_amd64.deb || true && \
	apt update && apt-get -y -f --no-install-recommends install && \
	curl -SLO https://chromedriver.storage.googleapis.com/2.34/chromedriver_linux64.zip && \
	apt install -y --no-install-recommends unzip && \
	unzip -d /usr/local/bin/ chromedriver_linux64.zip chromedriver && \
	rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN useradd -U -m -s /bin/bash -d /app tester

COPY . /app
WORKDIR /app
USER tester