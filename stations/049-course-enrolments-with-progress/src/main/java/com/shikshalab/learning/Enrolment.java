package com.shikshalab.learning;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

import java.time.LocalDate;

/**
 * The link between a student and a course, as an entity of its own: the many-to-many becomes two many-to-ones, and
 * the link gets room for its own data (the date, the progress).
 */
@Entity
@Table(name = "enrolments")
public class Enrolment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "student_id")
    private Student student;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "course_id")
    private Course course;
    private int courseLessons;   // a copy of the course's lesson count, so the database can check progress against it
    private LocalDate enrolledOn;
    private int lessonsCompleted;
    private LocalDate completedOn;

    protected Enrolment() {
    }

    Enrolment(Student student, Course course, LocalDate enrolledOn) {
        this.student = student;
        this.course = course;
        this.courseLessons = course.getLessonCount();
        this.enrolledOn = enrolledOn;
    }

    /** Sets the lessons done; the course is complete, with today's date, exactly when every lesson is done. */
    void recordProgress(int lessonsCompleted, LocalDate today) {
        this.lessonsCompleted = lessonsCompleted;
        if (lessonsCompleted < courseLessons) {
            completedOn = null;
        } else if (completedOn == null) {
            completedOn = today;
        }
    }

    public Long getId() {
        return id;
    }

    public Student getStudent() {
        return student;
    }

    public Course getCourse() {
        return course;
    }

    public LocalDate getEnrolledOn() {
        return enrolledOn;
    }

    public int getLessonsCompleted() {
        return lessonsCompleted;
    }

    public LocalDate getCompletedOn() {
        return completedOn;
    }
}
