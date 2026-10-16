package com.basketo.loyalty;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /loyalty/{customerId}: the balance (0 when nothing was ever earned) and the ledger, newest first,
 * as reason, delta and orderRef. Unknown customer: 404.
 */
class BalanceChallengeTest extends ApiTest {

    @Test
    void theBalanceAndItsHistory() throws Exception {
        long c = newCustomer();
        mvc.perform(get("/loyalty/{id}", c)).andExpect(status().isOk()).andExpect(content().json("{\"balance\":0,\"entries\":[]}"));
        earn(c, "BK-8001", 500_000);
        redeem(c, 20);
        mvc.perform(get("/loyalty/{id}", c)).andExpect(content().json("""
                {"customerId":%d,"balance":30,"entries":[
                 {"reason":"REDEEM","delta":-20,"orderRef":null},{"reason":"EARN","delta":50,"orderRef":"BK-8001"}]}""".formatted(c), true));
        mvc.perform(get("/loyalty/999999")).andExpect(status().isNotFound());
    }
}
