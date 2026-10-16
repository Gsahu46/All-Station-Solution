package com.tijori.transfers;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: Ravi (₹100) tries to send ₹5,000, the old way and the new way. */
@Import(OldTransferService.class)
class AuditRollbackTrapTest extends ApiTest {

    @Autowired
    OldTransferService old;

    @Test
    void theOldAuditRowRolledBackWithTheTransfer() {
        assertThatThrownBy(() -> old.transfer(2, 1, 500_000)).hasMessage("insufficient funds");
        assertThat(events()).isEmpty();   // the failed attempt left no trace: exactly what the auditors asked for, gone
    }

    @Test
    void theNewTrailKeepsTheAttemptAndItsFailure() throws Exception {
        transfer(2, 1, 500_000).andExpect(status().isUnprocessableContent());
        assertThat(events()).containsExactly("TRANSFER_ATTEMPTED", "TRANSFER_FAILED Insufficient funds");
        assertThat(balance(2)).isEqualTo(10_000);
    }
}
