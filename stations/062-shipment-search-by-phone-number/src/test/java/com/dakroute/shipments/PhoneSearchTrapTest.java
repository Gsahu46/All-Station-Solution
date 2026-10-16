package com.dakroute.shipments;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old search and the indexes people try first, measured with EXPLAIN (ANALYZE, BUFFERS) on copies
 * of the 300,003 demo shipments. Pages are 8 kB blocks PostgreSQL touched; fewer pages is less work.
 */
class PhoneSearchTrapTest extends ApiTest {

    static final LocalDate MARCH_1 = LocalDate.of(2026, 3, 1), MARCH_7 = LocalDate.of(2026, 3, 7), MARCH_31 = LocalDate.of(2026, 3, 31);
    static final LocalDate JAN_1 = LocalDate.of(2026, 1, 1), SEP_30 = LocalDate.of(2026, 9, 30);

    @AfterEach
    void dropCopies() {
        jdbc.sql("DROP TABLE IF EXISTS old_shipments, shipments_copy").update();
    }

    @Test
    void theOldSearchCleanedThePhoneInSqlSoItsIndexWasNeverUsed() {
        // The old table kept phones as typed, in three formats, with an index on phone that someone added.
        jdbc.sql("""
                CREATE TABLE old_shipments AS SELECT id, awb, CASE id % 3 WHEN 0 THEN '+91 ' || substr(phone, 1, 5) || ' ' || substr(phone, 6)
                    WHEN 1 THEN '0' || phone ELSE phone END AS phone, booked_on, status FROM shipments""").update();
        jdbc.sql("CREATE INDEX old_shipments_phone ON old_shipments (phone)").update();
        jdbc.sql("ANALYZE old_shipments").update();
        String old = ShipmentSearch.SQL.replace("FROM shipments", "FROM old_shipments")
                .replace("phone = :phone", "right(regexp_replace(phone, '[^0-9]', '', 'g'), 10) = :phone");
        assertThat(jdbc.sql(old).param("phone", CUSTOMER).param("from", MARCH_1).param("to", MARCH_31).param("limit", 50).query().listOfRows()).hasSize(2);

        Plan before = explain(old, CUSTOMER, MARCH_1, MARCH_31);
        Plan after = explainSearch("shipments", CUSTOMER, MARCH_1, MARCH_31);
        assertThat(before.nodes()).contains("Seq Scan");   // a function around the column: the index on phone cannot help
        assertThat(before.indexes()).isEmpty();
        assertThat(after.indexes()).containsOnly("shipments_phone_booked_on");
        assertThat(after.pages()).isLessThanOrEqualTo(10);
        assertThat(before.pages()).isGreaterThan(100 * after.pages());
    }

    @Test
    void theColumnOrderOfTheIndexDecidesHowMuchIsRead() {
        jdbc.sql("CREATE TABLE shipments_copy AS SELECT * FROM shipments").update();
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan noIndex = explainSearch("shipments_copy", SELLER, MARCH_1, MARCH_7);

        jdbc.sql("CREATE INDEX copy_phone ON shipments_copy (phone)").update();   // phone only: all 30,000 of the seller's rows
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan phoneOnly = explainSearch("shipments_copy", SELLER, MARCH_1, MARCH_7);
        jdbc.sql("DROP INDEX copy_phone").update();

        jdbc.sql("CREATE INDEX copy_date_phone ON shipments_copy (booked_on, phone)").update();   // range first: every phone in those dates
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan dateFirst = explainSearch("shipments_copy", CUSTOMER, JAN_1, SEP_30);
        jdbc.sql("DROP INDEX copy_date_phone").update();

        jdbc.sql("CREATE INDEX copy_phone_date ON shipments_copy (phone, booked_on)").update();   // equality first, then range
        jdbc.sql("ANALYZE shipments_copy").update();
        Plan sellerWeek = explainSearch("shipments_copy", SELLER, MARCH_1, MARCH_7);
        Plan customerYear = explainSearch("shipments_copy", CUSTOMER, JAN_1, SEP_30);

        assertThat(noIndex.nodes()).contains("Seq Scan");
        assertThat(sellerWeek.indexes()).containsOnly("copy_phone_date");
        assertThat(customerYear.indexes()).containsOnly("copy_phone_date");
        assertThat(phoneOnly.indexRows()).isEqualTo(30_000);   // every one of the seller's entries, then filtered by date and sorted
        assertThat(sellerWeek.indexRows()).isLessThan(300);    // from 7 March backwards, stopping once 50 are certain
        assertThat(phoneOnly.pages()).isGreaterThan(2 * sellerWeek.pages());
        assertThat(dateFirst.pages()).isGreaterThan(10 * customerYear.pages());
    }
}
