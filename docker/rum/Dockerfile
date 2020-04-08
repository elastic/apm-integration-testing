FROM node:12-slim

ARG RUM_AGENT_BRANCH=master
ARG RUM_AGENT_REPO=elastic/apm-agent-rum-js
ARG APM_SERVER_URL

RUN apt update -qq \
    && apt install -qq -y curl git gnupg libgconf-2-4 --no-install-recommends \
    && curl -sSfkL https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt update -qq \
    && apt install -qq -y google-chrome-unstable fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst ttf-freefont python g++ build-essential \
      --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /src/*.deb

# It's a good idea to use dumb-init to help prevent zombie chrome processes.
ADD https://github.com/Yelp/dumb-init/releases/download/v1.2.0/dumb-init_1.2.0_amd64 /usr/local/bin/dumb-init
RUN chmod +x /usr/local/bin/dumb-init

RUN git clone https://github.com/${RUM_AGENT_REPO}.git /rumjs-integration-test
RUN (cd /rumjs-integration-test \
  && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
  && git checkout ${RUM_AGENT_BRANCH})

WORKDIR /rumjs-integration-test

RUN npm install

# Run the build on all the packages/* to make sure the files referenced in both
# main and module fields are available when they are required by successive dependencies
RUN npx lerna run build && npx lerna run build:e2e --scope=@elastic/apm-rum

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
