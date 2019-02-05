MIGRATION_SCRIPT = """
// add ecs version
ctx._source.ecs = ['version': '1.0.0-beta2'];

// beat -> observer
def beat = ctx._source.remove("beat");
if (beat != null) {
    beat.remove("name");
    ctx._source.observer = beat;
    ctx._source.observer.type = "apm-server";
}

if (! ctx._source.containsKey("observer")) {
    ctx._source.observer = new HashMap();
}

// observer.major_version
ctx._source.observer.version_major = 7;

def listening = ctx._source.remove("listening");
if (listening != null) {
    ctx._source.observer.listening = listening;
}

// remove host[.name]
// clarify if we can simply delete this or it will be set somewhere else in 7.0
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

    // context.response -> http.response
    HashMap resp = context.remove("response");
    if (resp != null) {
        if (! ctx._source.containsKey("http")) {
            ctx._source.http = new HashMap();
        }
        ctx._source.http.response = resp;
    }

    // context.request -> http & url
    HashMap request = context.remove("request");
    if (request != null) {
        if (! ctx._source.containsKey("http")) {
            ctx._source.http = new HashMap();
        }

        // context.request.http_version -> http.version
        def http_version = request.remove("http_version");
        if (http_version != null) {
          ctx._source.http.version = http_version;
        }

        ctx._source.http.request = new HashMap();

        // context.request.body -> http.request.body.original
        def body = request.remove("body");
        if (body != null) {
          ctx._source.http.request.body = new HashMap()
          //ctx._source.http.request.body.original = body;
              // TODO: figure out how to handle body - it can be a string or an object
              //request.body = bodyContent;
        }

        // context.request.url -> url
        HashMap url = request.remove("url");
        def fragment = url.remove("hash");
        if (fragment != null) {
            url.fragment = fragment;
        }
        def domain = url.remove("hostname");
        if (domain != null) {
            url.domain = domain;
        }
        def path = url.remove("pathname");
        if (path != null) {
            url.path = path;
        }
        def scheme = url.remove("protocol");
        if (scheme != null) {
            def end = scheme.lastIndexOf(":");
            if (end > -1) {
                scheme = scheme.substring(0, end);
            }
            url.scheme = scheme
        }
        def original = url.remove("raw");
        if (original != null) {
            url.original = original;
        }
        def port = url.remove("port");
        if (port != null) {
            try {
                int portNum = Integer.parseInt(port);
                url.port = portNum;
            } catch (Exception e) {
                // toss port
            }
        }
        def query = url.remove("search");
        if (query != null) {
            url.query = query;
        }
        ctx._source.url = url;

        // restore what is left of request, under http
        ctx._source.http.request = request;
        ctx._source.http.request.method = ctx._source.http.request.method?.toLowerCase()
    }

    // context.service.agent -> agent
    HashMap service = context.remove("service");
    ctx._source.agent = service.remove("agent");

    // context.service -> service
    ctx._source.service = service;

    // context.system -> host
    def system = context.remove("system");
    if (system != null) {
        system.os = new HashMap();
        system.os.platform = system.remove("platform");
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
        // user.username -> user.name
        def username = user.remove("username");
        if (username != null) {
            user.name = username;
        }
        // context.user.ip -> client.ip
        if (user.containsKey("ip")) {
            ctx._source.client = new HashMap();
            ctx._source.client.ip = user.remove("ip");
        }
        // context.user.user-agent -> user_agent.original.text
        // XXX: untested
        //if (user.containsKey("user-agent")) {
        //  if (ctx._source.user_agent == null) {
        //    ctx._source.user_agent = new HashMap();
        //  }
        //  ctx._source.user_agent.original.text = user.remove("user-agent");
        //}

        //TODO: what about user_agent pipelines?

        ctx._source.user = user;
    }

    // context.custom -> error,transaction,span.custom
    def custom = context.remove("custom");
    if (custom != null) {
        if (ctx._source.processor.event == "span") {
            ctx._source.span.custom = custom;
        } else if (ctx._source.processor.event == "transaction") {
            ctx._source.transaction.custom = custom;
        } else if (ctx._source.processor.event == "error") {
            ctx._source.error.custom = custom;
        }
    }

    // context.db -> span.db
    def db = context.remove("db");
    if (db != null) {
        ctx._source.span.db = db;
    }

    // context.http -> span.http
    def http = context.remove("http");
    if (http != null) {
        // context.http.url -> span.http.url.original
        def url = http.remove("url");
        if (url != null) {
            http.url = ["original": url];
        }
        // context.http.status_code -> span.http.response.status_code
        def status_code = http.remove("status_code");
        if (status_code != null) {
            http.response = ["status_code": status_code];
        }
        ctx._source.span.http = http;
    }
}

if (ctx._source.processor.event == "span") {
    // bump timestamp.us by span.start.us for spans
    // shouldn't @timestamp this already be a Date?
    def ts = ctx._source.get("@timestamp");
    if (ts != null && !ctx._source.containsKey("timestamp")) {
        // add span.start to @timestamp for rum documents v1
        if (ctx._source.context.service.agent.name == "js-base" && ctx._source.span.start.containsKey("us")) {
           ts += ctx._source.span.start.us/1000;
        }
    }
    if (ctx._source.span.containsKey("hex_id")) {
      ctx._source.span.id = ctx._source.span.remove("hex_id");
    }
    def parent = ctx._source.span.remove("parent");
    if (parent != null && ctx._source.parent == null) {
      ctx._source.parent = ["id": parent];
    }
}

// create trace.id
if (ctx._source.processor.event == "transaction" || ctx._source.processor.event == "span" || ctx._source.processor.event == "error") {
  if (ctx._source.containsKey("transaction")) {
    def tr_id = ctx._source.transaction.get("id");
    if (ctx._source.trace == null && tr_id != null) {
        // create a trace id from the transaction.id
        // v1 transaction.id was a UUID, should have 122 random bits or so
        ctx._source.trace = new HashMap();
        ctx._source.trace.id = tr_id.replace("-", "");
    }
  }

  // create timestamp.us from @timestamp
  def ts = ctx._source.get("@timestamp");
  if (ts != null && !ctx._source.containsKey("timestamp")) {
    //set timestamp.microseconds to @timestamp
    ctx._source.timestamp = new HashMap();
    ctx._source.timestamp.us = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss").parse(ts).getTime()*1000;
  }

}

// transaction.span_count.dropped.total -> transaction.span_count.dropped
if (ctx._source.processor.event == "transaction") {
    // transaction.span_count.dropped.total -> transaction.span_count.dropped
    if (ctx._source.transaction.containsKey("span_count")) {
        def dropped = ctx._source.transaction.span_count.remove("dropped");
        if (dropped != null) {
            ctx._source.transaction.span_count.dropped = dropped.total;
        }
    }
}

if (ctx._source.processor.event == "error") {
    // culprit is now a keyword, so trim it down to 1024 chars
    def culprit = ctx._source.error.remove("culprit");
    if (culprit != null) {
        ctx._source.error.culprit = culprit.substring(0, Integer.min(1024, culprit.length()));
    }

    // error.exception is now a list (exception chain)
    def exception = ctx._source.error.remove("exception");
    if (exception != null) {
        ctx._source.error.exception = [exception];
    }
}
"""  # noqa


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

        print("comparing {} with {}".format(exp, dst))
        exclude_rum = {'query': {'bool': {'must_not': [{'term': {'agent.name': 'js-base'}}]}}}
        want = es.es.search(index=exp, body=exclude_rum, sort="@timestamp:asc", size=1)["hits"]["hits"][0]["_source"]
        got = es.es.search(index=dst, body=exclude_rum, sort="@timestamp:asc", size=1)["hits"]["hits"][0]["_source"]

        # no id or ephemeral_id in reindexed docs
        assert want["observer"].pop("ephemeral_id"), "missing ephemeral_id"
        assert want["observer"].pop("id"), "missing id"

        # versions should be different
        want_version = want["observer"].pop("version")
        got_version = got["observer"].pop("version")
        assert want_version is not None
        assert want_version != got_version

        # hostnames should be different
        want_hostname = want["observer"].pop("hostname")
        got_hostname = got["observer"].pop("hostname")
        assert want_hostname is not None
        assert want_hostname != got_hostname

        # host.name to be removed
        host = want.pop("host")
        del(host["name"])
        # only put host back if it's not empty
        if host:
            want["host"] = host

        # onboarding doc timestamps won't match exactly
        if want["processor"]["event"] == "onboarding":
            del(want["@timestamp"])
            del(got["@timestamp"])

        # span.type split in https://github.com/elastic/apm-server/issues/1837, not done in reindex script yet
        if want["processor"]["event"] == "span":
            want_span_type = want["span"].pop("type", None)
            want_span_subtype = want["span"].pop("subtype", None)
            want_span_action = want["span"].pop("action", None)
            got_span_type = got["span"].pop("type", None)
            if got_span_type:
                assert got_span_type.startswith(want_span_type)
            else:
                assert want_span_type is None

        assert want == got
