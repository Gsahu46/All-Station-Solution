package com.tijori.otp;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/** Real parallel requests through the whole app: virtual threads released together by a latch. */
@Timeout(value = 60, unit = TimeUnit.SECONDS, threadMode = Timeout.ThreadMode.SEPARATE_THREAD)
class OtpConcurrencyTest extends ApiTest {

    /** Sends each (key, mobile) pair at the same instant and counts the answers by status. */
    Map<Integer, AtomicInteger> together(List<String[]> requests) throws Exception {
        Map<Integer, AtomicInteger> byStatus = new ConcurrentHashMap<>();
        CountDownLatch start = new CountDownLatch(1);
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (String[] r : requests) {
                threads.submit(() -> {
                    start.await();
                    int status = otp(r[0], r[1]).andReturn().getResponse().getStatus();
                    byStatus.computeIfAbsent(status, s -> new AtomicInteger()).incrementAndGet();
                    return null;
                });
            }
            start.countDown();
        }
        return byStatus;
    }

    @Test
    void twentyBotRequestsAtOnceGetThreeSms() throws Exception {
        List<String[]> bot = java.util.stream.IntStream.range(0, 20).mapToObj(i -> new String[]{"bot-key-" + i + "-xyz", "9876543210"}).toList();
        Map<Integer, AtomicInteger> byStatus = together(bot);
        assertThat(byStatus.get(202).get()).isEqualTo(3);
        assertThat(byStatus.get(429).get()).isEqualTo(17);
        assertThat(sms.sentTo("9876543210")).isEqualTo(3);
    }

    @Test
    void differentNumbersEachGetTheirOwnThree() throws Exception {
        List<String[]> mixed = new java.util.ArrayList<>();
        for (String mobile : new String[]{"9000000001", "9000000002", "9000000003"}) {
            for (int i = 0; i < 5; i++) {
                mixed.add(new String[]{"key-" + mobile + "-" + i, mobile});
            }
        }
        Map<Integer, AtomicInteger> byStatus = together(mixed);
        assertThat(byStatus.get(202).get()).isEqualTo(9);
        for (String mobile : new String[]{"9000000001", "9000000002", "9000000003"}) {
            assertThat(sms.sentTo(mobile)).isEqualTo(3);
        }
    }
}
