#!/usr/bin/env python
"""
Assuming test_upgrade was run, compare results of setting a payload to a apm-server-6.6.0 + reindex vs apm-server-7.0.0.

eg: ./venv/bin/python ./scripts/upgrade/compare_reindexed.py apm-7.0.0-error-2019.01.29
- 6.6.0 indexed from apm-6.6.0-error-2019.01.29 (original)
- 7.0.0 indexed from apm-7.0.0-error-2019.01.29 (wanted)
- 6.6.0 migrated from apm-7.0.0-error-2019.01.29-migrated (got)

"""
import json
import sys

import elasticsearch
import jsondiff


def main():
    idx = sys.argv[1]
    num = 0
    if len(sys.argv) > 2:
        num = int(sys.argv[2])
    es = elasticsearch.Elasticsearch()
    old_exclude_rum = {'query': {'bool': {'must_not': [{'term': {'context.service.agent.name': 'js-base'}}]}}}
    exclude_rum = {'query': {'bool': {'must_not': [{'term': {'agent.name': 'js-base'}}]}}}
    orig = es.search(index=idx.replace("7.0.0", "6.6.0"), body=old_exclude_rum, sort="@timestamp:asc,context.service.agent.name:asc", size=num+1)["hits"]["hits"][num]["_source"]
    want = es.search(index=idx, body=exclude_rum, sort="@timestamp:asc,agent.name:asc", size=num+1)["hits"]["hits"][num]["_source"]
    got = es.search(index=idx+"-migrated", body=exclude_rum, sort="@timestamp:asc,agent.name:asc", size=num+1)["hits"]["hits"][num]["_source"]

    print("Diff:")
    print(jsondiff.JsonDiffer(syntax='symmetric', dump=True, dumper=jsondiff.JsonDumper(indent=True)).diff(want, got))
    print()
    print("Original:")
    json.dump(orig, sys.stdout, sort_keys=True)
    print()
    print("Wanted:")
    json.dump(want, sys.stdout, sort_keys=True)
    print()
    print("Got:")
    json.dump(got, sys.stdout, sort_keys=True)
    print()


if __name__ == '__main__':
    main()
