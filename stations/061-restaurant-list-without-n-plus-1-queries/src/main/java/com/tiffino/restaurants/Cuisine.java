package com.tiffino.restaurants;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "cuisines")
class Cuisine {

    @Id
    private Long id;
    private String name;

    protected Cuisine() {
    }

    String getName() {
        return name;
    }
}
