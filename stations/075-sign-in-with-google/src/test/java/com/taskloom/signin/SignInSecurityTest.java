package com.taskloom.signin;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SignInSecurityTest extends ApiTest {

    @Test
    void everySignInGetsItsOwnPkceChallengeStateAndNonce() throws Exception {
        Map<String, String> one = start(new MockHttpSession());
        Map<String, String> two = start(new MockHttpSession());
        assertThat(one).containsEntry("code_challenge_method", "S256");
        for (String p : new String[]{"code_challenge", "state", "nonce"}) {
            assertThat(one.get(p)).isNotEqualTo(two.get(p));
        }
    }

    @Test
    void theVerifierSentToGoogleMatchesTheChallengeInTheRedirect() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        Map<String, String> q = start(browser);
        String code = "code-" + UUID.randomUUID();
        GOOGLE.idTokens.put(code, GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", q.get("nonce")).build()));
        GOOGLE.tokenRequests.clear();
        callback(browser, code, q.get("state")).andExpect(status().isFound());
        String verifier = GOOGLE.tokenRequests.getLast().get("code_verifier");
        assertThat(Base64.getUrlEncoder().withoutPadding().encodeToString(MessageDigest.getInstance("SHA-256").digest(verifier.getBytes(StandardCharsets.US_ASCII))))
                .isEqualTo(q.get("code_challenge"));
    }

    @Test
    void aCallbackWithAnotherBrowsersStateIsRefusedBeforeGoogleIsAsked() throws Exception {
        MockHttpSession victim = new MockHttpSession();
        Map<String, String> q = start(new MockHttpSession());   // the attacker started their own sign-in
        GOOGLE.tokenRequests.clear();
        callback(victim, "attackers-code", q.get("state")).andExpect(status().isUnauthorized());
        assertThat(GOOGLE.tokenRequests).isEmpty();
        me(victim).andExpect(status().isUnauthorized());
    }

    @Test
    void anIdTokenWithAnotherNonceIsRefused() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        signIn(browser, "100000000000000000001", "asha@acme.example", c -> c.claim("nonce", "replayed-from-yesterday"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void anUnverifiedEmailNeverLinksAnInvitation() throws Exception {
        String email = invite("Nisha");
        MockHttpSession browser = new MockHttpSession();
        // Anyone can create a Google account with nisha's address and not verify it.
        signIn(browser, newSub(), email, c -> c.claim("email_verified", false)).andExpect(status().isForbidden());
        MockHttpSession nisha = new MockHttpSession();
        signIn(nisha, newSub(), email).andExpect(status().isFound());   // the invitation is still there for her
        me(nisha).andExpect(jsonPath("$.name").value("Nisha"));
    }

    @Test
    void anotherGoogleAccountWithALinkedMembersEmailDoesNotBecomeThatMember() throws Exception {
        // asha is linked by her Google id. A second Google account showing her address, even verified, is someone else.
        MockHttpSession browser = new MockHttpSession();
        signIn(browser, newSub(), "asha@acme.example").andExpect(status().isForbidden());
        me(browser).andExpect(status().isUnauthorized());
    }

    @Test
    void theSessionIdChangesAtSignIn() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        Map<String, String> q = start(browser);
        String before = browser.getId();
        String code = "code-" + UUID.randomUUID();
        GOOGLE.idTokens.put(code, GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", q.get("nonce")).build()));
        callback(browser, code, q.get("state")).andExpect(status().isFound());
        assertThat(browser.getId()).isNotEqualTo(before);   // a session id planted before sign-in is worth nothing after
    }

    @Test
    void signingOutNeedsTheCsrfTokenBecauseTheCookieTravelsByItself() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        signIn(browser, "100000000000000000001", "asha@acme.example");
        mvc.perform(post("/logout").session(browser)).andExpect(status().isForbidden());   // a form on another site
        me(browser).andExpect(status().isOk());
        mvc.perform(post("/logout").session(browser).with(csrf())).andExpect(status().isNoContent());
        me(browser).andExpect(status().isUnauthorized());
    }

    @Test
    void oddCallbacksAre401NeverAnError() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        Map<String, String> q = start(browser);
        mvc.perform(get("/login/oauth2/code/google").param("error", "access_denied").param("state", q.get("state")).session(browser)).andExpect(status().isUnauthorized());
        callback(new MockHttpSession(), "x", "' OR '1'='1").andExpect(status().isUnauthorized());
        callback(new MockHttpSession(), "a".repeat(5000), "b".repeat(5000)).andExpect(status().isUnauthorized());
        Map<String, String> fresh = start(browser);
        callback(browser, "a-code-google-never-issued", fresh.get("state")).andExpect(status().isUnauthorized());
    }
}
