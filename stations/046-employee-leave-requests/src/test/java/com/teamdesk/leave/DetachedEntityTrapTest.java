package com.teamdesk.leave;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: the old approval, run the way production ran it. The same lines save
 * everything or half of it, depending only on whether a transaction was open around them.
 */
class DetachedEntityTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @Test
    void withoutATransactionTheManagerSeesNineButTheDatabaseKeepsTwelve() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        int shown = new OldLeaveDesk(requests).approve(id);
        assertThat(shown).isEqualTo(9);
        assertThat(statusInTheDatabase(id)).isEqualTo("APPROVED");   // the request was saved...
        assertThat(balanceInTheDatabase(1)).isEqualTo(12);           // ...the balance was not: 3 days of leave for free
    }

    @Test
    void theSameLinesInsideATransactionSaveBoth() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        transaction.executeWithoutResult(status -> new OldLeaveDesk(requests).approve(id));
        assertThat(statusInTheDatabase(id)).isEqualTo("APPROVED");
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);   // dirty checking wrote the employee too
    }

    @Test
    void theFixedDeskSavesBothWithoutCallingSave() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        approve(id);
        assertThat(statusInTheDatabase(id)).isEqualTo("APPROVED");
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);
    }
}
