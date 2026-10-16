package com.tijori.notifications;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

/**
 * Shared setup: the whole app, today fixed at 16 Oct 2026 in India, an empty outbox and default preferences before
 * each test. Asha (1) has a phone, an email and the app; Rohan (2) has only a phone, and push turned off.
 */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    /** The characters used here that fit GSM-7, the alphabet a 160-character SMS part is counted in. */
    static final String GSM7_SUBSET = "[A-Za-z0-9 @$!\"#%&'()*+,\\-./:;<=>?\\n]*";

    @TestBean
    Clock clock;

    static Clock clock() {
        return Clock.fixed(Instant.parse("2026-10-16T06:00:00Z"), ZoneId.of("Asia/Kolkata"));
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    Outbox outbox;
    @Autowired
    Customers customers;

    @BeforeEach
    void freshDay() {
        outbox.clear();
        customers.reset();
    }

    ResultActions notify(String body) throws Exception {
        return mvc.perform(post("/notifications").contentType(MediaType.APPLICATION_JSON).content(body));
    }

    static String debit(long customer, long paise) {
        return "{\"customerId\":%d,\"type\":\"DEBIT_ALERT\",\"amountPaise\":%d,\"merchant\":\"BigBasket\"}".formatted(customer, paise);
    }

    /** A JSON path to one channel's status, so tests do not depend on how many channels exist. */
    static String statusOf(String channel) {
        return "$.deliveries[?(@.channel=='" + channel + "')].status";
    }

    ResultActions preferences(long customer, String body) throws Exception {
        return mvc.perform(put("/customers/{id}/notification-preferences", customer).contentType(MediaType.APPLICATION_JSON).content(body));
    }
}
