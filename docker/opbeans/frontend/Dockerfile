FROM node:16-slim

ARG TARGETARCH=amd64
RUN apt-get -qq update \
  && apt install -qq -y --no-install-recommends \
    curl \
    git \
    gnupg \
    libgconf-2-4 \
    python \
    chromium \
    chromium-sandbox \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
	&& rm -rf /var/lib/apt/lists/*

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

ENV CHROME_PATH=/usr/bin/chromium

COPY tasks.js /home/chrome/
COPY processes.config.js /home/chrome/

CMD ["node_modules/.bin/pm2-docker", "processes.config.js"]
