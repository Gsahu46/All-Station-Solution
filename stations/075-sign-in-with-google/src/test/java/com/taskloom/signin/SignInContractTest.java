package com.taskloom.signin;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SignInContractTest extends ApiTest {

    @Test
    void startingSignInRedirectsToGoogleForThisApp() throws Exception {
        mvc.perform(get("/oauth2/authorization/google")).andExpect(status().isFound());
        Map<String, String> q = start(new MockHttpSession());
        assertThat(q).containsEntry("response_type", "code").containsEntry("client_id", CLIENT_ID)
                .containsEntry("scope", "openid email profile").containsEntry("redirect_uri", "http://localhost/login/oauth2/code/google")
                .containsKeys("state", "nonce", "code_challenge");
    }

    @Test
    void aLinkedMemberSignsInAndSeesTheirAccount() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        signIn(browser, "100000000000000000001", "asha@acme.example").andExpect(status().isFound());
        me(browser).andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Asha Rao"))
                .andExpect(jsonPath("$.email").value("asha@acme.example")).andExpect(jsonPath("$.workspace").value("Acme"))
                .andExpect(jsonPath("$.signedInWith").value("google"));
        mvc.perform(get("/me").param("account", "acc-2").session(browser)).andExpect(jsonPath("$.name").value("Asha Rao"));   // a parameter chooses nothing
    }

    @Test
    void anInvitedEmailIsLinkedAtFirstSignInAndTheGoogleIdAfterThat() throws Exception {
        String email = invite("Ravi");
        String sub = newSub();
        MockHttpSession first = new MockHttpSession();
        signIn(first, sub, email.toUpperCase(java.util.Locale.ROOT)).andExpect(status().isFound());   // Google may send other capitals
        me(first).andExpect(jsonPath("$.name").value("Ravi")).andExpect(jsonPath("$.email").value(email));
        // Later Ravi changes the email on his Google account: the same Google id still finds the same account.
        MockHttpSession later = new MockHttpSession();
        signIn(later, sub, "ravi.new@gmail.example").andExpect(status().isFound());
        me(later).andExpect(jsonPath("$.email").value(email));
    }

    @Test
    void aGoogleAccountWithNoTaskloomAccountIs403AndANewSignInIsNotStarted() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        signIn(browser, newSub(), "stranger@gmail.example").andExpect(status().isForbidden())
                .andExpect(jsonPath("$.title").value("No Taskloom account"));
        me(browser).andExpect(status().isUnauthorized());
    }

    @Test
    void meWithoutSigningInIs401AndAnUnknownProviderIs404() throws Exception {
        mvc.perform(get("/me")).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Sign in with Google at /oauth2/authorization/google."));
        mvc.perform(get("/oauth2/authorization/github")).andExpect(status().isNotFound());   // only Google is set up; Spring's default is a 500
    }
}
