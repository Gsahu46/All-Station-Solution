package com.shikshalab.learning;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: enrol, record progress, list a student's courses; valid, invalid and not found. */
class EnrolmentContractTest extends ApiTest {

    @Test
    void anEnrolmentStartsTodayAtZero() throws Exception {
        enrol(1, 1).andExpect(status().isCreated()).andExpect(header().string("Location", "/enrolments/1"))
                .andExpect(content().json("""
                        {"id":1,"studentId":1,"courseId":1,"courseTitle":"Spring Boot from zero","enrolledOn":"%s",
                         "lessonsCompleted":0,"lessonCount":40,"progressPercent":0,"completedOn":null}""".formatted(today())));
    }

    @Test
    void progressIsKeptPerStudentAndCourse() throws Exception {
        enrol(1, 1);
        enrol(1, 2);
        progress(1, "{\"lessonsCompleted\":12}").andExpect(status().isOk()).andExpect(jsonPath("$.progressPercent").value(30));
        mvc.perform(get("/students/1/courses")).andExpect(jsonPath("$[0].lessonsCompleted").value(12));
        mvc.perform(get("/students/2/courses")).andExpect(jsonPath("$[0].lessonsCompleted").value(0));   // Rahul's own row
    }

    @Test
    void theLastLessonCompletesTheCourseAndUndoingItReopens() throws Exception {
        enrol(3, 1);
        progress(1, "{\"lessonsCompleted\":8}").andExpect(jsonPath("$.progressPercent").value(100)).andExpect(jsonPath("$.completedOn").value(today()));
        progress(1, "{\"lessonsCompleted\":7}").andExpect(jsonPath("$.completedOn").doesNotExist());
    }

    @Test
    void aStudentsCoursesComeInEnrolmentOrder() throws Exception {
        enrol(2, 1);
        enrol(3, 1);
        enrol(1, 2);
        mvc.perform(get("/students/1/courses")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].courseTitle", contains("SQL for analysts", "Git basics")));
        mvc.perform(get("/students/2/courses")).andExpect(jsonPath("$[*].courseId", contains(1)));
    }

    @Test
    void enrollingTwiceIs409() throws Exception {
        enrol(1, 1).andExpect(status().isCreated());
        enrol(1, 1).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already enrolled"));
    }

    @Test
    void badRequestsAre400Or422() throws Exception {
        enrol(1, 1);
        mvc.perform(post("/courses/1/enrolments").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
        progress(1, "{\"lessonsCompleted\":-1}").andExpect(status().isBadRequest());
        progress(1, "{}").andExpect(status().isBadRequest());
        progress(1, "{\"lessonsCompleted\":\"twelve\"}").andExpect(status().isBadRequest());
        progress(1, "{\"lessonsCompleted\":41}").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Beyond the course"));
        enrol(1, 99).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown student"));
    }

    @Test
    void unknownCoursesEnrolmentsAndStudentsAre404() throws Exception {
        enrol(99, 1).andExpect(status().isNotFound());
        progress(99, "{\"lessonsCompleted\":1}").andExpect(status().isNotFound());
        mvc.perform(get("/students/99/courses")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No student 99."));
    }
}
