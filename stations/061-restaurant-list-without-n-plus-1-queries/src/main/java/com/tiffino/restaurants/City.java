package com.tiffino.restaurants;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "cities")
class City {

    @Id
    private String code;
    private String name;

    protected City() {
    }

    String getCode() {
        return code;
    }
}
