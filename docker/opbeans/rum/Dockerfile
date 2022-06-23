FROM node:16-slim

# Install latest chrome dev package and fonts to support major charsets (Chinese, Japanese, Arabic, Hebrew, Thai and a few others)
# Note: this installs the necessary libs to make the bundled version of Chromium that Puppeteer
# installs, work
ARG TARGETARCH=amd64
RUN apt update -qq \
    && apt install -qq -y --no-install-recommends \
      curl \
      git \
      gnupg \
      libgconf-2-4 \
      libxss1 \
      libxtst6 \
      python \
      g++ \
      build-essential \
      chromium \
      chromium-sandbox \
      fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /src/*.deb

# If running Docker >= 1.13.0 use docker run's --init arg to reap zombie processes, otherwise
# uncomment the following lines to have `dumb-init` as PID 1
ADD https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_${TARGETARCH} /usr/local/bin/dumb-init
RUN chmod +x /usr/local/bin/dumb-init
ENTRYPOINT ["dumb-init", "--"]

# Uncomment to skip the chromium download when installing puppeteer. If you do,
# you'll need to launch puppeteer with:
#     browser.launch({executablePath: 'google-chrome-unstable'})
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV CHROME_PATH=/home/pptruser/chromium-no-sandbox.sh
ENV PUPPETEER_EXECUTABLE_PATH=/home/pptruser/chromium-no-sandbox.sh

WORKDIR /home/pptruser

# Install puppeteer so it's available in the container.
# the install is retry threee times with a pause of 10 seconds
RUN for i in 1 2 3; \
    do \
      npm i puppeteer && break; \
      sleep 10; \
      ([ $i -eq 3 ] && exit 1) || true; \
    done;

# Add user so we don't need --no-sandbox.
# same layer as npm install to keep re-chowned files from using up several hundred MBs more space
RUN groupadd -r pptruser && useradd -r -g pptruser -G audio,video pptruser \
      && mkdir -p /home/pptruser/Downloads \
      && chown -R pptruser:pptruser /home/pptruser
#    && chown -R pptruser:pptruser /node_modules;

RUN echo kernel.unprivileged_userns_clone=1 > /etc/sysctl.d/00-local-userns.conf

# Run everything after as non-privileged user.
USER pptruser

COPY package*.json /home/pptruser/

# the install is retry threee times with a pause of 10 seconds
RUN for i in 1 2 3; \
    do \
      npm install --no-optional;\
      sleep 10; \
      ([ $i -eq 3 ] && exit 1) || true; \
    done;

COPY tasks.js /home/pptruser/
COPY processes.config.js /home/pptruser/

RUN echo '/usr/bin/chromium --disable-gpu-sandbox --disable-namespace-sandbox --disable-setuid-sandbox --no-sandbox --single-process $*' > ${CHROME_PATH} \
  && chmod ugo+rx ${CHROME_PATH}

CMD ["node_modules/.bin/pm2-docker", "processes.config.js"]
