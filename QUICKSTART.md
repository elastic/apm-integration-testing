# APM LocalEnv Quickstart

In addition to the end to end (eg agent -> apm server -> elasticsearch <- kibana) development and testing of Elastic APM, this repo also serves as a nice way to spin up a local environment of Elastic APM.  The [README](/README.md) has very detailed instructions, but focuses mostly on using it for development.  This doc really just concentrates on getting it running.  For advanced topics, check out the main README.

Note that by "local environment", this can be on your actual local machine, or running on a cloud instance with port forwards set up.

[![Build Status](https://apm-ci.elastic.co/view/All/job/elastic+apm-integration-testing+main+push/badge/icon?style=plastic)](https://apm-ci.elastic.co/job/elastic+apm-integration-testing+main+push/)

## Prerequisites

The basic requirements for starting a local environment are:

- Docker
- Python (version 3 preferred)

This repo is tested with Python 3 but best effort is made to make starting/stopping environments work with Python 2.7.

### Docker

[Installation instructions](https://www.docker.com/community-edition)

### Python 3

- Windows: [Installation instructions](https://www.python.org/downloads/windows/)
- Mac (using [Homebrew](https://brew.sh/)):
  ```sh
  brew install python
  ```
- Debian/Ubuntu
  ```sh
  sudo apt-get install python3
  ```

## Running Local Enviroments

### Starting an Environment

The tool that we use to start and stop the environment is `./scripts/compose.py`.  This provides a handy cli for starting an APM environment using docker-compose.

#### TL;DR

Start an env by running:
`./scripts/compose.py start --all 6.4 --release`

This will start a complete 6.4 environment, which includes all of the sample apps and hits them each with a load generator.  Once that is done (and everything has started up) you can navigate to [Your local Kibana Instance](http://localhost:5601/app/apm#/)

#### Details

If you don't want to start everything (for example, on a laptop with limited resources while trying to run zoom at the same time) you can pick and choose which services you run.  Say, for example, that you want to run node, java, and rum.  You could use this command:
```console
./scripts/compose.py start \
    --release \
    --with-opbeans-node \
    --with-opbeans-rum \
    --with-opbeans-java \
    6.4
```

There are many other configuration options, but this is a quickstart.  See the [README](/README.md).

If you want to see what services are available to start, you can run: `./scripts/compose.py start --help | grep "^  --with-opbeans"` which will filter out a list of the agent envs:
```console
  --with-opbeans-dotnet Enable opbeans-dotnet
  --with-opbeans-go     Enable opbeans-go
  --with-opbeans-java   Enable opbeans-java
  --with-opbeans-node   Enable opbeans-node
  --with-opbeans-python
  --with-opbeans-ruby   Enable opbeans-ruby
  --with-opbeans-rum    Enable opbeans-rum
```
So when new agents are added we don't have to update these instructions.


**Bonus**:  With either the `all` or individual methods above, you can also pass `--with-metricbeat` or `--with-filebeat` flags, which will also set up appropriate containers and dashboards.  One side note here is that you will probably need to set a default index pattern.

#### Status

Each app gets its own port.  You can actually hit them with your browser.  They all have a similar look & feel.

You can check the status of your APM cluster with `./scripts/compose.py status`, which basically calls :

`docker ps --format 'table {{.Names}}\t{{.Ports}}'...`

Here is a tablular view, excluding non-essentials:

|Container Name                              | Link                                   |
|--------------------------------------------|----------------------------------------|
|`localtesting_6.4.0_opbeans-rum`            |[opbeans-rum](http://localhost:9222) (note - this needs chrome)   |
|`localtesting_6.4.0_opbeans-java`           |[opbeans-java](http://localhost:3002)   |
|`localtesting_6.4.0_opbeans-dotnet`         |[opbeans-dotnet](http://localhost:3004) |
|`localtesting_6.4.0_opbeans-go`             |[opbeans-go](http://localhost:3003)     |
|`localtesting_6.4.0_opbeans-node`           |[opbeans-node](http://localhost:3000)   |
|`localtesting_6.4.0_opbeans-ruby`           |[opbeans-ruby](http://localhost:3001)   |
|`localtesting_6.4.0_opbeans-python`         |[opbeans-python](http://localhost:8000) |
|`localtesting_6.4.0_kibana`                 |[kibana](http://localhost:5601)         |
|`localtesting_6.4.0_elasticsearch`          |[elasticsearch](http://localhost:9200)  |
|`localtesting_6.4.0_apm-server`             |[APM Server](http://localhost:8200)     |

You can attach your own APM agent to the APM server if you wish`.`

### Note for Cloud Instances

If you want to run this on a cloud server (GCP, AWS), you will need to set up port forwarding to access them, and the easiest way to do this is through your `~/.ssh/config` file.  My section for my cloud box looks like this:

```
Host gcptunnel
    HostName <my.gcp.host.ip>
    IdentityFile ~/.ssh/google_compute_engine           <--- yours may differ
    User jamie                                          <--- yours probably differs
    Compression yes
    ExitOnForwardFailure no
    LocalForward 3000 127.0.0.1:3000
    LocalForward 3001 127.0.0.1:3001
    LocalForward 3002 127.0.0.1:3002
    LocalForward 3003 127.0.0.1:3003
    LocalForward 3004 127.0.0.1:80
    LocalForward 5601 127.0.0.1:5601
    LocalForward 8000 127.0.0.1:8000
    LocalForward 9200 127.0.0.1:9200
    LocalForward 9222 127.0.0.1:9222
```

Then to start them up you just run `ssh gcptunnel`.

### Stopping an Environment

All services:
```
./scripts/compose.py stop

# OR

docker-compose down
```
