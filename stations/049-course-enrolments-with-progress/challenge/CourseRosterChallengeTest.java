package com.shikshalab.learning;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /courses/{id}/students lists who is enrolled, from the other side of the link: studentId, name,
 * lessonsCompleted, progressPercent, completedOn, furthest along first, then by name. Unknown course: 404.
 */
class CourseRosterChallengeTest extends ApiTest {

    @Test
    void theRosterIsReadThroughTheJoinEntity() throws Exception {
        enrol(2, 1);
        enrol(2, 2);
        progress(2, "{\"lessonsCompleted\":24}");
        progress(1, "{\"lessonsCompleted\":6}");
        mvc.perform(get("/courses/2/students")).andExpect(status().isOk()).andExpect(content().json("""
                [{"studentId":2,"name":"Rahul Menon","lessonsCompleted":24,"progressPercent":100,"completedOn":"%s"},
                 {"studentId":1,"name":"Asha Verma","lessonsCompleted":6,"progressPercent":25,"completedOn":null}]""".formatted(today()), true));
        mvc.perform(get("/courses/3/students")).andExpect(content().json("[]"));
        mvc.perform(get("/courses/99/students")).andExpect(status().isNotFound());
    }
}
