var util = require('util');
var vm = require('vm');

const server = require('http').createServer();
var io = require('socket.io')(server, {
    cors: {
      origin: "http://localhost:9000",
      methods: ["GET", "POST"],
      credentials: true
    }
  });

var debug;

var emit_stats = function (socket, ts, metrics) {
  console.log('EMITTING STATS');
  socket.emit('timestamp', ts);

  var deep_metrics = {};
  ['gauges','timers','counters'].forEach(function (metric_type) {
    deep_metrics[metric_type] = deepen(metrics[metric_type]) || {};
  });

  var sandbox = vm.createContext(deep_metrics);
  var stats = socket.stats;
  stats.forEach(function (stat) {
    if (stat == 'all') {
      socket.emit('all', deep_metrics);
    }
    else {
      var stat_val;
      if (stat.match('[*]')) {
        var parsed = stat.match(/(\w+)\.(.*)$/);
        var metric_type = parsed[1];
        var pattern = parsed[2]
            .replace(/[-[\]{}()+?.,\\^$|#\s]/g, '\\$&') // Escape regex characters (excluding *)
            .replace('*', '[\\w-]*'); // Replace wildcard with optional regex word characters

        var re = new RegExp(pattern);
        var matches = {};
        for (var metric in metrics[metric_type]) {
          if (metric.match(re)) {
            matches[metric] = metrics[metric_type][metric];
          }
        }

        if (Object.keys(matches).length) {
          var match = {};
          match[metric_type] = deepen(matches);
          stat_val = match;
        }
      }
      else {
        try {
          var sstat = stat.split('.');
          var match_stat = sstat[0];
          var addl_stat = sstat.slice(1);
          if (addl_stat.length) {
            match_stat += "['" + addl_stat.join("']['") + "']";
          }
          stat_val = vm.runInContext(match_stat, sandbox);
        }
        catch (e) {}
      }
      socket.emit(stat, stat_val);
    }
  });
};

var deepen = function (o) {
  var oo = {}, t, parts, part;
  for (var k in o) {
    t = oo;
    parts = k.split('.');
    var key = parts.pop();
    while (parts.length) {
      part = parts.shift();
      t = t[part] = t[part] || {};
    }
    t[key] = o[k];
  }
  return oo;
};

exports.init = function (startup_time, config, events) {
  debug = config.debug;

  if (!config.socketPort) {
    util.log('socketPort must be specified');
    return false;
  }

  io = io.listen(config.socketPort);
  console.log('LISTENING');
  io.on('connection', function (socket) {
    console.log('CONNECTION RECEVIED');
    socket.stats = [];

    var emitter = function (ts, metrics) {
      emit_stats(socket, ts, metrics);
    };
    events.on('flush', emitter);

    socket.on('subscribe', function (stat, callback) {
      console.log('RECEVIED SUBSCRIPTION');
      socket.stats.push(stat);

      if (callback) {
        callback('subscribed ' + stat);
      }
    });

    socket.on('unsubscribe', function (stat, callback) {
      var stats = socket.stats;
      for (var i = 0; i < stats.length; i++) {
        if (stats[i] == stat) {
          stats.splice(i, 1);
          socket.stats = stats;

          if (callback) {
            callback('unsubscribed ' + stat);
          }
        }
      }

      if (callback) {
        callback('not subscribed to ' + stat);
      }
    });

    socket.on('disconnect', function () {
      events.removeListener('flush', emitter);
    });
  });

  return true;
};
