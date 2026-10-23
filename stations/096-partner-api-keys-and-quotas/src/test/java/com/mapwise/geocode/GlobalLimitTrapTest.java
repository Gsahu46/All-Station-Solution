package com.mapwise.geocode;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Zoomkart's bug sends 50 requests at once. Written first. */
class GlobalLimitTrapTest extends ApiTest {

    @Test
    void oneGlobalLimitLetsOnePartnersBugSlowEveryone() {
        // The old way: one bucket for the whole API, whoever is asking.
        RateLimiter old = new RateLimiter(CLOCK);
        Partners.Partner everyone = new Partners.Partner(0, "the whole API", "-", 5, 10, 100_000, false);
        for (int i = 0; i < 50; i++) {
            old.take(everyone);   // Zoomkart's runaway loop
        }
        assertThat(old.take(everyone).allowed()).isFalse();   // Chalo's one request: refused for Zoomkart's bug
    }

    @Test
    void eachPartnerHasItsOwnBucket() throws Exception {
        List<Integer> zoomkart = new ArrayList<>();
        for (int i = 0; i < 50; i++) {
            zoomkart.add(answer(ZOOMKART));
        }
        assertThat(zoomkart).containsOnly(200, 429);
        assertThat(zoomkart.stream().filter(s -> s == 200)).hasSize(10);   // its burst, then 429 for its own bug
        assertThat(answer(CHALO)).isEqualTo(200);   // Chalo is not affected
    }
}
