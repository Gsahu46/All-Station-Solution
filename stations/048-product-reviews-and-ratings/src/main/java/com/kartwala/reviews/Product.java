package com.kartwala.reviews;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "products")
public class Product {

    @Id
    private Long id;
    private String name;

    protected Product() {
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }
}
