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
    private static final String CONTENT = "bimalyContent";
    private final Runs runs;
    private final PolicyQueue queue;
    private final IdempotentRepository processedFiles;
    private final String partner;
    private final String deadLetter;
    private final int redeliveries;
    private final Duration redeliveryDelay;
    private final String held;
    private final int maxRejectedPercent;

    PolicyFileRoute(Runs runs, PolicyQueue queue, IdempotentRepository processedFiles,
                    @Value("${bimaly.partner.uri}") String partner, @Value("${bimaly.files.data}") String data,
                    @Value("${bimaly.files.redeliveries}") int redeliveries,
                    @Value("${bimaly.files.redelivery-delay}") Duration redeliveryDelay,
                    @Value("${bimaly.files.max-rejected-percent:20}") int maxRejectedPercent) {
        this.runs = runs;
        this.queue = queue;
        this.processedFiles = processedFiles;
        this.partner = partner;
        this.deadLetter = "file:" + data + "/dead-letter";
        this.redeliveries = redeliveries;
        this.redeliveryDelay = redeliveryDelay;
        this.held = "file:" + data + "/held";
        this.maxRejectedPercent = maxRejectedPercent;
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
                        // Too much of a file of 10 lines or more is wrong: the bank's export is probably broken. Send nothing; a person decides.
                        .filter(this::tooManyRejected)
                            .process(this::hold)
                            .to(held)
                            .stop()
                        .end()
                        .process(e -> queue.sendAll(e.getMessage().getBody(PolicyFile.Parsed.class).accepted()))
                        .process(e -> runs.finish(run(e), Runs.Status.DONE, null))
                .end();
    }

    private void start(Exchange e) throws NoSuchAlgorithmException {
        byte[] content = e.getMessage().getBody(byte[].class);
        String checksum = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        e.setProperty(CHECKSUM, checksum);
        e.setProperty(CONTENT, content);
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

    private boolean tooManyRejected(Exchange e) {
        Runs.Run run = run(e);
        return run.lines >= 10 && run.rejected.size() * 100 > run.lines * maxRejectedPercent;
    }

    /** Records why, and puts the file back in the body as it arrived, for the held folder. */
    private void hold(Exchange e) {
        Runs.Run run = run(e);
        runs.finish(run, Runs.Status.HELD, run.rejected.size() + " of " + run.lines + " lines were rejected; the limit is " + maxRejectedPercent + "%.");
        e.getMessage().setBody(e.getProperty(CONTENT, byte[].class));
    }

    private static Runs.Run run(Exchange e) {
        return e.getProperty(RUN, Runs.Run.class);
    }
}
