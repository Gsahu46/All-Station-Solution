package com.hireloop.candidates;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Security: 401 without or with wrong credentials, no account enumeration, one user is never another, CORS, and odd input. */
class CandidateSecurityTest extends ApiTest {

    @Test
    void theProfileNeeds401WithoutCredentials() throws Exception {
        mvc.perform(get("/candidates/me")).andExpect(status().isUnauthorized())
                .andExpect(content -> org.assertj.core.api.Assertions.assertThat(content.getResponse().getContentType()).contains("application/problem+json"));
    }

    @Test
    void anUnknownEmailAndAWrongPasswordLookTheSame() throws Exception {
        // Byte-for-byte identical, so an attacker cannot tell which emails have accounts.
        var unknown = me("nobody@example.com", "any-password-here").andReturn().getResponse();
        var wrong = me("priya@example.com", "wrong-password-here").andReturn().getResponse();
        org.assertj.core.api.Assertions.assertThat(unknown.getStatus()).isEqualTo(401).isEqualTo(wrong.getStatus());
        org.assertj.core.api.Assertions.assertThat(unknown.getContentAsString()).isEqualTo(wrong.getContentAsString());
    }

    @Test
    void oneCandidateOnlyEverSeesTheirOwnProfile() throws Exception {
        signup("owner@example.com", "Owner", "owner-password-1").andExpect(status().isCreated());
        signup("other@example.com", "Other", "other-password-1").andExpect(status().isCreated());
        me("owner@example.com", "owner-password-1").andExpect(jsonPath("$.email").value("owner@example.com"));
        // There is no /candidates/{id}: "me" is taken from the verified identity, never from the URL, so no id can be swapped.
        me("owner@example.com", "other-password-1").andExpect(status().isUnauthorized());
    }

    @Test
    void theApiIsReachableOnlyFromHireloopsOwnWebApp() throws Exception {
        mvc.perform(options("/candidates/signup").header("Origin", "https://evil.example").header("Access-Control-Request-Method", "POST"))
                .andExpect(status().isForbidden());
        mvc.perform(options("/candidates/signup").header("Origin", "https://app.hireloop.example").header("Access-Control-Request-Method", "POST"))
                .andExpect(status().isOk()).andExpect(header().string("Access-Control-Allow-Origin", "https://app.hireloop.example"));
    }

    @Test
    void oddInputIsRejectedNotExecuted() throws Exception {
        // A SQL-looking email is just text: parameters are bound, so it can only fail validation or not match.
        signup("robert'); DROP TABLE candidates;--@x", "Bobby", "a-good-long-password").andExpect(status().isBadRequest());
        mvc.perform(get("/candidates/me").with(httpBasic("priya@example.com' OR '1'='1", "x"))).andExpect(status().isUnauthorized());
        // A null byte in the name must not reach the database.
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/candidates/signup").contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\":\"nul@example.com\",\"fullName\":\"a\u0000b\",\"password\":\"a-good-long-password\"}")).andExpect(status().isBadRequest());
    }
}
