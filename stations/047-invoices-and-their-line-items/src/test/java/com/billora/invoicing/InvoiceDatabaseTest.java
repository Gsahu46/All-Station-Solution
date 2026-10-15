package com.billora.invoicing;

import jakarta.persistence.EntityManagerFactory;
import org.hibernate.SessionFactory;
import org.hibernate.stat.Statistics;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, a replacement rolled back whole, and what reading an invoice costs. */
class InvoiceDatabaseTest extends ApiTest {

    @Autowired
    InvoiceBook book;
    @Autowired
    EntityManagerFactory entityManagerFactory;

    void insertLine(long invoice, int quantity, long price) {
        jdbc.sql("INSERT INTO invoice_lines (invoice_id, description, quantity, unit_price_paise) VALUES (?, 'Test', ?, ?)")
                .params(invoice, quantity, price).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() throws Exception {
        create(INVOICE);
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO invoices (customer_name) VALUES ('  ')").update()).hasMessageContaining("invoices_customer_not_blank");
        assertThatThrownBy(() -> insertLine(99, 1, 100)).hasMessageContaining("invoice_lines_invoice_fk");
        assertThatThrownBy(() -> insertLine(1, 0, 100)).hasMessageContaining("invoice_lines_quantity_range");
        assertThatThrownBy(() -> insertLine(1, 1, 0)).hasMessageContaining("invoice_lines_price_range");
        assertThatThrownBy(() -> jdbc.sql("DELETE FROM invoices WHERE id = 1").update()).hasMessageContaining("invoice_lines_invoice_fk");
    }

    @Test
    void aReplacementTheDatabaseRefusesKeepsTheOldLines() throws Exception {
        create(INVOICE);
        // Past the controller's checks: the second line breaks a constraint, and the deletes roll back with the inserts.
        assertThatThrownBy(() -> book.replaceLines(1, List.of(new InvoiceBook.LineInput("Cloud hosting, March 2026", 1, 499900),
                new InvoiceBook.LineInput("Support hours", 0, 150000)))).hasMessageContaining("invoice_lines_quantity_range");
        assertThat(lineRows(1)).isEqualTo(2);
        assertThat(sumOfLineRows(1)).isEqualTo(1_399_900);
    }

    @Test
    void readingAnInvoiceWithItsLinesIsOneQuery() throws Exception {
        create(INVOICE);
        Statistics stats = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
        stats.clear();
        book.get(1);
        assertThat(stats.getPrepareStatementCount()).isEqualTo(1);   // @EntityGraph joins the LAZY lines in
    }
}
