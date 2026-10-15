package com.ghoomo.rooms;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "rooms")
public class Room {

    @Id
    private Long id;
    private String hotel;
    private String name;
    private short capacity;

    protected Room() {   // for JPA
    }

    public Long getId() {
        return id;
    }

    public String getHotel() {
        return hotel;
    }

    public String getName() {
        return name;
    }
}
