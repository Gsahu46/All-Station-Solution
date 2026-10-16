package com.tijori.transfers;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: transfers and the account's audit trail; valid, invalid and not found. */
class TransferContractTest extends ApiTest {

    @Test
    void aTransferChangesBothBalancesAndIsAuditedTwice() throws Exception {
        transfer(1, 2, 150_000).andExpect(status().isCreated())
                .andExpect(content().json("{\"fromAccountId\":1,\"toAccountId\":2,\"amountPaise\":150000,\"status\":\"COMPLETED\"}"));
        assertThat(balance(1)).isEqualTo(2_350_000);
        assertThat(balance(2)).isEqualTo(160_000);
        mvc.perform(get("/audit-events").param("accountId", "2")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].event").value(org.hamcrest.Matchers.contains("TRANSFER_ATTEMPTED", "TRANSFER_COMPLETED")));
        assertThat(jdbc.sql("SELECT count(DISTINCT attempt_id) FROM audit_events").query(Long.class).single()).isEqualTo(1);   // one attempt, two events
    }

    @Test
    void everyRefusalIsAuditedWithItsReason() throws Exception {
        transfer(2, 1, 500_000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Insufficient funds"));
        transfer(1, 1, 1_000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Same account"));
        transfer(1, 99, 1_000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown account"));
        assertThat(balance(1)).isEqualTo(2_500_000);   // the debit before "unknown account" was rolled back
        assertThat(events()).containsExactly("TRANSFER_ATTEMPTED", "TRANSFER_FAILED Insufficient funds",
                "TRANSFER_ATTEMPTED", "TRANSFER_FAILED Same account", "TRANSFER_ATTEMPTED", "TRANSFER_FAILED Unknown account");
    }

    @Test
    void malformedTransfersAre400AndNotAttempts() throws Exception {
        transfer(1, 2, 99).andExpect(status().isBadRequest());
        transfer(1, 2, 50_000_001).andExpect(status().isBadRequest());
        mvc.perform(post("/transfers").contentType(MediaType.APPLICATION_JSON).content("{\"fromAccountId\":1,\"amountPaise\":1000}")).andExpect(status().isBadRequest());
        mvc.perform(post("/transfers").contentType(MediaType.APPLICATION_JSON).content("{\"fromAccountId\":1,\"toAccountId\":2,\"amountPaise\":10.5}")).andExpect(status().isBadRequest());
        assertThat(events()).isEmpty();
    }

    @Test
    void unknownAccountsHaveNoTrail() throws Exception {
        mvc.perform(get("/audit-events").param("accountId", "99")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No account 99."));
        mvc.perform(get("/audit-events")).andExpect(status().isBadRequest());
    }
}
