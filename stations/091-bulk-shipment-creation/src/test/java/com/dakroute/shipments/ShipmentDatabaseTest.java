package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The rules hold for any writer, not only this API: plain SQL, no Java in between. */
class ShipmentDatabaseTest extends ApiTest {

    static String row(String ref, String to, String phone, int grams, String name) {
        return "INSERT INTO shipments (ref, from_pincode, to_name, to_line1, to_city, to_pincode, to_phone, weight_grams) VALUES ('%s', '560001', '%s', '14 Lodhi Road', 'New Delhi', '%s', '%s', %d)"
                .formatted(ref, name, to, phone, grams);
    }

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).hasMessageContaining(constraint);
    }

    @Test
    void shipmentRulesHoldWithoutJava() {
        jdbc.sql(row("ORD-1", "110003", "9810000001", 1200, "Meera")).update();
        violates("shipments_ref_unique", row("ORD-1", "110003", "9810000001", 1200, "Meera"));
        violates("shipments_ref_shape", row("ord 2", "110003", "9810000001", 1200, "Meera"));
        violates("shipments_pincodes", row("ORD-2", "011003", "9810000001", 1200, "Meera"));
        violates("shipments_phone", row("ORD-2", "110003", "5810000001", 1200, "Meera"));
        violates("shipments_weight", row("ORD-2", "110003", "9810000001", 50001, "Meera"));
        violates("shipments_address_present", row("ORD-2", "110003", "9810000001", 1200, "  "));
    }

    @Test
    void anItemTheDatabaseRefusesFailsAloneAndTheOthersStay() throws Exception {
        jdbc.sql("""
                CREATE FUNCTION refuse_ord_2() RETURNS trigger AS $$ BEGIN IF NEW.ref = 'ORD-2' THEN RAISE EXCEPTION 'disk full'; END IF; RETURN NEW; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_ord_2 BEFORE INSERT ON shipments FOR EACH ROW EXECUTE FUNCTION refuse_ord_2()""").update();
        try {
            bulk(List.of(item("ORD-1"), item("ORD-2"), item("ORD-3"))).andExpect(jsonPath("$.created").value(2))
                    .andExpect(jsonPath("$.results[1].errors[0].message").value("could not be saved"));
        } finally {
            jdbc.sql("DROP TRIGGER refuse_ord_2 ON shipments; DROP FUNCTION refuse_ord_2()").update();
        }
        assertThat(jdbc.sql("SELECT ref FROM shipments ORDER BY id").query(String.class).list()).containsExactly("ORD-1", "ORD-3");
    }
}
