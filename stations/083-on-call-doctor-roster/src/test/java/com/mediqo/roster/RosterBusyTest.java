package com.mediqo.roster;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;

/** With no retries left, the loser of a race is told to try again (503), not given a 500 or a wrong 409. */
@TestPropertySource(properties = "mediqo.serializable-attempts=1")
class RosterBusyTest extends ParallelApiTest {

    @Test
    void aLostRaceWithNoRetriesLeftIs503AndChangesNothing() throws Exception {
        assertThat(atOnce("cardiology", "dr.sharma", "dr.iyer")).containsExactlyInAnyOrder(200, 503);
        assertThat(onCall("cardiology")).isEqualTo(1);
        assertThat(jdbc.sql("SELECT count(*) FROM roster_changes").query(Integer.class).single()).isEqualTo(1);
    }
}
