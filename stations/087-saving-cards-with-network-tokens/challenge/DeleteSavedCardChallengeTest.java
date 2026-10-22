package com.paysetu.cards;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /customers/{id}/saved-cards/{cardId}. The token is deleted at the network too, the card leaves the
 * list and cannot pay; deleting it again is still 204. Another customer's card is 403, an unknown one 404.
 */
class DeleteSavedCardChallengeTest extends ApiTest {

    ResultActions remove(String user, long customer, long card) throws Exception {
        return mvc.perform(delete("/customers/{id}/saved-cards/{card}", customer, card).with(httpBasic(user, password(user))));
    }

    @Test
    void aDeletedCardIsGoneEverywhere() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        remove("asha", ASHA, card).andExpect(status().isNoContent());
        remove("asha", ASHA, card).andExpect(status().isNoContent());
        list("asha", ASHA).andExpect(jsonPath("$.length()").value(0));
        pay("asha", "ORD-1", card, 50000).andExpect(status().isNotFound());
        assertThat(network.holds(VISA)).isFalse();
    }

    @Test
    void onlyTheOwnerCanDeleteAndUnknownCardsAre404() throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        remove("rohan", ASHA, card).andExpect(status().isForbidden());
        remove("rohan", ROHAN, card).andExpect(status().isNotFound());   // Asha's card through Rohan's own path
        remove("asha", ASHA, 99).andExpect(status().isNotFound());
        assertThat(network.holds(VISA)).isTrue();
    }
}
