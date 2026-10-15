package com.shikshalab.learning;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The join table's rules with Java bypassed, a rollback, and the same enrolment requested at once. */
class EnrolmentDatabaseTest extends ApiTest {

    void insert(long student, long course, int lessons, int done, String completedOn) {
        jdbc.sql("INSERT INTO enrolments (student_id, course_id, course_lessons, enrolled_on, lessons_completed, completed_on) VALUES (?, ?, ?, DATE '2026-10-01', ?, ?::date)")
                .params(student, course, lessons, done, completedOn).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        insert(1, 3, 8, 0, null);
        assertThatThrownBy(() -> insert(1, 3, 8, 0, null)).hasMessageContaining("enrolments_student_course_unique");
        assertThatThrownBy(() -> insert(99, 3, 8, 0, null)).hasMessageContaining("enrolments_student_fk");
        assertThatThrownBy(() -> insert(2, 3, 9, 0, null)).hasMessageContaining("enrolments_course_fk");   // Git basics has 8 lessons, not 9
        assertThatThrownBy(() -> insert(2, 3, 8, 9, null)).hasMessageContaining("enrolments_progress_range");
        assertThatThrownBy(() -> insert(2, 3, 8, 8, null)).hasMessageContaining("enrolments_completed_when_done");
        assertThatThrownBy(() -> insert(2, 3, 8, 5, "2026-10-02")).hasMessageContaining("enrolments_completed_when_done");
        assertThatThrownBy(() -> jdbc.sql("UPDATE courses SET lesson_count = 0 WHERE id = 3").update()).hasMessageContaining("courses_lesson_count_range");
    }

    @Test
    void shrinkingACourseBelowSomeonesProgressIsRefusedWhole() {
        insert(1, 3, 8, 6, null);
        // ON UPDATE CASCADE carries the new count into Asha's row, where 6 of 5 breaks the progress check: nothing changes.
        assertThatThrownBy(() -> jdbc.sql("UPDATE courses SET lesson_count = 5 WHERE id = 3").update()).hasMessageContaining("enrolments_progress_range");
        assertThat(jdbc.sql("SELECT lesson_count FROM courses WHERE id = 3").query(Integer.class).single()).isEqualTo(8);
        jdbc.sql("UPDATE courses SET lesson_count = 10 WHERE id = 3").update();   // growing is fine, and follows into the row
        assertThat(jdbc.sql("SELECT course_lessons FROM enrolments WHERE course_id = 3").query(Integer.class).single()).isEqualTo(10);
        jdbc.sql("UPDATE courses SET lesson_count = 8 WHERE id = 3").update();
    }

    @Test
    void thirtyClicksOnEnrolMakeOneEnrolment() throws Exception {
        List<Integer> statuses = together(30, () -> enrol(1, 1).andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 201).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(29);
        assertThat(jdbc.sql("SELECT count(*) FROM enrolments").query(Long.class).single()).isEqualTo(1);
    }
}
