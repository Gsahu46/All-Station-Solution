package com.taskloom.signin;

import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpSession;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.redirectedUrl;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The home-made flow decoded the ID token and took its email: no signature, no issuer, no audience,
 * no expiry. Each test builds one token it believed, then sends the same token through the real sign-in.
 */
class UncheckedIdTokenTrapTest extends ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();

    /** The old check, as it was. */
    static String oldSignedInEmail(String idToken) {
        JsonNode payload = JSON.readTree(Base64.getUrlDecoder().decode(idToken.split("\\.")[1]));
        return payload.get("email").asString();
    }

    /** Sign in through the real flow, with Google's token endpoint handing out exactly this ID token. */
    org.springframework.test.web.servlet.ResultActions signInWith(MockHttpSession browser, java.util.function.Function<String, String> idTokenForNonce) throws Exception {
        var request = start(browser);
        String code = "code-" + java.util.UUID.randomUUID();
        GOOGLE.idTokens.put(code, idTokenForNonce.apply(request.get("nonce")));
        return callback(browser, code, request.get("state"));
    }

    @Test
    void aGoogleTokenMeantForAnotherAppIsRefused() throws Exception {
        // Really signed by Google, really asha: but issued to a photo app she signed in to, which now replays it.
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> {
            String token = GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", nonce).audience("photo-app.apps.googleusercontent.com").build());
            assertThat(oldSignedInEmail(token)).isEqualTo("asha@acme.example");   // the old flow: signed in as asha
            return token;
        }).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.title").value("Sign-in failed"));
        me(browser).andExpect(status().isUnauthorized());
    }

    @Test
    void aTokenFromAnotherIssuerIsRefused() throws Exception {
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> {
            String token = GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", nonce).issuer("https://accounts.evil.example").build());
            assertThat(oldSignedInEmail(token)).isEqualTo("asha@acme.example");
            return token;
        }).andExpect(status().isUnauthorized());
    }

    @Test
    void aTokenSignedWithSomeoneElsesKeyIsRefused() throws Exception {
        RSAKey attacker = new RSAKeyGenerator(2048).keyID("fake-google-1").generate();   // even the same key id
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> {
            String token = FakeGoogle.signWith(attacker, googleClaims("100000000000000000001", "asha@acme.example", nonce).build());
            assertThat(oldSignedInEmail(token)).isEqualTo("asha@acme.example");
            return token;
        }).andExpect(status().isUnauthorized());
    }

    @Test
    void anExpiredTokenIsRefused() throws Exception {
        Instant lastWeek = Instant.now().minus(Duration.ofDays(7));
        MockHttpSession browser = new MockHttpSession();
        signInWith(browser, nonce -> GOOGLE.sign(googleClaims("100000000000000000001", "asha@acme.example", nonce)
                .issueTime(Date.from(lastWeek)).expirationTime(Date.from(lastWeek.plus(Duration.ofHours(1)))).build()))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void theRightTokenSignsIn() throws Exception {
        // The control: the same claims, for this app, from Google, in time.
        MockHttpSession browser = new MockHttpSession();
        signIn(browser, "100000000000000000001", "asha@acme.example").andExpect(status().isFound()).andExpect(redirectedUrl("/me"));
        me(browser).andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Asha Rao"));
    }
}
