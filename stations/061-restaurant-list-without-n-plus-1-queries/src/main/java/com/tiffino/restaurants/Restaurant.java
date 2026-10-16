package com.tiffino.restaurants;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.Table;

import java.util.HashSet;
import java.util.Set;

@Entity
@Table(name = "restaurants")
class Restaurant {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "city_code")
    private String cityCode;
    private String name;

    /** Lazy, the JPA default for collections: loaded only when asked for, which is how the N+1 starts. */
    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(name = "restaurant_cuisines", joinColumns = @JoinColumn(name = "restaurant_id"), inverseJoinColumns = @JoinColumn(name = "cuisine_id"))
    private Set<Cuisine> cuisines = new HashSet<>();

    protected Restaurant() {
    }

    Long getId() {
        return id;
    }

    String getName() {
        return name;
    }

    Set<Cuisine> getCuisines() {
        return cuisines;
    }
}
