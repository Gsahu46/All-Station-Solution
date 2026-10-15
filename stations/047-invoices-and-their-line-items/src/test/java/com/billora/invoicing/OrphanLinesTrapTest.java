package com.billora.invoicing;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: the old line replacement, with the old mapping, on the same tables. The
 * lines leave the Java list but never leave the table, so the next read brings them back.
 */
class OrphanLinesTrapTest extends ApiTest {

    @Autowired
    EntityManager entities;
    @Autowired
    TransactionTemplate transaction;

    /** The old PUT: clear the list, add the corrected lines. Exactly what Invoice.replaceLines does, minus orphanRemoval. */
    void oldReplace(long id) {
        transaction.executeWithoutResult(status -> {
            OldInvoice invoice = entities.find(OldInvoice.class, id);
            invoice.getLines().clear();
            invoice.getLines().add(new OldInvoice.Line(invoice, "Cloud hosting, March 2026", 1, 499900));
            invoice.getLines().add(new OldInvoice.Line(invoice, "Support hours", 4, 150000));
        });
    }

    @Test
    void withoutOrphanRemovalTheOldLinesStayAndCount() throws Exception {
        create(INVOICE);
        oldReplace(1);
        assertThat(lineRows(1)).isEqualTo(4);                 // 2 new rows, and the 2 "removed" ones
        assertThat(sumOfLineRows(1)).isEqualTo(2_499_800);    // ₹13,999 + ₹10,999 instead of ₹10,999
        mvc.perform(get("/invoices/1"))
                .andExpect(jsonPath("$.lines.length()").value(4))
                .andExpect(jsonPath("$.totalPaise").value(2_499_800));
    }

    @Test
    void withOrphanRemovalTheyAreDeleted() throws Exception {
        create(INVOICE);
        replaceLines(1, CORRECTED);
        assertThat(lineRows(1)).isEqualTo(2);
        assertThat(sumOfLineRows(1)).isEqualTo(1_099_900);
    }

    @Test
    void addingToTheListWithoutTheBackReferenceLeavesInvoiceIdEmpty() throws Exception {
        create(INVOICE);
        // invoice_id comes from line.invoice (the owning side), not from the list: the list alone says nothing.
        assertThatThrownBy(() -> transaction.executeWithoutResult(status ->
                entities.find(OldInvoice.class, 1L).getLines().add(new OldInvoice.Line(null, "Domain renewal", 1, 99900))))
                .hasMessageContaining("invoice_id");
        assertThat(lineRows(1)).isEqualTo(2);
    }
}
