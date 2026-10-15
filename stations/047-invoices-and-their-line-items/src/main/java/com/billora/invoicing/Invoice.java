package com.billora.invoicing;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OrderBy;
import jakarta.persistence.Table;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Entity
@Table(name = "invoices")
public class Invoice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String customerName;
    // cascade: lines are saved with the invoice. orphanRemoval: a line taken out of this list is deleted, not left behind.
    @OneToMany(mappedBy = "invoice", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("id")
    private List<InvoiceLine> lines = new ArrayList<>();

    protected Invoice() {
    }

    Invoice(String customerName) {
        this.customerName = customerName;
    }

    /** Both sides of the link: the list for Java, and line.invoice, which is what fills invoice_id. */
    void addLine(InvoiceLine line) {
        lines.add(line);
        line.setInvoice(this);
    }

    void replaceLines(List<InvoiceLine> newLines) {
        lines.clear();   // the same list object: Hibernate tracks it, and deletes what left it
        newLines.forEach(this::addLine);
    }

    long totalPaise() {
        return lines.stream().mapToLong(InvoiceLine::amountPaise).sum();
    }

    public Long getId() {
        return id;
    }

    public String getCustomerName() {
        return customerName;
    }

    /** Read-only: lines are added and removed through the helpers, so the two sides never disagree. */
    public List<InvoiceLine> getLines() {
        return Collections.unmodifiableList(lines);
    }
}
