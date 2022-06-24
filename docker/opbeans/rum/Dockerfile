FROM node:16-bullseye-slim

ENV DEBIAN_FRONTEND noninteractive
# Install latest chrome dev package and fonts to support major charsets (Chinese, Japanese, Arabic, Hebrew, Thai and a few others)
# Note: this installs the necessary libs to make the bundled version of Chromium that Puppeteer
# installs, work
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
      dumb-init \
      fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /src/*.deb

# Uncomment to skip the chromium download when installing puppeteer. If you do,
# you'll need to launch puppeteer with:
#     browser.launch({executablePath: 'google-chrome-unstable'})
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV CHROME_PATH=/usr/bin/chromium
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /home/pptruser

# Add user to not run as a root.
RUN groupadd -r pptruser && useradd -r -g pptruser -G audio,video pptruser \
      && mkdir -p /home/pptruser/Downloads \
      && chown -R pptruser:pptruser /home/pptruser

COPY package*.json /home/pptruser/
COPY tasks.js /home/pptruser/
COPY processes.config.js /home/pptruser/
RUN chown -R pptruser:pptruser /home/pptruser;

# Run everything after as non-privileged user.
USER pptruser

# the install is retry threee times with a pause of 10 seconds
RUN for i in 1 2 3; \
    do \
      npm install --no-optional;\
      sleep 10; \
      ([ $i -eq 3 ] && exit 1) || true; \
    done;

# If running Docker >= 1.13.0 use docker run's --init arg to reap zombie processes, otherwise
# uncomment the following lines to have `dumb-init` as PID 1
ENTRYPOINT ["dumb-init", "--"]
CMD ["node_modules/.bin/pm2-docker", "processes.config.js"]
