package com.taskloom.signin;

import com.nimbusds.jwt.JWTClaimsSet;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.Map;
import java.util.UUID;
import java.util.function.UnaryOperator;
import java.util.stream.Collectors;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Shared setup: the whole app with its security, pointed at a fake Google on a local port. A sign-in in a test goes
 * through every real step: the redirect to "Google", the code coming back, the token request over HTTP, and Spring's
 * checks of the ID token.
 */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final FakeGoogle GOOGLE = new FakeGoogle();
    static final String CLIENT_ID = "taskloom-demo.apps.googleusercontent.com";

    @DynamicPropertySource
    static void pointAtFakeGoogle(DynamicPropertyRegistry registry) {
        registry.add("spring.security.oauth2.client.provider.google.issuer-uri", () -> GOOGLE.issuer);
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    Accounts accounts;

    /** Step 1: the browser asks Taskloom to start; Taskloom redirects to Google. Returns the redirect's query. */
    Map<String, String> start(MockHttpSession browser) throws Exception {
        String location = mvc.perform(get("/oauth2/authorization/google").session(browser)).andReturn().getResponse().getHeader("Location");
        return UriComponentsBuilder.fromUriString(location).build().getQueryParams().toSingleValueMap().entrySet().stream()
                .collect(Collectors.toMap(Map.Entry::getKey, e -> URLDecoder.decode(e.getValue(), StandardCharsets.UTF_8)));
    }

    /** The claims Google puts in an ID token for this app; tests change one at a time. */
    static JWTClaimsSet.Builder googleClaims(String sub, String email, String nonce) {
        Instant now = Instant.now();
        return new JWTClaimsSet.Builder().issuer(GOOGLE.issuer).subject(sub).audience(CLIENT_ID)
                .issueTime(Date.from(now)).expirationTime(Date.from(now.plus(Duration.ofHours(1))))
                .claim("nonce", nonce).claim("email", email).claim("email_verified", true).claim("name", "Test person");
    }

    /** Step 3: Google redirects the browser back with a code and the state. */
    ResultActions callback(MockHttpSession browser, String code, String state) throws Exception {
        return mvc.perform(get("/login/oauth2/code/google").param("code", code).param("state", state).session(browser));
    }

    /** The whole sign-in, with the ID token Google would hand out (changed by the test if it likes). */
    ResultActions signIn(MockHttpSession browser, String sub, String email, UnaryOperator<JWTClaimsSet.Builder> change) throws Exception {
        Map<String, String> request = start(browser);
        String code = "code-" + UUID.randomUUID();
        GOOGLE.idTokens.put(code, GOOGLE.sign(change.apply(googleClaims(sub, email, request.get("nonce"))).build()));
        return callback(browser, code, request.get("state"));
    }

    ResultActions signIn(MockHttpSession browser, String sub, String email) throws Exception {
        return signIn(browser, sub, email, c -> c);
    }

    /** A new invited member for this test only, so tests never share an invitation. */
    String invite(String name) {
        String email = name.toLowerCase(java.util.Locale.ROOT) + "-" + UUID.randomUUID().toString().substring(0, 8) + "@acme.example";
        accounts.invite(email, name, "Acme");
        return email;
    }

    static String newSub() {
        return Long.toString(Math.abs(UUID.randomUUID().getMostSignificantBits()));
    }

    ResultActions me(MockHttpSession browser) throws Exception {
        return mvc.perform(get("/me").session(browser));
    }
}
