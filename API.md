# API

Each integration testing app implements the following API:

* `/`
  - return status: 200 OK
  - return body: OK
  - traced: yes

* `/bar`
  - return status: 200 OK
  - return body: bar
  - traced: yes
  - creates additional "extra" span

* `/foo`
  - return status: 200 OK
  - return body: foo
  - traced: yes

* `/healthcheck`
  - return status: 200 OK
  - return body: OK
  - traced: no
