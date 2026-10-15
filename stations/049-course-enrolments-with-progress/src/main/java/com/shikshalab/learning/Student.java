package com.shikshalab.learning;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "students")
public class Student {

    @Id
    private Long id;
    private String name;

    protected Student() {
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }
}
