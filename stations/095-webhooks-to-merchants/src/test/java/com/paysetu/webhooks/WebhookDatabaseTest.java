package com.paysetu.webhooks;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class WebhookDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    @Test
    void deliveryRulesHoldWithoutJava() {
        String secret = "'whsec_" + "A".repeat(32) + "'";
        jdbc.sql("INSERT INTO webhook_endpoints (merchant_id, url, secret, created_at) VALUES (1, 'https://a.example/h', " + secret + ", now())").update();
        jdbc.sql("INSERT INTO events (id, merchant_id, type, object_ref, amount_paise, payload, created_at) VALUES ('00000000-0000-0000-0000-000000000001', 1, 'payment.captured', 'PAY-1', 100, '{}', now())").update();
        jdbc.sql("INSERT INTO deliveries (event_id, endpoint_id, next_attempt_at) VALUES ('00000000-0000-0000-0000-000000000001', 1, now())").update();

        violates("endpoints_url_once_per_merchant", "INSERT INTO webhook_endpoints (merchant_id, url, secret, created_at) VALUES (1, 'https://a.example/h', " + secret + ", now())");
        violates("endpoints_url_http", "INSERT INTO webhook_endpoints (merchant_id, url, secret, created_at) VALUES (1, 'file:///etc/passwd', " + secret + ", now())");
        violates("endpoints_secret_format", "INSERT INTO webhook_endpoints (merchant_id, url, secret, created_at) VALUES (1, 'https://b.example/h', 'password', now())");
        violates("events_once_per_object", "INSERT INTO events (id, merchant_id, type, object_ref, amount_paise, payload, created_at) VALUES (gen_random_uuid(), 1, 'payment.captured', 'PAY-1', 100, '{}', now())");
        violates("events_amount_positive", "INSERT INTO events (id, merchant_id, type, object_ref, amount_paise, payload, created_at) VALUES (gen_random_uuid(), 1, 'payment.captured', 'PAY-2', 0, '{}', now())");
        violates("events_type", "INSERT INTO events (id, merchant_id, type, object_ref, amount_paise, payload, created_at) VALUES (gen_random_uuid(), 1, 'payment.refunded', 'PAY-3', 100, '{}', now())");
        violates("deliveries_once_per_endpoint", "INSERT INTO deliveries (event_id, endpoint_id, next_attempt_at) VALUES ('00000000-0000-0000-0000-000000000001', 1, now())");
        violates("deliveries_attempts_range", "UPDATE deliveries SET attempts = 9");
        violates("deliveries_status", "UPDATE deliveries SET status = 'LOST', next_attempt_at = NULL");
        violates("deliveries_pending_has_next", "UPDATE deliveries SET next_attempt_at = NULL");
        violates("deliveries_pending_has_next", "UPDATE deliveries SET status = 'FAILED'");
        violates("deliveries_delivered_has_time", "UPDATE deliveries SET status = 'DELIVERED', next_attempt_at = NULL");
    }

    @Test
    void anEventWhoseDeliveriesCannotBeWrittenIsNotRecordedEither() throws Exception {
        secretFor("ravi", 1, "https://ravi-kirana.example/hooks/paysetu");
        jdbc.sql("""
                CREATE FUNCTION refuse_delivery() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'outbox full'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_delivery BEFORE INSERT ON deliveries FOR EACH ROW EXECUTE FUNCTION refuse_delivery()""").update();
        try {
            assertThatThrownBy(() -> testEvent("ravi", 1, "PAY-1001", 49900)).hasRootCauseMessage("ERROR: outbox full\n  Where: PL/pgSQL function refuse_delivery() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_delivery ON deliveries; DROP FUNCTION refuse_delivery()").update();
        }
        assertThat(jdbc.sql("SELECT count(*) FROM events").query(Long.class).single()).isZero();   // no event that no one would ever be told about
        testEvent("ravi", 1, "PAY-1001", 49900).andExpect(status().isAccepted());   // and reporting it again works
    }
}
