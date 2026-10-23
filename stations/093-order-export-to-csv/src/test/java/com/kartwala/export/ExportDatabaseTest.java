package com.kartwala.export;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class ExportDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    @Test
    void orderAndExportRulesHoldWithoutJava() {
        violates("orders_ref_once_per_seller", "INSERT INTO orders (seller_id, order_ref, placed_at, product_name, quantity, amount_paise, buyer_city, status) VALUES (1, 'KW-1001', now(), 'x', 1, 100, 'Pune', 'PLACED')");
        violates("orders_quantity_positive", "UPDATE orders SET quantity = 0 WHERE id = 1");
        violates("orders_amount_positive", "UPDATE orders SET amount_paise = 0 WHERE id = 1");
        violates("orders_status", "UPDATE orders SET status = 'LOST' WHERE id = 1");
        violates("export_log_range", "INSERT INTO export_log (seller_id, from_date, to_date) VALUES (1, '2025-01-01', '2026-01-02')");
        violates("export_log_range", "INSERT INTO export_log (seller_id, from_date, to_date) VALUES (1, '2026-02-01', '2026-01-01')");
    }

    @Test
    void anExportThatCannotBeLoggedDoesNotStart() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_log() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'audit store down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_log BEFORE INSERT ON export_log FOR EACH ROW EXECUTE FUNCTION refuse_log()""").update();
        try {
            assertThatThrownBy(() -> export("neha.store", "2026-01-01", "2026-12-31")).hasRootCauseMessage("ERROR: audit store down\n  Where: PL/pgSQL function refuse_log() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_log ON export_log; DROP FUNCTION refuse_log()").update();
        }
        assertThat(jdbc.sql("SELECT count(*) FROM export_log").query(Long.class).single()).isZero();
    }
}
