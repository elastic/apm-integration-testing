#!/usr/bin/env python
"""
Create a pipeline for use with the migration reindexing script.

"""
import datetime
import os
import sys

import elasticsearch


p = os.path.abspath(os.path.join((os.path.dirname(__file__)), "..", "..", "tests", "server"))
sys.path.append(p)
from test_upgrade import MIGRATION_SCRIPT


def put():
    es = elasticsearch.Elasticsearch()
    id_ = datetime.datetime.now().strftime('apm-upgrade-%Y%m%d-%H%M%S')
    es.ingest.put_pipeline(
        id=id_,
        body={
            "description": "test APM reindex pipeline",
            "processors": [
                {
                    "script": {
                        "lang": "painless",
                        "source": MIGRATION_SCRIPT.replace("._source.", "."),
                    }
                }
            ]
        }
    )
    return id_


def main():
    print("created pipeline: " + put())


if __name__ == '__main__':
    main()
