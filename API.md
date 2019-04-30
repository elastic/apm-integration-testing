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
  - create "bar" span
  - create additional "extra" span

* `/foo`
  - return status: 200 OK
  - return body: foo
  - create "foo" span
  - traced: yes

* `/healthcheck`
  - return status: 200 OK
  - return body: OK
  - traced: no

* `/oof`
  - return status: 500 Internal Server Error
  - traced: yes
