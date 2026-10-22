package com.kartwala.prices;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class PriceDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    @Test
    void rulesHoldWithoutJava() {
        violates("products_price_positive", "UPDATE products SET price_paise = 0 WHERE id = 1");
        violates("products_name_length", "UPDATE products SET name = '' WHERE id = 1");
        violates("revisions_changed_by_shape", "INSERT INTO revisions (changed_at_ms, changed_by) VALUES (0, 'Neha Store, probably')");
        violates("products_aud_revtype", "INSERT INTO products_aud (id, rev, revtype) VALUES (1, 1, 7)");
        violates("products_aud_pk", "INSERT INTO products_aud (id, rev, revtype) VALUES (1, 1, 1)");
    }

    /** One change, two rows: a revision and the product as it now is. That is how fast history grows. */
    @Test
    void eachChangeAddsOneRevisionAndOneHistoryRow() throws Exception {
        setPrice("neha.store", 1, 549900);
        setPrice("neha.store", 2, 999900);
        assertThat(jdbc.sql("SELECT count(*) FROM revisions").query(Long.class).single()).isEqualTo(3);     // the import and two changes
        assertThat(jdbc.sql("SELECT count(*) FROM products_aud").query(Long.class).single()).isEqualTo(5);  // three imported, two changed
    }

    /** The price and its history are one transaction: if the history cannot be written, the price does not change. */
    @Test
    void aPriceWhoseHistoryFailsDoesNotChange() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_history() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'history is down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_history BEFORE INSERT ON products_aud FOR EACH ROW EXECUTE FUNCTION refuse_history()""").update();
        try {
            assertThatThrownBy(() -> setPrice("neha.store", 1, 549900)).hasRootCauseMessage("ERROR: history is down\n  Where: PL/pgSQL function refuse_history() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_history ON products_aud; DROP FUNCTION refuse_history()").update();
        }
        assertThat(jdbc.sql("SELECT price_paise FROM products WHERE id = 1").query(Long.class).single()).isEqualTo(5499900);
        assertThat(jdbc.sql("SELECT count(*) FROM revisions").query(Long.class).single()).isEqualTo(1);
    }
}
