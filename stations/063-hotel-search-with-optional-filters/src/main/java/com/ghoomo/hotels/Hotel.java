package com.ghoomo.hotels;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
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
@Table(name = "hotels")
class Hotel {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
    private String city;
    private short stars;
    @Column(name = "price_per_night_paise")
    private long pricePerNightPaise;

    @ManyToMany
    @JoinTable(name = "hotel_amenities", joinColumns = @JoinColumn(name = "hotel_id"), inverseJoinColumns = @JoinColumn(name = "amenity_code"))
    private Set<Amenity> amenities = new HashSet<>();

    protected Hotel() {
    }

    Long getId() {
        return id;
    }

    String getName() {
        return name;
    }

    String getCity() {
        return city;
    }

    short getStars() {
        return stars;
    }

    long getPricePerNightPaise() {
        return pricePerNightPaise;
    }

    Set<Amenity> getAmenities() {
        return amenities;
    }
}
