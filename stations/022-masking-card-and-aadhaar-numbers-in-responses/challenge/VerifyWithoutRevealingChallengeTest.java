package com.tijori.profiles;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /customers/{id}/aadhaar-checks with {"last4": "0123"} lets support check what a caller reads out,
 * without the API ever showing the number. Only support may call it.
 */
class VerifyWithoutRevealingChallengeTest extends ApiTest {

    ResultActions check(String user, String id, String last4) throws Exception {
        return mvc.perform(post("/customers/{id}/aadhaar-checks", id).with(httpBasic(user, user + "-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content("{\"last4\":\"" + last4 + "\"}"));
    }

    @Test
    void supportLearnsOnlyWhetherItMatches() throws Exception {
        check("neha", "c-1001", "0123").andExpect(status().isOk()).andExpect(jsonPath("$.match").value(true));
        check("neha", "c-1001", "9999").andExpect(status().isOk()).andExpect(jsonPath("$.match").value(false));
        check("neha", "c-9999", "0123").andExpect(status().isNotFound());
    }

    @Test
    void onlySupportMayCheckAndOnlyFourDigitsAreAccepted() throws Exception {
        check("asha", "c-1001", "0123").andExpect(status().isForbidden());
        check("neha", "c-1001", "123").andExpect(status().isBadRequest());
        check("neha", "c-1001", "234567890123").andExpect(status().isBadRequest());   // no guessing the whole number
    }
}
