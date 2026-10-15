package com.ghoomo.bookings;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.LocalDate;
import java.time.ZoneId;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app through MockMvc. Dates are relative to today in India, so the tests never go stale.
 * Ghoomo Inn, Jaipur (hotel 1): STANDARD sleeps 2, DELUXE 3, FAMILY 4.
 */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    static LocalDate today() {
        return LocalDate.now(ZoneId.of("Asia/Kolkata"));
    }

    static String day(int fromToday) {
        return today().plusDays(fromToday).toString();
    }

    /** A valid request: 2 adults in a STANDARD room, 3 nights starting in 30 days. Tests change one thing at a time. */
    static String booking() {
        return """
                {"hotelId":1,"roomType":"STANDARD","checkIn":"%s","checkOut":"%s","adults":2,"children":0,
                 "guestName":"Asha Verma","phone":"98765 43210"}""".formatted(day(30), day(33));
    }

    ResultActions book(String body) throws Exception {
        return mvc.perform(post("/hotel-bookings").contentType(MediaType.APPLICATION_JSON).content(body));
    }
}
