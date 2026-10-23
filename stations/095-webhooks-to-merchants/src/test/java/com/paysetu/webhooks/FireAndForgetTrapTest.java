package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The merchant's server is down for five minutes. Written first. */
class FireAndForgetTrapTest extends ApiTest {

    /** The old way: post it right after the payment and never look at the answer. No signature, no retry, no log. */
    static CompletableFuture<HttpResponse<Void>> oldWay(String url, String body) {
        return HttpClient.newHttpClient().sendAsync(HttpRequest.newBuilder(URI.create(url)).header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body)).build(), HttpResponse.BodyHandlers.discarding());
    }

    @Test
    void theOldWayLosesThePaymentWhileTheMerchantIsDown() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.answer = () -> 503;   // down for maintenance
            oldWay(merchant.url(), "{\"type\":\"payment.captured\",\"data\":{\"paymentRef\":\"PAY-1001\",\"amountPaise\":49900}}").join();
            merchant.answer = () -> 200;   // back after five minutes
            CLOCK.advance(Duration.ofMinutes(10));
            dispatcher.dispatchDue();

            assertThat(merchant.received()).hasSize(1);   // the one try, answered 503, and never again
            assertThat(merchant.received().getFirst().signature()).isNull();   // and anyone could have sent it
            assertThat(jdbc.sql("SELECT count(*) FROM deliveries").query(Long.class).single()).isZero();   // nothing to retry from
        }
    }

    @Test
    void theApiKeepsThePaymentUntilTheMerchantIsBack() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.answer = () -> CLOCK.instant().isBefore(T0.plus(Duration.ofMinutes(5))) ? 503 : 200;
            String secret = secretFor("ravi", 1, merchant.url());
            testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());

            for (int second = 0; second <= 600; second += 10) {   // ten minutes, a dispatcher round every 10 s
                CLOCK.set(T0.plusSeconds(second));
                dispatcher.dispatchDue();
            }

            // Tried at once, then after 30 s, 1 min, 2 min and 4 min: the fifth try, 7.5 minutes in, is answered 200.
            assertThat(merchant.received()).extracting(r -> Duration.between(T0, r.at()).toSeconds()).containsExactly(0L, 30L, 90L, 210L, 450L);
            assertThat(merchant.received()).allMatch(r -> r.verifiedWith(secret));   // each try signed afresh
            assertThat(merchant.received()).extracting(TestMerchant.Received::id).containsOnly(merchant.received().getFirst().id());   // one id: the merchant can drop repeats
            var log = onlyDelivery("ravi");
            assertThat(log.at("/delivery/status").asString()).isEqualTo("DELIVERED");
            assertThat(log.at("/delivery/deliveredAt").asString()).isEqualTo("2026-10-23T10:07:30Z");
            assertThat(log.get("attempts")).extracting(a -> a.get("statusCode").asInt()).containsExactly(503, 503, 503, 503, 200);
        }
    }
}
