package com.kartwala.sellerpages;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "sellers")
class Seller {

    @Id
    private Long id;
    private String name;

    protected Seller() {
    }
}
