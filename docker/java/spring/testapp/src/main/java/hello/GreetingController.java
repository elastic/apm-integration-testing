package hello;

import co.elastic.apm.api.ElasticApm;
import co.elastic.apm.api.Span;
import co.elastic.apm.api.Transaction;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ResponseBody;

@Controller
public class GreetingController {

    @GetMapping("/")
    @ResponseBody
    public String index() {
        return "OK";
    }

    @GetMapping("/foo")
    @ResponseBody
    public String foo() {
        Span sp = ElasticApm.currentSpan().createSpan();
        sp.setName("foo");
        sp.setType("just a regular foo");
        String foo = new FooBar().foo();
        sp.end();
        return foo;
    }

    @GetMapping("/bar")
    @ResponseBody
    public String bar() {
        Span sp = ElasticApm.currentSpan().createSpan();
        sp.setName("bar");
        sp.setType("just a regular bar");
        String bar = new FooBar().bar();
        sp.end();
        return bar;
    }
    
    @GetMapping("/oof")
    @ResponseBody
    public String oof() {
        new FooBar().oof();
        return "oof";
    }

    @GetMapping("/healthcheck")
    @ResponseBody
    public String healthcheck() {
        return "OK";
    }

}
