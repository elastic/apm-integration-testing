FROM node:8-slim

ARG RUM_AGENT_BRANCH
ARG RUM_AGENT_REPO
ARG APM_SERVER_URL

RUN apt-get -qq update \
    && apt-get -qq install -yq libgconf-2-4 \
    && apt-get -qq install -y curl git --no-install-recommends \
    && curl -L https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get -qq update \
    && apt-get -qq install -y google-chrome-unstable fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst ttf-freefont python g++ build-essential \
      --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -qq purge --auto-remove -y \
    && rm -rf /src/*.deb

# It's a good idea to use dumb-init to help prevent zombie chrome processes.
ADD https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init
RUN chmod +x /usr/local/bin/dumb-init

RUN git clone -b $RUM_AGENT_BRANCH --single-branch https://github.com/$RUM_AGENT_REPO.git --depth 1 rumjs-integration-test

WORKDIR /rumjs-integration-test

RUN npm install

RUN npx lerna run --scope=@elastic/apm-rum build && npx lerna run build:e2e

# Add user so we don't need --no-sandbox.
RUN groupadd -r pptruser && useradd -r -g pptruser -G audio,video pptruser \
    && mkdir -p /home/pptruser/Downloads \
    && chown -R pptruser:pptruser /home/pptruser \
    && chown -R pptruser:pptruser /rumjs-integration-test/node_modules

# Run everything after as non-privileged user.
USER pptruser

ENTRYPOINT ["dumb-init", "--"]

COPY run.sh /run.sh

EXPOSE 8000 9222

CMD [ "/bin/bash", "/run.sh" ]
