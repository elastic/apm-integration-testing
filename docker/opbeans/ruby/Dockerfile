FROM ruby:2.5

# Install node.js
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash - \
    && apt-get install -y nodejs

# Install yarn
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -\
      && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
      && apt-get update \
      && apt-get install -y yarn

LABEL lastupdate="2018-04-19"

WORKDIR /app

RUN curl -L https://github.com/elastic/opbeans-ruby/archive/master.tar.gz | tar --strip-components=1 -xzv

RUN bundle update && yarn

COPY entrypoint.sh /app/entrypoint.sh

CMD ["bin/boot"]
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
