package com.tijori.passkeys;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /webauthn/passkeys lists the customer's own passkeys (id, label); DELETE /webauthn/passkeys/{id}
 * removes one (204), after which it cannot sign in. Another customer's passkey is 404 and stays.
 */
class ManagePasskeysChallengeTest extends ApiTest {

    @Test
    void aCustomerListsAndRemovesTheirOwnPasskey() throws Exception {
        Device phone = passkeyFor("zoya");
        String token = codeToken("zoya");
        String id = body(mvc.perform(get("/webauthn/passkeys").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk()).andExpect(jsonPath("$[*].label", contains("zoya's phone")))).get(0).get("id").asString();
        mvc.perform(delete("/webauthn/passkeys/{id}", id).header("Authorization", "Bearer " + token)).andExpect(status().isNoContent());
        authenticate(phone.get(authenticationOptions())).andExpect(status().isUnauthorized());
    }

    @Test
    void anotherCustomersPasskeyIs404AndStays() throws Exception {
        Device zoyasPhone = passkeyFor("zoya");
        String zoyasId = body(mvc.perform(get("/webauthn/passkeys").header("Authorization", "Bearer " + codeToken("zoya")))).get(0).get("id").asString();
        mvc.perform(delete("/webauthn/passkeys/{id}", zoyasId).header("Authorization", "Bearer " + codeToken("dev"))).andExpect(status().isNotFound());
        authenticate(zoyasPhone.get(authenticationOptions())).andExpect(status().isOk());
    }
}
