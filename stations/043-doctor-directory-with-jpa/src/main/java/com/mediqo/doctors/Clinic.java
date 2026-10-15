package com.mediqo.doctors;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "clinics")
public class Clinic {

    @Id
    private Long id;
    private String name;
    private String city;
    private String address;

    protected Clinic() {   // for JPA
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getCity() {
        return city;
    }

    public String getAddress() {
        return address;
    }
}
