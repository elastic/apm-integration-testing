'use strict'

var apm = require('elastic-apm-node').start({
  frameworkName: 'express',
  frameworkVersion: 'unknown',
  serviceName: process.env.EXPRESS_SERVICE_NAME,
  apiRequestTime: "50ms",
  ignoreUrls: ['/healthcheck']
})

var app = require("express")();

app.get("/", function(req, res) {
    res.send("OK");
});

app.get("/healthcheck", function(req, res) {
    res.send("OK");
});

app.get("/foo", function(req, res) {
    foo_route()
    res.send("foo");
});

function foo_route () {
    var span = apm.startSpan('app.foo', 'custom')
    span.end()
}

app.get("/bar", function(req, res) {
    bar_route()
    res.send("bar");
});

function bar_route () {
    var span = apm.startSpan('app.bar', 'custom')
    extra_route()
    span.end()
}

function extra_route () {
    var span = apm.startSpan('app.extra', 'custom')
    span.end()
}

app.get("/oof", function(req, res, next) {
    next(new Error("oof"));
});

app.use(function (err, req, res, next) {
  console.error(err.stack)
  res.status(500).send('Something broke!')
});

var server = app.listen(process.env.EXPRESS_PORT, '0.0.0.0', function () {
    console.log("Listening on %s...", server.address().port);
});
