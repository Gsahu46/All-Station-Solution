package com.bimaly.integration;

import org.apache.camel.Exchange;
import org.apache.camel.builder.RouteBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.HexFormat;

/** The bank's SFTP folder → validate each file → valid lines on the policy-requests queue. One run per file. */
@Component
class PolicyFileRoute extends RouteBuilder {

    private static final String RUN = "bimalyRun";
    private final Runs runs;
    private final PolicyQueue queue;
    private final String partner;
    private final String deadLetter;
    private final int redeliveries;
    private final Duration redeliveryDelay;

    PolicyFileRoute(Runs runs, PolicyQueue queue,
                    @Value("${bimaly.partner.uri}") String partner, @Value("${bimaly.files.data}") String data,
                    @Value("${bimaly.files.redeliveries}") int redeliveries,
                    @Value("${bimaly.files.redelivery-delay}") Duration redeliveryDelay) {
        this.runs = runs;
        this.queue = queue;
        this.partner = partner;
        this.deadLetter = "file:" + data + "/dead-letter";
        this.redeliveries = redeliveries;
        this.redeliveryDelay = redeliveryDelay;
    }

    @Override
    public void configure() {
        // One error handler for everything: try again, then park the file in the dead-letter folder. Nothing is lost.
        errorHandler(deadLetterChannel("direct:dead-letter").useOriginalMessage()
                .maximumRedeliveries(redeliveries).redeliveryDelay(redeliveryDelay.toMillis()));
        from("direct:dead-letter")
                .process(e -> runs.finish(run(e), Runs.Status.DEAD_LETTERED, e.getProperty(Exchange.EXCEPTION_CAUGHT, Exception.class).getMessage()))
                .to(deadLetter);

        // noop=true: Camel's file components are idempotent with noop, so each file is only ever read once.
        from(partner + "&noop=true&include=.*\\.csv&sortBy=file:name")
                .routeId("policy-files")
                .process(this::start)
                .process(this::validate)
                .process(e -> queue.sendAll(e.getMessage().getBody(PolicyFile.Parsed.class).accepted()))
                .process(e -> runs.finish(run(e), Runs.Status.DONE, null));
    }

    private void start(Exchange e) throws NoSuchAlgorithmException {
        byte[] content = e.getMessage().getBody(byte[].class);
        String checksum = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        e.setProperty(RUN, runs.start(e.getMessage().getHeader(Exchange.FILE_NAME_ONLY, String.class), checksum));
    }

    private void validate(Exchange e) {
        PolicyFile.Parsed parsed = PolicyFile.parse(run(e).file, e.getMessage().getBody(byte[].class));
        Runs.Run run = run(e);
        run.lines = parsed.lines();
        run.accepted = parsed.accepted().size();
        run.rejected = parsed.rejected();
        e.getMessage().setBody(parsed);
    }

    private static Runs.Run run(Exchange e) {
        return e.getProperty(RUN, Runs.Run.class);
    }
}
