package com.mapwise.geocode;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RateLimitTest extends ApiTest {

    @Test
    void aBurstOfTenThenOneEveryFifthOfASecond() throws Exception {
        for (int i = 0; i < 10; i++) {
            assertThat(answer(ZOOMKART)).isEqualTo(200);
        }
        geocode(ZOOMKART, "MG Road, Bengaluru").andExpect(status().isTooManyRequests()).andExpect(header().string("Retry-After", "1"))
                .andExpect(jsonPath("$.detail").value("Rate limit: 5 requests a second, bursts of up to 10."));
        CLOCK.advance(Duration.ofMillis(200));   // one token back
        assertThat(List.of(answer(ZOOMKART), answer(ZOOMKART))).containsExactly(200, 429);
        CLOCK.advance(Duration.ofSeconds(60));   // a quiet minute fills the bucket, but only to its size
        assertThat(IntStream.range(0, 11).map(i -> {
            try {
                return answer(ZOOMKART);
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        }).filter(s -> s == 200).count()).isEqualTo(10);
    }

    @Test
    void theDailyQuotaStopsAtTwentyAndComesBackAtMidnightUtc() throws Exception {
        for (int i = 0; i < 10; i++) {
            answer(CHALO);   // a burst: 3 answered, 7 refused, and only the 3 count against the day
        }
        for (int i = 0; i < 17; i++) {
            CLOCK.advance(Duration.ofSeconds(1));
            assertThat(answer(CHALO)).as("request %d of the day", i + 4).isEqualTo(200);
        }
        CLOCK.advance(Duration.ofSeconds(1));
        Instant midnight = LocalDate.ofInstant(CLOCK.instant(), ZoneOffset.UTC).plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant();
        geocode(CHALO, "MG Road, Bengaluru").andExpect(status().isTooManyRequests())
                .andExpect(header().string("Retry-After", String.valueOf(Duration.between(CLOCK.instant(), midnight).toSeconds())))
                .andExpect(jsonPath("$.detail").value("Daily quota of 20 requests used. It resets at 00:00 UTC."));
        CLOCK.set(midnight);
        assertThat(answer(CHALO)).isEqualTo(200);
    }

    @Test
    void aHundredRequestsAtOnceGetExactlyTheBurst() throws Exception {
        CountDownLatch start = new CountDownLatch(1);
        Callable<Integer> request = () -> {
            start.await();
            return answer(ZOOMKART);
        };
        List<Future<Integer>> answers;
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            answers = IntStream.range(0, 100).mapToObj(i -> threads.submit(request)).toList();
            start.countDown();
        }
        assertThat(answers).extracting(Future::resultNow).filteredOn(s -> s == 200).hasSize(10);
        assertThat(answers).extracting(Future::resultNow).filteredOn(s -> s == 429).hasSize(90);
    }

    /** The bucket alone, harder: 8 threads, 20,000 takes, a bucket of 5,000. Not one token more may be handed out. */
    @Test
    void parallelTakesNeverHandOutMoreThanTheBucketHolds() throws Exception {
        RateLimiter limiter = new RateLimiter(CLOCK);
        Partners.Partner plan = new Partners.Partner(9, "load test", "-", 1, 5_000, 1_000_000, false);
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Long>> threads;
        try (var pool = Executors.newFixedThreadPool(8)) {
            threads = IntStream.range(0, 8).mapToObj(t -> pool.submit(() -> {
                start.await();
                long allowed = 0;
                for (int i = 0; i < 2_500; i++) {
                    allowed += limiter.take(plan).allowed() ? 1 : 0;
                }
                return allowed;
            })).toList();
            start.countDown();
        }
        assertThat(threads.stream().mapToLong(Future::resultNow).sum()).isEqualTo(5_000);
        assertThat(limiter.usage(plan).usedToday()).isEqualTo(5_000);
    }
}
