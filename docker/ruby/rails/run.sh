#!/usr/bin/env bash
set -x

# Latest is not a branch but the latest released version, so it's not required to
if [ "${RUBY_AGENT_VERSION}" = "latest" ] ; then
  echo "Let's use the latest release."
else
  echo "Let's checkout from the source code and see whether the version is a branch or a sha1."
  git clone https://github.com/${RUBY_AGENT_REPO}.git /agent/apm-agent-ruby
  cd /agent/apm-agent-ruby
  git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*'
  git checkout ${RUBY_AGENT_VERSION}
  git show-ref --verify refs/heads/${RUBY_AGENT_VERSION} && touch /tmp/branch || true
fi
