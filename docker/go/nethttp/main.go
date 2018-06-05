package main

import (
	"net/http"

	"github.com/elastic/apm-agent-go"
	"github.com/elastic/apm-agent-go/module/apmhttp"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/", indexHandler)
	mux.HandleFunc("/healthcheck", healthcheckHandler)
	mux.HandleFunc("/foo", fooHandler)
	mux.HandleFunc("/bar", barHandler)
	http.ListenAndServe(":8080", apmhttp.Wrap(mux))
}

func indexHandler(w http.ResponseWriter, req *http.Request) {
	w.Write([]byte("OK"))
}

func healthcheckHandler(w http.ResponseWriter, req *http.Request) {
	w.Write([]byte("OK"))
}

func fooHandler(w http.ResponseWriter, req *http.Request) {
	w.Write([]byte(foo(req)))
}

func barHandler(w http.ResponseWriter, req *http.Request) {
	w.Write([]byte(bar(req)))
}

func foo(req *http.Request) string {
	span, _ := elasticapm.StartSpan(req.Context(), "foo", "app")
	if span != nil {
		defer span.End()
	}
	return "foo"
}

func bar(req *http.Request) string {
	span, ctx := elasticapm.StartSpan(req.Context(), "bar", "app")
	if span != nil {
		req = req.WithContext(ctx)
		defer span.End()
	}
	_ = extra(req)
	return "bar"
}

func extra(req *http.Request) string {
	span, _ := elasticapm.StartSpan(req.Context(), "extra", "app")
	if span != nil {
		defer span.End()
	}
	return "extra"
}
