package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old statement page looked the account up by the id in the URL, and nothing else. Account
 * numbers count up, so changing 1001 to 1002 showed the next customer's statement. Each test runs the old query,
 * then asks the API the same question as the same customer.
 */
class UrlIdTrustTrapTest extends ApiTest {

    /** The old lookup, as it was: trust the id. */
    Map<String, Object> oldLookup(long accountId) {
        return jdbc.sql("SELECT id, name, balance_paise FROM accounts WHERE id = ?").param(accountId).query().singleRow();
    }

    @Test
    void changingTheIdInTheUrlShowedTheNextCustomersAccount() throws Exception {
        assertThat(oldLookup(1002)).containsEntry("name", "Dev Patel");   // zoya, signed in, asking for 1002
        account("zoya", 1002).andExpect(status().isNotFound());
        statement("zoya", 1002, "2026-09").andExpect(status().isNotFound());
    }

    @Test
    void walkingThroughTheNumbersFindsOnlyYourOwn() throws Exception {
        // Not someone else's and not existing look the same: the numbers reveal nothing.
        for (long id = 1000; id <= 1005; id++) {
            int s = account("zoya", id).andReturn().getResponse().getStatus();
            assertThat(s).as("account %d", id).isEqualTo(id == 1001 || id == 1003 ? 200 : 404);
        }
    }

    @Test
    void theOwnAccountStillWorks() throws Exception {
        // The control.
        account("zoya", 1001).andExpect(status().isOk());
        statement("zoya", 1001, "2026-09").andExpect(status().isOk());
    }
}
