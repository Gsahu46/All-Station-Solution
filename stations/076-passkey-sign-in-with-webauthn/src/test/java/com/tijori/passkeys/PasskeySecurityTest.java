package com.tijori.passkeys;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PasskeySecurityTest extends ApiTest {

    @Test
    void noTokenIs401() throws Exception {
        mvc.perform(get("/accounts/me")).andExpect(status().isUnauthorized()).andExpect(header().string("WWW-Authenticate", "Bearer"));
        send("/webauthn/registration/options", null, "{}").andExpect(status().isUnauthorized());
    }

    @Test
    void addingAPasskeyNeedsASignInFromTheLastFiveMinutes() throws Exception {
        String token = codeToken("zoya");
        later(Duration.ofMinutes(5));   // the token itself is still valid for 10 minutes
        send("/webauthn/registration/options", token, "{}").andExpect(status().isForbidden()).andExpect(jsonPath("$.detail").value("Sign in again to add a passkey"));
        me(token).andExpect(status().isOk());
    }

    @Test
    void aChallengeIssuedToAnotherCustomerCannotAddAPasskeyHere() throws Exception {
        String dev = codeToken("dev");
        String zoya = codeToken("zoya");
        ObjectNode madeOnDevsChallenge = new Device().create(registrationOptions(dev));
        register(zoya, "Not mine", madeOnDevsChallenge).andExpect(status().isBadRequest());
        assertThat(jdbc.sql("SELECT count(*) FROM passkeys").query(Long.class).single()).isZero();
    }

    @Test
    void aPasskeyCannotSayItBelongsToAnotherCustomer() throws Exception {
        Device devsPhone = passkeyFor("dev");
        ObjectNode signIn = devsPhone.get(authenticationOptions());
        byte[] zoyasHandle = jdbc.sql("SELECT user_handle FROM customers WHERE email = 'zoya@example.com'").query(byte[].class).single();
        ((ObjectNode) signIn.path("response")).put("userHandle", Base64.getUrlEncoder().withoutPadding().encodeToString(zoyasHandle));
        authenticate(signIn).andExpect(status().isUnauthorized());   // the signature does not cover userHandle: the server must compare it
    }

    @Test
    void aChallengeExpiresAfterFiveMinutes() throws Exception {
        Device phone = passkeyFor("zoya");
        JsonNode options = authenticationOptions();
        later(Duration.ofMinutes(5).plusSeconds(1));
        authenticate(phone.get(options)).andExpect(status().isUnauthorized());
    }

    @Test
    void aCounterThatGoesBackwardsLooksLikeACloneAndIsRefused() throws Exception {
        Device key = passkeyOn(Device.securityKey(), "zoya");
        authenticate(key.get(authenticationOptions())).andExpect(status().isOk());
        jdbc.sql("UPDATE passkeys SET sign_count = 1000").update();   // as if the real key had signed 1000 times: this one is a copy
        authenticate(key.get(authenticationOptions())).andExpect(status().isUnauthorized());
    }

    @Test
    void aCodeWorksOnceAndOnlyNearItsTime() throws Exception {
        String code = currentCode();
        codeSignIn("zoya@example.com", "zoya-demo-pass", code).andExpect(status().isOk());
        codeSignIn("zoya@example.com", "zoya-demo-pass", code).andExpect(status().isUnauthorized());     // already used
        later(Duration.ofSeconds(30));
        String previous = Totp.code(TOTP_SECRET, Totp.step(CLOCK.now.getEpochSecond()) - 1);
        assertThat(previous).isEqualTo(code);
        String now = currentCode();
        later(Duration.ofSeconds(30));
        codeSignIn("zoya@example.com", "zoya-demo-pass", now).andExpect(status().isOk());              // one step late: a slow phone clock
        String old = Totp.code(TOTP_SECRET, Totp.step(CLOCK.now.getEpochSecond()) - 2);
        codeSignIn("dev@example.com", "dev-demo-pass", old).andExpect(status().isUnauthorized());     // two steps late: no
    }

    @Test
    void tenParallelSignInsWithOneCodeGiveOneToken() throws Exception {
        String code = currentCode();
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> results = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10; i++) {
                results.add(threads.submit(() -> {
                    start.await();
                    return codeSignIn("zoya@example.com", "zoya-demo-pass", code).andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        List<Integer> statuses = new ArrayList<>();
        for (Future<Integer> f : results) {
            statuses.add(f.get());
        }
        assertThat(statuses).containsOnly(200, 401).filteredOn(s -> s == 200).hasSize(1);
    }

    @Test
    void oddAnswersAre400Or401NeverAnError() throws Exception {
        passkeyFor("zoya");
        for (String body : new String[]{"{}", "{\"rawId\":\"!!\",\"response\":{}}", "{\"rawId\":\"' OR '1'='1\",\"response\":{\"clientDataJSON\":\"x\"}}",
                "{\"rawId\":\"" + "a".repeat(5000) + "\",\"response\":{\"clientDataJSON\":\"" + "b".repeat(5000) + "\"}}", "[]"}) {
            int s = send("/webauthn/authentication", null, body).andReturn().getResponse().getStatus();
            assertThat(s).as(body.length() > 60 ? body.substring(0, 60) : body).isIn(400, 401);
        }
        send("/webauthn/authentication", null, "not json").andExpect(status().isBadRequest());
    }
}
