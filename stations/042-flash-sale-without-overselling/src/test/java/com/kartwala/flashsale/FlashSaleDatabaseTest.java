package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DuplicateKeyException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, and the rollback that puts a phone back. */
class FlashSaleDatabaseTest extends ApiTest {

    @Test
    void namedConstraintsHoldWithoutJava() {
        openSale(1);
        assertThatThrownBy(() -> jdbc.sql("UPDATE flash_sales SET stock_left = -1 WHERE id = 10").update()).hasMessageContaining("flash_sales_stock_not_negative");
        assertThatThrownBy(() -> jdbc.sql("UPDATE flash_sales SET stock_left = 2 WHERE id = 10").update()).hasMessageContaining("flash_sales_stock_within_total");
        assertThatThrownBy(() -> jdbc.sql("UPDATE flash_sales SET ends_at = starts_at WHERE id = 10").update()).hasMessageContaining("flash_sales_window_order");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO purchases (sale_id, customer_id, price_paise) VALUES (99, 'C-000001', 1)").update())
                .hasMessageContaining("purchases_sale_fk");
        jdbc.sql("INSERT INTO purchases (sale_id, customer_id, price_paise) VALUES (10, 'C-000001', 1)").update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO purchases (sale_id, customer_id, price_paise) VALUES (10, 'C-000001', 1)").update())
                .hasMessageContaining("purchases_one_per_customer");
    }

    @Test
    void aSecondPurchaseByTheSameCustomerPutsThePhoneBack() {
        openSale(3);
        store.buy(10, "C-000001");
        assertThat(stockLeft(10)).isEqualTo(2);
        assertThatThrownBy(() -> store.buy(10, "C-000001")).isInstanceOf(DuplicateKeyException.class);
        assertThat(stockLeft(10)).isEqualTo(2);   // the UPDATE ran, then the INSERT failed: both rolled back
    }

    @Test
    void zeroRowsAffectedMeansNothingWasTaken() {
        openSale(1);
        assertThat(store.buy(10, "C-000001")).isPresent();
        assertThat(store.buy(10, "C-000002")).isEmpty();
        assertThat(purchases(10)).isEqualTo(1);
    }
}
