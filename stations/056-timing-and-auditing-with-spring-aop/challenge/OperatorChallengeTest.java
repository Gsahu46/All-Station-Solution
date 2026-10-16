package com.paysetu.payouts;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Challenge 2: every audit event also records who: the X-Operator header of the HTTP request (an operations person's
 * id), or "system" when there is none (a scheduled job, or a call without the header). A new migration adds the
 * column with a check; the aspect reads the current request. Demo: the header is trusted; a real app uses the login.
 */
class OperatorChallengeTest extends ApiTest {

    @Test
    void theAuditEventNamesTheOperator() throws Exception {
        mvc.perform(post("/payouts").header("X-Operator", "ops-asha").contentType(MediaType.APPLICATION_JSON)
                .content("{\"merchantId\":1,\"amountPaise\":1000,\"ifsc\":\"HDFC0001234\",\"accountNumber\":\"50100123457890\"}"));
        payout(1, 1000);
        assertThat(jdbc.sql("SELECT actor FROM audit_events ORDER BY id").query(String.class).list()).containsExactly("ops-asha", "system");
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> jdbc.sql("UPDATE audit_events SET actor = ' '").update())
                .hasMessageContaining("audit_events_actor_not_blank");
    }
}
