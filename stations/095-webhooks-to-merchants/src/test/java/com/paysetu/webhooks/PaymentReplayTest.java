package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The payment service reports a captured payment again (its own retry after a timeout): one effect. */
class PaymentReplayTest extends ApiTest {

    @Test
    void theSamePaymentReportedTwiceIsOneEventAndOneDelivery() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            secretFor("ravi", 1, merchant.url());
            var first = json(testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted()));
            var again = json(testEvent("ravi", 1, "pay-1001", 49900).andExpect(status().isOk()).andExpect(jsonPath("$.replay").value(true)));
            assertThat(again.get("eventId")).isEqualTo(first.get("eventId"));
            testEvent("ravi", 1, "PAY-1001", 50000).andExpect(status().isConflict());   // the same payment with another amount is a bug, not a replay
            dispatcher.dispatchDue();
            dispatcher.dispatchDue();
            assertThat(merchant.received()).hasSize(1);
            assertThat(jdbc.sql("SELECT count(*) FROM events").query(Long.class).single()).isEqualTo(1);
        }
    }
}
