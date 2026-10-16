package com.kartwala.prices;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/**
 * Written first. The old schedule table: local times without a time zone, no rule against overlaps, read by a server
 * whose clock runs in UTC.
 */
class OverwrittenPriceTrapTest extends ApiTest {

    /** The old checkout query: the price change in force "now", as the UTC server's local time saw it. */
    static final String OLD = """
            SELECT price_paise FROM old_price_changes WHERE product_id = 2
            AND starts_at <= (CAST(:at AS timestamptz) AT TIME ZONE 'UTC') AND ends_at > (CAST(:at AS timestamptz) AT TIME ZONE 'UTC')""";

    @BeforeEach
    void oldTable() {
        jdbc.sql("CREATE TABLE old_price_changes (product_id BIGINT, price_paise INTEGER, starts_at TIMESTAMP, ends_at TIMESTAMP)").update();
        // The seller typed midnight, meaning midnight in India.
        jdbc.sql("INSERT INTO old_price_changes VALUES (2, 14900, '2026-11-08 00:00', '2026-11-11 00:00')").update();
    }

    @AfterEach
    void dropOldTable() {
        jdbc.sql("DROP TABLE old_price_changes").update();
    }

    private List<Integer> old(String at) {
        return jdbc.sql(OLD).param("at", at).query(Integer.class).list();
    }

    @Test
    void localTimesWentLiveAtTheServersMidnightNotTheShops() throws Exception {
        assertThat(old("2026-11-08T00:30:00+05:30")).isEmpty();                 // half an hour into Diwali in India: no sale yet
        assertThat(old("2026-11-08T05:30:00+05:30")).containsExactly(14900);    // midnight in UTC
        priceAt(2, "2026-11-08T00:30:00+05:30").andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.pricePaise").value(14900));
    }

    @Test
    void twoOverlappingChangesBothApplyAndCheckoutPicksOne() {
        jdbc.sql("INSERT INTO old_price_changes VALUES (2, 12900, '2026-11-09 00:00', '2026-11-10 00:00')").update();   // a flash sale, added later
        assertThat(old("2026-11-09T12:00:00+05:30")).containsExactlyInAnyOrder(14900, 12900);   // which one checkout took depended on the plan
    }

    @Test
    void theRealTableRefusesTheOverlap() {
        Throwable refused = catchThrowable(() -> jdbc.sql("INSERT INTO prices (product_id, price_paise, valid_from, valid_to) VALUES (2, 12900, '2026-11-09 00:00+05:30', '2026-11-10 00:00+05:30')").update());
        assertThat(refused).hasMessageContaining("prices_no_overlap");
    }
}
