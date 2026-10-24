package com.bimaly.integration;

import org.apache.camel.Exchange;
import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.spi.IdempotentRepository;
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
    private static final String CHECKSUM = "bimalyChecksum";
    private final Runs runs;
    private final PolicyQueue queue;
    private final IdempotentRepository processedFiles;
    private final String partner;
    private final String deadLetter;
    private final int redeliveries;
    private final Duration redeliveryDelay;

    PolicyFileRoute(Runs runs, PolicyQueue queue, IdempotentRepository processedFiles,
                    @Value("${bimaly.partner.uri}") String partner, @Value("${bimaly.files.data}") String data,
                    @Value("${bimaly.files.redeliveries}") int redeliveries,
                    @Value("${bimaly.files.redelivery-delay}") Duration redeliveryDelay) {
        this.runs = runs;
        this.queue = queue;
        this.processedFiles = processedFiles;
        this.partner = partner;
        this.deadLetter = "file:" + data + "/dead-letter";
        this.redeliveries = redeliveries;
        this.redeliveryDelay = redeliveryDelay;
    }

    @Override
    public void configure() {
        // A file that can never be processed: no retry. The file as it arrived goes to the dead-letter folder, and
        // its run says why. The download stays recorded (seenFiles), so the next poll does not pick it up again.
        onException(PolicyFile.BadFileException.class).handled(true).maximumRedeliveries(0).useOriginalMessage()
                .process(e -> runs.finish(run(e), Runs.Status.DEAD_LETTERED, e.getProperty(Exchange.EXCEPTION_CAUGHT, Exception.class).getMessage()))
                .to(deadLetter);

        // Anything else (the broker is down, the disk is full) may pass: try the step again, then fail the run.
        // Not handled, so the file is not recorded as processed and the next poll picks it up again.
        onException(Exception.class).handled(false).maximumRedeliveries(redeliveries).redeliveryDelay(redeliveryDelay.toMillis())
                .process(e -> runs.finish(run(e), Runs.Status.FAILED, e.getProperty(Exchange.EXCEPTION_CAUGHT, Exception.class).getMessage()));

        // noop: the bank's folder is read-only to us, so files stay there and the poller must remember them itself.
        // sortBy: when one poll finds several days' files, they go in date order (the date is in the name).
        from(partner + "&noop=true&include=.*\\.csv&sortBy=file:name&idempotentRepository=#seenFiles"
                + "&idempotentKey=${file:name}-${file:size}-${file:modified}")
                .routeId("policy-files")
                .process(this::start)
                .idempotentConsumer(exchangeProperty(CHECKSUM), processedFiles).skipDuplicate(false)
                .choice()
                    .when(exchangeProperty(Exchange.DUPLICATE_MESSAGE).isEqualTo(true))
                        .process(e -> runs.finish(run(e), Runs.Status.DUPLICATE, "The same content was already processed."))
                    .otherwise()
                        .process(this::validate)
                        .process(e -> queue.sendAll(e.getMessage().getBody(PolicyFile.Parsed.class).accepted()))
                        .process(e -> runs.finish(run(e), Runs.Status.DONE, null))
                .end();
    }

    private void start(Exchange e) throws NoSuchAlgorithmException {
        byte[] content = e.getMessage().getBody(byte[].class);
        String checksum = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        e.setProperty(CHECKSUM, checksum);
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
