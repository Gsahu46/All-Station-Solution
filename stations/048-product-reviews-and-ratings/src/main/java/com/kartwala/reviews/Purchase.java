package com.kartwala.reviews;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDate;

/** An order line of one product for one customer; delivered_on is set when the courier record says delivered. */
@Entity
@Table(name = "purchases")
public class Purchase {

    @Id
    private Long id;
    private Long customerId;
    private Long productId;
    private LocalDate deliveredOn;

    protected Purchase() {
    }

    public Long getId() {
        return id;
    }
}
