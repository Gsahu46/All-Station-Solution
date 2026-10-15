package com.kartwala.reviews;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "customers")
public class Customer {

    @Id
    private Long id;
    private String name;

    protected Customer() {
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }
}
