package com.tijori.loans;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, and "today" fixed at 19 Oct 2026 so the rate a test gets never changes. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(ApiTest.FixedToday.class)
abstract class ApiTest {

    @TestConfiguration
    static class FixedToday {
        @Bean
        @Primary
        Clock fixedClock() {
            return Clock.fixed(Instant.parse("2026-10-19T04:30:00Z"), ZoneId.of("Asia/Kolkata"));
        }
    }

    @Autowired
    MockMvc mvc;

    ResultActions quote(String product, long principalPaise, int months) throws Exception {
        return mvc.perform(post("/loan-quotes").contentType(MediaType.APPLICATION_JSON).content(
                "{\"product\":\"" + product + "\",\"principalPaise\":" + principalPaise + ",\"tenureMonths\":" + months + "}"));
    }
}
