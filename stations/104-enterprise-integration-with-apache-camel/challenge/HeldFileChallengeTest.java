package com.bimaly.integration;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: when a large share of a file is wrong, the bank's export is probably broken: hold the whole file for a
 * person instead of sending the part that happens to look right. Files under 10 lines are judged line by line.
 */
class HeldFileChallengeTest extends ApiTest {

    static final String GOOD = "KB-92%02d,Meera Iyer,1988-04-12,TERM10,1000000000\n";
    static final String BAD = "KB-92%02d,Meera Iyer,1988-04-12,TERM10\n";

    @Test
    void aFileWithMoreThanOneFifthOfItsLinesWrongIsHeldAndSendsNothing() throws Exception {
        String content = HEADER + lines(1, 7, GOOD) + lines(8, 10, BAD);
        upload("KOSHBANK-20270201.csv", content);
        Runs.Run run = awaitRun("KOSHBANK-20270201.csv", Runs.Status.HELD);

        assertThat(run.error).isEqualTo("3 of 10 lines were rejected; the limit is 20%.");
        assertThat(run.rejected).hasSize(3);
        assertThat(Files.readString(Path.of("target/test-data/held/KOSHBANK-20270201.csv"))).isEqualTo(content);
        assertThat(waiting()).isZero();
    }

    @Test
    void oneFifthIsStillAllowedAndASmallFileIsJudgedLineByLine() throws Exception {
        upload("KOSHBANK-20270202.csv", HEADER + lines(11, 18, GOOD) + lines(19, 20, BAD));
        assertThat(awaitRun("KOSHBANK-20270202.csv", Runs.Status.DONE).accepted).isEqualTo(8);
        upload("KOSHBANK-20270203.csv", HEADER + lines(21, 22, GOOD) + lines(23, 25, BAD));
        assertThat(awaitRun("KOSHBANK-20270203.csv", Runs.Status.DONE).accepted).isEqualTo(2);
        assertThat(waiting()).isEqualTo(10);
    }

    private static String lines(int from, int to, String format) {
        StringBuilder s = new StringBuilder();
        for (int i = from; i <= to; i++) {
            s.append(format.formatted(i));
        }
        return s.toString();
    }
}
