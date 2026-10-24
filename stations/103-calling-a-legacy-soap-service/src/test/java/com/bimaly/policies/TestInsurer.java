package com.bimaly.policies;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The insurer's SOAP service, faked for the tests: hand-written SOAP 1.1 envelopes, as a legacy system sends them.
 * TERM10 and HEALTH5 are sold; premium is a thousandth of the sum (a demo rule). Anything else is a Client fault.
 */
final class TestInsurer {

    static final TestInsurer INSURER = new TestInsurer();
    record Call(String soapAction, String body) {
    }

    final List<Call> calls = new CopyOnWriteArrayList<>();
    volatile long delayMillis;
    volatile boolean broken;   // answer every call with a Server fault
    private final AtomicInteger issued = new AtomicInteger();
    private final HttpServer server;

    private TestInsurer() {
        try {
            server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        server.createContext("/policy", this::handle);
        server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        server.start();
    }

    String url() {
        return "http://127.0.0.1:" + server.getAddress().getPort() + "/policy";
    }

    void reset() {
        calls.clear();
        delayMillis = 0;
        broken = false;
    }

    static String field(String xml, String name) {
        Matcher m = Pattern.compile("<(?:\\w+:)?" + name + ">([^<]*)</").matcher(xml);
        return m.find() ? m.group(1) : null;
    }

    private void handle(HttpExchange x) throws IOException {
        String body = new String(x.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        calls.add(new Call(x.getRequestHeaders().getFirst("SOAPAction"), body));
        try {
            Thread.sleep(delayMillis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        String product = field(body, "productCode");
        long sum = Long.parseLong(field(body, "sumInsuredPaise"));
        String reply;
        int status = 500;   // SOAP 1.1 over HTTP: faults come with 500
        if (broken) {
            reply = fault("soap:Server", "Internal error", null, null);
        } else if (!List.of("TERM10", "HEALTH5").contains(product)) {
            reply = fault("soap:Client", "Validation failed", "PRODUCT_UNKNOWN", "Product " + product + " is not sold.");
        } else if (sum > 50_000_000_000L) {
            reply = fault("soap:Client", "Validation failed", "SUM_TOO_HIGH", "The sum insured is above the limit for online issuance.");
        } else {
            status = 200;
            reply = envelope("<p:IssuePolicyResponse xmlns:p=\"http://insurer.example/policy/v1\"><p:policyNumber>SG-2026-"
                    + String.format(java.util.Locale.ROOT, "%06d", issued.incrementAndGet()) + "</p:policyNumber><p:premiumPaise>" + sum / 1000
                    + "</p:premiumPaise></p:IssuePolicyResponse>");
        }
        byte[] out = reply.getBytes(StandardCharsets.UTF_8);
        x.getResponseHeaders().add("Content-Type", "text/xml; charset=utf-8");
        try {
            x.sendResponseHeaders(status, out.length);
            x.getResponseBody().write(out);
        } catch (IOException clientGaveUp) {
            // the app stopped waiting
        }
        x.close();
    }

    static String envelope(String content) {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?><soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\"><soap:Body>"
                + content + "</soap:Body></soap:Envelope>";
    }

    static String fault(String code, String reason, String detailCode, String detailMessage) {
        String detail = detailCode == null ? "" : "<detail><p:PolicyFault xmlns:p=\"http://insurer.example/policy/v1\"><p:code>" + detailCode
                + "</p:code><p:message>" + detailMessage + "</p:message></p:PolicyFault></detail>";
        return envelope("<soap:Fault><faultcode>" + code + "</faultcode><faultstring>" + reason + "</faultstring>" + detail + "</soap:Fault>");
    }
}
