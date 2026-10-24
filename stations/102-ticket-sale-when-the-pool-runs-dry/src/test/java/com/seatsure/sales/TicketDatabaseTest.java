package com.seatsure.sales;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class TicketDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    @Test
    void saleAndOrderRulesHoldWithoutJava() {
        violates("sales_sold_range", "UPDATE sales SET sold = capacity + 1 WHERE id = 2");
        violates("sales_sold_range", "UPDATE sales SET sold = -1 WHERE id = 1");
        violates("sales_price_positive", "UPDATE sales SET price_paise = 0 WHERE id = 1");
        violates("orders_seats_range", "INSERT INTO orders (sale_id, buyer, seats, amount_paise, status) VALUES (1, 'x', 7, 100, 'PENDING_PAYMENT')");
        violates("orders_amount_positive", "INSERT INTO orders (sale_id, buyer, seats, amount_paise, status) VALUES (1, 'x', 1, 0, 'PENDING_PAYMENT')");
        violates("orders_status", "INSERT INTO orders (sale_id, buyer, seats, amount_paise, status) VALUES (1, 'x', 1, 100, 'SHIPPED')");
        violates("orders_paid_has_charge", "INSERT INTO orders (sale_id, buyer, seats, amount_paise, status) VALUES (1, 'x', 1, 100, 'PAID')");
    }

    @Test
    void anOrderThatCannotBeRecordedTakesNoSeats() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_order() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'orders table read-only'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_order BEFORE INSERT ON orders FOR EACH ROW EXECUTE FUNCTION refuse_order()""").update();
        try {
            assertThatThrownBy(() -> order(1, "Priya Nair", 2)).hasRootCauseMessage("ERROR: orders table read-only\n  Where: PL/pgSQL function refuse_order() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_order ON orders; DROP FUNCTION refuse_order()").update();
        }
        assertThat(sold(1)).isZero();
    }
}
