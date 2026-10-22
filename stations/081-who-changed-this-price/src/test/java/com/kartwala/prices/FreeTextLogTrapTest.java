package com.kartwala.prices;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old code wrote a line of text to a log table when a price changed, in whatever words the
 * developer chose that week, with the user name the app sent. The TV went from ₹54,999 to ₹5,499 and nobody could
 * say who did it. Each test asks the old log a question, then asks the real history.
 */
class FreeTextLogTrapTest extends ApiTest {

    /** The old log, as it was: lines of text, editable like any row. */
    static final List<String> OLD_LOG = new ArrayList<>(List.of(
            "price updated for product 1 to 5499 by neha",
            "Product #1: new price Rs 54,999.00",
            "changed price -> 5499 (user: ops)"));

    @Test
    void theOldLogCouldNotSayWhoOrWhenOrEvenWhichPrice() {
        // "Who set product 1 to ₹5,499?" Two lines might be it, in two formats, with two different people, and no time.
        Matcher who = Pattern.compile("product 1 to (\\d+) by (\\w+)").matcher(String.join("\n", OLD_LOG));
        assertThat(who.find()).isTrue();
        assertThat(OLD_LOG.get(2)).doesNotContain("product");   // which product was this one?
        OLD_LOG.set(0, "price updated for product 1 to 54999 by neha");   // and anyone with write access could tidy it up
        assertThat(OLD_LOG).noneMatch(l -> l.matches(".*\\d{4}-\\d{2}-\\d{2}.*"));   // not one line has a date
    }

    @Test
    void theHistoryNamesWhoAndWhenForEveryPrice() throws Exception {
        setPrice("neha.store", 1, 549900).andExpect(status().isOk());
        history("priya.ops", 1).andExpect(status().isOk())
                .andExpect(jsonPath("$[0].changedBy").value("neha.store")).andExpect(jsonPath("$[0].pricePaise").value(549900))
                .andExpect(jsonPath("$[0].previousPricePaise").value(5499900)).andExpect(jsonPath("$[0].changedAt").isNotEmpty())
                .andExpect(jsonPath("$[1].changedBy").value("catalogue.import"));
    }

    @Test
    void whoIsTheSignedInUserNotWhatTheRequestSays() throws Exception {
        setPrice("neha.store", 1, "{\"pricePaise\":549900,\"changedBy\":\"priya.ops\"}").andExpect(status().isOk());
        history("neha.store", 1).andExpect(jsonPath("$[0].changedBy").value("neha.store"));
    }

    @Test
    void theHistoryCannotBeTidiedUp() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE products_aud SET price_paise = 5499900").update())
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("history_is_append_only");
        assertThatThrownBy(() -> jdbc.sql("DELETE FROM revisions").update())
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("history_is_append_only");
    }
}
