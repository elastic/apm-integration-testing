'use strict'

//TODO: use ENV_VARIABLE for URLs and ports

var apm = require('elastic-apm').start({
  appName: process.env.EXPRESS_APP_NAME, 
  flushInterval: 1,
  secretToken: '1234',
  serverUrl: process.env.APM_SERVER_URL
})

var app = require("express")();

app.get("/", function(req, res) {
    res.send("OK");
});

app.get("/foo", function(req, res) {
    foo_route()
    res.send("foo");
});

function foo_route () {
    var trace = apm.buildTrace()
    trace.start('app.foo')
    trace.end()
}

app.get("/bar", function(req, res) {
    bar_route()
    res.send("bar");
});

function bar_route () {
    var trace = apm.buildTrace()
    trace.start('app.bar')
    extra_route()
    trace.end()
}

function extra_route () {
    var trace = apm.buildTrace()
    trace.start('app.extra')
    trace.end()
}

app.use(apm.middleware.express())

var server = app.listen(process.env.EXPRESS_PORT, '0.0.0.0', function () {
    console.log("Listening on %s...", server.address().port);
});

