package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class WebhookSecurityTest extends ApiTest {

    @Test
    void withoutASignInIt401sAndAnotherMerchantsWebhooksAre403() throws Exception {
        String body = "{\"url\":\"https://ravi-kirana.example/hooks\"}";
        mvc.perform(post("/merchants/1/webhook-endpoints").contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isUnauthorized());
        mvc.perform(post("/merchants/1/webhook-endpoints").with(httpBasic("ravi", "wrong")).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isUnauthorized());
        mvc.perform(get("/webhook-deliveries")).andExpect(status().isUnauthorized());
        mvc.perform(get("/webhook-deliveries/1")).andExpect(status().isUnauthorized());
        mvc.perform(post("/merchants/1/test-events").contentType(MediaType.APPLICATION_JSON).content("{\"paymentRef\":\"PAY-1\",\"amountPaise\":1}"))
                .andExpect(status().isUnauthorized());

        // Ravi points Meena's payments at his own server, or invents a payment for her: both refused.
        registerEndpoint("ravi", 2, "https://ravi-kirana.example/hooks").andExpect(status().isForbidden());
        testEvent("ravi", 2, "PAY-1001", 49900).andExpect(status().isForbidden());
        assertThat(jdbc.sql("SELECT count(*) FROM webhook_endpoints").query(Long.class).single()).isZero();
    }

    @Test
    void aMerchantSeesOnlyTheirOwnDeliveries() throws Exception {
        try (TestMerchant meenasServer = new TestMerchant(CLOCK)) {
            secretFor("meena", 2, meenasServer.url());
            testEvent("meena", 2, "PAY-2001", 120000).andExpect(status().isAccepted());
            deliveries("meena", "").andExpect(jsonPath("$.length()").value(1));
            deliveries("ravi", "").andExpect(jsonPath("$.length()").value(0));
            deliveries("ravi", "?merchantId=2").andExpect(jsonPath("$.length()").value(0));   // the merchant comes from the sign-in
            mvc.perform(get("/webhook-deliveries/1").with(httpBasic("ravi", password("ravi")))).andExpect(status().isNotFound());
            mvc.perform(get("/webhook-deliveries/1").with(httpBasic("meena", password("meena")))).andExpect(status().isOk());
        }
    }

    @Test
    void maliciousInputIsRefused() throws Exception {
        for (String url : new String[]{"file:///etc/passwd", "javascript:alert(1)", "http://ravi:secret@ravi-kirana.example/hooks",
                "https://ravi-kirana.example/hooks#x", "https://ravi-kirana.example/a\r\nX-Injected: 1", "http:///no-host",
                "https://ravi-kirana.example/" + "a".repeat(2000)}) {
            registerEndpoint("ravi", 1, url).andExpect(status().isBadRequest());
        }
        for (String ref : new String[]{"PAY-1'; DROP TABLE events;--", "../../etc", "PAY 1", "P", "x".repeat(41)}) {
            testEvent("ravi", 1, ref, 100).andExpect(status().isBadRequest());
        }
        testEvent("ravi", 1, "PAY-1001", 0).andExpect(status().isBadRequest());
        testEvent("ravi", 1, "PAY-1001", -100).andExpect(status().isBadRequest());
        mvc.perform(post("/merchants/1/test-events").with(httpBasic("ravi", password("ravi"))).contentType(MediaType.APPLICATION_JSON)
                .content("{\"paymentRef\":\"PAY-1001\"}")).andExpect(status().isBadRequest());   // no amount
        mvc.perform(get("/webhook-deliveries/1 OR 1=1").with(httpBasic("ravi", password("ravi")))).andExpect(status().isBadRequest());
        assertThat(jdbc.sql("SELECT count(*) FROM webhook_endpoints").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT count(*) FROM events").query(Long.class).single()).isZero();
    }

    @Test
    void aForgedTamperedOrReplayedRequestFailsVerification() {
        String secret = WebhookSignature.newSecret();
        String body = "{\"type\":\"payment.captured\",\"data\":{\"paymentRef\":\"PAY-1001\",\"amountPaise\":49900}}";
        long ts = T0.getEpochSecond();
        String signature = WebhookSignature.sign(secret, "evt-1", ts, body);

        assertThat(WebhookSignature.verify(secret, "evt-1", String.valueOf(ts), signature, body, T0)).isTrue();
        assertThat(WebhookSignature.verify(secret, "evt-1", String.valueOf(ts), signature, body.replace("49900", "4990000"), T0)).isFalse();
        assertThat(WebhookSignature.verify(WebhookSignature.newSecret(), "evt-1", String.valueOf(ts), signature, body, T0)).isFalse();
        assertThat(WebhookSignature.verify(secret, "evt-2", String.valueOf(ts), signature, body, T0)).isFalse();
        // The same signed request sent again six minutes later: refused, the timestamp is part of what is signed.
        assertThat(WebhookSignature.verify(secret, "evt-1", String.valueOf(ts), signature, body, T0.plusSeconds(360))).isFalse();
        assertThat(WebhookSignature.verify(secret, "evt-1", String.valueOf(ts + 360), signature, body, T0.plusSeconds(360))).isFalse();
        assertThat(WebhookSignature.verify(secret, "evt-1", String.valueOf(ts), "v1,not-base64!", body, T0)).isFalse();
        assertThat(WebhookSignature.verify(secret, "evt-1", String.valueOf(ts), null, body, T0)).isFalse();
        assertThat(WebhookSignature.verify(secret, "evt-1", "soon", signature, body, T0)).isFalse();
        assertThat(WebhookSignature.verify(secret, "evt-1", String.valueOf(ts), "v0,abc " + signature, body, T0)).isTrue();   // any one that matches
    }
}
