package com.billora.invoicing;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "invoice_lines")
public class InvoiceLine {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)   // the owning side: this field is the invoice_id column
    @JoinColumn(name = "invoice_id")
    private Invoice invoice;
    private String description;
    private int quantity;
    private long unitPricePaise;

    protected InvoiceLine() {
    }

    InvoiceLine(String description, int quantity, long unitPricePaise) {
        this.description = description;
        this.quantity = quantity;
        this.unitPricePaise = unitPricePaise;
    }

    void setInvoice(Invoice invoice) {
        this.invoice = invoice;
    }

    long amountPaise() {
        return quantity * unitPricePaise;
    }

    public Long getId() {
        return id;
    }

    public String getDescription() {
        return description;
    }

    public int getQuantity() {
        return quantity;
    }

    public long getUnitPricePaise() {
        return unitPricePaise;
    }
}
