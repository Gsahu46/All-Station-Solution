package com.paysetu.cards;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Instant;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the network tells Paysetu about a token's life. POST /network/token-events, signed in as the network
 * (user sim-network, password sim-network-demo-pass): UPDATED with a new expiry when the bank re-issues the card (the
 * token stays the same), SUSPENDED and RESUMED. Customers may not send events. A V3 migration allows "suspended".
 */
class TokenEventsChallengeTest extends ApiTest {

    String tokenOf(long card) {
        return jdbc.sql("SELECT token_ref FROM saved_cards WHERE id = ?").param(card).query(String.class).single();
    }

    ResultActions event(String user, String json) throws Exception {
        return mvc.perform(post("/network/token-events").with(httpBasic(user, password(user))).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void aReissuedCardKeepsItsTokenWithTheNewExpiry() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);   // 12/2028
        CLOCK.now = Instant.parse("2029-01-10T06:30:00Z");
        pay("asha", "ORD-1", card, 50000).andExpect(status().isUnprocessableContent());
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"UPDATED\",\"expiryMonth\":12,\"expiryYear\":2033}".formatted(tokenOf(card))).andExpect(status().isNoContent());
        pay("asha", "ORD-2", card, 50000).andExpect(status().isCreated());
        list("asha", ASHA).andExpect(jsonPath("$[0].expiryYear").value(2033));
    }

    @Test
    void aSuspendedTokenCannotPayUntilResumed() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"SUSPENDED\"}".formatted(tokenOf(card))).andExpect(status().isNoContent());
        pay("asha", "ORD-3", card, 50000).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This saved card is suspended by the bank"));
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"RESUMED\"}".formatted(tokenOf(card))).andExpect(status().isNoContent());
        pay("asha", "ORD-4", card, 50000).andExpect(status().isCreated());
    }

    @Test
    void onlyTheNetworkSendsEventsAndUnknownTokensAre404() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        event("asha", "{\"tokenRef\":\"%s\",\"event\":\"SUSPENDED\"}".formatted(tokenOf(card))).andExpect(status().isForbidden());
        event("sim-network", "{\"tokenRef\":\"tkn_aaaaaaaaaaaaaaaaaaaa\",\"event\":\"SUSPENDED\"}").andExpect(status().isNotFound());
        event("sim-network", "{\"tokenRef\":\"%s\",\"event\":\"STOLEN\"}".formatted(tokenOf(card))).andExpect(status().isBadRequest());
    }
}
