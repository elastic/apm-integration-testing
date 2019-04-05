#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

cd scripts/kibana/validate-ts-interfaces-against-apm-server-sample-docs
yarn
yarn setup && yarn lint
