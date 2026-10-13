package com.seatsure.registrations;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.concurrent.atomic.AtomicInteger;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app, called through MockMvc. No server port and no network: requests go straight to Spring MVC. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    private static final AtomicInteger NEXT = new AtomicInteger();

    /** Asha's registration, with a new email each time, so tests never depend on each other (or on a duplicate rule). */
    static String asha() {
        return """
                {"name":"Asha Kulkarni","email":"asha.%d@example.com","phone":"9876543210","tickets":2}
                """.formatted(NEXT.incrementAndGet());
    }

    @Autowired
    MockMvc mvc;

    @Autowired
    RegistrationStore store;

    ResultActions register(String eventId, String json) throws Exception {
        return mvc.perform(post("/events/{eventId}/registrations", eventId).contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
