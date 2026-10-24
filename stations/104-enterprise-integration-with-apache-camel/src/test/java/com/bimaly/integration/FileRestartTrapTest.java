package com.bimaly.integration;

import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.impl.DefaultCamelContext;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.util.FileSystemUtils;

import java.nio.file.Path;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** The app is restarted at night for a deployment. Written first. */
class FileRestartTrapTest {

    static final String FILE = PolicyFile.HEADER + "\nKB-8001,Meera Iyer,1988-04-12,TERM10,1000000000\nKB-8002,Ravi Kumar,1975-11-02,HEALTH5,50000000\n";

    /** The old way: the bank's folder is read-only, so noop=true, and Camel remembers the files it read in memory. */
    @Test
    void theOldRouteReadsTheSameFileAgainAfterARestart() throws Exception {
        Partners.upload("old", "KOSHBANK-20260101.csv", FILE);
        AtomicInteger processed = new AtomicInteger();
        for (int restart = 1; restart <= 2; restart++) {
            try (var camel = new DefaultCamelContext()) {
                camel.addRoutes(new RouteBuilder() {
                    @Override
                    public void configure() {
                        from(Partners.sftp("old", 200) + "&noop=true").process(e -> processed.incrementAndGet());
                    }
                });
                camel.start();
                int expected = restart;
                await().atMost(Duration.ofSeconds(15)).until(() -> processed.get() == expected);
                Thread.sleep(1_000);   // five more polls: within one run, the file is not read again
                assertThat(processed).hasValue(restart);
            }
        }
        assertThat(processed).as("the same file, processed once per start").hasValue(2);
    }

    /** The API: what was processed is recorded on disk, so a restart starts where the last run stopped. */
    @Test
    void theApiRemembersWhatItProcessedAcrossARestart() throws Exception {
        FileSystemUtils.deleteRecursively(Path.of("target/restart-data").toFile());
        Partners.upload("restart", "KOSHBANK-20260102.csv", FILE);

        try (var first = start()) {
            first.getBean(RabbitAdmin.class).purgeQueue(PolicyQueue.QUEUE);
            Runs runs = first.getBean(Runs.class);
            await().atMost(Duration.ofSeconds(20)).until(() -> runs.forFile("KOSHBANK-20260102.csv"),
                    r -> r.size() == 1 && r.getFirst().status == Runs.Status.DONE);
            assertThat(waiting(first)).isEqualTo(2);
        }
        try (var second = start()) {
            Thread.sleep(2_000);   // ten polls of the same folder
            assertThat(second.getBean(Runs.class).forFile("KOSHBANK-20260102.csv")).hasSize(1);
            assertThat(waiting(second)).as("still the two messages of the first start").isEqualTo(2);

            Partners.upload("restart", "KOSHBANK-20260103.csv", FILE);   // the same file again, under a new name
            await().atMost(Duration.ofSeconds(20)).until(() -> second.getBean(Runs.class).forFile("KOSHBANK-20260103.csv"),
                    r -> r.size() == 1 && r.getFirst().status == Runs.Status.DUPLICATE);
            assertThat(waiting(second)).isEqualTo(2);
        }
    }

    private static ConfigurableApplicationContext start() {
        return new SpringApplicationBuilder(IntegrationApplication.class).run("--server.port=0",
                "--bimaly.files.data=target/restart-data", "--bimaly.partner.uri=" + Partners.sftp("restart", 200),
                "--spring.rabbitmq.host=" + Partners.RABBIT.getHost(), "--spring.rabbitmq.port=" + Partners.RABBIT.getAmqpPort());
    }

    private static long waiting(ConfigurableApplicationContext app) {
        return app.getBean(RabbitAdmin.class).getQueueInfo(PolicyQueue.QUEUE).getMessageCount();
    }
}
