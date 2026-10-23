package com.dakroute.shipments;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old endpoint saved the whole batch in one transaction. Item 312 of 500 had a five-digit PIN
 * code: the database refused it, the transaction rolled back, nothing was created, and the seller got a 500 with no
 * hint which item. Here the same thing with three items.
 */
class AllOrNothingTrapTest extends ApiTest {

    @Autowired
    TransactionTemplate tx;

    void insert(String ref, String toPincode) {
        jdbc.sql("""
                INSERT INTO shipments (ref, from_pincode, to_name, to_line1, to_city, to_pincode, to_phone, weight_grams)
                VALUES (?, '560001', 'Meera Iyer', '14 Lodhi Road', 'New Delhi', ?, '9810000001', 1200)""").params(ref, toPincode).update();
    }

    @Test
    void theOldWayOneBadItemCreatedNothingAndSaidNothingUseful() {
        assertThatThrownBy(() -> tx.executeWithoutResult(s -> {
            insert("ORD-1", "110003");
            insert("ORD-2", "11003");    // five digits
            insert("ORD-3", "110003");
        })).hasMessageContaining("shipments_pincodes");   // a database message, not a field a seller can fix
        assertThat(count()).isZero();
    }

    @Test
    void theApiCreatesTheGoodItemsAndNamesTheBadOne() throws Exception {
        bulk(List.of(item("ORD-1"), item("ORD-2").replace("110003", "11003"), item("ORD-3"))).andExpect(status().isOk())
                .andExpect(jsonPath("$.created").value(2)).andExpect(jsonPath("$.failed").value(1))
                .andExpect(jsonPath("$.results[1].index").value(1)).andExpect(jsonPath("$.results[1].ref").value("ORD-2"))
                .andExpect(jsonPath("$.results[1].status").value("failed"))
                .andExpect(jsonPath("$.results[1].errors[0].field").value("to.pincode"))
                .andExpect(jsonPath("$.results[1].errors[0].message").value("must be 6 digits, not starting with 0"));
        assertThat(count()).isEqualTo(2);
    }
}
