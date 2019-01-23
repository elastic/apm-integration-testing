MIGRATION_SCRIPT = """
// beat -> observer
def beat = ctx._source.remove("beat");
if (beat != null) {
    ctx._source.observer = beat;
}

def listening = ctx._source.remove("listening");
if (listening != null) {
    ctx._source.observer.listening = listening;
}

// remove host[.name]
ctx._source.remove("host");

// docker.container -> container
def docker = ctx._source.remove("docker");
if (docker != null && docker.containsKey("container")) {
    ctx._source.container = docker.container;
}

// rip up context
HashMap context = ctx._source.remove("context");
if (context != null) {
    // context.process -> process
    if (context.containsKey("process")) {
        ctx._source.process = context.remove("process");
        ctx._source.process.args = ctx._source.process.remove("argv");
    }

    // context.request -> http & url
    HashMap request = context.remove("request");
    if (request != null) {
        // context.request.http_version -> http.version
        // context.request.method -> http.request.method
        if (request.containsKey("http_version") || request.containsKey("method")) {
            ctx._source.http = new HashMap();
            if (request.containsKey("http_version")) {
                ctx._source.http.version = request.remove("http_version");
            }
            if (request.containsKey("method")) {
                ctx._source.http.request = new HashMap();
                ctx._source.http.request.method = request.remove("method");
            }
        }
        // context.request.url -> url
        HashMap url = request.remove("url");
        url.fragment = url.remove("hash");
        url.domain = url.remove("hostname");
        url.path = url.remove("pathname");
        // TODO remove ;//
        url.scheme = url.remove("protocol");
        url.original = url.remove("raw");
        url.query = url.remove("search");
        request.url = url;

        // XXX: body is not currently restored
        def reqBody = request.remove("body");
        if (reqBody != null) {
              def body = new HashMap();
              body.original = reqBody;
              // TODO: figure out how to handle body - it can be a string or an object
              //request.body = bodyContent;
        }

        // restore what is left of request, under http
        ctx._source.http.request = request;
    }

    // context.service.agent -> agent
    HashMap service = context.remove("service");
    ctx._source.agent = service.remove("agent");

    // context.service -> service
    ctx._source.service = service;

    // context.system -> host
    def system = context.remove("system");
    if (system != null) {
        if (! system.containsKey("host")) {
            system.host = new HashMap();
        }
        system.host.os = new HashMap();
        system.host.os.platform = system.remove("platform");
        ctx._source.host = system;
    }

    // context.tags -> labels
    def tags = context.remove("tags");
    if (tags != null) {
        ctx._source.labels = tags;
    }

    // context.user -> user & user_agent
    if (context.containsKey("user")) {
        HashMap user = context.remove("user");
        // context.user.ip -> client.ip
        if (user.containsKey("ip")) {
            ctx._source.client = new HashMap();
            ctx._source.client.ip = user.remove("ip");
        }
        // context.user.user-agent -> user_agent.original.text
        // XXX: untested
        //def ua = user.remove("user-agent");
        //if (ua != null) {
        //    ctx._source.user_agent.original.text = ua
        //}
        ctx._source.user = user;
    }

    // restore what is left of context
    if (context.size() > 0) {
        ctx._source.context = context;
    }
}

if (ctx._source.processor.event == "transaction" || ctx._source.processor.event == "span") {
    // make timestamp.us from @timestamp
    // bump timestamp.us by span.start.us for spans
    // shouldn't @timestamp this already be a Date?
    // TODO: only for v1 docs?
    def ts = ctx._source.get("@timestamp");
    if (ts != null && !ctx._source.containsKey("timestamp")) {
        ctx._source.timestamp = new HashMap();
        ctx._source.timestamp.us = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").parse(ts).getTime()*1000;
        if (ctx._source.processor.event == "span") {
            ctx._source.timestamp.us += ctx._source.span.start.us
        }
    }

    // set trace.id and parent.id
    if (ctx._source.transaction.containsKey("id")) {
        // create a trace id from the transaction.id
        // v1 transaction.id was a UUID, should have 122 random bits or so
        ctx._source.trace = new HashMap();
        ctx._source.trace.id = ctx._source.transaction.id.replace("-", "");

        // set parent.id on errors and spans
        if (ctx._source.processor.event == "error" || ctx._source.processor.event == "span") {
            // was v1 parent ever used?
            ctx._source.parent = ctx._source.trace;
        }
    }

    // transaction.span_count.dropped.total -> transaction.span_count.dropped
    if (ctx._source.transaction.containsKey("span_count")) {
        def dropped = ctx._source.transaction.span_count.remove("dropped");
        if (dropped != null) {
            ctx._source.transaction.span_count.dropped = dropped.total;
        }
    }
}
"""


def test_reindex_v2(es):
    for src, info in es.es.indices.get("apm*").items():
        try:
            version = src.split("-", 2)[1]
        except Exception:
            continue
        if version == "7.0.0":
            continue
        exp = src.replace(version, "7.0.0")
        dst = exp + "-migrated"
        print("reindexing {} to {}".format(src, dst))
        es.es.reindex(
            body={
                "source": {
                    "index": src,
                },
                "dest": {
                    "index": dst,
                    # "type": "_doc",
                    "version_type": "internal"
                },
                "script": {
                    "source": MIGRATION_SCRIPT,
                }
            },
            wait_for_completion=True,
        )

        got = es.es.search(index=dst, sort="@timestamp:asc", size=1)["hits"]["hits"][0]["_source"]

        # can't do this for now since index splitting isn't in nightly snap yet and can't --apm-server-build easily
        # print("comparing {} with {}".format(exp, dst))
        # want = es.es.search(index=exp, sort="@timestamp:asc", size=1)["hits"]["hits"][0]["_source"]
        print(got)
        want = es.es.search(index="apm-7.0.0-*", sort="@timestamp:asc", size=1, body={
            "query": {"bool": {"must": [
                {"term": {"observer.version": {"value": "7.0.0"}}},
                {"term": {"@timestamp": {"value": got["@timestamp"]}}},
                {"term": {"processor.event": {"value": got["processor"]["event"]}}}
            ]}}})["hits"]["hits"][0]["_source"]

        assert want == got
