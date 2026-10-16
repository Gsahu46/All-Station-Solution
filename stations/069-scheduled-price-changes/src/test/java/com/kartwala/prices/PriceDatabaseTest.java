package com.kartwala.prices;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The schedule's rules as PostgreSQL enforces them, with plain SQL. */
class PriceDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    private void price(long product, int paise, String from, String to) {
        jdbc.sql("INSERT INTO prices (product_id, price_paise, valid_from, valid_to) VALUES (?, ?, CAST(? AS timestamptz), CAST(? AS timestamptz))")
                .params(product, paise, from, to).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> price(1, 49900, "2027-01-01 00:00+05:30", "2027-02-01 00:00+05:30")).isInstanceOf(DataAccessException.class)
                .hasMessageContaining("prices_no_overlap");   // product 1's base price is open-ended
        assertThatThrownBy(() -> price(9, 49900, "2027-01-01 00:00+05:30", null)).hasMessageContaining("prices_product_fk");
        assertThatThrownBy(() -> price(3, 0, "2025-01-01 00:00+05:30", "2025-02-01 00:00+05:30")).hasMessageContaining("prices_price_range");
        assertThatThrownBy(() -> price(3, 9900, "2025-02-01 00:00+05:30", "2025-01-01 00:00+05:30")).hasMessageContaining("prices_window_order");
    }

    @Test
    void aWindowMayStartExactlyWhereAnotherEnds() {
        price(3, 79900, "2025-01-01 00:00+05:30", "2026-01-01 00:00+05:30");   // ends where the first 2026 price begins: half-open, no overlap
        assertThat(jdbc.sql("SELECT count(*) FROM prices WHERE product_id = 3").query(Long.class).single()).isEqualTo(3);
    }

    @Test
    void aBatchWithOneOverlapAddsNothing() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            price(3, 79900, "2025-01-01 00:00+05:30", "2025-06-01 00:00+05:30");
            price(3, 69900, "2025-05-01 00:00+05:30", "2025-07-01 00:00+05:30");
        })).hasMessageContaining("prices_no_overlap");
        assertThat(jdbc.sql("SELECT count(*) FROM prices WHERE product_id = 3").query(Long.class).single()).isEqualTo(2);
    }
}
