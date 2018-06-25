FROM node:8

RUN apt-get update && apt-get install -y \
	apt-transport-https \
	ca-certificates \
	curl \
    gnupg \
	--no-install-recommends \
	&& curl -sSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
	&& echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
	&& apt-get update && apt-get install -y \
	google-chrome-stable \
	--no-install-recommends \
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

ENV CHROME_PATH=/usr/bin/chromium-browser

COPY tasks.js /home/chrome/
COPY processes.config.js /home/chrome/

CMD ["node_modules/.bin/pm2-docker", "processes.config.js"]
