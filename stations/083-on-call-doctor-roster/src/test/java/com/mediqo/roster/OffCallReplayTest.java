package com.mediqo.roster;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The ward app retries after a timeout: the same request twice gives one change and the same answer. */
class OffCallReplayTest extends ApiTest {

    @Test
    void theSameOffCallTwiceChangesTheRosterOnce() throws Exception {
        String first = offCall("orthopaedics", "dr.khan").andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        String again = offCall("orthopaedics", "dr.khan").andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(again).isEqualTo(first);
        assertThat(jdbc.sql("SELECT count(*) FROM roster_changes").query(Long.class).single()).isEqualTo(1);
        assertThat(onCall("orthopaedics")).isEqualTo(2);
    }

    @Test
    void aRetryIsNotRefusedEvenWhenTheWardIsNowAtItsMinimum() throws Exception {
        offCall("cardiology", "dr.sharma");
        // sharma's app did not hear the answer and asks again. The ward is now at its minimum, but sharma is already off:
        // the retry is answered, not refused as if sharma were the last doctor on call.
        offCall("cardiology", "dr.sharma").andExpect(status().isOk());
        assertThat(jdbc.sql("SELECT count(*) FROM roster_changes").query(Long.class).single()).isEqualTo(1);
    }
}
