package com.billora.invoicing;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;

import java.util.ArrayList;
import java.util.List;

/**
 * The mapping as it shipped, kept only in tests, on the same tables: cascade ALL but no orphanRemoval, and a public,
 * modifiable list. Only the annotations differ from Invoice.
 */
@Entity
@Table(name = "invoices")
public class OldInvoice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    Long id;
    String customerName;
    @OneToMany(mappedBy = "invoice", cascade = CascadeType.ALL)
    List<Line> lines = new ArrayList<>();

    public List<Line> getLines() {
        return lines;
    }

    @Entity(name = "OldInvoiceLine")
    @Table(name = "invoice_lines")
    public static class Line {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        Long id;
        @ManyToOne(fetch = FetchType.LAZY, optional = false)
        @JoinColumn(name = "invoice_id")
        OldInvoice invoice;
        String description;
        int quantity;
        long unitPricePaise;

        Line() {
        }

        Line(OldInvoice invoice, String description, int quantity, long unitPricePaise) {
            this.invoice = invoice;
            this.description = description;
            this.quantity = quantity;
            this.unitPricePaise = unitPricePaise;
        }
    }
}
