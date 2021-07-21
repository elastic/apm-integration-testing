ARG NODE_VERSION=
FROM node:${NODE_VERSION}

ARG GID=1001
ARG UID=1001
RUN mkdir -p /usr/share/kibana/config
WORKDIR /usr/share/kibana
RUN groupadd -f --gid ${GID} kibana \
  && useradd --uid ${UID} --gid ${GID} --groups 0 --home-dir /usr/share/kibana --no-create-home kibana
RUN chown -R kibana:0 /usr/share/kibana
# Bazel is installed at global level so we need permissions on /usr/local
RUN chown -R kibana:0 /usr/local
USER kibana

RUN git config --global user.email "none@example.com"
RUN git config --global user.name "None"
RUN git init && git add . && git commit -a -m "init commit"
ENV HOME=/usr/share/kibana
ENV NODE_OPTIONS= --max-old-space-size=4096
ENV FORCE_COLOR=1
ENV BABEL_DISABLE_CACHE=true

EXPOSE 5601
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["yarn kbn bootstrap && yarn start -c /usr/share/kibana/config/kibana_src.yml -c /usr/share/kibana/config/kibana.yml --no-dev-config"]


HEALTHCHECK --interval=10s --timeout=5s --start-period=1m --retries=300 CMD curl -sSL http://127.0.0.1:5601/login|grep -v 'Kibana server is not ready yet'
