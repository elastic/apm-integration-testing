#!/bin/bash

set -e

backends=${APM_SERVER_COUNT:-1}

config=/usr/local/etc/haproxy/haproxy.cfg

# generate configuration file
cat > $config <<EOF
defaults
    log stdout local0
    timeout connect 1h
    timeout client  1h
    timeout server  1h

frontend http
    bind *:8200
    mode http
    default_backend servers
    stats enable

backend servers
    mode http
    balance roundrobin
    option httpchk HEAD / HTTP/1.0
EOF

# shellcheck disable=SC2004
for ((i=1; i<=$backends; i++)); do
cat >> $config <<EOF
    server apm-server-${i} apm-server-${i}:8200 check fall 3 rise 2
EOF
done

exec "$@"
