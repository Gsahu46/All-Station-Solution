package com.basketo.loyalty;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: earn and redeem; valid, invalid and not found. Every test uses its own new customer. */
class LoyaltyContractTest extends ApiTest {

    @Test
    void theFirstEarnCreatesTheBalanceAndTheNextAddsToIt() throws Exception {
        long c = newCustomer();
        earn(c, "BK-2001", 149_900).andExpect(status().isCreated())
                .andExpect(content().json("{\"customerId\":%d,\"orderRef\":\"BK-2001\",\"earned\":14,\"balance\":14}".formatted(c)));   // ₹1,499: 14 points
        earn(c, "BK-2002", 25_000).andExpect(jsonPath("$.earned").value(2)).andExpect(jsonPath("$.balance").value(16));
        earn(c, "BK-2003", 9_999).andExpect(status().isCreated()).andExpect(jsonPath("$.earned").value(0));   // under ₹100
    }

    @Test
    void anOrderEarnsOnceInAnyCase() throws Exception {
        long c = newCustomer();
        earn(c, "bk-77", 50_000).andExpect(status().isCreated());
        earn(c, "BK-77", 50_000).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already earned"));
        assertThat(balance(c)).isEqualTo(5);
    }

    @Test
    void redeemingTakesPointsAndNeverMoreThanThere() throws Exception {
        long c = newCustomer();
        earn(c, "BK-3001", 1_000_000);   // 100 points
        redeem(c, 30).andExpect(status().isOk()).andExpect(content().json("{\"redeemed\":30,\"balance\":70}"));
        redeem(c, 71).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Not enough points"));
        redeem(newCustomer(), 1).andExpect(status().isUnprocessableContent());   // no balance row at all
        assertThat(balance(c)).isEqualTo(70);
    }

    @Test
    void malformedRequestsAre400() throws Exception {
        long c = newCustomer();
        earn(c, "BK", 100).andExpect(status().isBadRequest());
        earn(c, "BK 4001", 100).andExpect(status().isBadRequest());
        earn(c, "BK-4001", 0).andExpect(status().isBadRequest());
        redeem(c, 0).andExpect(status().isBadRequest());
        mvc.perform(post("/loyalty/{id}/earn", c).contentType(MediaType.APPLICATION_JSON).content("{\"orderRef\":\"BK-4001\",\"amountPaise\":100.5}"))
                .andExpect(status().isBadRequest());
        assertThat(balance(c)).isNull();
    }

    @Test
    void unknownCustomersAre404() throws Exception {
        earn(999_999, "BK-5001", 100).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No customer 999999."));
        redeem(999_999, 1).andExpect(status().isNotFound());
    }
}
