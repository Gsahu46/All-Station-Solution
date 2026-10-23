package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class DuplicateDeliveryMessagingTest extends ApiTest {

    @Autowired
    PlatformTransactionManager transactions;

    @Test
    void twoServersDispatchingAtOnceSendEachDeliveryOnce() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            merchant.delayMillis = 50;   // long enough for the two rounds to overlap
            secretFor("ravi", 1, merchant.url());
            for (int i = 1; i <= 20; i++) {
                testEvent("ravi", 1, "PAY-" + (1000 + i), 100L * i).andExpect(status().isAccepted());
            }
            CountDownLatch start = new CountDownLatch(1);
            try (var servers = Executors.newVirtualThreadPerTaskExecutor()) {
                for (int s = 0; s < 2; s++) {
                    servers.submit(() -> {
                        start.await();
                        return dispatcher.dispatchDue();
                    });
                }
                start.countDown();
            }
            assertThat(merchant.received()).hasSize(20);
            assertThat(merchant.received()).extracting(TestMerchant.Received::id).doesNotHaveDuplicates();
            assertThat(jdbc.sql("SELECT count(*) FROM delivery_attempts").query(Long.class).single()).isEqualTo(20);
        }
    }

    @Test
    void aDeliveryAnotherRoundIsClaimingIsSkippedNotWaitedFor() throws Exception {
        try (TestMerchant merchant = new TestMerchant(CLOCK)) {
            secretFor("ravi", 1, merchant.url());
            testEvent("ravi", 1, "PAY-1001", 100).andExpect(status().isAccepted());
            testEvent("ravi", 1, "PAY-1002", 200).andExpect(status().isAccepted());
            try (var otherServer = Executors.newVirtualThreadPerTaskExecutor()) {
                new TransactionTemplate(transactions).executeWithoutResult(tx -> {
                    jdbc.sql("SELECT id FROM deliveries WHERE id = 1 FOR UPDATE").query(Long.class).single();   // another round, mid-claim
                    Future<Integer> round = otherServer.submit(dispatcher::dispatchDue);
                    assertThat(round).succeedsWithin(Duration.ofSeconds(5)).isEqualTo(1);   // took delivery 2 at once
                });
            }
            assertThat(merchant.received()).hasSize(1);
        }
    }
}
