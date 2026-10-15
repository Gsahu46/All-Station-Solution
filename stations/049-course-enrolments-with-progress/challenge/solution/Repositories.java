package com.shikshalab.learning;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

interface StudentRepository extends JpaRepository<Student, Long> {
}

interface CourseRepository extends JpaRepository<Course, Long> {
}

interface EnrolmentRepository extends JpaRepository<Enrolment, Long> {

    boolean existsByStudentIdAndCourseId(long studentId, long courseId);

    @EntityGraph(attributePaths = {"student", "course"})
    Optional<Enrolment> findWithCourseById(long id);

    /** A student's courses, read through the link: one query, the course joined in. */
    @EntityGraph(attributePaths = {"student", "course"})
    List<Enrolment> findByStudentIdOrderByEnrolledOnAscIdAsc(long studentId);

    /** The other side of the link: a course's students, furthest along first. */
    @EntityGraph(attributePaths = {"student", "course"})
    List<Enrolment> findByCourseIdOrderByLessonsCompletedDescStudentNameAsc(long courseId);
}
