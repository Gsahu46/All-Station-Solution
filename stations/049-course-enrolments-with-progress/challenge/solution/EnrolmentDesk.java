package com.shikshalab.learning;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.LocalDate;
import java.util.List;

@Service
class EnrolmentDesk {

    record EnrolmentView(long id, long studentId, long courseId, String courseTitle, LocalDate enrolledOn,
                         int lessonsCompleted, int lessonCount, int progressPercent, LocalDate completedOn) {
        static EnrolmentView of(Enrolment e) {
            Course c = e.getCourse();
            return new EnrolmentView(e.getId(), e.getStudent().getId(), c.getId(), c.getTitle(), e.getEnrolledOn(),
                    e.getLessonsCompleted(), c.getLessonCount(), e.getLessonsCompleted() * 100 / c.getLessonCount(), e.getCompletedOn());
        }
    }

    record RosterLine(long studentId, String name, int lessonsCompleted, int progressPercent, LocalDate completedOn) {
    }

    private final StudentRepository students;
    private final CourseRepository courses;
    private final EnrolmentRepository enrolments;
    private final Clock clock;

    EnrolmentDesk(StudentRepository students, CourseRepository courses, EnrolmentRepository enrolments, Clock clock) {
        this.students = students;
        this.courses = courses;
        this.enrolments = enrolments;
        this.clock = clock;
    }

    @Transactional
    EnrolmentView enrol(long courseId, long studentId) {
        Course course = courses.findById(courseId)
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Course not found", "No course " + courseId + "."));
        Student student = students.findById(studentId)
                .orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown student", "No student " + studentId + "."));
        if (enrolments.existsByStudentIdAndCourseId(studentId, courseId)) {
            throw alreadyEnrolled(studentId, courseId);
        }
        try {
            return EnrolmentView.of(enrolments.save(new Enrolment(student, course, LocalDate.now(clock))));
        } catch (DataIntegrityViolationException e) {
            // Two enrolments of the same pair at the same moment both pass the check; the unique constraint stops one.
            if (String.valueOf(e.getMessage()).contains("enrolments_student_course_unique")) {
                throw alreadyEnrolled(studentId, courseId);
            }
            throw e;
        }
    }

    @Transactional
    EnrolmentView recordProgress(long enrolmentId, int lessonsCompleted) {
        Enrolment enrolment = enrolments.findWithCourseById(enrolmentId)
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Enrolment not found", "No enrolment " + enrolmentId + "."));
        int lessons = enrolment.getCourse().getLessonCount();
        if (lessonsCompleted > lessons) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Beyond the course",
                    "\"" + enrolment.getCourse().getTitle() + "\" has " + lessons + " lessons; " + lessonsCompleted + " cannot be completed.");
        }
        enrolment.recordProgress(lessonsCompleted, LocalDate.now(clock));   // a managed entity: saved at commit
        return EnrolmentView.of(enrolment);
    }

    @Transactional
    void unenrol(long enrolmentId) {
        Enrolment enrolment = enrolments.findById(enrolmentId)
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Enrolment not found", "No enrolment " + enrolmentId + "."));
        if (enrolment.getCompletedOn() != null) {
            throw problem(HttpStatus.CONFLICT, "Course completed", "A completed course stays on the student's record.");
        }
        enrolments.delete(enrolment);   // one row: the join entity is deleted on its own, nothing else is rewritten
    }

    @Transactional(readOnly = true)
    List<RosterLine> roster(long courseId) {
        if (!courses.existsById(courseId)) {
            throw problem(HttpStatus.NOT_FOUND, "Course not found", "No course " + courseId + ".");
        }
        return enrolments.findByCourseIdOrderByLessonsCompletedDescStudentNameAsc(courseId).stream()
                .map(e -> new RosterLine(e.getStudent().getId(), e.getStudent().getName(), e.getLessonsCompleted(),
                        e.getLessonsCompleted() * 100 / e.getCourse().getLessonCount(), e.getCompletedOn()))
                .toList();
    }

    @Transactional(readOnly = true)
    List<EnrolmentView> coursesOf(long studentId) {
        if (!students.existsById(studentId)) {
            throw problem(HttpStatus.NOT_FOUND, "Student not found", "No student " + studentId + ".");
        }
        return enrolments.findByStudentIdOrderByEnrolledOnAscIdAsc(studentId).stream().map(EnrolmentView::of).toList();
    }

    private static ErrorResponseException alreadyEnrolled(long studentId, long courseId) {
        return problem(HttpStatus.CONFLICT, "Already enrolled", "Student " + studentId + " is already enrolled in course " + courseId + ".");
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
