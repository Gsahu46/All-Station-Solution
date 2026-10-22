package com.paysetu.payments;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class PaymentDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    static final String PAID = "INSERT INTO payments (order_id, amount_paise, provider, status, provider_ref) VALUES ('ORD-9', 1000, 'sim-alpha', 'succeeded', 'ch_9')";

    @Test
    void oneOrderIsOnePaymentForEveryWriter() {
        jdbc.sql(PAID).update();
        violates("payments_order_once", PAID);
    }

    @Test
    void paymentRulesHoldWithoutJava() {
        jdbc.sql(PAID).update();
        violates("payments_refunds_within_amount", "UPDATE payments SET refunded_paise = 1001");
        violates("payments_refunds_within_amount", "UPDATE payments SET refunded_paise = -1");
        violates("payments_refunds_only_when_paid", "UPDATE payments SET refunded_paise = 10, status = 'unknown', provider_ref = NULL");
        violates("payments_succeeded_has_ref", "UPDATE payments SET provider_ref = NULL");
        violates("payments_declined_has_reason", "UPDATE payments SET status = 'declined', provider_ref = NULL");
        violates("payments_known_provider", "UPDATE payments SET provider = 'sim-omega'");
        violates("payments_status", "UPDATE payments SET status = 'charged'");
        violates("payments_order_shape", "UPDATE payments SET order_id = 'ord-9'");
        violates("payments_amount_positive", "UPDATE payments SET amount_paise = 0");
        violates("refunds_payment_fk", "INSERT INTO refunds (payment_id, amount_paise, status) VALUES (99, 1, 'requested')");
        violates("refunds_succeeded_has_ref", "INSERT INTO refunds (payment_id, amount_paise, status) VALUES (1, 1, 'succeeded')");
        violates("refunds_amount_positive", "INSERT INTO refunds (payment_id, amount_paise, status) VALUES (1, 0, 'requested')");
    }

    @Test
    void aRefundThatCannotBeRecordedReservesNothingAndCallsNoProvider() throws Exception {
        pay("ORD-5001", 100000);
        jdbc.sql("""
                CREATE FUNCTION refuse_refunds() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'refund table full'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_refunds BEFORE INSERT ON refunds FOR EACH ROW EXECUTE FUNCTION refuse_refunds()""").update();
        try {
            assertThatThrownBy(() -> refund(1, 50000)).hasRootCauseMessage("ERROR: refund table full\n  Where: PL/pgSQL function refuse_refunds() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_refunds ON refunds; DROP FUNCTION refuse_refunds()").update();
        }
        assertThat(column("SELECT refunded_paise::text FROM payments")).isEqualTo("0");
        assertThat(alpha.refunds).isEmpty();
    }
}
