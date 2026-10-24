package com.bimaly.integration;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

class DuplicateFileReplayTest extends ApiTest {

    static final String FILE = HEADER + "KB-6001,Meera Iyer,1988-04-12,TERM10,1000000000\nKB-6002,Ravi Kumar,1975-11-02,HEALTH5,50000000\n";

    @Test
    void theSameFileUploadedAgainSendsNothingAndIsRecordedAsADuplicate() throws Exception {
        upload("KOSHBANK-20261201.csv", FILE);
        awaitRun("KOSHBANK-20261201.csv", Runs.Status.DONE);
        assertThat(ids(drain())).containsExactly("KOSHBANK:KB-6001", "KOSHBANK:KB-6002");

        Thread.sleep(1_100);   // the server keeps times in seconds: a new upload must look new
        upload("KOSHBANK-20261201.csv", FILE);                // the bank's job ran twice
        upload("KOSHBANK-20261202.csv", FILE);                // or the same file under tomorrow's name
        assertThat(awaitRun("KOSHBANK-20261201.csv", Runs.Status.DUPLICATE).error).isEqualTo("The same content was already processed.");
        awaitRun("KOSHBANK-20261202.csv", Runs.Status.DUPLICATE);
        assertThat(runs.forFile("KOSHBANK-20261201.csv")).hasSize(2);
        assertThat(waiting()).isZero();
    }

    @Test
    void aCorrectedFileWithTheSameNameIsProcessed() throws Exception {
        upload("KOSHBANK-20261203.csv", HEADER + "KB-7001,Meera Iyer,1988-04-12,TERM10,1000000000\nKB-7002,Ravi Kumar,1975-11-02,CAR,0\n");
        assertThat(awaitRun("KOSHBANK-20261203.csv", Runs.Status.DONE).accepted).isEqualTo(1);

        Thread.sleep(1_100);
        upload("KOSHBANK-20261203.csv", HEADER + "KB-7001,Meera Iyer,1988-04-12,TERM10,1000000000\nKB-7002,Ravi Kumar,1975-11-02,HEALTH5,50000000\n");
        await().atMost(Duration.ofSeconds(20)).until(() -> runs.forFile("KOSHBANK-20261203.csv"),
                r -> r.size() == 2 && r.getLast().status == Runs.Status.DONE);
        // KB-7001 is sent again with the same id: the reader keeps the first and drops the copy.
        assertThat(ids(drain())).containsExactly("KOSHBANK:KB-7001", "KOSHBANK:KB-7001", "KOSHBANK:KB-7002");
    }
}
