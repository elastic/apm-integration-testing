#!/bin/bash -e
# for details about how it works see https://github.com/elastic/apm-integration-testing#continuous-integration

cd scripts/kibana/validate-ts-interfaces-against-apm-server-sample-docs

n=0
until [ "$n" -ge 5 ]
do
   yarn  && break  # substitute your command here
   n=$((n+1))
   sleep 15
done

n=0
until [ "$n" -ge 5 ]
do
    yarn setup elastic "${MERGE_TARGET}" elastic "${MERGE_TARGET}" && break
   n=$((n+1))
   sleep 15
done

n=0
until [ "$n" -ge 5 ]
do
   yarn lint && break  # substitute your command here
   n=$((n+1))
   sleep 15
done
