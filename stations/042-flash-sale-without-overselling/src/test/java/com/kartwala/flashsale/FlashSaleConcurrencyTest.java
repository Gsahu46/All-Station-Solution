package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/** The flash sale itself, through HTTP: every phone sold once, never more, one per customer. */
class FlashSaleConcurrencyTest extends ApiTest {

    @Test
    void fiveHundredBuyersForFiftyPhones() throws Exception {
        openSale(50);
        AtomicInteger n = new AtomicInteger();
        List<Integer> statuses = together(500, () -> buy(10, customer(n.incrementAndGet())).andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(50);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(450);
        assertThat(purchases(10)).isEqualTo(50);
        assertThat(stockLeft(10)).isZero();
    }

    @Test
    void oneCustomerTappingTwentyTimesGetsOnePhone() throws Exception {
        openSale(50);
        List<Integer> statuses = together(20, () -> buy(10, "C-000777").andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(purchases(10)).isEqualTo(1);
        assertThat(stockLeft(10)).isEqualTo(49);   // the 19 refused attempts put their phone back
    }
}
