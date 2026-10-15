package com.shikshalab.learning;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: DELETE /enrolments/{id} drops a course: 204, and it leaves the student's list while their other
 * courses keep their progress. A completed course is part of the record and cannot be dropped (409). Unknown: 404.
 */
class UnenrolChallengeTest extends ApiTest {

    @Test
    void droppingOneCourseLeavesTheOthersAlone() throws Exception {
        enrol(1, 1);
        enrol(2, 1);
        progress(2, "{\"lessonsCompleted\":10}");
        mvc.perform(delete("/enrolments/1")).andExpect(status().isNoContent());
        mvc.perform(get("/students/1/courses")).andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].courseId").value(2)).andExpect(jsonPath("$[0].lessonsCompleted").value(10));
        enrol(1, 1).andExpect(status().isCreated());   // and she can enrol again later, from zero
    }

    @Test
    void completedOrUnknownEnrolmentsStay() throws Exception {
        enrol(3, 1);
        progress(1, "{\"lessonsCompleted\":8}");
        mvc.perform(delete("/enrolments/1")).andExpect(status().isConflict());
        mvc.perform(delete("/enrolments/99")).andExpect(status().isNotFound());
    }
}
