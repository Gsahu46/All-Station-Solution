package com.mediqo.doctors;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

/**
 * A row of the doctors table, as Hibernate manages it. It holds private columns (personal phone, salary, notes) and a
 * lazy link to the clinic, which is why it never leaves the service: the API returns DoctorView instead.
 */
@Entity
@Table(name = "doctors")
public class Doctor {

    @Id
    private Long id;
    private String name;
    private String speciality;
    private String city;
    private String registrationNumber;
    private String personalPhone;
    private long salaryPaise;
    private String internalNotes;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "clinic_id")
    private Clinic clinic;

    protected Doctor() {   // for JPA
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getSpeciality() {
        return speciality;
    }

    public String getCity() {
        return city;
    }

    public String getRegistrationNumber() {
        return registrationNumber;
    }

    public String getPersonalPhone() {
        return personalPhone;
    }

    public long getSalaryPaise() {
        return salaryPaise;
    }

    public String getInternalNotes() {
        return internalNotes;
    }

    public Clinic getClinic() {
        return clinic;
    }
}
