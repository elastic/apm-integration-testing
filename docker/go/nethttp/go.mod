module testapp

go 1.15

require (
	github.com/davecgh/go-spew v1.1.1 // indirect
	go.elastic.co/apm/module/apmhttp/v2 v2.0.0
	go.elastic.co/apm/v2 v2.0.0
)

replace go.elastic.co/apm/v2 => /src/apm-agent-go

replace go.elastic.co/apm/module/apmhttp/v2 => /src/apm-agent-go/module/apmhttp
