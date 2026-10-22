package com.paysetu.cards;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old code kept the card number in saved_cards "just for retries": the breach copied it. These
 * tests search every text column of every table, and the application's log, for the card number.
 */
@ExtendWith(OutputCaptureExtension.class)
class CardNumberStorageTrapTest extends ApiTest {

    /** Every table and text column holding these digits. */
    List<String> placesHolding(String digits) {
        List<String> found = new ArrayList<>();
        for (Map<String, Object> c : jdbc.sql("""
                SELECT table_name, column_name FROM information_schema.columns
                WHERE table_schema = current_schema() AND data_type IN ('text', 'character varying')""").query().listOfRows()) {
            String sql = "SELECT count(*) FROM \"%s\" WHERE \"%s\" LIKE ?".formatted(c.get("table_name"), c.get("column_name"));
            if (jdbc.sql(sql).param("%" + digits + "%").query(Long.class).single() > 0) {
                found.add(c.get("table_name") + "." + c.get("column_name"));
            }
        }
        return found;
    }

    @Test
    void theOldDesignKeptTheCardNumberAndTheSearchFindsIt() {
        jdbc.sql("CREATE TABLE old_saved_cards (customer_id bigint, card_number text, token_ref text)").update();
        try {
            jdbc.sql("INSERT INTO old_saved_cards VALUES (1, ?, 'tkn_abcdefghijklmnopqrst')").param(VISA).update();   // "just for retries"
            assertThat(placesHolding(VISA)).containsExactly("old_saved_cards.card_number");
        } finally {
            jdbc.sql("DROP TABLE old_saved_cards").update();
        }
    }

    @Test
    void afterSavingPayingAndRetryingTheCardNumberIsNowhereInOurDatabaseOrLog(CapturedOutput log) throws Exception {
        long card = savedCardId("asha", ASHA, VISA);
        pay("asha", "ORD-1", card, 50051).andExpect(status().isPaymentRequired());   // declined
        pay("asha", "ORD-2", card, 50000).andExpect(status().isCreated());           // the retry uses the token, not the number
        save("asha", ASHA, "{\"cardNumber\":\"" + VISA + "\",\"expiryMonth\":12,\"expiryYear\":2028,\"consent\":false}").andExpect(status().isBadRequest());
        save("asha", ASHA, "{\"cardNumber\":\"4111111111111112\",\"expiryMonth\":12,\"expiryYear\":2028,\"consent\":true}").andExpect(status().isBadRequest());
        assertThat(placesHolding(VISA)).isEmpty();
        assertThat(placesHolding(VISA.substring(0, 12))).isEmpty();
        assertThat(log.getAll()).doesNotContain(VISA).doesNotContain("4111111111111112");
        assertThat(network.holds(VISA)).isTrue();   // the network's vault has it, outside Paysetu's systems
    }

    @Test
    void theRequestNeverPrintsTheCardNumber() {
        assertThat(new CardController.SaveCardRequest(VISA, 12, 2028, true).toString()).doesNotContain(VISA).contains("****");
    }
}
