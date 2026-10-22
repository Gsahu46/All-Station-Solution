package com.mediqo.roster;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class RosterConcurrencyTest extends ParallelApiTest {

    @Test
    void twoDoctorsLeavingAtOnceLeaveOneOnCall() throws Exception {
        assertThat(atOnce("cardiology", "dr.sharma", "dr.iyer")).containsExactlyInAnyOrder(200, 409);
        assertThat(onCall("cardiology")).isEqualTo(1);
        assertThat(roster.retries.get()).isPositive();   // the loser was stopped by SERIALIZABLE, run again, and refused
    }

    @Test
    void threeDoctorsLeavingAtOnceFromAWardThatNeedsOne() throws Exception {
        assertThat(atOnce("orthopaedics", "dr.bose", "dr.khan", "dr.rao")).containsExactlyInAnyOrder(200, 200, 409);
        assertThat(onCall("orthopaedics")).isEqualTo(1);
    }
}
