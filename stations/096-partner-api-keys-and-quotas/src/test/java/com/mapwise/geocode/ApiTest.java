package com.mapwise.geocode;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicInteger;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Shared setup: the whole app with a clock that stands still unless a test moves it. Each test starts at 10:00 UTC
 * on a new day, so every bucket is full and every daily count is zero, without any reset hook in the app.
 */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final String ZOOMKART = "mw_demo_zoomkart_7Qp2Lx9V";   // 5 a second, bursts of 10
    static final String CHALO = "mw_demo_chalo_K3vN8sT1";         // trial: 1 a second, bursts of 3, 20 a day
    static final String OLD_MAPS = "mw_demo_oldmaps_P0dW5yZr";    // suspended
    static final TestClock CLOCK = new TestClock(Instant.parse("2026-10-23T10:00:00Z"));
    private static final AtomicInteger day = new AtomicInteger();

    @Autowired
    MockMvc mvc;

    @TestBean
    Clock clock;

    static Clock clock() {
        return CLOCK;
    }

    @BeforeEach
    void aFreshDay() {
        CLOCK.set(Instant.parse("2026-10-23T10:00:00Z").plus(Duration.ofDays(day.addAndGet(2))));   // two days on: a test may run into the next one
    }

    ResultActions geocode(String key, String address) throws Exception {
        var request = get("/geocode").param("address", address);
        return mvc.perform(key == null ? request : request.header("X-Api-Key", key));
    }

    int answer(String key) throws Exception {
        return geocode(key, "MG Road, Bengaluru").andReturn().getResponse().getStatus();
    }
}
