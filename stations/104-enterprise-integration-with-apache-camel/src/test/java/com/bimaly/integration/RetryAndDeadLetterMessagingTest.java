package com.bimaly.integration;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

class RetryAndDeadLetterMessagingTest extends ApiTest {

    @Test
    void aBrokerThatRefusesIsRetriedThenTheFileIsTriedAgainOnTheNextPoll() throws Exception {
        // The broker refuses every message for the queue (as when it is out of disk or memory).
        rabbitmqctl("set_policy", "--apply-to", "queues", "refuse", "^policy\\.requests$", "{\"max-length\":0,\"overflow\":\"reject-publish\"}");
        try {
            upload("KOSHBANK-20261101.csv", HEADER + "KB-3001,Meera Iyer,1988-04-12,TERM10,1000000000\nKB-3002,Ravi Kumar,1975-11-02,HEALTH5,50000000\n");
            Runs.Run failed = awaitRun("KOSHBANK-20261101.csv", Runs.Status.FAILED);
            assertThat(failed.error).isNotBlank();
            assertThat(waiting()).isZero();
        } finally {
            rabbitmqctl("clear_policy", "refuse");
        }
        awaitRun("KOSHBANK-20261101.csv", Runs.Status.DONE);
        assertThat(runs.forFile("KOSHBANK-20261101.csv").getFirst().status).isEqualTo(Runs.Status.FAILED);
        assertThat(ids(drain())).containsExactly("KOSHBANK:KB-3001", "KOSHBANK:KB-3002");
    }

    @Test
    void aFileThatCanNeverBeReadGoesToTheDeadLetterFolderOnce() throws Exception {
        String content = "ref;name;dob;product;sum\nKB-4001;Meera Iyer;1988-04-12;TERM10;1000000000\n";
        upload("KOSHBANK-20261102.csv", content);
        Runs.Run run = awaitRun("KOSHBANK-20261102.csv", Runs.Status.DEAD_LETTERED);

        assertThat(run.error).isEqualTo("The first line is not the header " + PolicyFile.HEADER + ".");
        Path copy = Path.of("target/test-data/dead-letter/KOSHBANK-20261102.csv");
        await().atMost(Duration.ofSeconds(5)).until(() -> Files.exists(copy));
        assertThat(Files.readString(copy)).isEqualTo(content);   // as it arrived, for a person to look at
        Thread.sleep(1_500);   // seven more polls
        assertThat(runs.forFile("KOSHBANK-20261102.csv")).hasSize(1);
        assertThat(waiting()).isZero();
    }

    @Test
    void aWrongFileNameOrAnEmptyFileIsDeadLetteredToo() throws Exception {
        upload("koshbank-policies.csv", HEADER + "KB-5001,Meera Iyer,1988-04-12,TERM10,1000000000\n");
        upload("KOSHBANK-20261103.csv", HEADER);
        assertThat(awaitRun("koshbank-policies.csv", Runs.Status.DEAD_LETTERED).error)
                .isEqualTo("The file name koshbank-policies.csv is not BANK-YYYYMMDD.csv.");
        assertThat(awaitRun("KOSHBANK-20261103.csv", Runs.Status.DEAD_LETTERED).error)
                .isEqualTo("The file has a header but no policies.");
        assertThat(waiting()).isZero();
    }

    private static void rabbitmqctl(String... args) throws Exception {
        String[] command = new String[args.length + 1];
        command[0] = "rabbitmqctl";
        System.arraycopy(args, 0, command, 1, args.length);
        var result = Partners.RABBIT.execInContainer(command);
        assertThat(result.getExitCode()).as(result.getStderr()).isZero();
    }
}
