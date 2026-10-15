package com.shikshalab.learning;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "courses")
public class Course {

    @Id
    private Long id;
    private String title;
    private int lessonCount;

    protected Course() {
    }

    public Long getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public int getLessonCount() {
        return lessonCount;
    }
}
