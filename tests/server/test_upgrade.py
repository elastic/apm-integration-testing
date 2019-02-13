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
    def process = context.remove("process");
    if (process != null) {
        def args = process.remove("argv");
        if (args != null) {
            process.args = args;
        }
        ctx._source.process = process;
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

        // context.request.socket -> request.socket
        def socket = request.remove("socket");
        if (socket != null) {
            def add_socket = false;
            def new_socket = new HashMap();
            def remote_address = socket.remove("remote_address");
            if (remote_address != null) {
                add_socket = true;
                new_socket.remote_address = remote_address;
            }
            def encrypted = socket.remove("encrypted");
            if (encrypted != null) {
                add_socket = true;
                new_socket.encrypted = encrypted;
            }
            if (add_socket) {
                request.socket = new_socket;
            }
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

        def body = request.remove("body");

        ctx._source.http.request = request;
        ctx._source.http.request.method = ctx._source.http.request.method?.toLowerCase();

        // context.request.body -> http.request.body.original
        if (body != null) {
          ctx._source.http.request.body = new HashMap();
          ctx._source.http.request.body.original = body;
        }

    }
    
    
    // bump timestamp.us by span.start.us for spans
    // shouldn't @timestamp this already be a Date?
    if (ctx._source.processor.event == "span" && context.service.agent.name == "js-base"){
      def ts = ctx._source.get("@timestamp");
      if (ts != null && !ctx._source.containsKey("timestamp") && ctx._source.span.start.containsKey("us")) {
         // add span.start to @timestamp for rum documents v1
          ctx._source.timestamp = new HashMap();
          def tsms = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").parse(ts).getTime();
          ctx._source['@timestamp'] = Instant.ofEpochMilli(tsms + (ctx._source.span.start.us/1000));
          ctx._source.timestamp.us = (tsms*1000) + ctx._source.span.start.us;
        
      }
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
        def userip = user.remove("ip");
        if (userip != null) {
            ctx._source.client = new HashMap();
            ctx._source.client.ip = userip;
        }

        // move user-agent info
        def ua = user.remove("user-agent");
        if (ua != null) {
          ctx._source.user_agent = new HashMap();
          // setting original and original.text is not possible in painless
          // as original is a keyword in ES template we cannot set it to a HashMap here, 
          // so the following is the only possible solution:
          ctx._source.user_agent.original = ua.substring(0, Integer.min(1024, ua.length()));
        }

        def pua = user.remove("user_agent");
        if (pua != null) {
          if (ctx._source.user_agent == null){
            ctx._source.user_agent = new HashMap();
          }
          def os = pua.remove("os");
          def osminor = pua.remove("os_minor");
          def osmajor = pua.remove("os_major");
          def osname = pua.remove("os_name");

          def newos = new HashMap();
          if (os != null){
            newos.full = os;
          }
          if (osmajor != null || osminor != null){
            newos.version = osmajor + "." + osminor;
          }
          if (osname != null){
            newos.name = osname;
          }
          ctx._source.user_agent.os = newos;

          def device = pua.remove("device");
          if (device != null){
            ctx._source.user_agent.device = new HashMap();
            ctx._source.user_agent.device.name = device;
          }
          // not exactly reflecting 7.0, but the closes we can get
          def major = pua.remove("major");
          if (major != null){
            def version = major;
            def minor = pua.remove("minor");
            if (minor != null){
              version += "." + minor;
              def patch = pua.remove("patch");
              if (patch != null){
                version += "." + patch
              }
            }
            ctx._source.user_agent.version = version;
          }
        }

        // remove unknown fields from user, like is_authenticated
        def add_user = false;
        def new_user = new HashMap();
        def email = user.remove("email");
        if (email != null) {
            add_user = true;
            new_user.email = email;
        }
        def id = user.remove("id");
        if (id != null) {
            add_user = true;
            new_user.id = String.valueOf(id);
        }
        def name = user.remove("name");
        if (name != null) {
            add_user = true;
            new_user.name = name;
        }
        if (add_user) {
            ctx._source.user = new_user;
        }
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
    
    
    // context.page -> error.page,transaction.page
    def page = context.remove("page");
    if (page != null) {
        if (ctx._source.processor.event == "transaction") {
            ctx._source.transaction.page = page;
        } else if (ctx._source.processor.event == "error") {
            ctx._source.error.page = page;
        }
    }

    // context.db -> span.db
    def db = context.remove("db");
    if (db != null) {
        def db_user = db.remove("user");
        if (db_user != null) {
            db.user = ["name": db_user];
        }
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
    ctx._source.timestamp.us = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").parse(ts).getTime()*1000;
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


exclude_rum = {'query': {'bool': {'must_not': [{'term': {'agent.name': 'js-base'}}]}}}

import os, json
from elasticsearch import helpers

def test_reindex_v1(es):

    def index_docs(path):
        for entry in os.scandir(path):
            if entry.is_file():
                with open(entry.path, 'r') as f:
                    yield json.load(f)

    def setup(event_type, version):
        index = "apm-{}-{}-v1".format(version, event_type)
        es.es.indices.delete(index=index, ignore=[400, 404])
        path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            '..', '..', "tests", "server", version, event_type)
        helpers.bulk(es.es, index_docs(path), index=index, refresh=True)

    # ensure v1 docs are stored in 6.x and 7.0 indices
    for event_type in ["error", "transaction", "span"]:
        es.es.indices.delete(index="apm-7.0.0-{}-v1-migrated".format(event_type), ignore=[400, 404])
        setup(event_type, "6.x")
        setup(event_type, "7.0.0")

    # run reindexing script
    migrations = run_migration(es)

    # check v1 docs against expected 7.0 indices
    for event_type, exp, dst in migrations:
        if "v1" not in exp:
            continue
        verify(es, event_type, exp, dst, None)

def test_reindex_v2(es):
    # first migrate all indices
    migrations = run_migration(es)

    for event_type, exp, dst in migrations:
        # check against expected 7.0 indices
        verify(es, event_type, exp, dst, exclude_rum)

def verify(es, event_type, exp, dst, body):
        {
            "error": error,
            "metric": metric,
            "onboarding": onboarding,
            "span": span,
            "transaction": transaction,
        }.get(event_type)(es, exp, dst, body)

def run_migration(es):    # first migrate all indices
    migrations = []
    for src, info in es.es.indices.get("apm*").items():
        try:
            # apm-version-type-date
            _, version, event_type, _ = src.split("-", 3)
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
            refresh=True,
            wait_for_completion=True,
        )
        migrations.append((event_type, exp, dst))
    return migrations

def metric(es, exp, dst, body):
    pass  # skip non-deterministic metric comparisons
    # wants, gots = query_for(es, exp, dst, body, "@timestamp:asc,agent.name:asc,system.memory.actual.free")
    # assert len(wants) == len(gots), "{} docs expected, got {}".format(len(wants), len(gots))
    # for i, (w, g) in enumerate(zip(wants, gots)):
    #     common(i, w, g)


def span(es, exp, dst, body):
    wants, gots = query_for(es, exp, dst, body, "span.id:asc,span.start.us:asc,timestamp.us:asc,@timestamp:asc,agent.name:asc,span.duration.us")
    print("checking span - comparing {} with {}".format(exp, dst))

    assert len(wants) == len(gots), "{} docs expected, got {}".format(len(wants), len(gots))
    for i, (w, g) in enumerate(zip(wants, gots)):
        want = w["_source"]
        got = g["_source"]

        # span.type split in https://github.com/elastic/apm-server/issues/1837, not done in reindex script yet
        want_span_type = want["span"].pop("type", None)
        want_span_subtype = want["span"].pop("subtype", None)
        want_span_action = want["span"].pop("action", None)
        got_span_type = got["span"].pop("type", None)
        got_span_subtype = got["span"].pop("subtype", None)
        got_span_action = got["span"].pop("action", None)
        if got_span_type:
            assert got_span_type.startswith(want_span_type)
        else:
            assert want_span_type is None
        # only for go agent
        if got_span_action:
            assert got_span_action == want_span_action
        if got_span_subtype:
            assert got_span_subtype == want_span_subtype
        common(i, w, g)


def error(es, exp, dst, body):
    wants, gots = query_for(es, exp, dst, body, "error.id:asc,timestamp.us:asc,@timestamp:asc,agent.name:asc")
    print("checking error - comparing {} with {}".format(exp, dst))

    assert len(wants) == len(gots), "{} docs expected, got {}".format(len(wants), len(gots))
    for i, (w, g) in enumerate(zip(wants, gots)):
        want = w["_source"]
        got = g["_source"]

        # error transaction.type only introduced in 7.0, can't make it up before then
        if want.get("transaction", {}).get("type"):
            del(want["transaction"]["type"])
        common(i, w, g)


def transaction(es, exp, dst, body):
    wants, gots = query_for(es, exp, dst, body, "transaction.id:asc,timestamp.us:asc,@timestamp:asc,agent.name:asc")
    print("checking transaction - comparing {} with {}".format(exp, dst))

    assert len(wants) == len(gots), "{} docs expected, got {}".format(len(wants), len(gots))
    for i, (w, g) in enumerate(zip(wants, gots)):
        common(i, w, g)


def onboarding(es, exp, dst, body):
    wants, gots = query_for(es, exp, dst, body, "timestamp.us:asc,@timestamp:asc,agent.name:asc")
    print("checking onboarding - comparing {} with {}".format(exp, dst))

    assert len(wants) == len(gots), "{} docs expected, got {}".format(len(wants), len(gots))
    for i, (w, g) in enumerate(zip(wants, gots)):
        want = w["_source"]
        got = g["_source"]
        del(want["@timestamp"])
        del(got["@timestamp"])
        common(i, w, g)

def query_for(es, exp, dst, body, sort):
    wants = es.es.search(index=exp, body=body, sort=sort, size=1000)["hits"]["hits"]
    gots = es.es.search(index=dst, body=body, sort=sort, size=1000)["hits"]["hits"]
    return wants, gots


def common(i, w, g):
    want = w["_source"]
    got = g["_source"]

    print("comparing {:-3d}, want _id: {} with got _id: {}".format(i, w["_id"], g["_id"]))
    # no id or ephemeral_id in reindexed docs
    want["observer"].pop("ephemeral_id","")
    want["observer"].pop("id", "")

    # version should be set
    want["observer"].pop("version","")
    got_version = got["observer"].pop("version","")
    assert got_version is not None

    # hostnames might be different
    want["observer"].pop("hostname")
    got_hostname = got["observer"].pop("hostname")
    assert got_hostname is not None

    # host.name to be removed
    host = want.pop("host", {"name": ""})
    del(host["name"])
    # only put host back if it's not empty
    if host:
        want["host"] = host

    assert want == got
