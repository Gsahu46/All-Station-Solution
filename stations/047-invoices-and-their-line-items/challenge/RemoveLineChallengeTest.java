package com.billora.invoicing;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /invoices/{id}/lines/{position} removes one line (1 = the first, in the order returned) and
 * returns the invoice. The row must be gone from the table. The last line cannot be removed (409); a position or
 * invoice that does not exist is 404.
 */
class RemoveLineChallengeTest extends ApiTest {

    @Test
    void removingALineDeletesItsRow() throws Exception {
        create(INVOICE);
        mvc.perform(delete("/invoices/1/lines/2")).andExpect(status().isOk())
                .andExpect(jsonPath("$.lines.length()").value(1)).andExpect(jsonPath("$.totalPaise").value(499900));
        assertThat(lineRows(1)).isEqualTo(1);
        assertThat(sumOfLineRows(1)).isEqualTo(499900);
        mvc.perform(delete("/invoices/1/lines/1")).andExpect(status().isConflict());   // an invoice keeps at least one line
    }

    @Test
    void missingPositionsAndInvoicesAre404() throws Exception {
        create(INVOICE);
        mvc.perform(delete("/invoices/1/lines/3")).andExpect(status().isNotFound());
        mvc.perform(delete("/invoices/1/lines/0")).andExpect(status().isNotFound());
        mvc.perform(delete("/invoices/99/lines/1")).andExpect(status().isNotFound());
        assertThat(lineRows(1)).isEqualTo(2);
    }
}
