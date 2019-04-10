#!/usr/bin/env python
"""
Migrate an index using the reindexing script in a pipeline.

"""
import sys

import elasticsearch

import pipeline


def chase(cause):
    if "script_stack" in cause:
        for ss in cause["script_stack"]:
            print(ss.encode("utf-8"))  # don't expand \n, etc
    if "caused_by" in cause:
        chase(cause["caused_by"])


def main():
    source_index = sys.argv[1]
    dest_index = sys.argv[2] if len(sys.argv) > 2 else source_index.replace("6.6.2", "7.0.0") + "-migrated"
    pipeline_id = pipeline.put()
    es = elasticsearch.Elasticsearch()
    es.indices.delete(dest_index, expand_wildcards='none', ignore_unavailable=True)
    try:
        es.reindex(
            body={
                # "size": 1,
                "source": {
                    "index": source_index,
                },
                "dest": {
                    "index": dest_index,
                    "pipeline": pipeline_id,
                    "version_type": "internal",
                },
            },
            wait_for_completion=True,
            request_timeout=3600,
        )
    except elasticsearch.exceptions.TransportError as e:
        failure = e.info['failures'][0]  # just consider the first error
        cause = failure['cause']
        print("failed to reindex into", failure["index"], "with", pipeline_id, ":", cause['reason'])
        chase(cause)


if __name__ == '__main__':
    main()
