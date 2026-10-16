package com.taskloom.webinars;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app with its Clock replaced by a fixed one. "Now" is 16 Oct 2026, 06:00 UTC (11:30 in
 * India), in every test, on every machine, in every month of the year.
 */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final Instant NOW = Instant.parse("2026-10-16T06:00:00Z");

    @TestBean
    Clock clock;

    static Clock clock() {
        return Clock.fixed(NOW, ZoneOffset.UTC);
    }

    @Autowired
    MockMvc mvc;

    /** A 60-minute webinar; extra is appended inside the JSON object, e.g. ",\"repeat\":\"MONTHLY\"". */
    static String webinar(String startsAt, String zone, String extra) {
        return "{\"title\":\"Planning your first sprint\",\"startsAt\":\"%s\",\"zone\":\"%s\",\"durationMinutes\":60%s}".formatted(startsAt, zone, extra);
    }

    ResultActions create(String body) throws Exception {
        return mvc.perform(post("/webinars").contentType(MediaType.APPLICATION_JSON).content(body));
    }

    /** Creates the webinar and returns its URL (the store is shared by every test, so ids are not predictable). */
    String created(String body) throws Exception {
        return create(body).andReturn().getResponse().getHeader("Location");
    }
}
