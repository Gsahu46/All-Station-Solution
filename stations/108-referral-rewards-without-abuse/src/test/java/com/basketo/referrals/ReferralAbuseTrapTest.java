package com.basketo.referrals;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.basketo.referrals.TestWallet.WALLET;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** One phone, sixty new SIM cards: Karan refers "new customers" with his own code, sixty times. Written first. */
class ReferralAbuseTrapTest extends ApiTest {

    /**
     * The old way, on the old tables: a reward the moment someone signs up with a code, checked only against the phone
     * number. Each new SIM card is a new phone number.
     */
    @Test
    void theOldWayPaysAtSignUpForEveryNewPhoneNumber() {
        jdbc.sql("CREATE TEMP TABLE old_customers (phone TEXT PRIMARY KEY, device_id TEXT)").update();
        jdbc.sql("CREATE TEMP TABLE old_rewards (referrer TEXT, amount_paise BIGINT)").update();
        try {
            for (int i = 0; i < 60; i++) {
                String phone = "+9170000000" + String.format("%02d", i);
                if (jdbc.sql("SELECT count(*) FROM old_customers WHERE phone = ?").param(phone).query(Integer.class).single() == 0) {
                    jdbc.sql("INSERT INTO old_customers VALUES (?, 'device-of-one-person')").param(phone).update();
                    jdbc.sql("INSERT INTO old_rewards VALUES ('KARAN50', 10000)").update();
                }
            }
            long paid = jdbc.sql("SELECT sum(amount_paise) FROM old_rewards").query(Long.class).single();
            assertThat(paid).as("₹6,000 in rewards, and not one order").isEqualTo(600_000);
        } finally {
            jdbc.sql("DROP TABLE old_customers, old_rewards").update();
        }
    }

    @Test
    void theApiTakesOneReferralPerDeviceAndPaysOnlyForADeliveredOrder() throws Exception {
        List<Integer> statuses = atOnce(60, i -> signUp("KARAN50", "+9170000000" + String.format("%02d", i), "device-of-one-person")
                .andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 422).hasSize(59);
        assertThat(count("referrals")).isEqualTo(1);
        assertThat(count("rewards")).as("nothing paid at sign-up").isZero();

        long customer = jdbc.sql("SELECT referee_id FROM referrals").query(Long.class).single();
        order(9001, customer, 60_000, "DELIVERED").andExpect(status().isCreated());   // a real first order of ₹600
        long reward = jdbc.sql("SELECT id FROM rewards").query(Long.class).single();
        awaitDelivery(reward, "SENT");
        assertThat(WALLET.creditedTo(KARAN)).isEqualTo(10_000);
    }

    interface Work<T> {
        T call(int i) throws Exception;
    }

    /** n virtual threads, released together. */
    static <T> List<T> atOnce(int n, Work<T> work) throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        List<Future<T>> futures = new ArrayList<>();
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < n; i++) {
                int index = i;
                futures.add(pool.submit(() -> {
                    start.await();
                    return work.call(index);
                }));
            }
            start.countDown();
            List<T> out = new ArrayList<>();
            for (Future<T> f : futures) {
                out.add(f.get());
            }
            return out;
        }
    }
}
