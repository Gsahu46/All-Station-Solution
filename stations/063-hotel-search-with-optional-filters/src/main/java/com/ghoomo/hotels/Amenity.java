package com.ghoomo.hotels;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "amenities")
class Amenity {

    @Id
    private String code;
    private String name;

    protected Amenity() {
    }

    String getCode() {
        return code;
    }
}
