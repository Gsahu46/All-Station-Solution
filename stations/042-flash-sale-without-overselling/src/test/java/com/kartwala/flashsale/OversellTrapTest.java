package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/** The first test written for this station: 100 buyers at once for 5 phones, on the old code and on the new. */
class OversellTrapTest extends ApiTest {

    @Test
    void readCheckUpdateSellsMorePhonesThanThereAre() throws Exception {
        OldFlashSaleStore.createTables(jdbc, 5);
        AtomicInteger n = new AtomicInteger();
        together(100, () -> OldFlashSaleStore.buy(jdbc, customer(n.incrementAndGet())));
        long sold = jdbc.sql("SELECT count(*) FROM old_purchases").query(Long.class).single();
        int left = jdbc.sql("SELECT stock_left FROM old_flash_sales").query(Integer.class).single();
        assertThat(sold).isGreaterThan(5);         // more buyers than phones were told "yours"
        assertThat(left).isEqualTo(5 - sold);      // and the stock went below zero to match
    }

    @Test
    void oneConditionalUpdateSellsExactlyFive() throws Exception {
        openSale(5);
        AtomicInteger n = new AtomicInteger();
        together(100, () -> store.buy(10, customer(n.incrementAndGet())).isPresent());
        assertThat(purchases(10)).isEqualTo(5);
        assertThat(stockLeft(10)).isZero();
    }
}
