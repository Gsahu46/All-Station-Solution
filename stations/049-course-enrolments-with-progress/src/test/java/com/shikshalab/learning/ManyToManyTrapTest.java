package com.shikshalab.learning;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: the old @ManyToMany, on the table the business now needs. It can only
 * write the two ids, and it treats the link as a list of courses, not as rows with data of their own.
 */
class ManyToManyTrapTest extends ApiTest {

    @Autowired
    EntityManager entities;
    @Autowired
    TransactionTemplate transaction;

    @Test
    void manyToManyCannotWriteTheDateOrTheProgress() {
        // Asha enrols in Git basics the old way: add the course to her list.
        assertThatThrownBy(() -> transaction.executeWithoutResult(status ->
                entities.find(OldStudent.class, 1L).courses.add(entities.find(Course.class, 3L))))
                .hasMessageContaining("violates not-null constraint");   // course_lessons, enrolled_on: the mapping has no value for them
        assertThat(jdbc.sql("SELECT count(*) FROM enrolments").query(Long.class).single()).isZero();
    }

    @Test
    void itSeesTheCoursesButNotHowFarSheGot() throws Exception {
        enrol(1, 1).andExpect(status().isCreated());
        progress(1, "{\"lessonsCompleted\":12}").andExpect(status().isOk());
        List<String> titles = transaction.execute(status -> entities.find(OldStudent.class, 1L).courses.stream().map(Course::getTitle).toList());
        assertThat(titles).containsExactly("Spring Boot from zero");   // and nothing else: 12 of 40 lessons is in the row, not in the model
        assertThat(jdbc.sql("SELECT lessons_completed FROM enrolments WHERE student_id = 1").query(Integer.class).single()).isEqualTo(12);
    }

    @Test
    void droppingOneCourseRewritesTheWholeList() throws Exception {
        enrol(1, 1);
        enrol(2, 1);
        progress(2, "{\"lessonsCompleted\":10}");
        // With a List (a "bag"), Hibernate cannot delete one row: it deletes all of Asha's rows and re-inserts the rest.
        // The re-insert has no date, lesson count or progress, so it fails, and she cannot drop a course at all.
        assertThatThrownBy(() -> transaction.executeWithoutResult(status ->
                entities.find(OldStudent.class, 1L).courses.removeIf(c -> c.getId() == 1L)))
                .hasMessageContaining("violates not-null constraint");
        assertThat(jdbc.sql("SELECT lessons_completed FROM enrolments WHERE course_id = 2").query(Integer.class).single()).isEqualTo(10);
    }
}
