APM_INDEX = "apm-*"


def clean(elasticsearch):
    elasticsearch.indices.delete(APM_INDEX)


def verify_transaction_data(elasticsearch, name):
    s = elasticsearch.search(index=APM_INDEX, body={"query": {"match_all": {}}})
    doc_no = 1
    # TODO: why does this differ?
    if name == "flask_app":
        doc_no = 2
    elif name == "django_app":
        doc_no = 1
    assert s['hits']['total'] == doc_no
