var sparkMap = {};
sparkMap.getMap = {};
sparkMap.postMap = {}

function drawScenarios(r) {
  $.each(r['scenarios'], function(_, s){
    $('#scenarios_selector').append(`<option>${s}</option>`)
  }
  )
}

function processMolotov(data){
  var m = data.counters.molotov;
  var get_stats = {};
  var post_stats = {};
  // FIXME probably just pull the first one instead since we are ovewriting the above stats anyhow
  for(let [k,v] of Object.entries(m)){
    var g = v['GET'];
    var p = v['POST'];
    // This is probably deeply offensive to JS developers.
    if (g) {
      // FIXME this only gets the run of the opbean with the lowest IP (java rn)
      g1 = Object.values(g)[0];
      g2 = Object.values(g1)[0];
      g3 = Object.values(g2)[0];
      gres = Object.values(g3)[0];
      for (let req of Object.values(gres)){
        for (let [http_code, num] of Object.entries(req)){
          if (Object.keys(get_stats).includes(http_code)){
            get_stats[http_code] += num;
          } else {
            get_stats[http_code] = num;
          }
        }
      }
    }
    if (p) {
      p1 = Object.values(p)[0];
      p2 = Object.values(p1)[0];
      p3 = Object.values(p2)[0];
      pres = Object.values(p3)[0];


      // FIXME refactor for horrific DRY violation
      for (let req of Object.values(pres)){
        for (let [http_code, num] of Object.entries(req)){
          if (Object.keys(get_stats).includes(http_code)){
            post_stats[http_code] += num;
          } else {
            post_stats[http_code] = num;
          }
        }
      } 
    }
  }
  $('#get_stats').empty();
  $('#post_stats').empty();
  $('#get_stats').text('GET req/min');
  $('#post_stats').text('POST req/min');
  for (let [h, v] of Object.entries(get_stats)){

    if (Object.keys(sparkMap.getMap).includes(h)){
            sparkMap['getMap'][h].push(v);
            if (sparkMap['getMap'][h].length >= 25) {
              sparkMap['getMap'][h].shift();
            }
          } else {
            sparkMap['getMap'][h] = [v];
          }
    $('#get_stats').append(`<tr><td>${h}</td><td><span id="get-spark-${h}" style="float:left;"></span></td><td>${v * 12}</td></tr>`);
    $(`#get-spark-${h}`).sparkline(sparkMap['getMap'][h])

  }
  for (let [h, v] of Object.entries(post_stats)){
    $('#post_stats').append(`<tr><td>${h}</td><span id="post-spark-${h}" style="float:left;"></span></td><td>${v * 20}</td></tr>`);
  }
}

function drawProxies(r) {
  r["proxies"].forEach(drawProxy);
}

function drawProxy(proxy) {  
  $("#proxy-container").append(
    `<div style="float:left;" id="${ proxy.name }-container">` + 
    `<p id="${ proxy.name }-header" class="ui-state-default ui-corner-all ui-helper-clearfix" style="padding:4px;">` +
    `<span style="float:left; margin:-2px 5px 0 0;" class="proxy-name">${proxy.name}</span></p></div>`
    );
  drawSliders(proxy.name);
  drawServiceEnable(proxy.name);
}

function drawLg(r) {
  $.get({
    url: "http://localhost:8999/api/scenarios",
    contentType: "application/json",
    dataType: 'json',
    success: function(result){
      drawScenarios(result);
    }
  });
  $.each(r.proxies, function(idx, s) {
    var service_name = s.name;
    var port = s.listen.split(":").pop();
    if (service_name.startsWith("opbeans")){
      $("#load-controls").append(
        `<div id="${service_name}-container">` +
        `<p id="${service_name}-header" class="ui-state-default ui-corner-all ui-helper-clearfix" style="padding:4px;">` +
        `<span style="margin:-2px 5px 0 0;">${service_name}</span>` +
        `</p><fieldset><label for="lg-checkbox-${ service_name }">Load test<input type="checkbox" name="lg-checkbox-${service_name}" id="lg-checkbox-${service_name}"></label></fieldset>` +
        `</div>`
      );
      // Check the box if a job is already running
      $.get({
        url: "http://localhost:8999/api/list",
        contentType: "application/json",
        dataType: 'json',
        success: function(result){
          $.each(result, function(idx, lg){
            if (lg.running) {
                $(`#lg-checkbox-opbeans-${lg.name}`).attr('checked', 'checked')
            }
          });
         }
      });
      var sel = '#lg-checkbox-'+service_name;
      $(sel).click(function() {
      if (this.checked) {
        // Get list of proxies
        var scenario = $('#scenarios_selector').val();
        var job_data = {"job": service_name, "port": port}
        if (scenario !== 'Default'){
          job_data['scenario'] = scenario;
        }
        $.post({
              url: "http://localhost:8999/api/start",
              contentType: "application/json",
              data: JSON.stringify(job_data),
              dataType: 'json',
              success: function(result){
                console.log('Sent request to enable LG. result: ' + result)
              }
            })
      } else {
        $.get({
          url: "http://localhost:8999/api/stop?job="+service_name,
          contentType: "application/json",
          dataType: 'json',
          success: function(result){
            console.log('Sent request to disable LG. result: ' + result)
          }
        });
      }
    });
    }
  })
}



function drawSliders(service_name){
  $ ("#"+service_name+"-container").append(
    '<div style="margin: 15px" id="eq-'+service_name+`" class="eq">\
      <table>\
        <tr>\
        <td><span id="W" class="molotov_slide"></span></td>\
        <td><span id="Er" class="molotov_slide"></span></td>\
        <td><span id="L" class="toxi_slide"></span></td>\
        <td><span id="J" class="toxi_slide"></span></td>\
        <td><span id="B" class="toxi_slide"></span></td>\
        <td><span id="SC" class="toxi_slide"></span></td>\
        <td><span id="Sas" class="toxi_slide"></span></td>\
        <td><span id="Ssd" class="toxi_slide"></span></td>\
        <td><span id="CPU" class="docker_slide"></span></td>\
        <td><span id="Mem" class="docker_slide"></span></td>\
        </tr>\
        <tr>\
        <td align="center">W</td>\
        <td align="center">Er</td>\
        <td align="center">L</td>\
        <td align="center">J</td>\
        <td align="center">B</td>\
        <td align="center">SC</td>\
        <td align="center">Sas</td>\
        <td align="center">Ssd</td>\
        <td align="center">CPU</td>\
        <td align="center">Mem</td>\
        </tr>\
        <tr>\
        <td align="center"><div style="color:#68B847">&#9632;</div></td>\
        <td align="center"><div style="color:#68B847">&#9632;</div></td>\
        <td align="center"><div style="color:#B84768">&#9632;</div></td>\
        <td align="center"><div style="color:#B84768">&#9632;</div></td>\
        <td align="center"><div style="color:#B84768">&#9632;</div></td>\
        <td align="center"><div style="color:#B84768">&#9632;</div></td>\
        <td align="center"><div style="color:#B84768">&#9632;</div></td>\
        <td align="center"><div style="color:#B84768">&#9632;</div></td>\
        <td align="center"><div style="color:#4768B8">&#9632;</div></td>\
        <td align="center"><div style="color:#4768B8">&#9632;</div></td>\
        </tr>\
      </table>\
  </div>`
  );

  if (service_name == "opbeans-python") {
    $("#eq-"+service_name).append(
   `<div style="margin: 15px" id="eq-app-latency-`+service_name+`" class="eq">\
        <h3>Latency Distributor<span style="float:right"><select></select></span></h3>\
          <table>\
            <tr>\
            <td><span id="D" class="molotov_slide"></span></td>\
            <td><span id="Dl" class="molotov_slide"></span></td>\
            </tr>\
            <tr>\
            <td align="center">D</td>\ 
            <td align="center">Dl</td>\ 
            </tr>\
            <tr>\
            <td align="center"><div style="color:#68B847">&#9632;</div></td>\            
            <td align="center"><div style="color:#68B847">&#9632;</div></td>\            
            </tr>\
          </table>\
      </div>`
    );
    $.get({
      url: `http://localhost:8999/api/splays`,
      contentType: "application/json",
      dataType: "json",
      success: function(result) {
        $.each(result['splays'], function(_, s){
          $("#eq-app-latency-"+service_name+" * > * > select").append(`<option>${s}</option>`);
        }
        )}
      })
  }

  // TODO set cur val for molotov vals
  $.get({
        url: `http://localhost:8999/api/list`,
        contentType: "application/json",
        dataType: 'json',
        success: function(result){

          // if (! service_name.startsWith("opbeans-")) {
          //   return
          // }
          var lg_name = service_name.replace("opbeans-", "")
          $( "#eq-app-latency-"+service_name).accordion({collapsible: true, active: false});
          if (service_name == "opbeans-python") {
            $( "#eq-app-latency-"+ service_name+"> * > * > * > * > .molotov_slide" ).each(function() {
            if (this.id == 'Dl') {
              var previouslySetSlider = result[lg_name]['app_latency_lower_bound'] / 10
            } else if (this.id == 'D') {
              var previouslySetSlider = result[lg_name]['app_latency_weight'] * 10
            }
            if (previouslySetSlider != 0 && typeof previouslySetSlider !== 'undefined') {
              sliderVal = previouslySetSlider;
            }
              s = $( this ).empty().slider({
                value: sliderVal,
                min: 1,
                range: "min",
                animate: true,
                orientation: "vertical",
                change: handleMolotovSlideChange,
              });
              s.attr('service_name', service_name);
            }
            )}



          $( "#eq-"+ service_name+" > table > tbody > tr > td > .molotov_slide" ).each(function() {
            var lg_name = service_name.replace("opbeans-", "")
            if (result[lg_name]){
              console.log('found it', result[lg_name])
              // FIXME temp scaffolding code
              if (this.id == 'W') {
                var previouslySetSlider = result[lg_name]['workers']
              } else if (this.id == 'Er') {
                var previouslySetSlider = result[lg_name]['error_rate']
              }
            }
            // FIXME not representative of actual value on initial load
            if (this.id == 'W'){
              var sliderVal = 33;
            } else if (this.id == 'Er'){
                var sliderVal = 1;
            }
            else{
              var sliderVal = 100;
            }

            if (previouslySetSlider != 0 && typeof previouslySetSlider !== 'undefined') {
              sliderVal = previouslySetSlider;
            }
            s = $( this ).empty().slider({
              value: sliderVal,
              min: 1,
              range: "min",
              animate: true,
              orientation: "vertical",
              change: handleMolotovSlideChange,
            });
            s.attr('service_name', service_name);
            // $(`#${this.id}-${service_name}-val`).text(sliderVal);
          });
        }
      });

  // Set initial values from current values in proxy
  $.get({
        url: `http://localhost:`+window.location.port+`/api/app?name=${service_name}&denorm=1`,
        contentType: "application/json",
        dataType: 'json',
        success: function(result){

          $( "#eq-"+ service_name+" > table > tbody > tr > td > .toxi_slide" ).each(function() {
            var previouslySetSlider = result.toxics[this.id];
            var sliderVal = 0;
            if (previouslySetSlider != 0 && typeof previouslySetSlider !== 'undefined') {
              sliderVal = previouslySetSlider
            }
            s = $( this ).empty().slider({
              value: sliderVal,
              min: 1,
              range: "min",
              animate: true,
              orientation: "vertical",
              change: handleToxiSlideChange,
            });
            s.attr('service_name', service_name);
            // $(`#${this.id}-${service_name}-val`).text(sliderVal);
          });
        }
      });


  $.get({
    url: `http://localhost:`+window.location.port+`/api/docker/query?c=${service_name}`,
    contentType: "application/json",
    dataType: 'json',
    success: function(result){
      console.log(result);

      // setup EQ for Docker
      $( "#eq-"+ service_name+" > table > tbody > tr > td > .docker_slide" ).each(function() {
        var previouslySetSlider = result[this.id];
        var sliderVal = 100;
        if (previouslySetSlider != 0 && typeof previouslySetSlider !== 'undefined') {
              sliderVal = previouslySetSlider
        }
        s = $( this ).empty().slider({
          value: sliderVal,
          min: 1,
          range: "min",
          animate: true,
          orientation: "vertical",
          change: handleDockerSlideChange,
        });
        s.attr('service_name', service_name);
        // $(`#${this.id}-${service_name}-val`).text(sliderVal);
      });
    }
  });
}


function handleMolotovSlideChange(event, ui){
  proxy = ui.handle.parentElement.attributes.service_name.value;
  service = proxy.replace("opbeans-", "");
  console.log(ui.handle.parentElement.id);
  if (ui.handle.parentElement.id == 'W'){
    d = JSON.stringify({'job': service, 'workers': (ui.value/10)});
  } else if (ui.handle.parentElement.id == 'Er'){
    d = JSON.stringify({'job': service, 'error_weight': ui.value});
  } else if (ui.handle.parentElement.id == 'D'){
    d = JSON.stringify({'job': service, 'app_latency_weight': ui.value/10});
  } else if (ui.handle.parentElement.id == 'Dl'){
    d = JSON.stringify({'job': service, 'app_latency_lower_bound': ui.value * 10});
  } 
  $.ajax({
    type: "POST",
    url: 'http://localhost:8999/api/update',
    data: d,
    dataType: 'json',
    contentType: 'application/json'
  });
  $(ui.handle).closest('div').find(`#${event.target.id}-val`).text(ui.value);
}

function handleDockerSlideChange(event, ui){
  c = ui.handle.parentElement.attributes.service_name.value;
  component = ui.handle.parentElement.id;
  v = ui.value;
  $.ajax({
    type: "GET",
    url: window.location.origin + `/api/docker/update?c=${c}&component=${component}&val=${v}`,
    dataType: 'json',
    contentType: 'application/json'
  });
  $(ui.handle).closest('div').find(`#${event.target.id}-val`).text(ui.value);
}

function handleToxiSlideChange(event, ui){
  proxy = ui.handle.parentElement.attributes.service_name.value;
  d = JSON.stringify({'proxy': proxy, 'tox_code': ui.handle.parentElement.id, 'val': Math.abs(100- ui.value)});
  console.log('toxi change: ' + d);
  $.ajax({
    type: "POST",
    url: window.location.origin + "/api/slide",
    data: d,
    dataType: 'json',
    contentType: 'application/json'
  });
  $(ui.handle).closest('div').find(`#${event.target.id}-val`).text(ui.value);
}

function drawServiceEnable(service_name) {
  $( `#${ service_name }-header`).after(
    `<fieldset><label for="checkbox-${ service_name }">Enabled?<input type="checkbox" name="checkbox-${ service_name }" id="checkbox-${ service_name }"></label></fieldset>`
  );
  $( "input[type='checkbox']" ).checkboxradio();
  $.get({
        url: `http://localhost:`+window.location.port+`/api/app?name=${service_name}`,
        contentType: "application/json",
        dataType: 'json',
        success: function(result){
            if (result.enabled == true){
              $(`#checkbox-${ service_name }`).prop('checked',true).checkboxradio('refresh');
            }
        }
      });
  $(`#checkbox-${service_name}`).click(function() {
    if (this.checked) {
      $.get({
        url: window.location.origin + "/api/enable?proxy="+service_name,
        contentType: "application/json",
        dataType: 'json',
        success: function(result){
          console.log('Sent request to enable. result: ' + result)
        }
      });
    } else {
      $.get({
        url: window.location.origin + "/api/disable?proxy="+service_name,
        contentType: "application/json",
        dataType: 'json',
        success: function(result){
          console.log('Sent request to disable. result: ' + result)
        }
      });
    }
  });
}

