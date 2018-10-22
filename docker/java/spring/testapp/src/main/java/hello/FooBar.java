package hello;

import co.elastic.apm.api.ElasticApm;
import co.elastic.apm.api.Span;

public class FooBar {

    public String foo() {
        return "foo";
    }

    public String bar() {
        Span sp = ElasticApm.currentSpan().createSpan();
        sp.setName("extra");
        sp.setType("extra");
        extra();
        sp.end();
        return "bar";
    }

    private static String extra() {
        return "extra";
    }

    public void oof() {
        throw new RuntimeException("oof");
    }
}
