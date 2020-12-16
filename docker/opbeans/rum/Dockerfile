FROM node:8

# Install latest chrome dev package and fonts to support major charsets (Chinese, Japanese, Arabic, Hebrew, Thai and a few others)
# Note: this installs the necessary libs to make the bundled version of Chromium that Puppeteer
# installs, work.
RUN apt update -qq \
    && apt install -qq -y curl git gnupg libgconf-2-4 libxss1 libxtst6 python g++ build-essential --no-install-recommends \
    && curl -sSfkL https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt update -qq \
    && apt install -qq -y google-chrome-unstable fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst ttf-freefont \
      --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /src/*.deb

# Add Chrome as a user
RUN groupadd -r chrome && useradd -r -g chrome -G audio,video chrome \
    && mkdir -p /home/chrome && chown -R chrome:chrome /home/chrome

WORKDIR /home/chrome

# Run Chrome non-privileged
USER chrome

# Expose port 9222
EXPOSE 9222

COPY package*.json /home/chrome/

RUN npm install

ENV CHROME_PATH=/usr/bin/chromium-browser

COPY tasks.js /home/chrome/
COPY processes.config.js /home/chrome/

CMD ["node_modules/.bin/pm2-docker", "processes.config.js"]
