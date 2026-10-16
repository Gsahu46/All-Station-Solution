package com.paysetu.payouts;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.greaterThanOrEqualTo;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: payouts and their audit events; valid, invalid and not found. */
class PayoutContractTest extends ApiTest {

    @Test
    void aPayoutIsRecordedAndAudited() throws Exception {
        String url = payout(1, 1_000_000).andExpect(status().isCreated())
                .andExpect(content().json("{\"merchantId\":1,\"amountPaise\":1000000,\"ifsc\":\"HDFC0001234\",\"accountLast4\":\"7890\",\"status\":\"REQUESTED\"}"))
                .andReturn().getResponse().getHeader("Location");
        assertThat(balance(1)).isEqualTo(4_000_000);
        mvc.perform(get(url)).andExpect(status().isOk());
        mvc.perform(get("/audit-events")).andExpect(status().isOk())
                .andExpect(content().json("[{\"action\":\"PAYOUT_REQUESTED\",\"outcome\":\"SUCCESS\",\"subject\":\"1\",\"method\":\"PayoutService.request\",\"error\":null}]"))
                .andExpect(jsonPath("$[0].durationMs", greaterThanOrEqualTo(0)));
    }

    @Test
    void aRefusedPayoutIsAuditedAsAFailure() throws Exception {
        payout(2, 50_000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Not enough balance"));
        assertThat(balance(2)).isEqualTo(20_000);
        mvc.perform(get("/audit-events").param("action", "PAYOUT_REQUESTED"))
                .andExpect(content().json("[{\"outcome\":\"FAILURE\",\"subject\":\"2\",\"error\":\"Not enough balance\"}]"));
    }

    @Test
    void theAuditLogNeverHoldsTheAccountNumber() throws Exception {
        payout(1, 1_000_000);
        assertThat(jdbc.sql("SELECT count(*) FROM audit_events WHERE concat_ws(' ', action, subject, method, error) LIKE '%50100123457890%'")
                .query(Long.class).single()).isZero();
    }

    @Test
    void eventsComeNewestFirstAndCanBeFiltered() throws Exception {
        payout(1, 100);
        payout(2, 99_999_999);
        payout(1, 200);
        mvc.perform(get("/audit-events").param("limit", "2")).andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].outcome").value("SUCCESS")).andExpect(jsonPath("$[1].outcome").value("FAILURE"));
        mvc.perform(get("/audit-events").param("action", "PAYOUT_CANCELLED")).andExpect(content().json("[]"));
    }

    @Test
    void malformedPayoutsAre400AndNeverReachTheAuditedMethod() throws Exception {
        for (String body : new String[]{
                "{\"merchantId\":1,\"amountPaise\":99,\"ifsc\":\"HDFC0001234\",\"accountNumber\":\"50100123457890\"}",
                "{\"merchantId\":1,\"amountPaise\":1000,\"ifsc\":\"HDFC1001234\",\"accountNumber\":\"50100123457890\"}",
                "{\"merchantId\":1,\"amountPaise\":1000,\"ifsc\":\"HDFC0001234\",\"accountNumber\":\"5010-0123\"}",
                "{\"amountPaise\":1000,\"ifsc\":\"HDFC0001234\",\"accountNumber\":\"50100123457890\"}"}) {
            mvc.perform(post("/payouts").contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isBadRequest());
        }
        mvc.perform(get("/audit-events").param("limit", "0")).andExpect(status().isBadRequest());
        assertThat(auditEvents()).isZero();
    }

    @Test
    void unknownMerchantsAre422AndUnknownPayouts404() throws Exception {
        payout(99, 1000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown merchant"));
        mvc.perform(get("/payouts/99")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No payout 99."));
    }
}
