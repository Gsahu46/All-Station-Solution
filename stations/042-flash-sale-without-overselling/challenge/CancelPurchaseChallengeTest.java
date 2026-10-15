package com.kartwala.flashsale;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: DELETE /flash-sales/{saleId}/purchases/{purchaseId} cancels a purchase and puts the phone back, in one
 * transaction: 204, or 404 if there is no such purchase. Ten cancels of the same purchase at once put back one phone.
 */
class CancelPurchaseChallengeTest extends ApiTest {

    long purchaseId() {
        return jdbc.sql("SELECT id FROM purchases WHERE sale_id = 10").query(Long.class).single();
    }

    @Test
    void cancellingPutsThePhoneBack() throws Exception {
        openSale(5);
        buy(10, "C-000001");
        mvc.perform(delete("/flash-sales/10/purchases/{id}", purchaseId())).andExpect(status().isNoContent());
        assertThat(stockLeft(10)).isEqualTo(5);
        assertThat(purchases(10)).isZero();
        mvc.perform(delete("/flash-sales/10/purchases/{id}", 99999)).andExpect(status().isNotFound());
    }

    @Test
    void tenCancelsAtOnceReturnOnePhone() throws Exception {
        openSale(5);
        buy(10, "C-000001");
        long id = purchaseId();
        List<Integer> statuses = together(10, () -> mvc.perform(delete("/flash-sales/10/purchases/{id}", id)).andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 204).hasSize(1);
        assertThat(stockLeft(10)).isEqualTo(5);
    }
}
