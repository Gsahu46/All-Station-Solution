package com.fitnest.classes;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, and no bookings at the start of each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    ClassSchedule schedule;

    @BeforeEach
    void noBookings() {
        schedule.clearBookings();
    }

    ResultActions book(long classId, long memberId) throws Exception {
        return mvc.perform(post("/classes/{id}/bookings", classId)
                .contentType(MediaType.APPLICATION_JSON).content("{\"memberId\":" + memberId + "}"));
    }

    String bookAndGetLocation(long classId, long memberId) throws Exception {
        return book(classId, memberId).andReturn().getResponse().getHeader("Location");
    }
}
