package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PaymentReplayTest extends ApiTest {

    @Test
    void theSameOrderTwiceIsOnePaymentAndOneCharge() throws Exception {
        String first = pay("ORD-2001", 50000).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        String again = pay("ord-2001", 50000).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        assertThat(again).isEqualTo(first);
        assertThat(alpha.charges).hasSize(1);
        assertThat(column("SELECT count(*)::text FROM payments")).isEqualTo("1");
    }

    @Test
    void aDeclinedOrderRetriedIsTheSameDeclineAndADifferentAmountIs409() throws Exception {
        pay("ORD-2002", 50051).andExpect(status().isPaymentRequired());
        pay("ORD-2002", 50051).andExpect(status().isPaymentRequired()).andExpect(jsonPath("$.declineReason").value("INSUFFICIENT_FUNDS"));
        pay("ORD-2002", 50000).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Order ORD-2002 was already sent with a different amount"));
        assertThat(alpha.charges).hasSize(1);
    }

    @Test
    void anUnknownPaymentRetriedIsNotSentAgain() throws Exception {
        alpha.fault = AlphaApi.Fault.TIMEOUT_AFTER_CHARGING;
        alpha.lookupDown = true;
        pay("ORD-2003", 50000).andExpect(status().isAccepted());
        alpha.reset();
        pay("ORD-2003", 50000).andExpect(status().isAccepted()).andExpect(jsonPath("$.status").value("unknown"));
        assertThat(alpha.charges).isEmpty();   // reset cleared the simulation; the API did not charge again
        assertThat(beta.authorisations).isEmpty();
    }

    /** Writing a payment takes 200 ms here (a trigger), so all five look for the order before the first one is written. */
    @Test
    void fiveRetriesAtTheSameMomentAreOneCharge() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION slow_payments() RETURNS trigger AS $$ BEGIN PERFORM pg_sleep(0.2); RETURN NEW; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER slow_payments BEFORE INSERT ON payments FOR EACH ROW EXECUTE FUNCTION slow_payments()""").update();
        try {
            fiveAtOnce();
        } finally {
            jdbc.sql("DROP TRIGGER slow_payments ON payments; DROP FUNCTION slow_payments()").update();
        }
        assertThat(alpha.charges).hasSize(1);
        assertThat(column("SELECT count(*)::text FROM payments")).isEqualTo("1");
    }

    void fiveAtOnce() throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> futures = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 5; i++) {
                futures.add(threads.submit(() -> {
                    start.await();
                    return pay("ORD-2004", 50000).andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        for (Future<Integer> f : futures) {
            assertThat(f.get()).isIn(201, 202);   // 202: asked while the first was still with the provider
        }
    }
}
