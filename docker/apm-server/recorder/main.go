package main

import (
	"compress/gzip"
	"compress/zlib"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"sync"
	"time"
)

// syncWriter helps sync batches of writes
type syncWriter struct {
	sync.Mutex
	io.Writer
}

func newSyncWriter(w io.Writer) syncWriter {
	return syncWriter{Writer: w}
}

func bodyReader(req *http.Request) (io.ReadCloser, error) {
	if req.Body == nil {
		return nil, errors.New("no content")
	}

	switch req.Header.Get("Content-Encoding") {
	case "deflate":
		return zlib.NewReader(req.Body)
	case "gzip":
		return gzip.NewReader(req.Body)
	}
	return req.Body, nil
}

func payloadRecorder(record syncWriter) http.Handler {
	jsonEncoder := json.NewEncoder(record)
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		reply := func(a ...interface{}) (n int, err error) {
			return fmt.Fprintln(w, a...)
		}
		// ignore healthchecks
		if req.URL.Path == "/" {
			reply("ok")
			return
		}

		event := map[string]interface{}{
			"time":   time.Now().UTC(),
			"method": req.Method,
			"url":    req.URL.Path,
		}
		defer func() {
			record.Lock()
			if err := jsonEncoder.Encode(event); err != nil {
				log.Println(err)
			}
			record.Unlock()
		}()
		var body io.ReadCloser
		if br, err := bodyReader(req); err != nil {
			event["error"] = err
			reply(err.Error())
			return
		} else {
			body = br
		}
		// hope it's not too big
		b, err := ioutil.ReadAll(body)
		if err != nil {
			event["error"] = err
			reply(err.Error())
			return
		}
		if len(b) > 0 {
			event["body"] = string(b)
		}
		reply("ok")
	})
}

func main() {
	flag.String("e", "", "apm-server compatility option")
	flag.String("E", "", "apm-server compatility option")
	flag.String("httpprof", "", "apm-server compatility option")

	addr := flag.String("addr", ":8200", "HTTP listen address")
	out := flag.String("out", "events.json", "path to record")
	console := flag.Bool("console", false, "also dump events to stdout")
	flag.Parse()

	outfile, err := os.Create(*out)
	if err != nil {
		log.Fatal(err)
	}
	defer outfile.Close()
	var record io.Writer = outfile
	if *console {
		record = io.MultiWriter(record, os.Stdout)
	}
	sw := newSyncWriter(record)

	s := &http.Server{
		Addr:         *addr,
		Handler:      payloadRecorder(sw),
		ReadTimeout:  1 * time.Minute,
		WriteTimeout: 1 * time.Minute,
	}
	log.Fatal(s.ListenAndServe())
}
