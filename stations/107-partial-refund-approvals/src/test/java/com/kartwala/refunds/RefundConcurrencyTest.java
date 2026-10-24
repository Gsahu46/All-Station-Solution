package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

import static com.kartwala.refunds.RefundOverlapTrapTest.atOnce;
import static org.assertj.core.api.Assertions.assertThat;

class RefundConcurrencyTest extends ApiTest {

    @Test
    void twoApproversAtTheSameMomentDecideARefundOnce() throws Exception {
        long id = idOf(refund(PHONE, 1_200_000, "asha"));   // ₹12,000: needs a second person
        List<Integer> statuses = atOnce(2, () -> decide(id, "APPROVE", Thread.currentThread().threadId() % 2 == 0 ? "raj" : "meena")
                .andReturn().getResponse().getStatus());
        assertThat(statuses).containsExactlyInAnyOrder(200, 409);
        assertThat(jdbc.sql("SELECT status FROM refunds WHERE id = ?").param(id).query(String.class).single()).isEqualTo("APPROVED");
    }

    @Test
    void anApprovalAndARejectionAtOnceLeaveTheOrderConsistent() throws Exception {
        for (int round = 0; round < 10; round++) {
            noRefunds();
            long id = idOf(refund(PHONE, 1_500_000, "vikram"));
            List<Integer> statuses = atOnce(2, () -> {
                boolean approve = ThreadLocalRandom.current().nextBoolean();
                return decide(id, approve ? "APPROVE" : "REJECT", approve ? "raj" : "meena").andReturn().getResponse().getStatus();
            });
            assertThat(statuses).contains(200);
            assertThat(reserved(PHONE)).as("round " + round).isEqualTo(refundedOrPending(PHONE));
        }
    }

    @Test
    void manyAgentsWithDifferentAmountsNeverPassTheTotal() throws Exception {
        List<Integer> statuses = atOnce(40, () -> refund(WASHING_MACHINE, 50_000 * ThreadLocalRandom.current().nextLong(1, 9), "asha")
                .andReturn().getResponse().getStatus());
        assertThat(statuses).containsOnly(201, 409);
        assertThat(refundedOrPending(WASHING_MACHINE)).isLessThanOrEqualTo(1_250_000).isEqualTo(reserved(WASHING_MACHINE));
    }
}
