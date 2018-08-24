ARG kibana_base_image=docker.elastic.co/kibana/kibana:7.0.0-alpha1-SNAPSHOT

FROM ${kibana_base_image}
ARG kibana_canvas_version=2174
RUN /bin/bash -c "NODE_OPTIONS='--max-old-space-size=4096' ./bin/kibana-plugin install https://download.elastic.co/kibana/canvas/kibana-canvas-0.1.${kibana_canvas_version}.zip"
