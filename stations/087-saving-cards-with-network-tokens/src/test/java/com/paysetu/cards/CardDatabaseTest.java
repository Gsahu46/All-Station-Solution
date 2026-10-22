package com.paysetu.cards;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class CardDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    static String card(String token, String last4) {
        return "INSERT INTO saved_cards (customer_id, token_ref, network, last4, expiry_month, expiry_year, consent_at) VALUES (1, '%s', 'VISA', '%s', 12, 2028, now())".formatted(token, last4);
    }

    @Test
    void aCardNumberCannotBeStoredAsATokenOrALast4() {
        violates("saved_cards_token_shape", card(VISA, "1111"));
        violates("saved_cards_token_shape", card("tkn_" + VISA, "1111"));
        violates("saved_cards_last4_shape", card("tkn_abcdefghijklmnopqrst", VISA));
    }

    @Test
    void otherRulesHoldWithoutJava() {
        jdbc.sql(card("tkn_abcdefghijklmnopqrst", "1111")).update();
        violates("saved_cards_token_unique", card("tkn_abcdefghijklmnopqrst", "1111"));
        violates("saved_cards_network", "UPDATE saved_cards SET network = 'AMEX'");
        violates("saved_cards_expiry", "UPDATE saved_cards SET expiry_month = 13");
        violates("saved_cards_status", "UPDATE saved_cards SET status = 'gone'");
        violates("saved_cards_customer_fk", "UPDATE saved_cards SET customer_id = 99");
        violates("payments_amount_positive", "INSERT INTO payments (customer_id, saved_card_id, order_id, amount_paise, status) VALUES (1, 1, 'ORD-1', 0, 'pending')");
        violates("payments_succeeded_has_ref", "INSERT INTO payments (customer_id, saved_card_id, order_id, amount_paise, status) VALUES (1, 1, 'ORD-1', 100, 'succeeded')");
        violates("payments_status", "INSERT INTO payments (customer_id, saved_card_id, order_id, amount_paise, status) VALUES (1, 1, 'ORD-1', 100, 'charged')");
        jdbc.sql("INSERT INTO payments (customer_id, saved_card_id, order_id, amount_paise, status) VALUES (1, 1, 'ORD-1', 100, 'pending')").update();
        violates("payments_order_once", "INSERT INTO payments (customer_id, saved_card_id, order_id, amount_paise, status) VALUES (1, 1, 'ORD-1', 100, 'pending')");
    }

    @Test
    void aCardThatCannotBeRecordedLeavesNoTokenAtTheNetwork() {
        jdbc.sql("""
                CREATE FUNCTION refuse_cards() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'saved cards full'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_cards BEFORE INSERT ON saved_cards FOR EACH ROW EXECUTE FUNCTION refuse_cards()""").update();
        try {
            assertThatThrownBy(() -> save("asha", ASHA, VISA, 12, 2028)).hasRootCauseMessage("ERROR: saved cards full\n  Where: PL/pgSQL function refuse_cards() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_cards ON saved_cards; DROP FUNCTION refuse_cards()").update();
        }
        assertThat(network.holds(VISA)).isFalse();
    }
}
