package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;

import java.time.Clock;
import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** The real schedule and clock: nobody calls the dispatcher, and the payment still arrives. */
@SpringBootTest(properties = "paysetu.webhooks.dispatcher.poll=100ms")
@Import(PostgresTestConfig.class)
class ScheduledDeliveryTest {

    @Autowired
    Webhooks webhooks;

    @Test
    void theScheduledDispatcherSendsWithoutBeingAsked() throws Exception {
        try (TestMerchant merchant = new TestMerchant(Clock.systemUTC())) {
            String secret = webhooks.register(1, merchant.url()).secret();
            webhooks.paymentCaptured(1, "PAY-1001", 49900);
            await().atMost(Duration.ofSeconds(5)).until(() -> merchant.received().size() == 1);
            assertThat(merchant.received().getFirst().verifiedWith(secret)).isTrue();
        }
    }
}
