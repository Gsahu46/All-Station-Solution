package com.seatsure.holds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old booking code locked the seat, called the payment provider while still holding the lock,
 * and waited for locks with no time limit. When the provider was slow, every other customer for that seat waited
 * with it, and requests piled up. Each test plays the old behaviour against the real database, then the API.
 */
class LockAcrossPaymentTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate tx;

    @Test
    void aLockHeldAcrossASlowPaymentMadeEveryoneElseWait() throws Exception {
        CountDownLatch locked = new CountDownLatch(1);
        // The old confirm: lock F12, then "call the provider" (3 seconds) inside the same transaction.
        CompletableFuture<Void> oldConfirm = CompletableFuture.runAsync(() -> tx.executeWithoutResult(s -> {
            jdbc.sql("SELECT seat_no FROM seats WHERE show_id = 1 AND seat_no = 'F12' FOR UPDATE").query(String.class).single();
            locked.countDown();
            try {
                Thread.sleep(3000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }));
        locked.await();
        long started = System.nanoTime();
        // The old code had no lock timeout. The API has one: it answers within about half a second, and says why.
        hold("arjun", "F12").andExpect(status().isServiceUnavailable()).andExpect(header().string("Retry-After", "1"));
        assertThat(Duration.ofNanos(System.nanoTime() - started)).isLessThan(Duration.ofSeconds(2));
        oldConfirm.join();
        hold("arjun", "F12").andExpect(status().isCreated());   // and once the lock is gone, the seat can be held
    }

    @Test
    void theApiPaysWithoutHoldingAnyLock() throws Exception {
        String meera = holdId("meera", "F12");
        payments.delay = Duration.ofSeconds(2);   // a slow provider
        CompletableFuture<Integer> paying = CompletableFuture.supplyAsync(() -> {
            try {
                return confirm(meera).andReturn().getResponse().getStatus();
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        });
        Thread.sleep(300);   // meera's confirm is now waiting on the provider
        long started = System.nanoTime();
        hold("arjun", "F12").andExpect(status().isConflict());   // held by meera: told at once, no waiting
        hold("arjun", "F13").andExpect(status().isCreated());    // and the row next to it is not blocked at all
        assertThat(Duration.ofNanos(System.nanoTime() - started)).isLessThan(Duration.ofMillis(500));
        assertThat(paying.join()).isEqualTo(200);
    }
}
