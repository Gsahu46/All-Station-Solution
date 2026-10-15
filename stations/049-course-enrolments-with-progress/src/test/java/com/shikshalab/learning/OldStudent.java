package com.shikshalab.learning;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.Table;

import java.util.ArrayList;
import java.util.List;

/**
 * The mapping as it shipped, kept only in tests: a plain @ManyToMany over the same join table. It knows the two ids
 * and nothing else, so there is no field for the date or the progress, and nowhere to put one.
 */
@Entity
@Table(name = "students")
public class OldStudent {

    @Id
    Long id;
    String name;
    @ManyToMany
    @JoinTable(name = "enrolments", joinColumns = @JoinColumn(name = "student_id"), inverseJoinColumns = @JoinColumn(name = "course_id"))
    List<Course> courses = new ArrayList<>();
}
